from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.modules.catalog.models import Product, ProductVariant
from app.modules.commerce.models import Cart, CartItem
from app.modules.commerce.schemas import CartItemCreate
from app.modules.customers.models import Customer, Favorite

router = APIRouter(prefix="/api/v1", tags=["commerce"])
Session = Annotated[AsyncSession, Depends(get_session)]


async def customer_from_telegram(session: Session, telegram_id: Annotated[int, Header(alias="X-Telegram-ID")]) -> Customer:
    customer = await session.scalar(select(Customer).where(Customer.telegram_id == telegram_id))
    if customer is None:
        customer = Customer(telegram_id=telegram_id)
        session.add(customer)
        await session.flush()
    return customer


async def active_cart(session: AsyncSession, customer: Customer) -> Cart:
    cart = await session.scalar(select(Cart).where(Cart.customer_id == customer.id, Cart.status == "active"))
    if cart is None:
        cart = Cart(customer_id=customer.id)
        session.add(cart)
        await session.flush()
    return cart


@router.post("/carts/items", status_code=201)
async def add_cart_item(payload: CartItemCreate, session: Session, customer: Annotated[Customer, Depends(customer_from_telegram)]) -> dict[str, int | str]:
    variant = await session.get(ProductVariant, payload.variant_id)
    if variant is None or not variant.is_active:
        raise HTTPException(status_code=404, detail="variant_not_found")
    if variant.available_quantity < payload.quantity:
        raise HTTPException(status_code=409, detail="insufficient_stock")
    cart = await active_cart(session, customer)
    item = await session.scalar(select(CartItem).where(CartItem.cart_id == cart.id, CartItem.variant_id == variant.id))
    new_quantity = payload.quantity if item is None else item.quantity + payload.quantity
    if variant.available_quantity < new_quantity:
        raise HTTPException(status_code=409, detail="insufficient_stock")
    if item is None:
        session.add(CartItem(cart_id=cart.id, variant_id=variant.id, quantity=payload.quantity))
    else:
        item.quantity = new_quantity
    await session.commit()
    subtotal = 0
    rows = (await session.execute(select(CartItem, ProductVariant).join(ProductVariant, CartItem.variant_id == ProductVariant.id).where(CartItem.cart_id == cart.id))).all()
    for row_item, row_variant in rows:
        subtotal += row_item.quantity * row_variant.price_kopecks
    return {"cart_id": str(cart.id), "subtotal_kopecks": subtotal}


@router.post("/favorites/{product_id}", status_code=201)
async def add_favorite(product_id: UUID, session: Session, customer: Annotated[Customer, Depends(customer_from_telegram)]) -> dict[str, str]:
    product = await session.get(Product, product_id)
    if product is None or product.is_archived:
        raise HTTPException(status_code=404, detail="product_not_found")
    session.add(Favorite(customer_id=customer.id, product_id=product.id))
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(status_code=409, detail="already_favorite") from None
    return {"product_id": str(product.id)}
