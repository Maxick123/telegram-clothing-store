from datetime import UTC, datetime, timedelta

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.db import SessionFactory
from app.modules.catalog.models import Product, ProductVariant
from app.modules.commerce.models import Cart, CartItem, Order, OrderItem, StockReservation
from app.modules.commerce.schemas import CheckoutCreate
from app.modules.customers.models import Customer
from app.modules.marketing.service import apply_promo_code


async def checkout_cart(session: AsyncSession, customer: Customer, payload: CheckoutCreate) -> tuple[Order, list[OrderItem]]:
    cart = await session.scalar(
        select(Cart).where(Cart.id == payload.cart_id, Cart.customer_id == customer.id, Cart.status == "active").with_for_update()
    )
    if cart is None:
        raise HTTPException(status_code=404, detail="active_cart_not_found")
    cart_items = (await session.scalars(select(CartItem).where(CartItem.cart_id == cart.id).order_by(CartItem.id))).all()
    if not cart_items:
        raise HTTPException(status_code=409, detail="cart_is_empty")

    now = datetime.now(UTC)
    expires_at = now + timedelta(minutes=get_settings().stock_reservation_minutes)
    order = Order(
        customer_id=customer.id,
        cart_id=cart.id,
        recipient_first_name=payload.recipient_first_name,
        recipient_last_name=payload.recipient_last_name,
        phone=payload.phone,
        delivery_method=payload.delivery_method,
        delivery_cost_kopecks=payload.delivery_cost_kopecks,
        subtotal_kopecks=0,
        total_kopecks=0,
        reservation_expires_at=expires_at,
    )
    session.add(order)
    await session.flush()

    order_items: list[OrderItem] = []
    subtotal = 0
    for cart_item in cart_items:
        variant = await session.scalar(select(ProductVariant).where(ProductVariant.id == cart_item.variant_id).with_for_update())
        if variant is None or not variant.is_active or variant.available_quantity < cart_item.quantity:
            raise HTTPException(status_code=409, detail="insufficient_stock")
        product = await session.get(Product, variant.product_id)
        if product is None or product.is_archived:
            raise HTTPException(status_code=409, detail="product_not_available")
        variant.stock_reserved += cart_item.quantity
        order_item = OrderItem(
            order_id=order.id,
            variant_id=variant.id,
            product_name=product.name,
            product_sku=product.sku,
            variant_sku=variant.sku,
            color=variant.color,
            size=variant.size,
            quantity=cart_item.quantity,
            unit_price_kopecks=variant.price_kopecks,
        )
        session.add(order_item)
        session.add(StockReservation(order_id=order.id, variant_id=variant.id, quantity=cart_item.quantity, expires_at=expires_at))
        order_items.append(order_item)
        subtotal += cart_item.quantity * variant.price_kopecks

    discount_kopecks = await apply_promo_code(session, payload.promo_code, customer.id, order.id, subtotal)
    order.subtotal_kopecks = subtotal
    order.discount_kopecks = discount_kopecks
    order.total_kopecks = subtotal - discount_kopecks + payload.delivery_cost_kopecks
    customer.first_name = payload.recipient_first_name
    customer.last_name = payload.recipient_last_name
    customer.phone = payload.phone
    cart.status = "checked_out"
    await session.commit()
    return order, order_items


async def release_expired_reservations(now: datetime | None = None) -> int:
    release_time = now or datetime.now(UTC)
    async with SessionFactory() as session:
        reservations = (
            await session.scalars(
                select(StockReservation)
                .where(StockReservation.released_at.is_(None), StockReservation.expires_at <= release_time)
                .order_by(StockReservation.id)
                .with_for_update()
            )
        ).all()
        released = 0
        for reservation in reservations:
            order = await session.scalar(select(Order).where(Order.id == reservation.order_id).with_for_update())
            if order is None or order.status_code != "awaiting_payment":
                continue
            variant = await session.scalar(select(ProductVariant).where(ProductVariant.id == reservation.variant_id).with_for_update())
            if variant is None or variant.stock_reserved < reservation.quantity:
                raise RuntimeError("reservation_stock_inconsistent")
            variant.stock_reserved -= reservation.quantity
            reservation.released_at = release_time
            order.status_code = "payment_expired"
            released += 1
        await session.commit()
    return released
