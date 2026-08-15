from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, update

from app.core.db import SessionFactory
from app.modules.catalog.models import ProductVariant
from app.modules.commerce import order_service
from app.modules.commerce.models import Order, StockReservation
from app.main import app


@pytest.fixture
def client() -> TestClient:
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def admin_headers(client: TestClient) -> dict[str, str]:
    response = client.post("/api/v1/auth/login", json={"login": "admin", "password": "correct-password"})
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_checkout_reserves_stock_and_snapshots_variant_price(client: TestClient, admin_headers: dict[str, str]) -> None:
    """Removing the stock reserve or line-price snapshot must make this test fail."""
    suffix = uuid4().hex[:8]
    customer_headers = {"X-Telegram-ID": str(int(suffix, 16))}
    category = client.post("/api/v1/categories", headers=admin_headers, json={"name": "Худи", "slug": f"hoodies-{suffix}"}).json()
    product = client.post(
        "/api/v1/products",
        headers=admin_headers,
        json={"name": "Oversize Hoodie", "slug": f"hoodie-{suffix}", "sku": f"HD-{suffix}", "category_id": category["id"], "price_kopecks": 599000},
    ).json()
    variant = client.post(
        f"/api/v1/products/{product['id']}/variants",
        headers=admin_headers,
        json={"color": "Black", "size": "M", "sku": f"HD-BLK-M-{suffix}", "stock_on_hand": 2, "price_kopecks": 599000},
    ).json()
    cart = client.post("/api/v1/carts/items", headers=customer_headers, json={"variant_id": variant["id"], "quantity": 2}).json()

    response = client.post(
        "/api/v1/checkout",
        headers=customer_headers,
        json={"cart_id": cart["cart_id"], "recipient_first_name": "Максим", "recipient_last_name": "Иванов", "phone": "+79990000000", "delivery_method": "pickup", "delivery_cost_kopecks": 0},
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["status_code"] == "awaiting_payment"
    assert payload["items"] == [{"variant_id": variant["id"], "quantity": 2, "unit_price_kopecks": 599000}]
    assert payload["subtotal_kopecks"] == 1_198_000


def test_checkout_makes_reserved_variant_unavailable_to_next_cart(client: TestClient, admin_headers: dict[str, str]) -> None:
    """Removing the reservation increment must allow this second cart and fail the test."""
    suffix = uuid4().hex[:8]
    customer_headers = {"X-Telegram-ID": str(int(suffix, 16))}
    category = client.post("/api/v1/categories", headers=admin_headers, json={"name": "Куртки", "slug": f"jackets-{suffix}"}).json()
    product = client.post(
        "/api/v1/products",
        headers=admin_headers,
        json={"name": "Jacket", "slug": f"jacket-{suffix}", "sku": f"JK-{suffix}", "category_id": category["id"], "price_kopecks": 890000},
    ).json()
    variant = client.post(
        f"/api/v1/products/{product['id']}/variants",
        headers=admin_headers,
        json={"color": "Black", "size": "L", "sku": f"JK-BLK-L-{suffix}", "stock_on_hand": 1, "price_kopecks": 890000},
    ).json()
    first_cart = client.post("/api/v1/carts/items", headers=customer_headers, json={"variant_id": variant["id"], "quantity": 1}).json()
    created = client.post(
        "/api/v1/checkout",
        headers=customer_headers,
        json={"cart_id": first_cart["cart_id"], "recipient_first_name": "Максим", "recipient_last_name": "Иванов", "phone": "+79990000000", "delivery_method": "pickup", "delivery_cost_kopecks": 0},
    )
    second_add = client.post("/api/v1/carts/items", headers=customer_headers, json={"variant_id": variant["id"], "quantity": 1})

    assert created.status_code == 201
    assert second_add.status_code == 409
    assert second_add.json() == {"detail": "insufficient_stock"}


@pytest.mark.asyncio
async def test_expired_reservation_releases_stock_and_expires_order(client: TestClient, admin_headers: dict[str, str]) -> None:
    """Removing the release transaction must leave both the stock and order in the wrong state."""
    suffix = uuid4().hex[:8]
    customer_headers = {"X-Telegram-ID": str(int(suffix, 16))}
    category = client.post("/api/v1/categories", headers=admin_headers, json={"name": "Обувь", "slug": f"shoes-{suffix}"}).json()
    product = client.post(
        "/api/v1/products",
        headers=admin_headers,
        json={"name": "Sneakers", "slug": f"sneakers-{suffix}", "sku": f"SN-{suffix}", "category_id": category["id"], "price_kopecks": 999000},
    ).json()
    variant = client.post(
        f"/api/v1/products/{product['id']}/variants",
        headers=admin_headers,
        json={"color": "White", "size": "42", "sku": f"SN-WHT-42-{suffix}", "stock_on_hand": 1, "price_kopecks": 999000},
    ).json()
    cart = client.post("/api/v1/carts/items", headers=customer_headers, json={"variant_id": variant["id"], "quantity": 1}).json()
    order = client.post(
        "/api/v1/checkout",
        headers=customer_headers,
        json={"cart_id": cart["cart_id"], "recipient_first_name": "Максим", "recipient_last_name": "Иванов", "phone": "+79990000000", "delivery_method": "pickup", "delivery_cost_kopecks": 0},
    ).json()
    expired_at = datetime.now(UTC) - timedelta(minutes=1)
    async with SessionFactory() as session:
        await session.execute(update(StockReservation).where(StockReservation.order_id == UUID(order["id"])).values(expires_at=expired_at))
        await session.commit()

    release = getattr(order_service, "release_expired_reservations", None)
    released = 0 if release is None else await release(now=expired_at)

    assert released >= 1
    async with SessionFactory() as session:
        saved_variant = await session.get(ProductVariant, UUID(variant["id"]))
        saved_order = await session.get(Order, UUID(order["id"]))
        saved_reservation = await session.scalar(select(StockReservation).where(StockReservation.order_id == UUID(order["id"])))
    assert saved_variant is not None and saved_variant.stock_reserved == 0
    assert saved_order is not None and saved_order.status_code == "payment_expired"
    assert saved_reservation is not None and saved_reservation.released_at == expired_at
