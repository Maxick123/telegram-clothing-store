from typing import Annotated

import jwt
from fastapi import APIRouter, Cookie, Depends, HTTPException, Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.db import get_session
from app.core.security import create_access_token, decode_access_token
from app.modules.identity.models import Staff
from app.modules.identity.schemas import LoginRequest, StaffResponse, TokenResponse
from app.modules.identity.service import authenticate, issue_refresh_session, rotate_refresh_session

router = APIRouter(prefix="/api/v1")
bearer = HTTPBearer(auto_error=False)


async def current_staff(credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)], session: Annotated[AsyncSession, Depends(get_session)]) -> Staff:
    if credentials is None:
        raise HTTPException(status_code=401, detail="not_authenticated")
    try:
        staff_id = decode_access_token(credentials.credentials)
    except (jwt.InvalidTokenError, ValueError):
        raise HTTPException(status_code=401, detail="invalid_token") from None
    staff = await session.get(Staff, staff_id)
    if staff is None or not staff.is_active:
        raise HTTPException(status_code=401, detail="invalid_token")
    return staff


def require_permission(permission: str):
    async def dependency(staff: Annotated[Staff, Depends(current_staff)]) -> Staff:
        if permission not in staff.permission_codes:
            raise HTTPException(status_code=403, detail="permission_denied")
        return staff
    return dependency


@router.post("/auth/login", response_model=TokenResponse)
async def login(payload: LoginRequest, response: Response, session: Annotated[AsyncSession, Depends(get_session)]) -> TokenResponse:
    staff = await authenticate(session, payload.login, payload.password)
    if staff is None:
        raise HTTPException(status_code=401, detail="invalid_credentials")
    refresh_token = await issue_refresh_session(session, staff)
    response.set_cookie("refresh_token", refresh_token, httponly=True, samesite="strict", secure=get_settings().cookie_secure, max_age=get_settings().refresh_token_days * 86400, path="/api/v1/auth")
    return TokenResponse(access_token=create_access_token(staff.id))


@router.post("/auth/refresh", response_model=TokenResponse)
async def refresh(
    response: Response,
    session: Annotated[AsyncSession, Depends(get_session)],
    refresh_token: Annotated[str | None, Cookie()] = None,
) -> TokenResponse:
    if not refresh_token:
        raise HTTPException(status_code=401, detail="invalid_refresh_token")
    rotated = await rotate_refresh_session(session, refresh_token)
    if rotated is None:
        raise HTTPException(status_code=401, detail="invalid_refresh_token")
    staff, new_token = rotated
    response.set_cookie("refresh_token", new_token, httponly=True, samesite="strict", secure=get_settings().cookie_secure, max_age=get_settings().refresh_token_days * 86400, path="/api/v1/auth")
    return TokenResponse(access_token=create_access_token(staff.id))


@router.get("/auth/me", response_model=StaffResponse)
async def me(staff: Annotated[Staff, Depends(current_staff)]) -> StaffResponse:
    return StaffResponse(id=staff.id, login=staff.login, display_name=staff.display_name, permissions=sorted(staff.permission_codes))


@router.get("/staff", response_model=list[StaffResponse])
async def list_staff(_: Annotated[Staff, Depends(require_permission("staff.read"))], session: Annotated[AsyncSession, Depends(get_session)]) -> list[StaffResponse]:
    rows = (await session.scalars(select(Staff).order_by(Staff.login))).all()
    return [StaffResponse(id=row.id, login=row.login, display_name=row.display_name, permissions=sorted(row.permission_codes)) for row in rows]
