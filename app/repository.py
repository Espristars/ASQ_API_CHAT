from sqlalchemy.future import select
from sqlalchemy.exc import IntegrityError
from app.models import Message
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas import MessageCreate

async def create_message(db: AsyncSession, message_in: MessageCreate) -> Message:
    query = select(Message).where(
        Message.chat_id == message_in.chat_id,
        Message.sender_id == message_in.sender_id,
        Message.text == message_in.text
    )
    result = await db.execute(query)
    existing = result.scalar()
    if existing:
        return existing

    new_message = Message(
        chat_id=message_in.chat_id,
        sender_id=message_in.sender_id,
        text=message_in.text
    )
    db.add(new_message)
    try:
        await db.commit()
        await db.refresh(new_message)
    except IntegrityError:
        await db.rollback()
        raise
    return new_message

async def get_chat_history(db: AsyncSession, chat_id: int, limit: int = 50, offset: int = 0):
    query = select(Message).where(Message.chat_id == chat_id).order_by(Message.timestamp.asc()).limit(limit).offset(offset)
    result = await db.execute(query)
    messages = result.scalars().all()
    return messages