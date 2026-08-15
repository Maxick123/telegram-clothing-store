import httpx
import json
import pytest

from app.api_client import BackendClient, BackendError


@pytest.mark.asyncio
async def test_add_cart_item_sends_customer_header_and_payload() -> None:
    """Bot API client must identify the Telegram customer when adding a variant."""

    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/v1/carts/items"
        assert request.headers["X-Telegram-ID"] == "100500"
        assert json.loads(request.content) == {"variant_id": "34cb73f9-4883-4cce-884c-751303075f0d", "quantity": 2}
        return httpx.Response(201, json={"cart_id": "cart-1", "subtotal_kopecks": 1198000})

    client = BackendClient("http://store.test", transport=httpx.MockTransport(handler))
    try:
        result = await client.add_cart_item(100500, "34cb73f9-4883-4cce-884c-751303075f0d", quantity=2)
    finally:
        await client.close()

    assert result["subtotal_kopecks"] == 1198000


@pytest.mark.asyncio
async def test_backend_error_is_exposed_as_actionable_code() -> None:
    """Known API errors are available to handlers without leaking HTTP details to customers."""

    client = BackendClient(
        "http://store.test",
        transport=httpx.MockTransport(lambda _: httpx.Response(409, json={"detail": "insufficient_stock"})),
    )
    try:
        with pytest.raises(BackendError, match="insufficient_stock"):
            await client.add_cart_item(1, "34cb73f9-4883-4cce-884c-751303075f0d")
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_customer_support_message_is_saved_before_group_relay() -> None:
    """Customer support content is persisted through the shared conversation API."""

    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/v1/conversations/messages"
        assert request.headers["X-Telegram-ID"] == "100500"
        assert json.loads(request.content) == {
            "content": "Когда отправка?",
            "media": [],
            "telegram_message_id": 77,
        }
        return httpx.Response(201, json={"conversation_id": "a043e72a-586c-4cc4-922d-d273bb5405cd"})

    client = BackendClient("http://store.test", transport=httpx.MockTransport(handler))
    try:
        result = await client.create_customer_message(100500, content="Когда отправка?", media=[], telegram_message_id=77)
    finally:
        await client.close()

    assert result["conversation_id"] == "a043e72a-586c-4cc4-922d-d273bb5405cd"
