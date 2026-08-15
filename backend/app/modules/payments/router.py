from typing import Annotated
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.db import get_session
from app.modules.commerce.models import Order
from app.modules.commerce.router import customer_from_telegram
from app.modules.customers.models import Customer
from app.modules.payments.models import Payment
from app.modules.payments.yookassa_provider import create_redirect_payment

router = APIRouter(prefix="/api/v1", tags=["payments"])
Session = Annotated[AsyncSession, Depends(get_session)]


@router.post("/orders/{order_id}/payments/yookassa", status_code=201)
async def create_yookassa_payment(order_id: UUID, session: Session, customer: Annotated[Customer, Depends(customer_from_telegram)]) -> dict[str, str]:
    order = await session.scalar(select(Order).where(Order.id == order_id, Order.customer_id == customer.id).with_for_update())
    if order is None:
        raise HTTPException(status_code=404, detail="order_not_found")
    if order.status_code != "awaiting_payment":
        raise HTTPException(status_code=409, detail="order_not_payable")
    existing = await session.scalar(select(Payment).where(Payment.order_id == order.id))
    if existing and existing.confirmation_url:
        return {"payment_id": str(existing.id), "confirmation_url": existing.confirmation_url}
    try:
        remote = await create_redirect_payment(str(order.id), order.total_kopecks)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    payment = existing or Payment(order_id=order.id)
    payment.external_id = str(remote["id"])
    payment.status = str(remote.get("status", "pending"))
    confirmation = remote.get("confirmation") or {}
    payment.confirmation_url = str(confirmation.get("confirmation_url", "")) or None
    session.add(payment)
    await session.commit()
    if not payment.confirmation_url:
        raise HTTPException(status_code=502, detail="yookassa_confirmation_missing")
    return {"payment_id": str(payment.id), "confirmation_url": payment.confirmation_url}
