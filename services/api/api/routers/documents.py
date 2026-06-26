import asyncio

from fastapi import APIRouter, HTTPException

from api.models import DeleteResponse, DocumentsResponse
from api.services.queue import delete_job
from api.services.searcher import (
    delete_collection_qdrant,
    delete_document_chunks,
    scroll_documents,
)
from api.services.storage import delete_document_dir

router = APIRouter()


@router.get("/collections/{name}/documents", response_model=DocumentsResponse)
async def list_documents(name: str) -> DocumentsResponse:
    try:
        docs = await scroll_documents(name)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Qdrant error: {exc}")
    return DocumentsResponse(collection_name=name, documents=docs)


@router.delete("/collections/{name}/documents/{job_id}", response_model=DeleteResponse)
async def delete_document(name: str, job_id: str) -> DeleteResponse:
    try:
        await delete_document_chunks(name, job_id)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Qdrant error: {exc}")
    delete_document_dir(job_id)
    await delete_job(job_id)
    return DeleteResponse(deleted=True, detail=f"Document '{job_id}' removed from '{name}'")


@router.delete("/collections/{name}", response_model=DeleteResponse)
async def delete_collection(name: str) -> DeleteResponse:
    try:
        docs = await scroll_documents(name)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Qdrant error: {exc}")

    await asyncio.gather(*[delete_job(doc.job_id) for doc in docs])
    for doc in docs:
        delete_document_dir(doc.job_id)

    try:
        await delete_collection_qdrant(name)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Qdrant error: {exc}")

    return DeleteResponse(deleted=True, detail=f"Collection '{name}' deleted with {len(docs)} document(s)")
