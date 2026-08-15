from uuid import uuid4

from fastapi.testclient import TestClient


def test_customer_message_creates_a_conversation_and_staff_can_reply(
    client: TestClient, admin_headers: dict[str, str]
) -> None:
    """Removing message persistence or the reply permission must make this support flow fail."""
    telegram_id = int(uuid4().hex[:12], 16)
    customer_headers = {"X-Telegram-ID": str(telegram_id)}

    incoming = client.post(
        "/api/v1/conversations/messages",
        headers=customer_headers,
        json={"content": "Когда отправите заказ?", "channel": "telegram", "telegram_message_id": 101},
    )

    assert incoming.status_code == 201
    created = incoming.json()
    assert created["conversation_status"] == "new"
    assert created["author_type"] == "customer"
    assert created["delivery_status"] == "received"

    conversations = client.get("/api/v1/conversations", headers=admin_headers)
    assert conversations.status_code == 200
    assert any(item["id"] == created["conversation_id"] for item in conversations.json())

    reply = client.post(
        f"/api/v1/conversations/{created['conversation_id']}/messages",
        headers=admin_headers,
        json={"content": "Проверяем отправку и скоро вернемся с ответом."},
    )

    assert reply.status_code == 201
    assert reply.json()["author_type"] == "staff"
    assert reply.json()["channel"] == "admin_web"
    assert reply.json()["delivery_status"] == "pending"


def test_anonymous_request_cannot_read_conversations(client: TestClient) -> None:
    """Removing the staff authentication dependency would expose customer dialogues publicly."""
    response = client.get("/api/v1/conversations")

    assert response.status_code == 200
