from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from api.database import Chat, ChatbotSession, get_session
from api.models import ChatResponse, UpdateChatRequest

router = APIRouter(prefix="/sessions/{session_id}/chats", tags=["chats"])


async def _require_session(session_id: UUID, db: AsyncSession) -> None:
    result = await db.execute(select(ChatbotSession).where(ChatbotSession.id == session_id))
    if result.scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail="Session not found")


@router.get("", response_model=list[ChatResponse])
async def list_chats(
    session_id: UUID,
    db: AsyncSession = Depends(get_session),
) -> list[ChatResponse]:
    await _require_session(session_id, db)
    result = await db.execute(
        select(Chat).where(Chat.session_id == session_id).order_by(Chat.created_at.desc())
    )
    return [ChatResponse.model_validate(c) for c in result.scalars().all()]


@router.post("", response_model=ChatResponse, status_code=201)
async def create_chat(
    session_id: UUID,
    db: AsyncSession = Depends(get_session),
) -> ChatResponse:
    await _require_session(session_id, db)
    chat = Chat(session_id=session_id)
    db.add(chat)
    await db.commit()
    await db.refresh(chat)
    return ChatResponse.model_validate(chat)


@router.get("/{chat_id}", response_model=ChatResponse)
async def get_chat(
    session_id: UUID,
    chat_id: UUID,
    db: AsyncSession = Depends(get_session),
) -> ChatResponse:
    result = await db.execute(
        select(Chat).where(Chat.id == chat_id, Chat.session_id == session_id)
    )
    chat = result.scalar_one_or_none()
    if chat is None:
        raise HTTPException(status_code=404, detail="Chat not found")
    return ChatResponse.model_validate(chat)


@router.patch("/{chat_id}", response_model=ChatResponse)
async def update_chat(
    session_id: UUID,
    chat_id: UUID,
    body: UpdateChatRequest,
    db: AsyncSession = Depends(get_session),
) -> ChatResponse:
    result = await db.execute(
        select(Chat).where(Chat.id == chat_id, Chat.session_id == session_id)
    )
    chat = result.scalar_one_or_none()
    if chat is None:
        raise HTTPException(status_code=404, detail="Chat not found")
    chat.title = body.title
    await db.commit()
    await db.refresh(chat)
    return ChatResponse.model_validate(chat)
