import uuid

from sqlalchemy import ARRAY, Column, DateTime, ForeignKey, String, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, relationship

from api.config import settings

engine = create_async_engine(settings.database_url, echo=False)
async_session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


class Base(DeclarativeBase):
    pass


class ChatbotSession(Base):
    __tablename__ = "chatbot_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    collections = Column(ARRAY(String), nullable=False)
    tools = Column(ARRAY(String), nullable=False, server_default="{}")
    created_at = Column(DateTime(timezone=True), server_default=text("NOW()"))

    chats = relationship("Chat", back_populates="session", cascade="all, delete-orphan")


class Chat(Base):
    __tablename__ = "chats"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("chatbot_sessions.id", ondelete="CASCADE"), nullable=False)
    title = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=text("NOW()"))

    session = relationship("ChatbotSession", back_populates="chats")
    messages = relationship("ChatMessage", back_populates="chat", cascade="all, delete-orphan")


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    chat_id = Column(UUID(as_uuid=True), ForeignKey("chats.id", ondelete="CASCADE"), nullable=False)
    role = Column(String(10), nullable=False)
    content = Column(String, nullable=False)
    tool_responses = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=text("NOW()"))

    chat = relationship("Chat", back_populates="messages")


class McpToolServer(Base):
    __tablename__ = "mcp_tool_servers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False, unique=True)
    url = Column(String, nullable=False)
    status = Column(String, nullable=False, default="ok")
    last_introspected_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=text("NOW()"))

    tools = relationship("McpTool", back_populates="server", cascade="all, delete-orphan")


class McpTool(Base):
    __tablename__ = "mcp_tools"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    server_id = Column(UUID(as_uuid=True), ForeignKey("mcp_tool_servers.id", ondelete="CASCADE"), nullable=False)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    input_schema = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=text("NOW()"))

    server = relationship("McpToolServer", back_populates="tools")

    __table_args__ = (UniqueConstraint("server_id", "name", name="uq_mcp_tool_server_name"),)


async def create_tables() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_session():
    async with async_session_factory() as session:
        yield session
