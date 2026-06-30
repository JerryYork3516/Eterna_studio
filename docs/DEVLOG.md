# DEVLOG.md — Stage Gate 冻结入口

历史详细开发日志见 `09_DEVLOG.md`。

## G0 决策

- Runtime 策略：B. 本地 Python sidecar，Aftelle 通过 HTTP 调 `/runtime`
- DR 字段对齐：以 Studio 导出的 DR v0.3 envelope + Runtime API 真实返回字段为准
- 真实 LLM 来源：Stage 7 MVP 可 mock；真实 LLM 只能走 Runtime Config → Provider Registry → Provider Adapter → Execution Engine；Aftelle 不直连模型

## Stage 6.11 Freeze

- Backend pytest：208 passed
- Web typecheck：passed
- 6.7 Memory：PASS
- 6.8 Lattice：PASS
- 6.9 Voice/TTS：PASS
- 6.10 Screen：PASS_WITH_UI_NODE_NOT_EXPOSED

## Stage 7 Gate

- Runtime 策略文档：`docs/runtime_strategy.md`
- Runtime API 契约：`docs/runtime_api_contract.md`
- DR v0.3 契约：`docs/dr_contract_v0_3.md`
- Provider Profile 契约：`docs/provider_profile_contract.md`
- Aftelle Runtime 边界：`docs/aftelle_runtime_boundary.md`
- 准入标准：`docs/stage7_entry_gate.md`

## 当前状态

等待 Cursor 重新验收 Stage 7 Entry Gate。
