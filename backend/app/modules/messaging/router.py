from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.modules.commerce.router import customer_from_telegram
from app.modules.customers.models import Customer
from app.modules.identity.models import Staff
from app.modules.identity.router import require_permission
from app.modules.messaging.models import Conversation, Message
from app.modules.messaging.schemas import (
    CONVERSATION_STATUSES,
    ConversationResponse,
    ConversationUpdate,
    CustomerMessageCreate,
    CustomerMessageResponse,
    MessageResponse,
    StaffMessageCreate,
)
from app.modules.messaging.service import append_customer_message, append_staff_message, latest_message

router = APIRouter(prefix="/api/v1/conversations", tags=["conversations"])
Session = Annotated[AsyncSession, Depends(get_session)]
ConversationReader = Annotated[Staff, Depends(require_permission("conversations.read"))]
ConversationResponder = Annotated[Staff, Depends(require_permission("conversations.reply"))]


def message_response(message: Message) -> MessageResponse:
    return MessageResponse(
        id=message.id,
        conversation_id=message.conversation_id,
        author_type=message.author_type,
        author_customer_id=message.author_customer_id,
        author_staff_id=message.author_staff_id,
        direction=message.direction,
        channel=message.channel,
        content=message.content,
        media=message.media or [],
        telegram_message_id=message.telegram_message_id,
        delivery_status=message.delivery_status,
        delivery_error=message.delivery_error,
        delivered_at=message.delivered_at,
        read_at=message.read_at,
        created_at=message.created_at,
    )


async def conversation_response(session: AsyncSession, conversation: Conversation) -> ConversationResponse:
    return ConversationResponse(
        id=conversation.id,
        customer_id=conversation.customer_id,
        order_id=conversation.order_id,
        assigned_staff_id=conversation.assigned_staff_id,
        status=conversation.status,
        last_message_at=conversation.last_message_at,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
        latest_message=message_response(message) if (message := await latest_message(session, conversation.id)) else None,
    )


@router.post("/messages", response_model=CustomerMessageResponse, status_code=201)
async def create_customer_message(
    payload: CustomerMessageCreate,
    session: Session,
    customer: Annotated[Customer, Depends(customer_from_telegram)],
) -> CustomerMessageResponse:
    conversation, message = await append_customer_message(session, customer, payload)
    return CustomerMessageResponse(**message_response(message).model_dump(), conversation_status=conversation.status)


@router.get("", response_model=list[ConversationResponse])
async def list_conversations(
    _: ConversationReader,
    session: Session,
    status: Annotated[str | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> list[ConversationResponse]:
    if status is not None and status not in CONVERSATION_STATUSES:
        raise HTTPException(status_code=422, detail="conversation_status_invalid")
    statement = select(Conversation).order_by(Conversation.last_message_at.desc()).limit(limit)
    if status is not None:
        statement = statement.where(Conversation.status == status)
    conversations = (await session.scalars(statement)).all()
    return [await conversation_response(session, conversation) for conversation in conversations]


@router.get("/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(conversation_id: UUID, _: ConversationReader, session: Session) -> ConversationResponse:
    conversation = await session.get(Conversation, conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="conversation_not_found")
    return await conversation_response(session, conversation)


@router.get("/{conversation_id}/messages", response_model=list[MessageResponse])
async def list_messages(conversation_id: UUID, _: ConversationReader, session: Session) -> list[MessageResponse]:
    if await session.get(Conversation, conversation_id) is None:
        raise HTTPException(status_code=404, detail="conversation_not_found")
    messages = (await session.scalars(select(Message).where(Message.conversation_id == conversation_id).order_by(Message.created_at))).all()
    return [message_response(message) for message in messages]


@router.post("/{conversation_id}/messages", response_model=MessageResponse, status_code=201)
async def create_staff_message(
    conversation_id: UUID,
    payload: StaffMessageCreate,
    staff: ConversationResponder,
    session: Session,
) -> MessageResponse:
    _, message = await append_staff_message(session, staff, conversation_id, payload)
    return message_response(message)


@router.patch("/{conversation_id}", response_model=ConversationResponse)
async def update_conversation(
    conversation_id: UUID,
    payload: ConversationUpdate,
    _: ConversationResponder,
    session: Session,
) -> ConversationResponse:
    conversation = await session.get(Conversation, conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="conversation_not_found")
    update = payload.model_dump(exclude_unset=True)
    if "status" in update:
        conversation.status = update["status"]
    if "assigned_staff_id" in update:
        conversation.assigned_staff_id = update["assigned_staff_id"]
    await session.commit()
    return await conversation_response(session, conversation)
