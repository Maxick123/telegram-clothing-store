from datetime import UTC, datetime
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.marketing.models import PromoCode, PromoRedemption


async def apply_promo_code(session: AsyncSession, raw_code: str | None, customer_id: UUID, order_id: UUID, subtotal_kopecks: int) -> int:
    if not raw_code:
        return 0
    now = datetime.now(UTC)
    promo = await session.scalar(select(PromoCode).where(PromoCode.code == raw_code.strip().upper()).with_for_update())
    if promo is None:
        raise HTTPException(status_code=404, detail="promo_not_found")
    if not promo.is_active or (promo.starts_at is not None and promo.starts_at > now) or (promo.ends_at is not None and promo.ends_at < now):
        raise HTTPException(status_code=409, detail="promo_inactive")
    if subtotal_kopecks < promo.minimum_order_kopecks:
        raise HTTPException(status_code=409, detail="promo_minimum_not_met")
    total_uses = await session.scalar(select(func.count()).select_from(PromoRedemption).where(PromoRedemption.promo_code_id == promo.id))
    if promo.max_uses is not None and total_uses >= promo.max_uses:
        raise HTTPException(status_code=409, detail="promo_usage_limit")
    customer_uses = await session.scalar(select(func.count()).select_from(PromoRedemption).where(PromoRedemption.promo_code_id == promo.id, PromoRedemption.customer_id == customer_id))
    if promo.per_customer_limit is not None and customer_uses >= promo.per_customer_limit:
        raise HTTPException(status_code=409, detail="promo_customer_limit")
    if promo.discount_type == "percent":
        discount = subtotal_kopecks * promo.discount_value // 100
    else:
        discount = promo.discount_value
    discount = min(discount, subtotal_kopecks)
    session.add(PromoRedemption(promo_code_id=promo.id, customer_id=customer_id, order_id=order_id, discount_kopecks=discount))
    return discount
