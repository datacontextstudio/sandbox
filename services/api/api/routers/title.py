import httpx
from fastapi import APIRouter, HTTPException

from api.config import settings
from api.models import TitleRequest, TitleResponse

router = APIRouter()


@router.post("/generate-title", response_model=TitleResponse)
async def generate_title(req: TitleRequest) -> TitleResponse:
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{settings.ollama_base_url}/api/chat",
                json={
                    "model": req.llm_model,
                    "messages": [
                        {
                            "role": "system",
                            "content": (
                                "Summarize the following query in 4 to 6 words as a chat title. "
                                "Return only the title with no punctuation, no quotes, no explanation."
                            ),
                        },
                        {"role": "user", "content": req.query},
                    ],
                    "stream": False,
                },
            )
            resp.raise_for_status()
            title = resp.json()["message"]["content"].strip().strip('"').strip("'")
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"LLM service error: {exc}")

    return TitleResponse(title=title)
