from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from api.database import ChatMessage, ChatbotSession, get_session
from api.models import CreateMessageRequest, MessageResponse

router = APIRouter(prefix="/sessions/{session_id}/messages", tags=["messages"])


@router.post("", response_model=MessageResponse, status_code=201)
async def create_message(
    session_id: UUID,
    body: CreateMessageRequest,
    db: AsyncSession = Depends(get_session),
) -> MessageResponse:
    result = await db.execute(select(ChatbotSession).where(ChatbotSession.id == session_id))
    if result.scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail="Session not found")

    message = ChatMessage(session_id=session_id, role=body.role, content=body.content)
    db.add(message)
    await db.commit()
    await db.refresh(message)
    return MessageResponse.model_validate(message)


@router.get("", response_model=list[MessageResponse])
async def list_messages(
    session_id: UUID,
    db: AsyncSession = Depends(get_session),
) -> list[MessageResponse]:
    result = await db.execute(select(ChatbotSession).where(ChatbotSession.id == session_id))
    if result.scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail="Session not found")

    result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at)
    )
    messages = result.scalars().all()
    return [MessageResponse.model_validate(m) for m in messages]
