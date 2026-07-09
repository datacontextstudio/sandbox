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
    tools: list[str] = Query(default=[]),
    db: AsyncSession = Depends(get_session),
) -> SessionResponse | None:
    collections_array = cast(collections, ARRAY(String))
    clauses = [
        ChatbotSession.collections.op("@>")(collections_array),
        func.coalesce(func.array_length(ChatbotSession.collections, 1), 0) == len(collections),
    ]
    if tools:
        tools_array = cast(tools, ARRAY(String))
        clauses += [
            ChatbotSession.tools.op("@>")(tools_array),
            func.coalesce(func.array_length(ChatbotSession.tools, 1), 0) == len(tools),
        ]
    else:
        clauses.append(func.coalesce(func.array_length(ChatbotSession.tools, 1), 0) == 0)

    result = await db.execute(
        select(ChatbotSession)
        .where(*clauses)
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
    session = ChatbotSession(collections=body.collections, tools=body.tools)
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
