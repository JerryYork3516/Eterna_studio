# Eterna Canvas API

Backend runtime is now **Schema Contract v0.3** with `SCHEMA_VERSION = "0.3.0"`.
`WorkflowV03`, `ResidentInstanceV03`, the node registry, and the rule-based audit
system are the single runtime path.

Legacy v0.2-shaped workflow payloads are accepted only at adapter boundaries and
are normalized into `WorkflowV03` before validation, audit, mock run, export, or
resident compilation. No v0.2 validator/mock-run/exporter is mounted as the main
API chain.

MVP boundary: no database, no real LLM calls, no TTS runtime, no AR runtime, and
no auth.

## Local Run

```bash
cd apps/api
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
uvicorn app.main:app --reload --port 8000
```

- API root: <http://127.0.0.1:8000/>
- Swagger Docs: <http://127.0.0.1:8000/docs>
- OpenAPI JSON: <http://127.0.0.1:8000/openapi.json>

## Runtime Routes

| Method | Path | Runtime |
|--------|------|---------|
| GET | `/health` | returns `schema_version = "0.3.0"` |
| GET | `/schema/workflow` | exports `WorkflowV03` JSON Schema |
| GET | `/schema/workflow-v0.3` | alias for `WorkflowV03` JSON Schema |
| GET | `/schema/resident-instance-v0.3` | exports `ResidentInstanceV03` JSON Schema |
| GET | `/schema/node-registry-v0.3` | exports v0.3 node registry |
| GET | `/templates/list` | template metadata |
| POST | `/templates/persona-builder` | returns v0.3 persona builder workflow |
| POST | `/workflow/validate` | normalizes to v0.3, runs audit, returns `WorkflowValidationResponseV03` |
| POST | `/workflow/audit` | normalizes to v0.3, returns `AuditReportV03` |
| POST | `/workflow/mock-run` | v0.3 mock runtime over `WorkflowV03` |
| POST | `/workflow/export-preview` | v0.3 DTO export preview |
| POST | `/resident/compile` | compiles `WorkflowV03` into `ResidentInstanceV03` |
| POST | `/resident/audit` | audits `ResidentInstanceV03` |
| POST | `/resident/preview` | returns resident preview `OutputDtoV03` |

## Runtime Source Files

```text
app/
├── schema_version.py          # SCHEMA_VERSION = "0.3.0"
├── models/v0_3.py             # WorkflowV03, NodeV03, ResidentInstanceV03, DTO boundaries
├── registry/node_registry.py  # v0.3 node registry
├── services/audit_v0_3.py     # node/module/layer/resident audit execution
├── services/workflow_v0_3.py  # adapter, template builder, mock runtime, resident compiler
└── routers/                   # mounted FastAPI routes
```

Legacy files such as `models/workflow.py`, `services/validator.py`,
`services/mock_runner.py`, `services/exporter.py`, and `services/persona_builder.py`
remain in the repo only for historical compatibility and are not mounted by the
main v0.3 API path.

## Data Boundaries

- UI state lives in `UiStateV03`.
- Execution context lives in `RuntimeContextV03`.
- Final output lives in `OutputDtoV03`.

Output DTOs must not embed workflow objects, node objects, runtime context,
component objects, or circular references.
