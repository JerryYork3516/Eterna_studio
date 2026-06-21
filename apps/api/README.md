# Eterna Canvas — API (`apps/api`)

后端实现 **Schema Contract v0.2**（`SCHEMA_VERSION = "0.2.0"`，权威文档
[docs/SCHEMA_CONTRACT_v0.2.md](../../docs/SCHEMA_CONTRACT_v0.2.md)）。Pydantic
models 为唯一权威源；OpenAPI / JSON Schema 由 FastAPI 自动导出，前端用
`openapi-typescript` 生成 TS 类型。

v0.2 相对 v0.1 的增量（仅这些，无重构）：
- `ModuleTier = core | plugin | later` 枚举（§1.7），存于 `WorkflowNode.data.module_tier`。
- persona builder 13 层按 §8 表写死 `module_tier`；子模块节点默认 `null`。
- validator 新增主干层存在性规则（§3.1.1），**仅** `template_type == "persona_builder"` 启用。

MVP 边界：**不接数据库、不接真实 LLM、不做登录、不写前端**。

## 本地运行

```bash
cd apps/api
python3 -m venv .venv
source .venv/bin/activate
pip install -e .            # 或: pip install fastapi "pydantic>=2" "uvicorn[standard]"

uvicorn app.main:app --reload --port 8000
```

- API root: <http://127.0.0.1:8000/>
- Swagger Docs: <http://127.0.0.1:8000/docs>
- OpenAPI JSON: <http://127.0.0.1:8000/openapi.json>

## 端点（Contract §7）

| Method | Path | 说明 |
|--------|------|------|
| GET  | `/health` | 健康检查 |
| GET  | `/schema/workflow` | 导出 Workflow JSON Schema |
| GET  | `/templates/list` | 模板列表 |
| POST | `/templates/persona-builder` | 生成 13 层 persona 主干 |
| POST | `/workflow/validate` | 校验（package/layers/nodes ValidationReview） |
| POST | `/workflow/mock-run` | Mock Run（拓扑序执行，无真实调用） |
| POST | `/workflow/export-preview` | 导出预览（workflow_json / persona） |

## 目录

```
app/
├── main.py             # FastAPI 实例 + 路由挂载
├── schema_version.py   # SCHEMA_VERSION = "0.2.0" 单一来源
├── util.py             # now() / gen_id()
├── models/             # ★ Pydantic 唯一权威源
├── routers/            # health / schema / templates / workflow
├── services/
│   ├── completeness.py # ★ 节点完整性单点判定（validator 与 mock_runner 共用）
│   ├── validator.py    # ValidationReview（graph + node 检查）
│   ├── topo.py         # 拓扑排序 + 环检测
│   ├── mock_runner.py  # Mock Run 执行
│   ├── exporter.py     # export-preview
│   └── persona_builder.py  # 13 层模板生成器（§8）
└── data/locales/       # 层名兜底（zh / en）
samples/
├── persona-full.workflow.json   # ★ v0.2 完整 13 层参考样例（正向基线）
└── persona-demo.workflow.json   # 前3层联调 fixture（故意不完整，见下）
```

## 样例与校验语义（消除歧义）

两份 sample 用途不同，**不要混用**：

| 文件 | template_type | 结构 | `POST /workflow/validate` 期望 |
|------|---------------|------|--------------------------------|
| `persona-full.workflow.json` | `persona_builder` | 完整 13 层主干（persona_builder 生成器输出） | `package.status = warning`：13 个 core 层骨架为空 → 8 条 `empty_core_layer`(warning)，**0 error**。这是新建骨架的健康基线。 |
| `persona-demo.workflow.json` | `persona_builder` | **仅前 3 层 + 1 export**（阶段3 加载/保存联调 fixture） | `package.status = failed`：缺失的 core 层（4/6/7/8/10/13）→ `missing_trunk_layer`(error)；缺失 plugin 层（11/12）→ warning；存在但空的 core 层（1/2/3）→ `empty_core_layer`(warning)。 |

> **关键说明**：`persona-demo` 在 v0.1 校验为 `passed`，v0.2 校验为 `failed`，
> 这是 §3.1.1（V8 主干层存在性规则）的**预期行为**，不是回归缺陷——它本就是一个
> 故意不完整的 `persona_builder` 工作流，用于演示新规则在“核心主干层缺失”时报 error。
> 若要一份「能干净校验」的 persona 正向参考，请用 `persona-full.workflow.json`。
>
> 规则仅对 `template_type == "persona_builder"` 启用；通用 / 空白工作流不强制 13 层。
> mock-run / export-preview 不受主干层规则影响（它们仍只依赖 `completeness.py` 单点判定）。

## 关键约束

1. `models/` 是唯一权威源，OpenAPI 自动导出。
2. `services/completeness.py` 单点判定，validate 与 mock-run 结论一致。
3. `schema_version.py` 是 `SCHEMA_VERSION` 唯一来源（当前 `"0.2.0"`）。
4. Persona 13 层顺序、默认 lock_level、`module_tier` 固定（Contract §8），不可改。
5. 主干层期望 tier 的唯一来源 = `persona_builder.TIER_BY_INDEX`，validator 直接复用，不另维护副本。
