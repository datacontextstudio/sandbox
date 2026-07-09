from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class CreateSessionRequest(BaseModel):
    collections: list[str]
    tools: list[str] = []


class SessionResponse(BaseModel):
    id: UUID
    collections: list[str]
    tools: list[str]
    created_at: datetime

    class Config:
        from_attributes = True


class CreateMcpServerRequest(BaseModel):
    name: str
    url: str


class McpToolInfo(BaseModel):
    name: str
    description: str | None
    input_schema: dict | None

    class Config:
        from_attributes = True


class McpServerResponse(BaseModel):
    id: UUID
    name: str
    url: str
    status: str
    last_introspected_at: datetime | None
    created_at: datetime
    tools: list[McpToolInfo]
    detail: str | None = None

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


class ToolResponse(BaseModel):
    tool: str
    response: str


class CreateMessageRequest(BaseModel):
    role: str
    content: str
    tool_responses: list[ToolResponse] | None = None


class MessageResponse(BaseModel):
    id: UUID
    chat_id: UUID
    role: str
    content: str
    tool_responses: list[ToolResponse] | None = None
    created_at: datetime

    class Config:
        from_attributes = True
