"""FastAPI application — Eterna Canvas API (Schema Contract v0.3).

Mounts all routers. No database, no real LLM calls, no auth (MVP scope).
Run: uvicorn app.main:app --reload
Docs: http://127.0.0.1:8000/docs
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers import health, resident, schema, templates, workflow
from .schema_version import SCHEMA_VERSION

app = FastAPI(
    title="Eterna Canvas API",
    version=SCHEMA_VERSION,
    description="Schema Contract v0.3 — WorkflowV03 and ResidentInstanceV03 are the runtime source of truth.",
)

# Open CORS for local frontend integration (stage-3 联调). MVP only.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(schema.router)
app.include_router(templates.router)
app.include_router(workflow.router)
app.include_router(resident.router)


@app.get("/", tags=["health"])
def root() -> dict:
    return {
        "service": "eterna-canvas-api",
        "schema_version": SCHEMA_VERSION,
        "docs": "/docs",
    }
