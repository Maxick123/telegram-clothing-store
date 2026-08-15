from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.modules.catalog.models import Category, Product, ProductVariant
from app.modules.catalog.schemas import CategoryCreate, ProductCreate, VariantCreate
from app.modules.identity.models import Staff
from app.modules.identity.router import require_permission

router = APIRouter(prefix="/api/v1", tags=["catalog"])
Editor = Annotated[Staff, Depends(require_permission("products.manage"))]
Session = Annotated[AsyncSession, Depends(get_session)]


async def commit_unique(session: AsyncSession, detail: str) -> None:
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(status_code=409, detail=detail) from None


@router.post("/categories", status_code=201)
async def create_category(payload: CategoryCreate, _: Editor, session: Session) -> dict[str, object]:
    category = Category(**payload.model_dump())
    session.add(category)
    await commit_unique(session, "category_already_exists")
    return {"id": category.id, "name": category.name, "slug": category.slug}


@router.post("/products", status_code=201)
async def create_product(payload: ProductCreate, _: Editor, session: Session) -> dict[str, object]:
    if await session.get(Category, payload.category_id) is None:
        raise HTTPException(status_code=404, detail="category_not_found")
    product = Product(**payload.model_dump())
    session.add(product)
    await commit_unique(session, "product_already_exists")
    return {"id": product.id, "name": product.name, "slug": product.slug, "sku": product.sku}


@router.post("/products/{product_id}/variants", status_code=201)
async def create_variant(product_id: UUID, payload: VariantCreate, _: Editor, session: Session) -> dict[str, object]:
    if await session.get(Product, product_id) is None:
        raise HTTPException(status_code=404, detail="product_not_found")
    variant = ProductVariant(product_id=product_id, **payload.model_dump())
    session.add(variant)
    await commit_unique(session, "variant_already_exists")
    return {"id": variant.id, "sku": variant.sku, "color": variant.color, "size": variant.size, "available_quantity": variant.available_quantity}
