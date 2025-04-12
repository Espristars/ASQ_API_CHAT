from sqlalchemy.future import select
from sqlalchemy import or_, distinct, func
from sqlalchemy.orm import selectinload
from sqlalchemy.exc import IntegrityError
from app.models import Message, Chat, Group, User, Chat_Users
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas import MessageCreate, ChatCreate, GroupCreate, SearchChat, AddUserToGroup


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


async def get_chat_history(db: AsyncSession, user_id: int, chat_id: int, limit: int = 50, offset: int = 0):
    query = select(Chat).options(selectinload(Chat.participants)).where(Chat.id == chat_id)
    result = await db.execute(query)
    chat = result.scalar()
    if not chat:
        raise ValueError("Чат не найден")
    if not any(u.id == user_id for u in chat.participants):
        raise ValueError("Пользователь не является участником чата")

    query = select(Message).where(Message.chat_id == chat_id).order_by(Message.timestamp.asc()).limit(limit).offset(offset)
    result = await db.execute(query)
    messages = result.scalars().all()
    return messages


async def create_group(db: AsyncSession, message_in: GroupCreate) -> Group:
    if message_in.creator_id not in message_in.participant_ids:
        message_in.participant_ids.append(message_in.creator_id)
    query = select(User).where(User.id.in_(message_in.participant_ids))
    result = await db.execute(query)
    users = result.scalars().all()
    new_group = Group(
        name=message_in.name,
        creator_id=message_in.creator_id,
        participants=users
    )
    db.add(new_group)
    try:
        await db.commit()
        await db.refresh(new_group)
    except IntegrityError:
        await db.rollback()
        raise
    return new_group


async def create_chat(db: AsyncSession, message_in: ChatCreate) -> Chat:
    query = select(User).where(
        or_(
            User.email == message_in.second_email,
            User.id == message_in.creator_id
        )
    )
    result = await db.execute(query)
    users = result.scalars().all()

    if len(users) != 2:
        raise ValueError("Пользователь не найден")

    new_chat = Chat(
        participants=users
    )
    db.add(new_chat)
    try:
        await db.commit()
        await db.refresh(new_chat)
    except IntegrityError:
        await db.rollback()
        raise

    return new_chat


async def get_group_history(db: AsyncSession, user_id: int, group_id: int, limit: int = 50, offset: int = 0):
    query = select(Group).options(selectinload(Group.participants)).where(Group.id == group_id)
    result = await db.execute(query)
    group = result.scalar()
    if not group:
        raise ValueError("Группа не найдена")
    if not any(u.id == user_id for u in group.participants):
        raise ValueError("Пользователь не является участником группы")

    query = select(Message).where(Message.chat_id == group_id).order_by(Message.timestamp.asc()).limit(limit).offset(offset)
    result = await db.execute(query)
    messages = result.scalars().all()
    return messages


async def send_group_message(db: AsyncSession, message_in: MessageCreate):
    query = select(Group).options(selectinload(Group.participants)).where(Group.id == message_in.chat_id)
    result = await db.execute(query)
    group = result.scalar()
    if not group:
        raise ValueError("Группа не найдена")
    if not any(u.id == message_in.sender_id for u in group.participants):
        raise ValueError("Пользователь не является участником группы")

    query = select(Group).where(Group.id == message_in.chat_id)
    result = await db.execute(query)
    chat = result.scalar()
    if not chat:
        raise ValueError("Чат группы не найден")

    message_in = MessageCreate(
        chat_id=chat.id,
        sender_id=message_in.sender_id,
        text=message_in.text
    )
    message = await create_message(db, message_in)
    return message


async def find_chat_by_name(db: AsyncSession, message_in: SearchChat) -> Chat:
    query = select(User).where(
        or_(
            User.name == message_in.name,
            User.id == message_in.user_id
        )
    )
    result = await db.execute(query)
    users = result.scalars().all()
    if len(users) != 2:
        raise ValueError("Пользователь не найден")

    user_ids = {user.id for user in users}

    subquery = (
        select(Chat_Users.c.chat_id)
        .where(Chat_Users.c.user_id.in_(user_ids))
        .group_by(Chat_Users.c.chat_id)
        .having(func.count(distinct(Chat_Users.c.user_id)) == 2)
        .subquery()
    )

    query = select(Chat).where(
        Chat.id.in_(subquery)
    )
    result = await db.execute(query)
    chat = result.scalar()
    return chat


async def add_user_to_group(db: AsyncSession, message_in: AddUserToGroup) -> Group:
    query = select(Group).options(selectinload(Group.participants)).where(Group.id == message_in.group_id)
    result = await db.execute(query)
    group = result.scalar()
    if not group:
        raise ValueError("Группа не найдена")
    if not any(u.id == message_in.user_id for u in group.participants):
        raise ValueError("Пользователь не является участником группы")

    query = select(User).where(User.email == message_in.email)
    result = await db.execute(query)
    user = result.scalar()
    if not user:
        raise ValueError("Пользователь с указанной почтой не найден")

    if any(u.id == user.id for u in group.participants):
        raise ValueError("Пользователь уже состоит в группе")

    group.participants.append(user)
    try:
        await db.commit()
        await db.refresh(group)
    except IntegrityError:
        await db.rollback()
        raise
    return group