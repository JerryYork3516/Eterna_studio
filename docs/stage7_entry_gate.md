# Stage 7 准入标准.md — Aftelle / Eterna Studio

> 作用:判定 Stage 6 是否做到了"能开 Stage 7 正式开发"的程度。不满足硬 Gate,只能做原型验证(7.1.0 标定),不进正式 Stage 7。
> 关系:本文件是开发计划 **G0 闸门**的展开 + 前置条件的细化。与开发计划、架构设计、Token 控制方案配套。

---

## 0. 总原则

- 后端可以不完美,但 **Runtime 契约必须稳定**。
- Studio 可以是早期版,但**必须能稳定产出可加载的 `.digital_resident`**。
- Aftelle 只能作为 **Runtime Host**,不能补后端架构的坑、不做第二个 Studio。

---

## ⚠️ 前置:本标准依赖一个未决的 G0 决策

本文件的 Gate 2/6/7 默认了 **Runtime 策略 = "复用后端,Aftelle 通过 HTTP 调 /runtime 接口"(sidecar 方案)**。

但 **G0 的 Runtime 策略三选一尚未拍板**:
- **A. Swift 重写最小 Runtime** → 则 Gate 2 的契约不是 HTTP 接口,而是 Swift 内部 Runtime 协议,需相应改写。
- **B. 本地 Python sidecar(本标准默认此项)** → 直接适用下方 HTTP 契约。
- **C. 只复用 DR schema、Runtime 重写** → 介于两者之间。

**进入本准入评估前,先在 DEVLOG 记下 G0 选了哪条。** 选 A/C 时,把下方"HTTP 接口"理解为"等价的内部 Runtime 调用契约",字段要求不变,形式改变。

---

## Gate 1:DR 编译必须稳定(硬)

必须满足:
1. Studio 能稳定编译出 `.digital_resident`
2. Compile DR 与 Export DR 已拆分
3. `valid=false` 时不允许导出
4. 导出的 DR 能被 Runtime(load-dr)读取
5. DR 不含 API Key / Base URL / Token / Credential

**验收**:同一 Canvas 连续编译 3 次,产物结构稳定;导出的 DR 可被 load-dr 成功加载。

---

## Gate 2:Runtime API 契约冻结(硬)

冻结两个核心调用(sidecar 方案下为 HTTP,其他方案下为等价内部契约):
- `load-dr`(加载居民)
- `step`(一轮运行)

必须有文档 `docs/runtime_api_contract.md`,至少定义:
request / response / error / trace / visual_state schema + `runtime_api_version`。

返回结构固定为(**字段以真实后端返回 + Studio 真实 DR 为准核对,不假设不存在的字段**):
```json
{
  "runtime_api_version": "0.1",
  "resident_id": "resident_xxx",
  "run_id": "run_xxx",
  "status": "completed",
  "output_text": "...",
  "resident_state": {},
  "visual_state": { "mode": "idle", "intensity": 0.5 },
  "memory_snapshot": {},
  "trace": [],
  "diagnostics": {},
  "error": null
}
```

**补充(原版缺)**:Aftelle 收到不认识的 `runtime_api_version` 时,**拒绝并明确提示**,不带病运行(定义 `minimum_supported_api_version`)。

**红线**:Runtime App 不允许依赖临时/未冻结字段。

---

## Gate 3:Execution Engine 边界不被破坏(硬)

必须满足:
1. Execution Engine 是唯一 runtime 入口
2. UI / Aftelle 不直接调 provider
3. Node / Module / Slot 不直接执行
4. DR Compiler 不触碰 Runtime Kernel
5. Runtime App 不重写 Runtime Kernel

**红线**:Aftelle 内不能重实现 execution_engine / dr_compiler;不能直接调 OpenAI/Claude/Qwen;不能把 API Key 写进 DR。

---

## Gate 4:后端去 AI 味到"契约层"(硬)

不用全后端重构,但接口层必须产品化:
1. 顶层字段命名稳定
2. mock 信息移入 `diagnostics`
3. 错误不暴露 Python exception(包装成结构化 error)
4. trace 是结构化事件,不是随便塞日志
5. response 含 `runtime_api_version`
6. response 含 `visual_state`

**禁止出现**:`maybe_output` / `some_debug_info` / `result_from_ai` / `mock_result` / `test_response` / 随手 debug 字段。

---

## Gate 5:最小自动化测试通过(软,可边做边补)

至少要有:
```
test_compile_dr_success / test_compile_dr_invalid_canvas
test_export_requires_valid_compile
test_load_dr_success / test_load_dr_invalid_schema
test_resident_step_success / test_resident_step_returns_trace / test_resident_step_returns_visual_state
test_no_api_secret_in_dr
test_runtime_entry_is_execution_engine
```
**要求**:后端测试全部通过,Runtime 关键接口测试不能跳过。

> **硬/软区分**:其中 `test_load_dr_success`、`test_resident_step_success`、`test_no_api_secret_in_dr`、`test_runtime_entry_is_execution_engine` 为**硬性必须**(直接关系命脉链路和安全);其余可在 7.1 早期边做边补,不卡总准入。

---

## Gate 6:Aftelle 只依赖契约,不依赖后端内部实现(硬)

必须写清 `docs/aftelle_runtime_boundary.md`:
```
Aftelle CAN:
- load local .digital_resident
- call load-dr / step(或等价内部契约)
- render output_text / trace / visual_state
Aftelle CANNOT:
- compile DR
- 复制后端逻辑做内部 schema 校验
- call provider directly
- own scheduler logic
- store provider secrets in resident file
```

---

## Gate 7:真实 LLM 可不接,但 Provider 位置必须对(软→硬)

进入 Stage 7 **不强制真实 LLM**,允许 mock LLM/memory/tool。
但**位置必须正确**:`Runtime Config → Provider Registry → Provider Adapter → Execution Engine`。
**禁止**:Aftelle Settings 直接调 OpenAI。Aftelle 只提供配置入口,真实调用走后端 provider adapter。

> 注:这条对应 G0 第三项"真实 LLM 来源"。Stage 7 MVP 可用 mock 跑通链路,但 7.4 居民打磨前必须接真实 LLM(mock 无法验证人格/套话)。

---

## Gate 8:首个 Demo 任务必须可闭环(硬)

进入 Stage 7 前,必须能写出并用现有后端支撑这个闭环:
```
打开 Aftelle.app → 导入 .digital_resident → load-dr 成功
→ 粒子居民出现 idle → 用户输入一句话 → step 返回 output_text
→ 粒子切换 thinking/speaking/idle → Debug Panel 显示 trace/diagnostics
```
**如果这个闭环不能用现有后端支撑,说明 Stage 6 还没冻结,不能进 Stage 7。**

---

## Stage 7 禁止事项(进入后)

进入 Stage 7 后**禁止同时做**:
1. 大改 DR schema  2. 大改 Execution Engine  3. 大改 Provider Registry
4. 重写 Runtime loop  5. 开始 AR  6. 开始 iOS/Android
7. 开始多居民复杂互动  8. 开始社交媒体自主操控

Stage 7 只做:**macOS Runtime Host MVP**。

---

## 最终准入判断

**硬 Gate(全满足才进正式 Stage 7):** Gate 1 / 2 / 3 / 4 / 6 / 8 + G0 三项决策已记录。
**软 Gate(可边做边补):** Gate 5 非核心测试、Gate 7 真实 LLM。

判断清单:
- [ ] G0 已拍板(Runtime 策略 / DR 字段对齐 / 真实 LLM 来源),记入 DEVLOG
- [ ] DR 能稳定编译(Gate 1)
- [ ] Runtime API/内部契约冻结 + 文档(Gate 2)
- [ ] Execution Engine 边界未破(Gate 3)
- [ ] 接口层去 AI 味(Gate 4)
- [ ] 核心测试通过(Gate 5 硬性部分)
- [ ] Aftelle 边界文档完成(Gate 6)
- [ ] Provider 位置正确(Gate 7)
- [ ] Demo 闭环可被现有后端支撑(Gate 8)

---

## 一句话

Stage 6 只要做到:**G0 拍板 + DR 可稳定生成 + Runtime 契约可稳定加载运行 + 契约层专业化 + 核心测试守住边界 + Demo 闭环跑得通**,就可以进 Stage 7;否则 Aftelle 会沦为替后端擦屁股。
