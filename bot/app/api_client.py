from __future__ import annotations

from typing import Any

import httpx


class BackendError(RuntimeError):
    """A safe, machine-readable failure returned by the store backend."""

    def __init__(self, detail: str, status_code: int) -> None:
        super().__init__(detail)
        self.detail = detail
        self.status_code = status_code


class BackendUnavailable(BackendError):
    def __init__(self) -> None:
        super().__init__("backend_unavailable", 503)


class BackendClient:
    def __init__(self, base_url: str, *, transport: httpx.AsyncBaseTransport | None = None) -> None:
        self._client = httpx.AsyncClient(base_url=base_url.rstrip("/"), timeout=20, transport=transport)

    async def health(self) -> bool:
        try:
            response = await self._client.get("/health")
        except httpx.HTTPError:
            return False
        return response.status_code == 200

    async def add_cart_item(self, telegram_id: int, variant_id: str, *, quantity: int = 1) -> dict[str, Any]:
        return await self._customer_request(
            telegram_id,
            "POST",
            "/api/v1/carts/items",
            json={"variant_id": variant_id, "quantity": quantity},
        )

    async def add_favorite(self, telegram_id: int, product_id: str) -> dict[str, Any]:
        return await self._customer_request(telegram_id, "POST", f"/api/v1/favorites/{product_id}")

    async def checkout(self, telegram_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        return await self._customer_request(telegram_id, "POST", "/api/v1/checkout", json=payload)

    async def create_yookassa_payment(self, telegram_id: int, order_id: str) -> dict[str, Any]:
        return await self._customer_request(telegram_id, "POST", f"/api/v1/orders/{order_id}/payments/yookassa")

    async def create_customer_message(
        self,
        telegram_id: int,
        *,
        content: str | None,
        media: list[dict[str, Any]],
        telegram_message_id: int,
    ) -> dict[str, Any]:
        return await self._customer_request(
            telegram_id,
            "POST",
            "/api/v1/conversations/messages",
            json={"content": content, "media": media, "telegram_message_id": telegram_message_id},
        )

    async def _customer_request(self, telegram_id: int, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        try:
            response = await self._client.request(method, path, headers={"X-Telegram-ID": str(telegram_id)}, **kwargs)
        except httpx.HTTPError as exc:
            raise BackendUnavailable() from exc
        if response.is_success:
            payload = response.json()
            if isinstance(payload, dict):
                return payload
            raise BackendError("unexpected_backend_response", response.status_code)
        detail = "backend_error"
        try:
            payload = response.json()
            if isinstance(payload, dict) and isinstance(payload.get("detail"), str):
                detail = payload["detail"]
        except ValueError:
            pass
        raise BackendError(detail, response.status_code)

    async def close(self) -> None:
        await self._client.aclose()
