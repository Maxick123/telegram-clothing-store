from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.config import get_settings
from app.core.db import Base, SessionFactory, engine
from app.modules.identity.router import router as identity_router
from app.modules.identity.service import seed_identity
from app.modules.catalog.router import router as catalog_router
from app.modules.commerce.router import router as commerce_router
from app.modules.marketing.router import router as marketing_router
from app.modules.payments.router import router as payments_router
from app.modules.messaging.router import router as messaging_router


@asynccontextmanager
async def lifespan(_: FastAPI):
    if get_settings().auto_create_schema:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
    async with SessionFactory() as session:
        await seed_identity(session)
    yield

app = FastAPI(title="Clothing Store API", version="0.1.0", lifespan=lifespan)
app.include_router(identity_router)
app.include_router(catalog_router)
app.include_router(commerce_router)
app.include_router(marketing_router)
app.include_router(payments_router)
app.include_router(messaging_router)


@app.get("/health", tags=["system"])
async def health() -> dict[str, str]:
    return {"status": "ok"}
