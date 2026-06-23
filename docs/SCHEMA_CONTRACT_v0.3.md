# Eterna Studio Schema Contract v0.3

Stage 4 promotes v0.3 to the backend runtime source of truth. It defines DTOs,
node input schemas, registry metadata, audit rules, mock runtime contracts, and
resident compilation without connecting LLM, TTS, AR runtime, or databases.

## Workflow Schema

`WorkflowV03` contains:

- `id`
- `name`
- `schema_version = "0.3.0"`
- `layers`
- `modules`
- `nodes`
- `edges`
- `metadata`

Legacy v0.2-shaped payloads may be accepted only at adapter boundaries and must
be normalized into `WorkflowV03` before any runtime operation.

## Node Schema

`NodeV03` contains:

- `id`
- `type`
- `label`
- `category`
- `status = READY | MOCK | DISABLED`
- `input_schema`
- `inputs`
- `output_schema`
- `outputs`
- `params`
- `ui`
- `metadata`

Inputs must be declared by `input_schema` or by the registry fallback. Outputs
must be JSON DTOs and must not include workflow, node, edge, runtime, executor,
or component references.

## Node Input Schema

Supported input field types:

- `text`
- `textarea`
- `number`
- `select`
- `multi_select`
- `slider`
- `boolean`
- `color`
- `json`
- `tags`
- `key_value`
- `file`

If no node-level or registry input schema exists, audit uses a fallback textarea
field and emits `INPUT_SCHEMA_FALLBACK`.

## Resident Instance Schema

`ResidentInstanceV03` contains:

- `identity`
- `personality`
- `dialogue`
- `voice_profile`
- `avatar`
- `metadata`

It is pure DTO, `JSON.stringify` safe, and must not embed workflow, node, edge,
runtime, executor, or component references. Stage 4 keeps voice/avatar metadata
as mock descriptors only.

## Node Registry

Each `NodeRegistryEntry` contains:

- `type`
- `category`
- `display_name`
- `description`
- `input_schema`
- `output_schema`
- `status`
- `mock_executor` as an optional string identifier
- `audit_rules`

`mock_executor` is not a callable. It is a contract label only.

## Audit System

All audit findings use:

```json
{
  "status": "PASS | WARNING | FAIL",
  "level": "node | module | layer | resident",
  "code": "string",
  "message": "string",
  "path": "string"
}
```

Audit layers:

- Node audit: schema compliance, missing inputs, illegal outputs, circular
  reference detection, stringified JSON detection, and status checks.
- Module/layer audit: disconnected nodes, input/output declaration matching,
  layer output completeness, and module output completeness.
- Resident audit: resident DTO completeness, JSON safety, runtime-reference
  prevention, and mock marker checks.

Safety scan is rule-based only and checks for impersonation, violence/illegal
guidance, self-harm, manipulation, hate, fraud/induced spending, sensitive
privacy collection, and claims of being a real human.

## API Contract

- `POST /workflow/validate`
- `POST /workflow/audit`
- `POST /resident/compile`
- `POST /resident/audit`
- `POST /resident/preview`

Schema export helpers:

- `GET /schema/workflow-v0.3`
- `GET /schema/resident-instance-v0.3`
- `GET /schema/node-registry-v0.3`

## Data Separation

v0.3 defines separate DTOs for:

- `UiStateV03`: frontend state only
- `RuntimeContextV03`: execution context contract only
- `OutputDtoV03`: final JSON output DTO only

Output DTOs must not contain UI state or runtime context.
