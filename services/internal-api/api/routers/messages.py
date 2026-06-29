from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from api.database import Chat, ChatMessage, get_session
from api.models import CreateMessageRequest, MessageResponse

router = APIRouter(prefix="/sessions/{session_id}/chats/{chat_id}/messages", tags=["messages"])


async def _require_chat(session_id: UUID, chat_id: UUID, db: AsyncSession) -> None:
    result = await db.execute(
        select(Chat).where(Chat.id == chat_id, Chat.session_id == session_id)
    )
    if result.scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail="Chat not found")


@router.post("", response_model=MessageResponse, status_code=201)
async def create_message(
    session_id: UUID,
    chat_id: UUID,
    body: CreateMessageRequest,
    db: AsyncSession = Depends(get_session),
) -> MessageResponse:
    await _require_chat(session_id, chat_id, db)
    message = ChatMessage(chat_id=chat_id, role=body.role, content=body.content)
    db.add(message)
    await db.commit()
    await db.refresh(message)
    return MessageResponse.model_validate(message)


@router.get("", response_model=list[MessageResponse])
async def list_messages(
    session_id: UUID,
    chat_id: UUID,
    db: AsyncSession = Depends(get_session),
) -> list[MessageResponse]:
    await _require_chat(session_id, chat_id, db)
    result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.chat_id == chat_id)
        .order_by(ChatMessage.created_at)
    )
    return [MessageResponse.model_validate(m) for m in result.scalars().all()]
