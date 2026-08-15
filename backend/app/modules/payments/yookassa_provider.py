from base64 import b64encode
import asyncio
import json
from urllib.request import Request, urlopen
from uuid import uuid4

from app.core.config import get_settings


def kopecks_to_rub(amount_kopecks: int) -> str:
    return f"{amount_kopecks // 100}.{amount_kopecks % 100:02d}"


def create_payment_request(order_id: str, amount_kopecks: int) -> tuple[dict[str, object], dict[str, str]]:
    settings = get_settings()
    if not settings.yookassa_shop_id or not settings.yookassa_secret_key:
        raise RuntimeError("yookassa_not_configured")
    credentials = f"{settings.yookassa_shop_id}:{settings.yookassa_secret_key}".encode()
    payload: dict[str, object] = {
        "amount": {"value": kopecks_to_rub(amount_kopecks), "currency": "RUB"},
        "capture": True,
        "confirmation": {"type": "redirect", "return_url": f"{settings.public_base_url}/payment-return"},
        "description": f"Оплата заказа {order_id}",
        "metadata": {"order_id": order_id},
    }
    headers = {"Authorization": f"Basic {b64encode(credentials).decode()}", "Content-Type": "application/json", "Idempotence-Key": str(uuid4())}
    return payload, headers


async def create_redirect_payment(order_id: str, amount_kopecks: int) -> dict[str, object]:
    payload, headers = create_payment_request(order_id, amount_kopecks)
    request = Request("https://api.yookassa.ru/v3/payments", data=json.dumps(payload).encode(), headers=headers, method="POST")
    def send() -> dict[str, object]:
        with urlopen(request, timeout=20) as response:
            return json.loads(response.read())
    return await asyncio.to_thread(send)
