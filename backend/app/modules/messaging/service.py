from datetime import UTC, datetime
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.customers.models import Customer
from app.modules.identity.models import Staff
from app.modules.messaging.models import Conversation, Message
from app.modules.messaging.schemas import CustomerMessageCreate, StaffMessageCreate

OPEN_CONVERSATION_STATUSES = ("new", "open", "waiting_for_customer", "waiting_for_staff")


async def _customer_conversation(session: AsyncSession, customer: Customer, payload: CustomerMessageCreate) -> tuple[Conversation, bool]:
    if payload.conversation_id:
        conversation = await session.scalar(
            select(Conversation).where(Conversation.id == payload.conversation_id, Conversation.customer_id == customer.id)
        )
        if conversation is None:
            raise HTTPException(status_code=404, detail="conversation_not_found")
        return conversation, False

    statement = select(Conversation).where(
        Conversation.customer_id == customer.id,
        Conversation.status.in_(OPEN_CONVERSATION_STATUSES),
        Conversation.order_id == payload.order_id,
    ).order_by(Conversation.last_message_at.desc())
    conversation = await session.scalar(statement)
    if conversation is not None:
        return conversation, False

    conversation = Conversation(customer_id=customer.id, order_id=payload.order_id, status="new")
    session.add(conversation)
    await session.flush()
    return conversation, True


async def append_customer_message(session: AsyncSession, customer: Customer, payload: CustomerMessageCreate) -> tuple[Conversation, Message]:
    conversation, is_new = await _customer_conversation(session, customer, payload)
    now = datetime.now(UTC)
    if not is_new:
        conversation.status = "waiting_for_staff"
    conversation.last_message_at = now
    message = Message(
        conversation_id=conversation.id,
        author_type="customer",
        author_customer_id=customer.id,
        direction="incoming",
        channel=payload.channel,
        content=payload.content.strip() if payload.content else None,
        media=payload.media,
        telegram_message_id=payload.telegram_message_id,
        delivery_status="received",
        delivered_at=now,
    )
    session.add(message)
    await session.commit()
    return conversation, message


async def append_staff_message(session: AsyncSession, staff: Staff, conversation_id: UUID, payload: StaffMessageCreate) -> tuple[Conversation, Message]:
    conversation = await session.get(Conversation, conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="conversation_not_found")
    now = datetime.now(UTC)
    if conversation.assigned_staff_id is None:
        conversation.assigned_staff_id = staff.id
    conversation.status = "waiting_for_customer"
    conversation.last_message_at = now
    message = Message(
        conversation_id=conversation.id,
        author_type="staff",
        author_staff_id=staff.id,
        direction="outgoing",
        channel=payload.channel,
        content=payload.content.strip() if payload.content else None,
        media=payload.media,
        delivery_status="pending",
    )
    session.add(message)
    await session.commit()
    return conversation, message


async def latest_message(session: AsyncSession, conversation_id: UUID) -> Message | None:
    return await session.scalar(
        select(Message).where(Message.conversation_id == conversation_id).order_by(Message.created_at.desc()).limit(1)
    )
