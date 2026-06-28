# Digital Resident (DR) v0.2 — Behavior Policy Spec

> **DR = POLICY LAYER, *NOT* RUNTIME LAYER.**
>
> A `.digital_resident` document is a **declarative** description of a
> schedulable persona. It is the standardized *input* that a future
> **Orchestration v0.1** will read. Reading a DR must **never** execute,
> schedule, or orchestrate anything. There is no scheduler, no DAG, no
> concurrency, no retry, and no execution code anywhere a DR is parsed.

| | Policy Layer (DR v0.2) | Runtime Layer (Stage 6 Kernel) |
|---|---|---|
| Role | declares intent / scheduling preference / capability | executes one mock resident step |
| Owns | configuration data | `execution_engine` / `trace` / `memory` / `state` |
| Acts? | **never** — pure data | yes (mock loop) |
| Changed by v0.2? | new | **unchanged** |

A DR carries two machine-readable markers that make this boundary explicit and
checkable:

```jsonc
"dr_layer": "policy",      // always "policy"
"not_executable": true     // a DR never runs; it is read by Orchestration
```

---

## 1. Status & scope

- **dr_version:** `0.2`
- **Supersedes:** v0.1 / v0.1.1 (strict superset — see §4 Backward compatibility)
- **Purpose:** turn the DR into a *parsable schedulable persona model* so
  Orchestration v0.1 has a stable input contract.
- **Out of scope (explicitly NOT in this stage):** scheduler, orchestration,
  execution, DAG, concurrency, retry, runtime decision-making. None of these are
  implemented, and the Runtime Kernel is not modified.

### Files

| File | Purpose |
|---|---|
| `apps/api/app/schemas/digital_resident_v0_2.py` | Pydantic type definitions (declarative models) + pure `upgrade_v0_1_to_v0_2` data mapper |
| `apps/api/app/schemas/digital_resident_schema_v0_2.json` | JSON Schema (draft 2020-12) for validation |
| `apps/api/app/models/digital_resident_v0_2_example.json` | A complete, valid example DR v0.2 |
| `docs/dr_v0_2_spec.md` | This spec |

---

## 2. Document structure

A DR v0.2 document is an object with **DR metadata** + **eight required policy
sections** + **optional v0.1 compatibility fields**.

### 2.1 DR metadata (markers)

| Field | Type | Notes |
|---|---|---|
| `file_type` | `"digital_resident"` | constant |
| `dr_version` | `"0.2"` | constant |
| `schema_version` | string | protocol schema version (e.g. `"0.4.0"`) |
| `protocol_version` | string | e.g. `"0.4.0"` |
| `dr_layer` | `"policy"` | **policy-layer marker** |
| `not_executable` | `true` | **DR never runs** |

### 2.2 The eight policy sections (all required)

All fields are **declarative configuration only**. No field implements behavior.

1. **`identity`** — who the resident is.
   `resident_id` (required), `name`, `role`, `description`, `disclosure`,
   `persona_summary`, `tags[]`.

2. **`intent_model`** — what the resident is *for*.
   `primary_intent`, `goals[]`, `conversation_style`, `tone`,
   `proactivity` (`passive` | `reactive` | `proactive` — a declared *disposition*,
   not a behavior switch), `domains[]`.

3. **`scheduling_policy`** — **read ONLY by Orchestration to plan.**
   Pure data; triggers nothing, starts no job, runs no timer.
   `schedulable`, `trigger_modes[]` (`on_message` | `on_event` | `on_schedule`),
   `priority` (`low` | `normal` | `high`), `concurrency_hint` (a hint, not a
   concurrency mechanism), `cadence` (`{type: none|interval|cron, value}` — a
   *descriptor* of cadence, not a scheduler), `max_turns_per_session`,
   `cooldown_seconds`, `notes`.
   > **`scheduling_policy` is data, not behavior.** An Orchestrator may parse it
   > to decide how to plan work. The DR itself never schedules anything.

4. **`execution_policy`** — how an orchestrator *should treat* the resident.
   Declaration, not execution. **No retry count, no DAG, no concurrency.**
   `execution_mode` (`mock`), `runtime_version`, `min_kernel`,
   `required_slot_types[]`, `engines[]`, `allow_tool_use` (declared permission),
   `determinism`, `timeout_hint_seconds` (hint), `on_error_preference`
   (`mock_fallback` | `halt` | `skip` — a declared *disposition string*, not a
   recovery mechanism).

5. **`capabilities`** — what the resident is *declared able* to use.
   `modules[]`, `slots[]`, `declared_capabilities[]` (descriptors only — never
   invoked).

6. **`memory_policy`** — declared memory configuration (no engine, no I/O).
   `provider`, `store`, `isolation`, `persistence`, `retention`, `scope`.

7. **`risk_policy`** — declared safety / governance posture.
   `disclosure_required`, `audit_required`, `human_confirm_required`,
   `risk_level` (`none`…`critical`), `blocked_modules[]`, `safety_boundaries[]`.

8. **`stability_constraints`** — invariants an orchestrator MUST respect.
   `max_context_items`, `max_output_length`, `immutable_layers[]`
   (default `["layer_1","layer_3"]`), `forbidden_transitions[]`, `invariants[]`.

### 2.3 v0.1 compatibility fields (optional)

`resident`, `layers`, `modules`, `slots`, `runtime_requirements`,
`memory_config`, `safety_policy`, `audit`, `compile_info` — preserved verbatim
from v0.1 so old data is never lost or broken (see §4).

---

## 3. Design rules (invariants)

- **Declarative only.** Every field is configuration data. No field triggers an
  action, and no parsing path executes behavior.
- **`scheduling_policy` is for Orchestration parsing.** It is the contract a
  future Orchestration v0.1 reads. It is not, and never becomes, a scheduler.
- **No execution semantics.** No DAG, concurrency, retry, or runtime decision
  logic is introduced by this schema or its mapper.
- **Runtime untouched.** The Stage 6 Runtime Kernel
  (`execution_engine` / `trace` / `memory` / `state`) is unchanged and does not
  import this schema.

---

## 4. Backward compatibility (v0.1 → v0.2)

v0.2 is a **strict superset** of v0.1:

- **No field conflicts.** v0.2 adds new sections; it never renames or removes a
  v0.1 field.
- **No data loss.** The v0.1 blueprint fields are kept under their original keys
  (`additionalProperties` is allowed at the root and in every section).
- **Pure upgrade mapper.** `upgrade_v0_1_to_v0_2(dr_v01: dict) -> dict` performs
  a **data-only** field mapping (identity ← resident, execution_policy ←
  runtime_requirements, capabilities ← modules/slots, memory_policy ←
  memory_config, risk_policy ← safety_policy; scheduling_policy /
  stability_constraints get safe defaults). It runs no behavior, schedules
  nothing, executes nothing.

```python
from app.schemas.digital_resident_v0_2 import upgrade_v0_1_to_v0_2, DigitalResidentV02

dr_v02 = upgrade_v0_1_to_v0_2(dr_v01_dict)   # data transform only
DigitalResidentV02.model_validate(dr_v02)    # validates clean
```

---

## 5. How Orchestration consumes a DR (informative, not implemented here)

A future Orchestration v0.1 will **read** a DR and build a plan from
`scheduling_policy` + `execution_policy` + `capabilities`, while honoring
`risk_policy` and `stability_constraints`. That planning logic lives in the
Orchestration layer — **not** in the DR and **not** in the Runtime Kernel.
Reading a DR is a parse; it does not run the resident.

---

## 6. Validation

```bash
cd apps/api
.venv/bin/python - <<'PY'
import json
from jsonschema import Draft202012Validator
from app.schemas.digital_resident_v0_2 import DigitalResidentV02

schema  = json.load(open('app/schemas/digital_resident_schema_v0_2.json'))
example = json.load(open('app/models/digital_resident_v0_2_example.json'))

Draft202012Validator.check_schema(schema)          # schema is valid
Draft202012Validator(schema).validate(example)     # example passes JSON Schema
DigitalResidentV02.model_validate(example)          # example passes Pydantic
print("DR v0.2 example is valid.")
PY
```
