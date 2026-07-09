from fastapi import FastAPI

from api.routers import collections, documents, ingest, internal, jobs, query, title

app = FastAPI(title="DataContext Studio API")

app.include_router(collections.router)
app.include_router(documents.router)
app.include_router(ingest.router)
app.include_router(internal.router)
app.include_router(jobs.router)
app.include_router(query.router)
app.include_router(title.router)


@app.get("/healthz")
async def healthz() -> dict:
    return {"status": "ok"}
