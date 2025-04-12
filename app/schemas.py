from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class MessageCreate(BaseModel):
    chat_id: int
    sender_id: int
    text: str

class MessageResponse(BaseModel):
    id: int
    chat_id: int
    sender_id: int
    text: str
    timestamp: datetime
    read: bool

    class Config:
        orm_mode = True

class ChatCreate(BaseModel):
    creator_id: int
    second_email: str

class ChatResponse(BaseModel):
    id: int
    name: Optional[str]

    class Config:
        orm_mode = True

class GroupCreate(BaseModel):
    name: str
    creator_id: int
    participant_ids: List[int]

class GroupResponse(BaseModel):
    id: int
    name: str
    creator_id: int
    participant_ids: List[int]

    class Config:
        orm_mode = True

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None

class UserCreate(BaseModel):
    username: str
    email: str
    password: str

class UserResponse(BaseModel):
    id: int
    name: str
    email: str

    class Config:
        orm_mode = True

class SearchChat(BaseModel):
    user_id: int
    name: str

class AddUserToGroup(BaseModel):
    user_id: int
    group_id: int
    email: str