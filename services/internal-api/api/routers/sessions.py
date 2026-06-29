from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import ARRAY, String, cast, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from api.database import ChatbotSession, get_session
from api.models import CreateSessionRequest, SessionResponse

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.get("", response_model=SessionResponse | None)
async def find_session_by_collections(
    collections: list[str] = Query(...),
    db: AsyncSession = Depends(get_session),
) -> SessionResponse | None:
    collections_array = cast(collections, ARRAY(String))
    result = await db.execute(
        select(ChatbotSession)
        .where(
            ChatbotSession.collections.op("@>")(collections_array),
            func.array_length(ChatbotSession.collections, 1) == len(collections),
        )
        .order_by(ChatbotSession.created_at.desc())
        .limit(1)
    )
    session = result.scalar_one_or_none()
    if session is None:
        return None
    return SessionResponse.model_validate(session)


@router.post("", response_model=SessionResponse, status_code=201)
async def create_session(
    body: CreateSessionRequest,
    db: AsyncSession = Depends(get_session),
) -> SessionResponse:
    session = ChatbotSession(collections=body.collections)
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return SessionResponse.model_validate(session)


@router.get("/{session_id}", response_model=SessionResponse)
async def get_session_by_id(
    session_id: UUID,
    db: AsyncSession = Depends(get_session),
) -> SessionResponse:
    result = await db.execute(select(ChatbotSession).where(ChatbotSession.id == session_id))
    session = result.scalar_one_or_none()
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return SessionResponse.model_validate(session)
