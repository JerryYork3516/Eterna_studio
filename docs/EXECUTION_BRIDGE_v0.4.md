# v0.4 Execution Orchestrator — Control Plane over v0.3 Runtime

`schema_version = "0.4.0"` · `protocol_version = "0.4.0"`. Additive, non-breaking.
**v0.3 remains the only execution core.** v0.4 is orchestration + schema +
control plane. The execution bridge is the single path from v0.4 to v0.3.

## Three layers

1. **v0.4 Control Plane** — Node / Slot / Module / Engine resolution, execution
   graph view, permission / risk / audit computation, decision routing.
2. **Execution Orchestrator** (new core) — receives a v0.4 workflow, resolves
   bindings, gates by risk, translates to a v0.3 plan, forwards. Executes nothing.
3. **v0.3 Runtime** (unchanged) — workflow mock-run, audit, compile, resident
   compile. All real execution logic lives here.

## Execution flow (strict)

```
v0.4 workflow
  │
  ▼
V4ExecutionOrchestrator        services/v4_orchestrator.py
  • parse v0.4 (or migrate v0.3 → v0.4 for fallback)
  • resolve Node → Slot → Engine            (registries)
  • compute permission / risk / audit       (permissions_v0_4)
  │
  ▼
V4ToV3Translator               services/v4_translator.py
  • v0.4 workflow → v0.3 workflow (lossless via extensions.legacy when present)
  │
  ▼
V3ExecutionAdapter             services/v3_execution_adapter.py
  • strict boundary: execute_plan(V4ExecutionPlan) is the ONLY entry to v0.3
  • refuses blocked plans (ExecutionBlockedError); reconstructs WorkflowV03
    from plan.v0_3_workflow and forwards
  │
  ▼
v0.3 Runtime (unchanged)       services/workflow_v0_3.py · audit_v0_3.py
  • mock-run / audit / compile
```

Boundary rule: the orchestrator never imports the v0.3 runtime and never calls
`run_v0_3` directly — it hands a `V4ExecutionPlan` to `execute_plan`. This is
enforced by a test that scans the orchestrator source.

If the risk gate blocks (high without permission / critical without human
confirmation), the orchestrator returns `executed=false` and does **not** forward
— critical actions are never silently executed.

## v0.4 → v0.3 mapping table

| v0.4 | v0.3 | Rule |
|------|------|------|
| `WorkflowV04` | `WorkflowV03` | prefer `extensions.legacy` (lossless); else rebuild from trunk |
| `NodeV04.node_id` | `NodeV03.id` | identity preserved |
| `NodeV04.node_type` | `NodeV03.type` | category resolved from node registry |
| `NodeV04.execution_status` | `NodeV03.status` | READY / MOCK / DISABLED |
| `NodeV04.input_schema/output_schema` | same | carried through |
| `NodeV04.inputs/outputs` | same | carried through |
| `NodeV04.slot_binding` | `NodeV03.metadata.slot_binding` | recorded, **not executed** |
| `NodeV04.module_id` | `NodeV03.metadata.module_id` | recorded |
| `NodeV04.layer_id` | `NodeV03.metadata.layer_id` | recorded |
| `EdgeV04` | `EdgeV03` | source/target preserved |
| `LayerRefV04` | `LayerV03` | layer_id / layer_name / order preserved (13-layer frozen) |
| `ModuleV04` (capability) | recorded in metadata | capability modules never become executable |
| legacy structural modules | `ModuleV03` | recovered from `extensions.legacy_modules` |
| `SlotV04` | runtime binding mapping | slot_id / engine recorded in node metadata |
| `EngineV04` | mock-compatible adapter | resolved descriptor only; provider = `mock`, never called |

## New endpoints (additive; `/workflow/*` and `/resident/*` untouched)

- `POST /protocol/plan` — control-plane plan only (resolve + gate + translate),
  does **not** forward to the runtime.
- `POST /protocol/execute` — full bridge: orchestrator → translator → adapter →
  v0.3 runtime. Body: `{ workflow, action: validate|audit|mock_run|compile }`.

## Guarantees

- v0.3 workflow validate / audit / compile / mock-run are byte-for-byte unchanged.
- mock-run output through the bridge is structurally identical to the direct
  v0.3 run (same order / node statuses / artifacts; only run_id/timestamps differ).
- A v0.4 workflow can always be downgraded (fallback) to run on v0.3.
- No real AI / provider call; the Engine layer resolves the mock provider only.
- The 13-layer trunk (layer_id / layer_name / layer_order) is never modified.
- Runtime check priority (legal/permission/audit → identity → capability →
  ui/output) is a runtime gate order, **not** the layer order.
