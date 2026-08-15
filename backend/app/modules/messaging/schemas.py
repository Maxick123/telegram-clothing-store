from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

CONVERSATION_STATUSES = {"new", "open", "waiting_for_customer", "waiting_for_staff", "resolved", "closed"}


class MessageBody(BaseModel):
    content: str | None = Field(default=None, max_length=4096)
    media: list[dict[str, Any]] = Field(default_factory=list, max_length=10)

    @model_validator(mode="after")
    def require_content_or_media(self) -> "MessageBody":
        if not (self.content and self.content.strip()) and not self.media:
            raise ValueError("message_content_or_media_required")
        return self


class CustomerMessageCreate(MessageBody):
    conversation_id: UUID | None = None
    order_id: UUID | None = None
    channel: str = Field(default="telegram", pattern=r"^telegram$")
    telegram_message_id: int | None = Field(default=None, ge=1)


class StaffMessageCreate(MessageBody):
    channel: str = Field(default="admin_web", pattern=r"^(admin_web|admin_telegram)$")


class ConversationUpdate(BaseModel):
    status: str | None = Field(default=None, pattern=r"^(new|open|waiting_for_customer|waiting_for_staff|resolved|closed)$")
    assigned_staff_id: UUID | None = None


class MessageResponse(BaseModel):
    id: UUID
    conversation_id: UUID
    author_type: str
    author_customer_id: UUID | None
    author_staff_id: UUID | None
    direction: str
    channel: str
    content: str | None
    media: list[dict[str, Any]]
    telegram_message_id: int | None
    delivery_status: str
    delivery_error: str | None
    delivered_at: datetime | None
    read_at: datetime | None
    created_at: datetime


class ConversationResponse(BaseModel):
    id: UUID
    customer_id: UUID
    order_id: UUID | None
    assigned_staff_id: UUID | None
    status: str
    last_message_at: datetime
    created_at: datetime
    updated_at: datetime
    latest_message: MessageResponse | None = None


class CustomerMessageResponse(MessageResponse):
    conversation_status: str
