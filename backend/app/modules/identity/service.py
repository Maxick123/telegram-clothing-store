from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security import hash_password, hash_refresh_token, new_refresh_token, verify_password
from app.modules.identity.models import Permission, RefreshSession, Role, Staff

ALL_PERMISSIONS = {"staff.read", "staff.manage", "products.read", "products.manage", "orders.read", "orders.update_status", "customers.read", "conversations.read", "conversations.reply"}
ROLE_PERMISSIONS = {
    "Administrator": ALL_PERMISSIONS,
    "OrdersManager": {"orders.read", "orders.update_status", "customers.read", "conversations.read", "conversations.reply"},
    "SupportOperator": {"customers.read", "conversations.read", "conversations.reply"},
    "ContentManager": {"products.read", "products.manage"},
}


async def authenticate(session: AsyncSession, login: str, password: str) -> Staff | None:
    staff = await session.scalar(select(Staff).where(Staff.login == login, Staff.is_active.is_(True)))
    if staff is None or not verify_password(password, staff.password_hash):
        return None
    return staff


async def issue_refresh_session(session: AsyncSession, staff: Staff) -> str:
    raw, token_hash = new_refresh_token()
    session.add(RefreshSession(staff_id=staff.id, token_hash=token_hash, expires_at=datetime.now(UTC) + timedelta(days=get_settings().refresh_token_days)))
    await session.commit()
    return raw


async def rotate_refresh_session(session: AsyncSession, raw_token: str) -> tuple[Staff, str] | None:
    token_hash = hash_refresh_token(raw_token)
    refresh = await session.scalar(select(RefreshSession).where(RefreshSession.token_hash == token_hash, RefreshSession.revoked_at.is_(None)))
    if refresh is None or refresh.expires_at <= datetime.now(UTC):
        return None
    refresh.revoked_at = datetime.now(UTC)
    staff = await session.get(Staff, refresh.staff_id)
    if staff is None or not staff.is_active:
        await session.commit()
        return None
    return staff, await issue_refresh_session(session, staff)


async def seed_identity(session: AsyncSession) -> None:
    permissions: dict[str, Permission] = {}
    for code in sorted(ALL_PERMISSIONS):
        item = await session.scalar(select(Permission).where(Permission.code == code))
        if item is None:
            item = Permission(code=code)
            session.add(item)
        permissions[code] = item
    await session.flush()

    roles: dict[str, Role] = {}
    for name, codes in ROLE_PERMISSIONS.items():
        role = await session.scalar(select(Role).where(Role.name == name))
        if role is None:
            role = Role(name=name, permissions=[permissions[code] for code in sorted(codes)])
            session.add(role)
        roles[name] = role
    await session.flush()

    settings = get_settings()
    bootstrap = [
        (settings.bootstrap_admin_login, settings.bootstrap_admin_password, "Administrator", "Администратор"),
        (settings.bootstrap_support_login, settings.bootstrap_support_password, "SupportOperator", "Оператор поддержки"),
    ]
    for login, password, role_name, display_name in bootstrap:
        if password and await session.scalar(select(Staff).where(Staff.login == login)) is None:
            session.add(Staff(login=login, password_hash=hash_password(password), display_name=display_name, roles=[roles[role_name]]))
    await session.commit()
