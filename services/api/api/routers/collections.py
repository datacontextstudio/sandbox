from fastapi import APIRouter, HTTPException

from api.models import CollectionsResponse
from api.services.searcher import _get_client

router = APIRouter()


@router.get("/collections", response_model=CollectionsResponse)
async def list_collections() -> CollectionsResponse:
    client = _get_client()
    try:
        result = await client.get_collections()
        names = [c.name for c in result.collections]
        return CollectionsResponse(collections=names)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Qdrant error: {exc}")
