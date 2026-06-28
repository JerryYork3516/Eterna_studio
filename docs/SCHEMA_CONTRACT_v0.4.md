# Eterna Studio — Schema Contract v0.4

> **本文件是 v0.4 阶段的唯一事实源(single source of truth)。**
> 它整合并取代散落在多处的版本说明,用于终结"0.3 还是 0.4""13 层什么顺序"的歧义。
> 所有代码、前端、文档若与本文件冲突,**以后端代码为准并回头修正本文件**;
> 本文件与后端代码必须保持一致。
>
> 来源文件:`models/v0_3.py`、`models/v0_4.py`、`SCHEMA_CONTRACT_v0.3.md`、
> `PROTOCOL_v0.4_BOUNDARIES.md`、`EXECUTION_BRIDGE_v0.4.md`。

---

## 0. 版本状态(最重要,先读这一节)

**双轨版本,这是有意设计,不是错误:**

| 轨道 | 版本 | 角色 | 文件 |
|------|------|------|------|
| 核心执行 schema | **0.3.0** | 唯一执行核心(运行合约) | `schema_version.py` = "0.3.0" / `v0_3.py` |
| 协议 / 控制层 | **0.4.0** | 叠加的控制平面(Stage 5 协议收敛) | `v0_4.py` (SCHEMA_VERSION_V0_4 / PROTOCOL_VERSION_V0_4) |

**关键约束(违反会炸 UI):**
- ❌ **不要**把 `schema_version.py` 强升到 0.4.0。核心 schema 保持 **0.3.0**。
- ❌ **不要**把核心执行逻辑迁到 v0.4。v0.3 runtime 保持不变(byte-for-byte)。
- ✅ v0.4 是 **additive(纯叠加、非破坏)**,只通过 migration + 新的 `/…-v0.4`、
  `/protocol/*` 端点接入。
- ✅ 版本号写 `"0.4.0"`,**不是** `"4.0"`。

一句话:**v0.3 负责"真正执行",v0.4 负责"控制/编排/协议",两者共存,前端依赖 0.3 的数据形状不变。**

---

## 1. 冻结的 13 层主干(CANONICAL_LAYERS)

> 权威源:`models/v0_4.py → CANONICAL_LAYERS`。
> `layer_id / layer_name / layer_order` **冻结,不得重排、不得重命名、不得增删**。

| layer_id  | layer_name             | order |
|-----------|------------------------|-------|
| layer_1   | Identity Core          | 1     |
| layer_2   | Personality            | 2     |
| layer_3   | Safety Boundary        | 3     |
| layer_4   | Legal Permission       | 4     |
| layer_5   | Memory                 | 5     |
| layer_6   | Knowledge              | 6     |
| layer_7   | World / Context        | 7     |
| layer_8   | Behavior               | 8     |
| layer_9   | Capability / Tools     | 9     |
| layer_10  | Multimodal             | 10    |
| layer_11  | Relationship           | 11    |
| layer_12  | Meta / Self-Reflection | 12    |
| layer_13  | Export / Deployment    | 13    |

**注意历史变更:** 早期 v0.2 曾以 "Source / Input" 打头,现已不存在。
**当前唯一正确顺序是上表(Identity Core 打头)。** 任何仍按 v0.2 顺序的文档/图均已过期。

**前端获取方式:** `GET /schema/module-catalog-v0.4` 返回 layers,必须等于上表。
前端只渲染,不自造层定义。

---

## 2. 运行时检查优先级 ≠ 层顺序(易混点,务必区分)

系统运行时的"门控顺序"(gate order)是:
```
1. Legal / Permission / Audit   ← 永远最先
2. Identity / Persona / Memory
3. Capability / Agent / Tool
4. UI / Output                  ← 只展示,无最终决策权
```

**这是运行时的检查优先级,与第 1 节的 13 层结构顺序是两回事,二者互不改变。**
- 13 层顺序(Identity=1…Export=13)= 结构骨架,冻结。
- 门控顺序(Legal/Permission/Audit 优先)= 执行时的安全检查次序。
- Agent / Tool / Wallet / Phone 等必须先过权限 + 风险检查,才能执行。

---

## 3. 绑定链(冻结)

```
Node  --slot_binding-->  Slot  --engine_binding-->  Engine  -->  Provider(mock)
```

- **Node** 编排执行;`Node.slot_binding` = 调用哪个 Slot;Node 不直接绑真实 provider。
- **Slot** 是被调用的能力接口;`Slot.engine_binding` = 绑定哪个 Engine/Provider;
  Slot 不直接调真实 API。
- **Module** 是能力容器;**不参与 workflow 执行,不写入 resident_instance**;
  必须绑定一个现有 `layer_id`。
- **Engine** 是真实能力适配层;Stage 5 只有 **LLM Mock Engine**
  (`engine_type="llm"`, `provider="mock"`)。

---

## 4. v0.3 核心契约(不变,摘要)

> 详见 `v0_3.py` / `SCHEMA_CONTRACT_v0.3.md`。此处仅列要点,提醒"这部分冻结不动"。

- `WorkflowV03`: id / name / schema_version="0.3.0" / layers / modules / nodes / edges / metadata
- `NodeV03`: id / type / label / category / status(READY|MOCK|DISABLED) / input_schema /
  inputs / output_schema / outputs / params / ui / metadata
- `ResidentInstanceV03`: identity / personality / dialogue / voice_profile / avatar / metadata
  (纯 DTO,JSON.stringify 安全,禁止内嵌 workflow/node/edge/runtime/executor/component 引用)
- 输出 DTO 三分离:`UiStateV03`(仅前端态)/ `RuntimeContextV03`(仅执行上下文)/
  `OutputDtoV03`(仅最终输出),不得互相混入。
- v0.3 API **保持不变、不删除**:
  `POST /workflow/validate` · `/workflow/audit` · `/resident/compile` ·
  `/resident/audit` · `/resident/preview`
  schema 导出:`/schema/workflow-v0.3` · `/schema/resident-instance-v0.3` · `/schema/node-registry-v0.3`

---

## 5. v0.4 协议层(Stage 5 新增)

> 详见 `v0_4.py` / `PROTOCOL_v0.4_BOUNDARIES.md`。

### 5.1 枚举
- `RiskLevel`: none / low / medium / high / critical
- `ProtocolStatus`(Module/Slot 生命周期): CORE / READY / MOCK / PLANNED / LATER / DISABLED
- `SlotType`(首批受限): llm / tts / memory / avatar / ar / tool
- `ExecutionMode`: mock / sync / async
- `OnError`: mock / next_provider / fail
- `EngineType`: **仅 llm**(Stage 5 限制)

### 5.2 Node Protocol(锁定)
`NodeV04`: node_id / node_type / input_schema / output_schema /
execution_status(默认 MOCK) / slot_binding / layer_id / module_id /
inputs / outputs / metadata。
- 所有 node_id 必须非空且唯一。

### 5.3 Module Protocol(能力容器)
`ModuleV04`: protocol_version / module_id / module_type / module_name /
module_version / layer_id(必须 ∈ CANONICAL_LAYER_IDS) / inputs / outputs /
config / permissions / risk_level / status / slot_type +
预留字段(本阶段仅声明,不实现复杂逻辑):audit_required / human_confirm_required /
runtime_enabled / is_placeholder / category / tags / color_status。
- Module 不参与执行、不写 resident_instance、module_id 唯一。
- **未来 Agent / Wallet / Phone / Social / Emergency Contact / AR 一律注册为 Module,
  绑定现有 layer,严禁写进核心协议。**

### 5.4 Slot Protocol(能力接口)
`SlotV04`: protocol_version / slot_id / slot_type / input_schema / output_schema /
provider / execution_mode / fallback_policy / status / engine_binding / enabled。
- `FallbackPolicy`: on_error(mock|next_provider|fail) / retry / fallback_provider。
- Slot 不直接调真实 API;slot_id 唯一。

### 5.5 Engine Registry
`EngineV04`: protocol_version / engine_id / engine_type(仅 llm) / engine_name /
supported_slot_types / providers(默认 ["mock"]) / status。
- Stage 5 仅 LLM Mock Engine,provider="mock",不读 API key,不调真实 AI。

### 5.6 v0.4 信封(Workflow / Persona)
`WorkflowV04` / `PersonaV04` 在保留 13 层 trunk 的前提下,新增能力面:
modules / inputs / outputs / permissions / risk_level / audit_log /
extensions / metadata。
- 新功能统一进 **modules / extensions / metadata**,不改核心 13 层。
- `extensions` 只放扩展配置;`metadata` 只放描述信息;功能逻辑不得泄漏到核心 schema 外。

---

## 6. 风险 → 门控规则

| risk_level | 规则 |
|------------|------|
| low        | 自动执行 |
| medium     | 允许,**必须记一条 audit_log** |
| high       | **执行前必须过权限检查**;审计 |
| critical   | **必须人工确认或拒绝;绝不静默执行**;审计 |

`AuditLogEntryV04` 只记事实(action_id / module_id / actor / input / output /
decision_reason / risk_level / permission_result / blocked_or_allowed /
timestamp / human_confirmed_by),可导出可追溯,**不参与任何 UI 展示逻辑**。

---

## 7. 执行桥(v0.4 控制平面 → v0.3 运行核心)

> 详见 `EXECUTION_BRIDGE_v0.4.md`。三层架构:

```
v0.4 workflow
  → V4ExecutionOrchestrator (services/v4_orchestrator.py)
      解析 v0.4 / 必要时 migrate v0.3→v0.4;解析 Node→Slot→Engine;算权限/风险/审计
  → V4ToV3Translator (services/v4_translator.py)
      v0.4 workflow → v0.3 workflow(优先用 extensions.legacy 无损还原)
  → V3ExecutionAdapter (services/v3_execution_adapter.py)
      唯一入口 execute_plan(V4ExecutionPlan);拒绝被 block 的 plan
  → v0.3 Runtime(不变):mock-run / audit / compile
```

**边界铁律:**
- Orchestrator **绝不** import v0.3 runtime、绝不直接调 `run_v0_3`,
  只把 `V4ExecutionPlan` 交给 `execute_plan`(有测试扫描源码强制此约束)。
- 风险门控 block 时(high 无权限 / critical 无人工确认)→ 返回 `executed=false`,
  **不转发**,critical 行为绝不静默执行。

**新端点(纯叠加,`/workflow/*` 与 `/resident/*` 不动):**
- `POST /protocol/plan` — 仅控制平面(解析+门控+翻译),**不转发**到 runtime。
- `POST /protocol/execute` — 全桥:orchestrator→translator→adapter→v0.3 runtime。
  body: `{ workflow, action: validate|audit|mock_run|compile }`。
- `GET /schema/protocol-version`
- `GET /schema/module-catalog-v0.4`
- `GET /schema/slot-catalog-v0.4`
- `GET /schema/engine-registry-v0.4`

---

## 8. 迁移(v0.3 → v0.4)

- `schema_version 0.3.0 → 0.4.0`;`protocol_version 0.4.0` 默认补齐。
- 旧 workflow/persona 自动迁移、绝不丢弃:legacy 负载存入
  `extensions.legacy_modules` / `extensions.legacy_resident`;
  补齐 modules / permissions / risk_level / audit_log / extensions / metadata 默认值。
- **迁移不改变 13 层语义。**
- v0.4 workflow 永远可降级(fallback)回 v0.3 运行。

---

## 9. 保证(Guarantees,可作验收)

- v0.3 的 validate / audit / compile / mock-run **逐字节不变**。
- 经桥的 mock-run 输出与直连 v0.3 **结构一致**(order / node status / artifacts 相同,
  仅 run_id / timestamp 不同)。
- 无任何真实 AI / provider 调用;Engine 层只解析 mock provider。
- 13 层 trunk(layer_id / layer_name / layer_order)**从不被修改**。
- 运行时门控顺序(legal/permission/audit → identity → capability → ui/output)
  是**运行时门控顺序,不是层顺序**。

---

## 10. 给所有协作方(你 / GPT / Claude / Cursor / Codex)的硬约束

1. 改任何东西前先读本文件,以它 + 后端代码为准,不凭记忆。
2. **不要**把 `schema_version.py` 升 0.4;核心保持 0.3.0。
3. **不要**重排 / 重命名 13 层;以 CANONICAL_LAYERS 为唯一权威。
4. 新功能 = 新 Module,绑定现有 layer;不写进核心协议。
5. 前端不自造 schema/层定义,一律从后端 `/schema/*` 取。
6. Stage 5 不接真实 AI;真实接入是 Stage 6 的事,且仍走绑定链 + 门控。
7. 本文件与后端代码若冲突,**改文件去对齐代码**(代码是运行真相),不要反过来改代码迁就过期文档。
