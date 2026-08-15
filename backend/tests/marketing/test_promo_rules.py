from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client() -> TestClient:
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def admin_headers(client: TestClient) -> dict[str, str]:
    response = client.post("/api/v1/auth/login", json={"login": "admin", "password": "correct-password"})
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_percentage_promo_reduces_checkout_total_and_records_discount(client: TestClient, admin_headers: dict[str, str]) -> None:
    """Removing promo validation or discount calculation must leave the full price and fail this test."""
    suffix = uuid4().hex[:8]
    promo = client.post(
        "/api/v1/promo-codes",
        headers=admin_headers,
        json={"code": f"SAVE{suffix}", "discount_type": "percent", "discount_value": 10, "minimum_order_kopecks": 100000, "max_uses": 1, "per_customer_limit": 1},
    )
    assert promo.status_code == 201

    customer_headers = {"X-Telegram-ID": str(int(suffix, 16))}
    category = client.post("/api/v1/categories", headers=admin_headers, json={"name": "Платья", "slug": f"dresses-{suffix}"}).json()
    product = client.post(
        "/api/v1/products",
        headers=admin_headers,
        json={"name": "Dress", "slug": f"dress-{suffix}", "sku": f"DR-{suffix}", "category_id": category["id"], "price_kopecks": 200000},
    ).json()
    variant = client.post(
        f"/api/v1/products/{product['id']}/variants",
        headers=admin_headers,
        json={"color": "Red", "size": "S", "sku": f"DR-RED-S-{suffix}", "stock_on_hand": 2, "price_kopecks": 200000},
    ).json()
    cart = client.post("/api/v1/carts/items", headers=customer_headers, json={"variant_id": variant["id"], "quantity": 2}).json()
    checkout = client.post(
        "/api/v1/checkout",
        headers=customer_headers,
        json={"cart_id": cart["cart_id"], "recipient_first_name": "Максим", "recipient_last_name": "Иванов", "phone": "+79990000000", "delivery_method": "pickup", "delivery_cost_kopecks": 0, "promo_code": f"SAVE{suffix}"},
    )

    assert checkout.status_code == 201
    assert checkout.json()["discount_kopecks"] == 40000
    assert checkout.json()["total_kopecks"] == 360000
