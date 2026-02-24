# app/main.py
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, Request
from fastapi.responses import JSONResponse

from .auth import require_api_key
from .routers import intakes, cases, notes, documents, internal
from .routers import prior_auth
from .subscribers import setup_pipeline

log = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_pipeline()
    yield


app = FastAPI(
    title="Clove — Patient Advocacy API",
    lifespan=lifespan,
)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    log.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


@app.get("/health")
def health():
    return {"status": "oh yeah, we good"}


app.include_router(intakes.router,   dependencies=[Depends(require_api_key)])
app.include_router(cases.router,     dependencies=[Depends(require_api_key)])
app.include_router(notes.router,     dependencies=[Depends(require_api_key)])
app.include_router(documents.router, dependencies=[Depends(require_api_key)])
app.include_router(internal.router,  dependencies=[Depends(require_api_key)])
app.include_router(prior_auth.router, dependencies=[Depends(require_api_key)])