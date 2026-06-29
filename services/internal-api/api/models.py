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


class CreateMessageRequest(BaseModel):
    role: str
    content: str


class MessageResponse(BaseModel):
    id: UUID
    session_id: UUID
    role: str
    content: str
    created_at: datetime

    class Config:
        from_attributes = True
