from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.modules.catalog.models import ProductVariant


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(scope="module")
def admin_headers(client: TestClient) -> dict[str, str]:
    response = client.post("/api/v1/auth/login", json={"login": "admin", "password": "correct-password"})
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_available_quantity_subtracts_reservations() -> None:
    variant = ProductVariant(stock_on_hand=7, stock_reserved=3)
    assert variant.available_quantity == 4


def test_duplicate_product_variant_is_rejected(client: TestClient, admin_headers: dict[str, str]) -> None:
    suffix = uuid4().hex[:8]
    category = client.post("/api/v1/categories", headers=admin_headers, json={"name": "Худи", "slug": f"hoodies-{suffix}"})
    product = client.post(
        "/api/v1/products",
        headers=admin_headers,
        json={"name": "Oversize Hoodie", "slug": f"oversize-{suffix}", "sku": f"HD-{suffix}", "category_id": category.json()["id"], "price_kopecks": 599000},
    )
    payload = {"color": "Black", "size": "M", "sku": f"HD-BLK-M-{suffix}", "stock_on_hand": 2, "price_kopecks": 599000}
    first = client.post(f"/api/v1/products/{product.json()['id']}/variants", headers=admin_headers, json=payload)
    duplicate = client.post(f"/api/v1/products/{product.json()['id']}/variants", headers=admin_headers, json=payload)

    assert first.status_code == 201
    assert duplicate.status_code == 409
    assert duplicate.json() == {"detail": "variant_already_exists"}
