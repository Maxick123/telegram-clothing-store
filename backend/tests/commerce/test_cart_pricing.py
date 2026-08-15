from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(scope="module")
def admin_headers(client: TestClient) -> dict[str, str]:
    response = client.post("/api/v1/auth/login", json={"login": "admin", "password": "correct-password"})
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_cart_quote_uses_server_price_not_client_input(client: TestClient, admin_headers: dict[str, str]) -> None:
    suffix = uuid4().hex[:8]
    category = client.post("/api/v1/categories", headers=admin_headers, json={"name": "Футболки", "slug": f"tees-{suffix}"}).json()
    product = client.post("/api/v1/products", headers=admin_headers, json={"name": "Tee", "slug": f"tee-{suffix}", "sku": f"T-{suffix}", "category_id": category["id"], "price_kopecks": 150000}).json()
    variant = client.post(f"/api/v1/products/{product['id']}/variants", headers=admin_headers, json={"color": "White", "size": "M", "sku": f"T-W-M-{suffix}", "stock_on_hand": 5, "price_kopecks": 150000}).json()

    response = client.post("/api/v1/carts/items", headers={"X-Telegram-ID": str(int(suffix, 16))}, json={"variant_id": variant["id"], "quantity": 2, "unit_price_kopecks": 1})

    assert response.status_code == 201
    assert response.json()["subtotal_kopecks"] == 300000


def test_cart_rejects_quantity_above_available_stock(client: TestClient, admin_headers: dict[str, str]) -> None:
    suffix = uuid4().hex[:8]
    category = client.post("/api/v1/categories", headers=admin_headers, json={"name": "Брюки", "slug": f"pants-{suffix}"}).json()
    product = client.post("/api/v1/products", headers=admin_headers, json={"name": "Pants", "slug": f"pants-item-{suffix}", "sku": f"P-{suffix}", "category_id": category["id"], "price_kopecks": 300000}).json()
    variant = client.post(f"/api/v1/products/{product['id']}/variants", headers=admin_headers, json={"color": "Black", "size": "L", "sku": f"P-B-L-{suffix}", "stock_on_hand": 1, "price_kopecks": 300000}).json()

    response = client.post("/api/v1/carts/items", headers={"X-Telegram-ID": str(int(suffix, 16))}, json={"variant_id": variant["id"], "quantity": 2})

    assert response.status_code == 409
    assert response.json() == {"detail": "insufficient_stock"}


def test_customer_can_favorite_product_only_once(client: TestClient, admin_headers: dict[str, str]) -> None:
    suffix = uuid4().hex[:8]
    category = client.post("/api/v1/categories", headers=admin_headers, json={"name": "Куртки", "slug": f"jackets-{suffix}"}).json()
    product = client.post("/api/v1/products", headers=admin_headers, json={"name": "Jacket", "slug": f"jacket-{suffix}", "sku": f"J-{suffix}", "category_id": category["id"], "price_kopecks": 800000}).json()

    headers = {"X-Telegram-ID": str(int(suffix, 16))}
    first = client.post(f"/api/v1/favorites/{product['id']}", headers=headers)
    duplicate = client.post(f"/api/v1/favorites/{product['id']}", headers=headers)

    assert first.status_code == 201
    assert duplicate.status_code == 409
    assert duplicate.json() == {"detail": "already_favorite"}
