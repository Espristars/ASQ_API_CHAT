from app.repository import create_message
from app.schemas import MessageCreate
from sqlalchemy.ext.asyncio import AsyncSession

async def handle_new_message(db: AsyncSession, message_data: dict):
    message_in = MessageCreate(**message_data)
    message = await create_message(db, message_in)
    return message