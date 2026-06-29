from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class CreateSessionRequest(BaseModel):
    collections: list[str]


class SessionResponse(BaseModel):
    id: UUID
    collections: list[str]
    created_at: datetime

    class Config:
        from_attributes = True


class CreateChatRequest(BaseModel):
    pass


class UpdateChatRequest(BaseModel):
    title: str


class ChatResponse(BaseModel):
    id: UUID
    session_id: UUID
    title: str | None
    created_at: datetime

    class Config:
        from_attributes = True


class CreateMessageRequest(BaseModel):
    role: str
    content: str


class MessageResponse(BaseModel):
    id: UUID
    chat_id: UUID
    role: str
    content: str
    created_at: datetime

    class Config:
        from_attributes = True
