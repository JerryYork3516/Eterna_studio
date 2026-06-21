# Eterna Canvas — Schema Contract v0.2

> 状态：**合约 / 待 Claude Code 实现**（基于 v0.1，新增 module_tier 与主干层存在性 validate 规则）。
> 后端 Pydantic 为唯一权威源；前端按本合约导出的 OpenAPI / JSON Schema 对接。
> 本合约一经确认，字段变更须走版本号递增。
> **SCHEMA_VERSION 升级为 "0.2.0"。**

## v0.2 变更记录（相对 v0.1）
- **V7 新增 `module_tier` 字段**：`core | plugin | later`，**主干层与子模块节点都要有**。
  - 位置：`WorkflowNode.data.module_tier`。
  - 主干层（layer_container）的 tier 由后端按 §8 表写死默认值。
  - 子模块节点的 tier 字段存在，默认 `null`，由前端/用户设定。
  - 用途：后期打包、审核、导出、补全的依据（非纯视觉）。
- **V8 新增主干层存在性 validate 规则**：按 `layer_index` 1–13 判断（见 §3.1 规则表）。
- 13 层**顺序不变**，仍按 v0.1 §8。新 UI 图仅作前端布局参考，不作 schema 顺序依据。

## v0.1 变更记录（保留）
- M1 第13层 mixed lock；M2 LockLevel 新增 mixed（仅 layer_container）；
  M3 model 字段 LiteLLM 兼容；M4 ChangeApproval.diff 最小结构；
  M5 删除 LayerContainerData.lock_level（唯一权威 WorkflowNode.lock_level）；
  M6 title 拆 title_key + title_fallback。

---

## 0. 全局约定

- `schema_version`：所有核心顶层对象**必须**携带，字符串，**v0.2 为 `"0.2.0"`**。
- ID：`wf_*` / `nd_*` / `ed_*`，前缀 + 短 uuid。
- 时间：ISO-8601 UTC，如 `"2026-06-20T12:00:00Z"`。
- 图约束：workflow 是 **DAG**，无环；Mock Run 用**拓扑排序**。
- 语言：UI 走 i18n（不入数据）；persona 内容 MVP 语言无关，预留 `content_locale`（工作流级）/ `locale`（节点级，MVP 不启用）。

---

## 1. 枚举定义

### 1.1 NodeType
```
input | transform | model | agent | review | layer_container | output | export
```

### 1.2 NodeCategory
```
source | processing | ai | control | container | sink
```

### 1.3 LockLevel  ← M2
```
editable        # 自由编辑
review_required # 可改，改动须通过 ValidationReview
locked          # 改动须发起 ChangeApproval（审批 → 升版本 → 可回滚）
system_locked   # 系统级锁定，不可改、无法发起审批（如 audit_log 只追加）
mixed           # 仅 layer_container 可用；该容器实际编辑权限以其下级节点为准
```
> **约束**：`mixed` 只允许出现在 `type == layer_container` 的节点上。
> 出现在任何非容器节点上 → ValidationReview 报 `invalid_lock_level` (error)。

### 1.4 ReviewScope
```
node | layer | package
```

### 1.5 ReviewStatus / RunStatus
```
ReviewStatus: pending | passed | warning | failed
RunStatus:    pending | running | success | warning | error | skipped
```

### 1.6 ChangeApprovalStatus
```
draft | submitted | approved | rejected
```

### 1.7 ModuleTier  ← V7
```
core   # 核心必需：缺失=error，为空=warning
plugin # 可插拔：  缺失=warning，为空=ok
later  # 后期补充：缺失=ok，为空=ok
```
> 主干层与子模块节点均带此字段，存于 `WorkflowNode.data.module_tier`。
> 主干层 tier 由后端按 §8 写死；子模块 tier 默认 null，由前端/用户设。

---

## 2. 核心数据结构

### 2.1 Workflow（顶层）
```
Workflow {
  schema_version: str
  workflow_id: str
  name: str
  version: str
  template_type: str
  content_locale: str | null
  nodes: WorkflowNode[]
  edges: WorkflowEdge[]
  viewport?: Viewport
  metadata: WorkflowMetadata
  created_at: datetime
  updated_at: datetime
}
```

### 2.2 WorkflowMetadata
```
WorkflowMetadata {
  description?: str
  author?: str
  tags?: str[]
  ui_language?: str            // "zh"|"en"，仅记录界面语言
}
```

### 2.3 WorkflowNode  ← M6
```
WorkflowNode {
  node_id: str
  type: NodeType
  category: NodeCategory
  title_key: str               // i18n key，如 "layer.identity_core"
  title_fallback: str          // 缺失翻译/调试兜底，如 "身份核心层"
  position: { x: float, y: float }
  lock_level: LockLevel        // ★唯一权威（M5）。容器可为 mixed
  locale?: str | null          // 预留，MVP 不启用
  data: dict                   // 按 type 不同（见 §2.5）
  ports: { inputs: Port[], outputs: Port[] }
  validation?: ValidationReview
}
```

### 2.4 LayerContainerData  ← M5（已删除 lock_level）
```
LayerContainerData {
  layer_index: int             // 1..13
  description?: str
  status: str                  // "empty" | "in_progress" | "complete"
  version: str
  children_count: int
  validation?: ValidationReview
  change_approval?: ChangeApproval
}
```
> 注：layer 的锁定级别**不再**写在此处，统一读 `WorkflowNode.lock_level`。
> 当其为 `mixed` 时，真实编辑权限由该容器内各子节点各自的 `lock_level` 决定。

### 2.5 节点 data（按 type）

**model ← M3（LiteLLM 兼容命名）**
```
model: {
  provider?: str               // "openai" | "anthropic" | ...
  model?: str                  // "gpt-4o" | "claude-..." 
  api_base?: str
  temperature?: float
  max_tokens?: int
  system_prompt?: str
  user_prompt?: str
  response_format?: str        // "text" | "json_object" ...
}
```
> MVP 仅存储与回显，不发起真实调用。命名已对齐 LiteLLM，后期接入零改字段。

其余类型：
```
agent:  { tools?: str[], strategy? }
review: { scope: ReviewScope }
input:  { source_kind?: "text"|"file"|"api"|"manual" }
export: { format?: "workflow_json"|"persona" }
```

**所有节点 data 通用字段（V7）**
```
module_tier?: "core" | "plugin" | "later"
// 主干层(layer_container)：后端按 §8 写死，必填
// 子模块节点：默认 null，前端/用户设定
```

### 2.6 WorkflowEdge
```
WorkflowEdge {
  edge_id: str
  source: str
  source_port: str
  target: str
  target_port: str
}
```

### 2.7 Port / Viewport
```
Port    { port_id: str, name: str, direction: "in"|"out" }
Viewport{ x: float, y: float, zoom: float }
```

---

## 3. 两套审核机制（互不混用）

### 3.1 ValidationReview —— 格式/结构/完整性（系统自动）
```
ValidationReview {
  schema_version: str
  scope: ReviewScope
  status: ReviewStatus
  checks: ValidationCheck[]
  checked_at: datetime
}
ValidationCheck {
  rule: str          // missing_field | invalid_edge | orphan_node |
                     // cycle_detected | layer_required_field |
                     // invalid_lock_level | missing_trunk_layer |
                     // empty_core_layer ...
  level: "error" | "warning"
  target_id?: str
  message: str
}
```
> error 阻断（package status=failed）；warning 不阻断（status=warning）。
> validate 与 mock-run 共用同一节点完整性判定函数，结论一致。

#### 3.1.1 主干层存在性规则（V8）
> 按 `layer_index` 1–13 判断主干层是否存在（**不**按 title_key 判断）。
> 每层的期望 tier 见 §8 表。判定矩阵：

| 该层 tier | 缺失（layer_index 不存在） | 存在但 children_count=0 |
|-----------|---------------------------|------------------------|
| core      | `missing_trunk_layer` (error) | `empty_core_layer` (warning) |
| plugin    | `missing_trunk_layer` (warning) | ok（不报） |
| later     | ok（不报）                 | ok（不报） |

> 规则 rule 名：缺失统一 `missing_trunk_layer`，空 core 层 `empty_core_layer`。
> 仅对 `template_type == "persona_builder"` 的工作流启用本规则；
> 通用空白工作流不强制 13 层（保持平台通用性）。

### 3.2 ChangeApproval —— 核心层修改的人工审批  ← M4
```
ChangeApproval {
  schema_version: str
  approval_id: str
  target_kind: "node" | "layer"
  target_id: str
  status: ChangeApprovalStatus
  reason?: str
  diff?: ChangeDiff            // M4 最小结构
  resulting_version?: str
  created_at: datetime
}
ChangeDiff {                    // M4
  before: dict
  after: dict
  changed_fields: str[]
}
```

### 3.3 lock_level × ChangeApproval 联动
```
editable        → 直接改，仅事后 ValidationReview
review_required → 可改，改完须 ValidationReview 通过
locked          → 改动须先 ChangeApproval；approved 后升版本、可回滚
system_locked   → 不允许改，无审批入口
mixed (容器)    → 容器自身不直接持有编辑语义；逐子节点按各自 lock_level 判定
```

---

## 4. 运行结果（Mock Run）

```
RunResult {
  schema_version: str
  workflow_id: str
  status: RunStatus
  order: str[]                 // 拓扑序
  node_results: NodeRunResult[]
  artifacts: Artifact[]
  started_at: datetime
  finished_at: datetime
}
NodeRunResult {
  node_id: str
  status: RunStatus            // success|warning|skipped|error
  output: dict
  logs: RunLog[]
  duration_ms: int
}
RunLog   { ts: datetime, level: "info"|"warn"|"error", message: str }
Artifact { artifact_id: str, node_id: str, kind: str, name: str, preview: dict }
```
> 不完整节点 → warning 不崩；检测到环 → 整体 error + ValidationCheck.cycle_detected。

---

## 5. 模板与导出

```
TemplateDefinition {
  schema_version: str
  template_type: str
  name: str
  description?: str
  builder: str
}
ExportPreview {
  schema_version: str
  export_kind: "workflow_json" | "persona"
  content: dict
  warnings: str[]
}
```

---

## 6. i18n 与内容语言边界  ← M6

- 结构标签（层名/节点名/端口/按钮）→ UI i18n。节点持 `title_key`（渲染用）+ `title_fallback`（兜底/调试）。
- 用户填写的人格内容（存节点 data）→ 语言无关，不维护双语副本。
- `content_locale` / `locale` 预留但 MVP 不启用，一律 null。

---

## 7. API 请求 / 响应形状

### 7.1 `GET /health`
```
200 → { status: "ok", schema_version: "0.1.0" }
```

### 7.2 `GET /schema/workflow`
```
200 → JSON Schema（Pydantic 导出，前端生成 TS 类型）
```

### 7.3 `GET /templates/list`
```
200 → { templates: TemplateDefinition[] }
// blank / persona_builder / agent / knowledge_pipeline / review_pipeline
```

### 7.4 `POST /templates/persona-builder`
```
req → { name?: str, ui_language?: "zh"|"en" }
200 → { workflow: Workflow }   // 13 层主干（§8）
```

### 7.5 `POST /workflow/validate`
```
req → { workflow: Workflow }
200 → { package: ValidationReview, layers: ValidationReview[], nodes: ValidationReview[] }
```

### 7.6 `POST /workflow/mock-run`
```
req → { workflow: Workflow }
200 → { run: RunResult }
```

### 7.7 `POST /workflow/export-preview`
```
req → { workflow: Workflow, export_kind: "workflow_json"|"persona" }
200 → { preview: ExportPreview }
```

---

## 8. Persona Builder —— 13 层默认结构  ← M1 / V7

> 顺序保持不变（v0.2 仅加 tier，不重排）。tier 列为 V7 新增，后端写死。

| #  | title_key                   | title_fallback   | 默认 lock_level | module_tier |
|----|-----------------------------|------------------|-----------------|-------------|
| 1  | layer.source_input          | 资料输入层       | editable        | core        |
| 2  | layer.identity_core         | 身份核心层       | locked          | core        |
| 3  | layer.legal_permission      | 授权权限层       | locked          | core        |
| 4  | layer.safety_boundary       | 安全边界层       | locked          | core        |
| 5  | layer.world_context         | 世界观环境层     | review_required | later       |
| 6  | layer.personality           | 人格层           | review_required | core        |
| 7  | layer.memory                | 记忆层           | review_required | core        |
| 8  | layer.knowledge             | 知识层           | editable        | core        |
| 9  | layer.relationship          | 关系层           | review_required | later       |
| 10 | layer.behavior              | 行为层           | review_required | core        |
| 11 | layer.capability_tools      | 能力工具层       | editable        | plugin      |
| 12 | layer.multimodal            | 表现层           | review_required | plugin      |
| 13 | layer.audit_export_deploy   | 审计输出部署层   | **mixed**       | core        |

### 8.1 第13层 mixed 子节点锁定（M1）
该层 `lock_level = mixed`，其下子节点各自锁定：
```
audit_log         → system_locked   # 只追加
version_snapshot  → system_locked   # 只追加
export_workflow   → editable
export_persona    → editable
deploy_target     → review_required
```
> 校验规则：mixed 容器**必须**至少含一个子节点；否则 ValidationReview 报 `mixed_empty` (warning)。

---

## 9. 后端落地文件结构（apps/api）

```
apps/api/
├── pyproject.toml              # 依赖：fastapi, pydantic, uvicorn
├── README.md                   # 本地运行说明
├── app/
│   ├── main.py                 # FastAPI 实例 + 路由挂载
│   ├── schema_version.py       # SCHEMA_VERSION = "0.1.0" 单一来源
│   ├── models/                 # ★ Pydantic 唯一权威源
│   │   ├── __init__.py
│   │   ├── enums.py            # NodeType / NodeCategory / LockLevel / ...
│   │   ├── workflow.py         # Workflow / WorkflowNode / Edge / Port / Viewport
│   │   ├── layer.py            # LayerContainerData
│   │   ├── review.py           # ValidationReview / ValidationCheck
│   │   ├── approval.py         # ChangeApproval / ChangeDiff
│   │   ├── run.py              # RunResult / NodeRunResult / RunLog / Artifact
│   │   ├── template.py         # TemplateDefinition
│   │   └── export.py           # ExportPreview
│   ├── routers/
│   │   ├── health.py           # GET /health
│   │   ├── schema.py           # GET /schema/workflow
│   │   ├── templates.py        # GET /templates/list, POST /templates/persona-builder
│   │   └── workflow.py         # POST /validate, /mock-run, /export-preview
│   ├── services/
│   │   ├── validator.py        # ValidationReview 逻辑（node/layer/package）
│   │   ├── completeness.py     # ★ 节点完整性判定（validate 与 mock-run 共用）
│   │   ├── topo.py             # 拓扑排序 + 环检测
│   │   ├── mock_runner.py      # Mock Run 执行
│   │   ├── exporter.py         # export-preview（workflow_json / persona）
│   │   └── persona_builder.py  # 13 层模板生成器（§8）
│   └── data/
│       └── locales/            # 模板层名兜底（与前端 i18n 对齐）
│           ├── zh.json
│           └── en.json
└── samples/
    └── persona-demo.workflow.json   # 阶段3联调样例（已同步 M6 字段）
```

> 关键约束：
> 1. `models/` 是唯一权威源；OpenAPI 由 FastAPI 自动导出，前端用 openapi-typescript 生成 TS。
> 2. `services/completeness.py` 是单点判定，validator 与 mock_runner 都 import 它。
> 3. `schema_version.py` 是 SCHEMA_VERSION 的唯一来源，所有对象引用它。
