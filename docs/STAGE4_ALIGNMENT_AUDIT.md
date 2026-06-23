# Eterna Studio — Stage 4 → Stage 5 全栈对齐审计

> 审计目标：验证后端是否完全升级到 v0.3 单轨系统，前端是否完全基于 v0.3
> schema / registry / DTO 对齐，从而判定是否为真正的「单一数据源系统」。
>
> 审计方式：静态源码核查 + 后端 TestClient 冒烟 + 前端 `tsc` typecheck。
> 不接真实 LLM / TTS / Runtime / DB。

审计日期：2026-06-23 ｜ 分支：main ｜ SCHEMA_VERSION：`0.3.0`

---

## 一、后端检查

### 1. Schema 单轨化 — ✅ PASS

| 项 | 结论 | 证据 |
|----|------|------|
| `SCHEMA_VERSION == 0.3.0` | ✅ | `apps/api/app/schema_version.py:6` |
| v0.3 为唯一运行 schema | ✅ | 所有 router 走 `services/workflow_v0_3.py` + `services/audit_v0_3.py`；权威 DTO 在 `models/v0_3.py` |
| 是否仍存在 v0.2 workflow runtime | ⚠️ 残留但未挂载 | `services/{validator,mock_runner,persona_builder,completeness,exporter}.py` 仍存在，但**无任何 router / main / v0_3 服务引用**（仅彼此互相 import）。属于 orphan/dead code，非活动双运行时。 |

`models/workflow.py:1` 头注释已声明其为 legacy adapter shape：
> "Runtime source of truth is WorkflowV03 in app.models.v0_3."

`models/run.py`、`models/export.py`（`RunResult` / `Artifact` / `ExportPreview`）仍被
v0.3 服务复用为响应外壳，属于有意保留，非孤儿。

**判定：v0.3 单轨运行成立；v0.2 仅以孤儿模块形式残留（清理债，非阻断项）。**

### 2. API 完整性 — ✅ PASS（5/5 真实存在且返回 v0.3 DTO）

TestClient 实测（`app.main:app`）：

| API | 路由实现 | 状态 | 返回 DTO |
|-----|----------|------|----------|
| `POST /workflow/validate` | `routers/workflow.py:27` | 200 | `WorkflowValidationResponseV03`（`valid` + `AuditReportV03`，`schema_version=0.3.0`） |
| `POST /workflow/audit` | `routers/workflow.py:33` | 200 | `{ audit: AuditReportV03 }` |
| `POST /resident/compile` | `routers/resident.py:38` | 200 | `ResidentCompileResponseV03` |
| `POST /resident/audit` | `routers/resident.py:46` | 200 | `{ audit: AuditReportV03 }` |
| `POST /resident/preview` | `routers/resident.py:50` | 200 | `ResidentPreviewResponseV03`（`OutputDtoV03`） |

附加：`/schema/workflow-v0.3`、`/schema/resident-instance-v0.3`、`/schema/node-registry-v0.3`
（`routers/schema.py`）均真实导出 v0.3 JSON Schema / registry。

### 3. Resident Runtime 接入 — ✅ PASS（合约层）

- `resident_instance` 由后端 `compile_resident_from_workflow()` 生成
  （`services/workflow_v0_3.py:317`），从 workflow 节点聚合为 `ResidentInstanceV03`。
- 无独立 runtime pipeline（符合 Stage 4 限制：不接真实 runtime）。
- 无 mock-only / orphan model 进入 resident 输出：所有字段经 DTO 收敛，
  `metadata.mock / voice_profile.mock / avatar.mock = true` 明确标记。

### 4. Node Registry 完整性 — ✅ PASS

- `app/registry/node_registry.py` 覆盖 **30 个 node type**（含 layer_container / persona /
  media / model / runtime / sink / legacy 兼容类型）。
- 每个 entry 含 `input_schema`（12 种控件枚举 `NodeInputType`）、`output_schema`
  （纯 DTO 字段，`type ∈ string|number|boolean|object|array|null`）、`status`、
  `mock_executor`（**字符串标识符**，保证 registry JSON 可序列化、无 callable/循环引用）、
  `audit_rules`。
- 无 input_schema 的节点不静默通过：审计走 `FALLBACK_INPUT_SCHEMA` 并发
  `INPUT_SCHEMA_FALLBACK`(warning)（`services/audit_v0_3.py` audit_node）。
- status 统一 `READY / MOCK / DISABLED`（`NodeStatus` 枚举）。

### 5. Audit System — ✅ PASS（真实规则执行，非纯 schema）

三层审计为**真实运行逻辑**，非声明式 schema：

- **Node Audit**（`audit_node`）：schema 合规、必填输入缺失、输入类型匹配、
  非法字段、`outputs` 必须为 dict DTO、JSON 安全、循环引用（`id()` 遍历检测）、
  stringified JSON 检测、状态与 registry 比对、安全规则扫描。
- **Module/Layer Audit**（`audit_modules_and_layers`）：断链节点、边端点缺失、
  边 input/output 未声明、**Kahn 拓扑环检测**、module/layer 引用未知 node、
  layer/module 输出完整性。
- **Resident Audit**（`audit_resident`）：6 必需段存在、identity/personality 完整性、
  mock 标记、`JSON.stringify` 安全、runtime/node/workflow 引用禁令、安全扫描。

实测 persona-builder 生成的 v0.3 workflow：`validate.valid=True`、`audit.status=PASS`、
resident compile→audit→preview 全 PASS、resident_instance `json.dumps` 安全（无循环）。

> **后端结论：v0.3 READY ✅**

---

## 二、前端检查

### 1. Node Source 单一性 — ❌ NOT ALIGNED

- 前端仍使用**硬编码本地注册表** `apps/web/src/registry/nodeRegistry.ts`（30 个
  `def(...)` 条目，每个自带本地 `execute` mock 执行器）。
- **不消费** `GET /schema/node-registry-v0.3`（前端全仓无该端点调用）。
- 存在**双 registry**：前端 `nodeRegistry.ts` ↔ 后端 `node_registry.py`，各自维护。

### 2. Input Schema 驱动 UI — ❌ NOT schema-driven（前端独立来源）

- 节点输入 UI 由前端硬编码 `apps/web/src/registry/nodeInputs.ts` 渲染
  （`WorkflowNodeCard.tsx:6,135` `getNodeInputSchema`）。
- 前端只实现 **6 种控件**（text/textarea/number/select/slider/boolean），
  后端 `input_schema` 定义 **12 种**（多出 multi_select/color/json/tags/key_value/file）。
- **不消费**后端 `input_schema`；属第二套手写 schema。

### 3. Output DTO 来源一致性 — ❌ NOT ALIGNED（核心问题）

- 前端在**本地执行** workflow：`CanvasShell.tsx:3854 executeWorkflow(...)`，
  使用 `engine/executeWorkflow.ts` + 本地 `nodeRegistry` 执行器。
- `resident_instance` 由前端本地 `buildResidentInstance()`
  （`nodeRegistry.ts`）合成，经 `extractResidentInstance`（`CanvasShell.tsx:277,2027`）
  注入 Resident Preview 面板。
- **完全绕过** `POST /resident/compile`（前端全仓无该端点调用）。
- 两份 resident DTO 形状不一致：前端版含 `voice_profile.pitch/timbre`、
  `avatar.density/motion`，**缺** `identity.disclosure`、`metadata`、统一 `mock` 标记；
  后端 `ResidentInstanceV03` 才是合约权威形。→ **DTO 双源 + 前端二次加工/补全。**

### 4. 状态系统一致性 — ⚠️ PARTIAL（值大体一致，但来源独立）

- 前端 `NodeStatus` 与后端 `READY/MOCK/DISABLED` 枚举值一致，且多数节点状态吻合。
- 但前端状态为硬编码字面量，**非从 backend registry 同步**；存在漂移风险
  （任一侧改动不会传导）。无前端自定义新状态值。

### 5. 数据流一致性 — ❌ 双数据源 / 前端绕过 backend

实际链路：

```
text_input → nodes → 【前端 executeWorkflow 本地 mock】 → resident_instance（前端 buildResidentInstance）→ 前端 preview
```

而非要求的：

```
text_input → nodes → 【backend /resident/compile】 → resident_instance → frontend preview
```

前端确实调用后端的 `validate / mock-run / export-preview / templates`
（`api.ts`），但**核心产物（resident_instance）链路完全在前端本地完成**，
未触达 `/resident/compile`、`/resident/preview`、`/resident/audit`、`/workflow/audit`。

> **前端结论：PARTIALLY ALIGNED**（校验/运行/导出走后端；节点库、输入 schema、
> resident 产物三处为独立前端源）。按「只接受单一真相源」的判据，核心 resident
> 数据流判定为 **NOT ALIGNED**。

---

## 三、对齐判定

| 维度 | 判定 |
|------|------|
| **Backend** | **v0.3 READY** ✅ |
| **Frontend** | **PARTIALLY ALIGNED**（resident 核心链路 NOT ALIGNED）|

---

## 四、风险分析

1. **双 schema 风险（v0.2 vs v0.3）**
   - 后端 v0.2 服务（validator/mock_runner/persona_builder/completeness/exporter）
     仍在仓库，孤儿但可被误引用。
   - 前端内部 workflow 模型仍是 **v0.2 形状**（`node_id` / `lock_level` / `ports` /
     `title_key` / `data`，见 `schema-types.ts` `Workflow` 与 `executeWorkflow.ts`），
     仅在发送时 stamp `schema_version:"0.3.0"`，由后端 `normalize_workflow_v0_3`
     适配。→ 前端 v0.2 形 / 后端 v0.3 形并存，靠 adapter 桥接。

2. **UI / backend data drift**
   - 输入控件：前端 6 种 vs 后端 12 种，schema 不同步。
   - 节点库与状态：两套独立维护，改一侧不传导。

3. **DTO 污染风险**
   - 前端 `buildResidentInstance` 自行补全字段、形状与后端权威 DTO 不一致；
     前端版缺 `disclosure` / `metadata` / 统一 `mock` 标记，安全边界字段弱于后端。

4. **registry 不一致风险**
   - 前端 `nodeRegistry.ts` 与后端 `node_registry.py` 同名不同源，长期必然漂移。

5. **audit 假执行风险** — 低
   - 后端三层 audit 为真实规则逻辑（实测有 finding 产出与 PASS/FAIL 流转），
     非假执行。但**前端不触发后端 audit**，用户在 UI 看到的产物未经后端审核。

6. **测试覆盖风险**
   - 仓库**无任何自动化测试**（无 pytest / 无 test 文件）。当前验证依赖
     一次性 TestClient 冒烟与 typecheck，无回归保护。

---

## 五、最终结论：**CONDITIONAL READY**

后端已达 Stage 5 起步标准；前端尚未收敛为单一真相源。进入 Stage 5（接真实
LLM / TTS / Memory / AR Runtime）**前必须**完成以下收敛项，否则会出现「能跑但
前后端各自为政」的双源系统：

**必修项（阻断 Stage 5）**

1. 前端节点库改为消费 `GET /schema/node-registry-v0.3`，删除 `nodeRegistry.ts`
   硬编码定义（或降级为纯 fallback）。
2. 前端输入 UI 改由后端 `input_schema` 驱动，补齐缺失的 6 种控件
   （multi_select/color/json/tags/key_value/file），废弃 `nodeInputs.ts` 独立 schema。
3. Resident 产物链路改为调用 `POST /resident/compile`（必要时 `/resident/preview`），
   移除前端 `buildResidentInstance` 二次合成；前端只渲染后端返回的
   `ResidentInstanceV03`，预览前过 `/resident/audit` 或 `/workflow/audit`。
4. 前端内部 workflow 模型迁移到 v0.3 形（`WorkflowV03`），减少 adapter 依赖。

**建议项（非阻断）**

5. 删除/归档后端孤儿 v0.2 服务，消除双 schema 误用面。
6. 补最小回归测试（后端 pytest 覆盖 5 个 v0.3 端点 + audit 规则；前端保留 typecheck）。

---

## 验证记录

- 后端：`app.main` 导入正常；TestClient 冒烟 14 条路由，5 个 v0.3 端点全部 200 且
  返回 `schema_version=0.3.0`；persona-builder workflow validate/audit/compile/
  resident-audit/preview 全 PASS；resident_instance `json.dumps` 无循环。
- 前端：`npm run typecheck`（`tsc --noEmit`）通过，0 错误。
- 测试：仓库无自动化测试套件。
