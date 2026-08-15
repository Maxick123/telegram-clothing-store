from fastapi.testclient import TestClient
import pytest

from app.main import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as test_client:
        yield test_client


def test_login_sets_refresh_cookie_and_returns_access_token(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/login",
        json={"login": "admin", "password": "correct-password"},
    )

    assert response.status_code == 200
    assert response.json()["token_type"] == "bearer"
    assert response.json()["access_token"]
    assert response.cookies.get("refresh_token")


def test_support_operator_cannot_list_staff(client: TestClient) -> None:
    login = client.post(
        "/api/v1/auth/login",
        json={"login": "support", "password": "correct-password"},
    )
    response = client.get(
        "/api/v1/staff",
        headers={"Authorization": f"Bearer {login.json()['access_token']}"},
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "permission_denied"}


def test_me_returns_staff_permissions(client: TestClient) -> None:
    login = client.post(
        "/api/v1/auth/login",
        json={"login": "admin", "password": "correct-password"},
    )
    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {login.json()['access_token']}"},
    )

    assert response.status_code == 200
    assert response.json()["login"] == "admin"
    assert "staff.read" in response.json()["permissions"]


def test_refresh_rotates_cookie_and_returns_new_access_token(client: TestClient) -> None:
    login = client.post(
        "/api/v1/auth/login",
        json={"login": "admin", "password": "correct-password"},
    )
    old_refresh = login.cookies["refresh_token"]
    response = client.post("/api/v1/auth/refresh")

    assert response.status_code == 200
    assert response.json()["access_token"]
    assert response.cookies["refresh_token"] != old_refresh
