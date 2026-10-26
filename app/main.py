from contextlib import asynccontextmanager

from fastapi import FastAPI
from psycopg import Error

from app.api.routes import router
from app.config import get_settings
from app.db import initialise_database


@asynccontextmanager
async def lifespan(_: FastAPI):
    if get_settings().environment != "test":
        try:
            await initialise_database()
        except Error:
            # The API remains usable in local demo mode when PostgreSQL is unavailable.
            pass
    yield


app = FastAPI(title=get_settings().app_name, version="0.1.0", lifespan=lifespan)
app.include_router(router)


@app.get("/health", tags=["system"])
async def health() -> dict[str, str]:
    return {"status": "ok"}
