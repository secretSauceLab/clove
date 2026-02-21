# app/main.py
from fastapi import FastAPI, Depends

from .auth import require_api_key
from .routers import intakes, cases, notes, documents, internal

app = FastAPI(title="Patient Advocacy Intake API")


@app.get("/health")
def health():
    return {"status": "oh yeah, we good"}


app.include_router(intakes.router,   dependencies=[Depends(require_api_key)])
app.include_router(cases.router,     dependencies=[Depends(require_api_key)])
app.include_router(notes.router,     dependencies=[Depends(require_api_key)])
app.include_router(documents.router, dependencies=[Depends(require_api_key)])
app.include_router(internal.router,  dependencies=[Depends(require_api_key)])