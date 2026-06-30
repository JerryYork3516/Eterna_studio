# Stage 6 Freeze Evidence — DR v0.3 Compile Stability

> Purpose: record whether the same canvas compiles into a structurally stable `.digital_resident` across repeated runs.
> Scope: evidence only. No new functionality, no schema changes.

## Test input

Canvas used for all 3 runs:
- Workflow name: `Aria Demo`
- Template type: `schema_v04`
- Nodes: 13 layers (`layer_1` ... `layer_13`)
- Edges: empty

## Method

The same canvas was compiled 3 times through `compile_dr_v0_3(...)`.
For each output, the following structural summary was compared:

- top-level DR keys
- `manifest` keys
- `payload` keys
- `slots` count
- `modules` count
- `13_layers_snapshot` count
- `required_capabilities`
- `runtime_requirements.runtime_api_version`
- `manifest.resident_id`
- `manifest.resident_name`

## Results

Run 1 summary:
- top-level keys: stable
- manifest keys: stable
- payload keys: stable
- slot count: `13`
- module count: `143`
- layer count: `13`
- required capabilities: stable
- runtime_api_version: `0.4.0`
- resident_id: `aria_demo`
- resident_name: `Aria Demo`

Run 2 summary:
- top-level keys: stable
- manifest keys: stable
- payload keys: stable
- slot count: `13`
- module count: `143`
- layer count: `13`
- required capabilities: stable
- runtime_api_version: `0.4.0`
- resident_id: `aria_demo`
- resident_name: `Aria Demo`

Run 3 summary:
- top-level keys: stable
- manifest keys: stable
- payload keys: stable
- slot count: `13`
- module count: `143`
- layer count: `13`
- required capabilities: stable
- runtime_api_version: `0.4.0`
- resident_id: `aria_demo`
- resident_name: `Aria Demo`

## Conclusion

**PASS** — the three compile outputs were structurally identical for the fields compared above.

Notes:
- This is evidence of stability for the tested canvas only.
- No claim is made about all possible canvases.
