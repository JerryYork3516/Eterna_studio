# runtime_api_contract.md — Aftelle ↔ Runtime (sidecar)

> 作用:冻结 Aftelle(Swift)与本地 Python Runtime sidecar 之间的 HTTP 契约。
> 前提:G0 选 B(本地 Python sidecar,见 runtime_strategy.md)。
> 状态:**已冻结(FROZEN,2026-06-30),已与后端 6.11 `load-dr` / `step` 实际返回逐字段核对**。字段命名对齐 DR v0.3 的 lattice/voice/memory(见 dr_contract_v0_3.md)。

---

## 0. 约定

- 传输:本地 `http://127.0.0.1:<port>`,不走公网。
- 编码:UTF-8 JSON。
- 版本:每个响应带 `runtime_api_version`;Aftelle 定义 `minimum_supported_api_version`,不匹配则拒绝并提示。
- 当前 HTTP Runtime response `runtime_api_version = "6.11.0"`;`schema_version = "0.4.0"`;`runtime_version = "resident_v1_mock"`。
- DR 内 `runtime_requirements.runtime_api_version = "0.4.0"` 是 DR 运行要求字段,不等同于 HTTP Runtime API 版本。

---

## 1. POST /runtime/resident/load-dr —— 加载居民

**请求:**
```json
{
  "runtime_api_version": "6.11.0",
  "dr": { /* 完整 .digital_resident JSON,或本地路径 */ },
  "namespace": "default"
}
```

**响应:**
```json
{
  "runtime_api_version": "6.11.0",
  "schema_version": "0.4.0",
  "runtime_version": "resident_v1_mock",
  "ok": true,
  "resident_id": "schema_canvas",
  "dr_version": "0.3",
  "revision": "1",
  "loaded": {
    "identity": { "name": "...", "primary_language": "zh", "city_symbol": "..." },
    "lattice_state": { /* 初始 lattice state,见 §3 */ },
    "voice_profile": { "voice_id": "mock_voice", "speed": 1, "timbre": "neutral" },
    "memory_namespace": "default"
  },
  "diagnostics": {},
  "error": null
}
```

**错误响应(结构化,不暴露 Python exception):**
```json
{ "ok": false, "error": { "code": "DR_SCHEMA_INVALID", "message": "..." } }
```

---

## 2. POST /runtime/resident/step —— 跑一轮

**请求:**
```json
{
  "runtime_api_version": "6.11.0",
  "resident_id": "schema_canvas",
  "run_id": "run_xxx",
  "input_text": "你好",
  "namespace": "default"
}
```

**响应(对齐 DR v0.3 的 runtime_plan 链路):**
```json
{
  "runtime_api_version": "6.11.0",
  "schema_version": "0.4.0",
  "runtime_version": "resident_v1_mock",
  "ok": true,
  "resident_id": "schema_canvas",
  "run_id": "run_xxx",
  "status": "completed",
  "output_text": "...",
  "lattice_state": {
    "emotion": "neutral",
    "energy": 0.5,
    "attention": 0.5,
    "motion": "idle_breathing",
    "voice_state": "speaking",
    "particle_density": 0.5,
    "color_palette": ["#7aa2f7", "#5dd39e", "#f2a65a"],
    "focus_target": "none"
  },
  "visual_state": { /* equals lattice_state */ },
  "voice_state": "speaking",
  "memory_snapshot": {},
  "trace": [ /* 见 §4 */ ],
  "execution_trace": [ /* trace 的兼容别名,内容一致 */ ],
  "diagnostics": { "execution_mode": "mock" },
  "next_action": "none",
  "error": null
}
```

> 当前 Runtime response **返回 top-level `visual_state`**,其内容直接映射当前 `lattice_state`。Stage 7 MVP 仍以 `lattice_state` + `voice_state` 作为视觉状态输入来源,`visual_state` 只是顶层兼容字段。
> **流式**:`output_text` 在 sidecar 方案下,未来可优先用流式端点(SSE / chunked,见 §5)逐字接收,避免等全部生成。Stage 7 Entry Gate 当前只冻结 `/step` 非流式返回。
> `next_action` 当前恒为 `"none"`(Stage 7 单步);**为 Stage 8 Agent 多步循环预留**,Stage 7 不实现循环。

---

## 3. lattice_state / voice_state schema(= Stage 7 MVP visual input)

| 字段 | 类型 | 范围/示例 |
|---|---|---|
| emotion | string | "neutral" / 情绪枚举 |
| energy | number | 0–1 |
| attention | number | 0–1 |
| motion | string | "idle_breathing" 等 |
| voice_state | string | idle/speaking/listening/muted |
| particle_density | number | 0–1 |
| color_palette | string[] | hex 颜色数组 |
| focus_target | string | "none" 或目标 id |

---

## 4. trace schema(结构化事件,可扩展)

```json
{
  "trace": [
    { "event_type": "memory.read",   "ts": "...", "detail": {} },
    { "event_type": "llm.reasoning", "ts": "...", "detail": {} },
    { "event_type": "memory.write",  "ts": "...", "detail": {} },
    { "event_type": "lattice.update","ts": "...", "detail": {} },
    { "event_type": "voice.speak",   "ts": "...", "detail": {} }
  ],
  "execution_trace": [ /* 与 trace 内容一致,作为兼容别名 */ ]
}
```

> `trace` 是主字段,`execution_trace` 是兼容别名,两者内容一致。`event_type` 用可扩展枚举,当前对齐 runtime_plan 的步骤。**为 Stage 8 Agent 预留**:将来加 `tool_call` 等事件类型不需改 trace 结构。Aftelle Debug Panel 按 event_type 渲染。

---

## 5. (可选)流式端点

```
POST /runtime/resident/step/stream  → SSE / chunked
  data: {"delta":"你"}  data: {"delta":"好"}  ...  data: {"done":true,"lattice_state":{...},"voice_state":"speaking"}
```
Stage 7 Entry Gate 当前不依赖流式端点。未来 Aftelle 收到首个 delta 就开始出字 + 切 speaking 状态,实现"立刻开口"。最终事件带完整 lattice_state / voice_state。

---

## 6. 错误码(结构化,不暴露内部)

| code | 含义 |
|---|---|
| DR_SCHEMA_INVALID | DR 不合规/版本不支持 |
| RESIDENT_NOT_LOADED | step 前未 load-dr |
| PROVIDER_FAILED | LLM/TTS provider 失败(返回 fallback) |
| API_VERSION_UNSUPPORTED | 版本不匹配 |
| INTERNAL | 兜底,message 脱敏 |

---

## 7. 已核对清单(2026-06-30)

- [x] 后端 6.11 `load-dr` 实际返回已核对,响应带 `runtime_api_version = "6.11.0"`
- [x] 后端 `step` 实际返回 top-level `visual_state`,内容直接映射 `lattice_state`
- [x] `trace` 和 `execution_trace` 都存在,两者内容一致
- [x] `diagnostics` 存在;`memory_snapshot` 存在
- [x] 成功响应 `error = null`;失败/拒绝响应为结构化 error 对象
- [x] 实际 HTTP response `runtime_api_version = "6.11.0"`;DR 内 `runtime_requirements.runtime_api_version = "0.4.0"` 保持为 DR 运行要求字段

> 本文件已从"草案"改为"冻结"。Stage 7 MVP 的 `minimum_supported_api_version = "6.11.0"`。
