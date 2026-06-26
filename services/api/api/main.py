from fastapi import FastAPI

from api.routers import collections, ingest, jobs, query

app = FastAPI(title="DataContext Studio API")

app.include_router(collections.router)
app.include_router(ingest.router)
app.include_router(jobs.router)
app.include_router(query.router)


@app.get("/healthz")
async def healthz() -> dict:
    return {"status": "ok"}
