from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.database import get_db
from app.models import User
from app.schemas import (
    MessageCreate,
    MessageResponse,
    ChatCreate,
    ChatResponse,
    GroupCreate,
    GroupResponse,
    SearchChat,
    AddUserToGroup,
    Token,
    UserCreate,
    UserResponse
)
from app.repository import (
    get_chat_history,
    create_group,
    create_chat,
    get_group_history,
    send_group_message,
    find_chat_by_name,
    add_user_to_group,
    create_message
)
from app.websocket_manager import manager
from app.auth import (
    create_access_token, authenticate_user, get_current_user,
    get_password_hash
)


router = APIRouter(prefix="/chat", tags=["Chat"])

@router.post("/register", response_model=UserResponse)
async def register(user: UserCreate, db: AsyncSession = Depends(get_db)):
    query = select(User).where(User.email == user.email)
    result = await db.execute(query)
    existing_user = result.scalar_one_or_none()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    hashed_password = get_password_hash(user.password)
    new_user = User(name=user.username, email=user.email, password=hashed_password)
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return new_user

@router.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    user = await authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(data={"sub": user.name})
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/history/{chat_id}", response_model=list[MessageResponse])
async def history(
    chat_id: int,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
    ):
    messages = await get_chat_history(db, current_user.id, chat_id, limit, offset)
    return messages


@router.post("/chat", response_model=ChatResponse)
async def post_chat(
    user: ChatCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
    ):
    if user.creator_id != current_user.id:
        raise HTTPException(status_code=403, detail="Неверный идентификатор пользователя")
    chat = await create_chat(db, user)
    return chat


@router.post("/group", response_model=GroupResponse)
async def post_group(
    user: GroupCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
    ):
    if user.creator_id != current_user.id:
        raise HTTPException(status_code=403, detail="Неверный идентификатор пользователя")
    group = await create_group(db, user)
    return group

@router.get("/group-history/{group_id}", response_model=list[MessageResponse])
async def group_history(
    group_id: int,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
    ):
    messages = await get_group_history(db, current_user.id, group_id, limit, offset)
    return messages

@router.post("/group-message", response_model=MessageResponse)
async def post_group_message(
    user: MessageCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
    ):
    if user.sender_id != current_user.id:
        raise HTTPException(status_code=403, detail="Неверный идентификатор отправителя")
    message = await send_group_message(db, user)
    return message

@router.post("/find-chat", response_model=ChatResponse)
async def post_find_chat(
    user: SearchChat,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
    ):
    chat = await find_chat_by_name(db, user)
    if not chat:
        raise HTTPException(status_code=404, detail="Чат не найден")
    return chat

@router.post("/group/add-user", response_model=GroupResponse)
async def post_add_user_to_group(
    user: AddUserToGroup,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
    ):
    group = await add_user_to_group(db, user)
    return group


@router.websocket("/ws/{chat_id}")
async def websocket_endpoint(websocket: WebSocket, chat_id: int, db: AsyncSession = Depends(get_db)):
    token = websocket.query_params.get("token")
    if token is None:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Missing token")
        return

    try:
        current_user = await get_current_user(token, db)
    except HTTPException as exc:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid token")
        return

    await manager.connect(chat_id, websocket)
    try:
        while True:
            data = await websocket.receive_json()
            if data.get("sender_id") != current_user.id:
                await websocket.send_json({"error": "Unauthorized sender"})
                continue
            message_in = MessageCreate(**data)
            message = await create_message(db, message_in)
            response = {
                "id": message.id,
                "chat_id": message.chat_id,
                "sender_id": message.sender_id,
                "text": message.text,
                "timestamp": message.timestamp.isoformat(),
                "read": message.read
            }
            await manager.broadcast(chat_id, response)
    except WebSocketDisconnect:
        manager.disconnect(chat_id, websocket)
    except Exception as e:
        print(f"WebSocket closed before error could be sent: {e}")