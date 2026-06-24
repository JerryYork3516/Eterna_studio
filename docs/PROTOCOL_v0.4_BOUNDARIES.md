# Protocol v0.4.0 — Boundaries & Binding Chain (Stage 5)

`schema_version = "0.4.0"` · `protocol_version = "0.4.0"` (not "4.0").

## Binding chain (frozen)

```
Node  --slot_binding-->  Slot  --engine_binding-->  Engine  -->  Provider(mock)
```

- **Node** orchestrates execution. `Node.slot_binding` = which Slot the node calls.
  A Node never binds a real provider directly.
- **Slot** is a *called* capability interface. `Slot.engine_binding` = which
  Engine/Provider the slot binds. A Slot never calls a real API.
- **Module** is a capability container. It does **not** participate in workflow
  execution and never writes into `resident_instance`.
- **Engine** is the real capability adapter layer. Stage 5 ships only the
  **LLM Mock Engine** (`engine_type="llm"`, `provider="mock"`).

## Hard rules

- **Stage 5 does not connect real AI.** No real LLM/TTS/Image/Video, no
  OpenAI/Claude/Gemini call, no API-key read.
- **New features register as modules only.** Wallet / Phone / Social / Emergency
  Contact / AR / Agent must be added to the Module catalog bound to an existing
  layer — never written into the core protocol.
- **`extensions`** holds extension configuration only; **`metadata`** holds
  descriptive information only; feature logic must not leak outside the core
  schema.
- **The 13-layer protocol is not modified this stage.** `layer_id`,
  `layer_name`, `layer_order` are frozen in `CANONICAL_LAYERS`.
- **Runtime check priority ≠ Layer order.** The runtime gate order is:
  1. Legal / Permission / Audit
  2. Identity / Persona / Memory
  3. Capability / Agent / Tool
  4. UI / Output

  Legal/permission/audit always precede capability execution. Agent / Tool /
  Wallet / Phone must pass permission + risk checks first. UI/Output only
  displays results and holds no final decision power. This ordering does not and
  must not change the frozen 13-layer order.

## Risk → gating rules

| risk_level | rule |
|------------|------|
| `low`      | auto execute |
| `medium`   | allowed, **must record an audit log entry** |
| `high`     | **must pass a permission check** before execution; audited |
| `critical` | **must be human-confirmed or rejected; never silently executed**; audited |

## Audit log

`high` / `critical` (and `medium`) actions must produce an `audit_log` entry.
The log records facts only (`action_id, module_id, actor, input, output,
decision_reason, risk_level, permission_result, blocked_or_allowed, timestamp,
human_confirmed_by`), is exportable/traceable, and is not part of any UI display
logic.

## Migration

`schema_version 0.3.0 → 0.4.0`; `protocol_version 0.4.0` is filled by default.
Old workflow/persona data is auto-migrated, never discarded: legacy payloads are
preserved under `extensions.legacy_modules` / `extensions.legacy_resident`, and
`modules / permissions / risk_level / audit_log / extensions / metadata` are
filled with defaults. Migration does not change 13-layer semantics.
