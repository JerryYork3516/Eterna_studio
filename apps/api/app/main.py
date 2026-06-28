"""FastAPI application — Eterna Canvas API (Schema Contract v0.3).

Mounts all routers. No database, no real LLM calls, no auth (MVP scope).
Run: uvicorn app.main:app --reload
Docs: http://127.0.0.1:8000/docs
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .models.v0_4 import PROTOCOL_VERSION_V0_4
from .routers import dr, health, protocol_v0_4, resident, runtime, runtime_config, schema, templates, workflow
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
    # Stage 6.2: let the browser read the DR download metadata headers.
    expose_headers=["Content-Disposition", "X-DR-Filename", "X-DR-Audit-Valid", "X-DR-Version"],
)

app.include_router(health.router)
app.include_router(schema.router)
app.include_router(templates.router)
app.include_router(workflow.router)
app.include_router(resident.router)
app.include_router(protocol_v0_4.router)
app.include_router(runtime.router)
app.include_router(runtime_config.router)
app.include_router(dr.router)


@app.get("/", tags=["health"])
def root() -> dict:
    return {
        "service": "eterna-canvas-api",
        "schema_version": SCHEMA_VERSION,
        "protocol_version": PROTOCOL_VERSION_V0_4,
        "docs": "/docs",
    }
