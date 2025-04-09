from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.database import get_db
from app.models import User
from app.schemas import (
    MessageResponse, Token, UserCreate, UserResponse
)
from app.repository import get_chat_history
from app.websocket_manager import manager
from app.services import handle_new_message
from app.auth import (
    create_access_token, authenticate_user, get_current_user,
    get_password_hash
)


router = APIRouter(tags=["Secrets"])

@router.post("/register", response_model=UserResponse)
async def register(user: UserCreate, db: AsyncSession = Depends(get_db)):
    query = select(User).where(User.email == user.email)
    result = await db.execute(query)
    existing_user = result.scalar_one_or_none()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    hashed_password = get_password_hash(user.password)
    new_user = User(name=user.name, email=user.email, password=hashed_password)
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
    access_token = create_access_token(data={"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/history/{chat_id}", response_model=list[MessageResponse])
async def history(
    chat_id: int, limit: int = 50, offset: int = 0,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
    ):
    messages = await get_chat_history(db, chat_id, limit, offset)
    return messages


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
            message = await handle_new_message(db, data)
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
        await websocket.send_json({"error": str(e)})