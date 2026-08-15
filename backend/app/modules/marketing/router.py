from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.modules.identity.models import Staff
from app.modules.identity.router import require_permission
from app.modules.marketing.models import PromoCode
from app.modules.marketing.schemas import PromoCodeCreate

router = APIRouter(prefix="/api/v1", tags=["marketing"])
Editor = Annotated[Staff, Depends(require_permission("marketing.manage"))]
Session = Annotated[AsyncSession, Depends(get_session)]


@router.post("/promo-codes", status_code=201)
async def create_promo_code(payload: PromoCodeCreate, _: Editor, session: Session) -> dict[str, str]:
    if payload.discount_type == "percent" and payload.discount_value > 100:
        raise HTTPException(status_code=422, detail="percent_discount_too_large")
    if payload.starts_at and payload.ends_at and payload.starts_at >= payload.ends_at:
        raise HTTPException(status_code=422, detail="promo_period_invalid")
    promo = PromoCode(**payload.model_dump(exclude={"code"}), code=payload.code.upper())
    session.add(promo)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(status_code=409, detail="promo_code_already_exists") from None
    return {"id": str(promo.id), "code": promo.code}
