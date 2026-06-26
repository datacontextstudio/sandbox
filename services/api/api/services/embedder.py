import httpx

from api.config import settings


async def embed_text(text: str) -> list[float]:
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            f"{settings.ollama_base_url}/api/embed",
            json={"model": settings.embed_model, "input": [text]},
        )
        response.raise_for_status()
        return response.json()["embeddings"][0]
