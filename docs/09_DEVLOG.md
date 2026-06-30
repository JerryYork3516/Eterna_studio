# DEVLOG.md — Aftelle 开发日志(给我自己看)

> 这份是给我自己的,不是给 AI 自动读的。
> 三个作用:① 提醒我做到哪、为什么这么定;② 每次开 GPT/Dify/新对话时,把"当前状态"那段粘过去当背景;③ 防止我忘了当初的决定又推翻重来。
> **规则:每次做完一件事、或讨论出一个结论、或改完一个 bug,就来记一笔。不用长,几行即可。**

---

## 📌 当前状态(每次更新,粘给 AI 时就粘这一段)

- **现在在做**:Stage 7.x —— [一句话:具体哪一步]
- **上一步刚完成**:[做完了什么]
- **当前卡在**:[如果有卡点,写在这;没有就写"无"]
- **下一步**:[接下来要做什么]
- **额度情况**:[这周大概用了多少 / 还够不够]

> - **现在在做**: Stage 7 Entry Gate —— 补齐正式进入 Stage 7 前的冻结文档与准入验收
> - **上一步刚完成**: Stage 6.11 Freeze Audit，后端 pytest 208 passed，前端 typecheck passed，6.7–6.10 手动验收完成
> - **当前卡在**: Stage 7 Gate 缺少冻结文档：DEVLOG.md、runtime_api_contract.md、aftelle_runtime_boundary.md
> - **下一步**: 补齐 Gate 文档后，让 Cursor 重新验收 Stage 7 Entry Gate
> - **额度情况**: 进入 Stage 7 前先控 token，只做文档冻结，不改代码---

## ✅ 我现在要做的事(开工清单,做完打勾)

进 7.1 之前:

- [x] **【G0·已拍板】Runtime 策略：B. 本地 Python sidecar，Aftelle 通过 HTTP 调 /runtime** ← 只有我能定
- [x] **【G0·已拍板】DR 字段对齐：以 Studio 导出的 DR v0.3 envelope + Runtime API 6.11.0 实际返回字段为准**
- [x] **【G0·已拍板】真实 LLM 来源：Stage 7 MVP 可 mock；真实 LLM 只能走 Runtime Config → Provider Registry → Provider Adapter → Execution Engine；Aftelle 不直连 OpenAI/Claude/Qwen**
- [ ] 把 `Agent.md` 改成正确的 `AGENTS.md`
- [ ] 建 GitHub/Gitee **私有**仓库,放进全部文档,锁好 .gitignore(密钥/真实DR不进库)
- [ ] 做 2-3 个测试 DR fixture(1 个正常 + 1 个错误 + 空壳)
- [x] Stage 6 收尾完成：DR v0.3 Contract Freeze 已完成，Aftelle 读取字段以后以 docs/dr_contract_v0_3.md 为准
- [ ] 开工首日锁定技术栈版本(Swift / Xcode / 最低 macOS),写进仓库
- [ ] 用 Claude Code `/status` 确认我的额度和计费方式

进 7.1 后:

- [ ] 搭空 Xcode 项目,放约 10 个粒子
- [ ] 走通:加载 DR → 改粒子逻辑 → 看到变化
- [ ] 记下:7.1 花了多少额度、AI 读了多少文件、卡在哪 → 用它外推整个 Stage 7

---

## 📒 决策记录(重要的决定记在这,防止以后忘了又推翻)

> 格式:**日期 — 决定了什么 — 为什么**

- 2026-06-30 — G0 Runtime 策略拍板：选 B，本地 Python sidecar，Aftelle 通过 HTTP 调 `/runtime` — Stage 7 先做 macOS Runtime Host MVP，不重写后端 Runtime Kernel，避免 Aftelle 变成第二个 Studio。
- [继续往下记...]
- 2026-06-30 — G0 DR 字段对齐拍板：以 Studio 导出的 DR v0.3 envelope + Runtime API 6.11.0 实际返回字段为准 — 不再按旧 v0.1/v0.2 或假设字段设计 Aftelle。
- 2026-06-30 — G0 真实 LLM 来源拍板：Stage 7 MVP 可用 mock；真实 LLM 只能走 Runtime Config → Provider Registry → Provider Adapter → Execution Engine — Aftelle 不直连 OpenAI/Claude/Qwen，不保存 provider secret。
- 2026-06-30 — Stage 6.11 Freeze Audit 通过 — 后端 pytest 208 passed，前端 typecheck passed；6.7 Memory PASS，6.8 Lattice PASS，6.9 Voice/TTS PASS，6.10 Screen PASS_WITH_UI_NODE_NOT_EXPOSED。
- 2026-06-30 — Stage 7 Entry Gate 初验未通过正式准入 — 代码链路与测试基本通过，但缺少 Gate 冻结文档：`DEVLOG.md`、`docs/runtime_api_contract.md`、`docs/aftelle_runtime_boundary.md`。
- 

---

## 🐛 Bug 记录(修好的 bug 记一笔,下次遇到类似的不用重新踩坑)

> 格式:**问题 — 原因 — 怎么修的**

- [示范] DR 加载报错 — 原因是 fixture 缺了 schema_version 字段 — 给 fixture 补上字段后正常

---

## 💬 讨论结论(在 GPT/Dify 讨论完,把结论搬到这)

> 格式:**日期 — 讨论了什么 — 结论是什么**

- 2026-XX-XX — 问了三家 AI 评估整套方案 — 共识:体系扎实,唯一风险是准备过头不开工;补了粒子盲测、文件白名单、commit保险三个执行层漏点
- [继续往下记...]

---

## 🅿️ 以后再说(现在不做的需求/想法,攒在这,别打断当前进度)

> 任何"想到但现在不该做"的,扔这里,别立刻去做

- 双居民复杂互动 → Stage 7 后半段
- 付费/登录/云端 → Stage 9
- Android/Windows 移植 → 远期,大脑现成只重做身体
- AR / Vision Pro 身体 → Stage 8
- [继续往下扔...]

---

## 自律守则(给我自己的提醒,卡住时回来看)

1. **想清楚再让 AI 动手** —— 别让代码 AI 当我的草稿纸,架构反复在讨论里消化完。
2. **改动前先想能不能只改一小块** —— 默认局部改,不默认大改。
3. **一个 bug 一个 AI,不换人群殴。**
4. **每条指令圈定范围**,不说"看整个项目"。
5. **准备够了就开工** —— 再想新问题,大多答案是"前面已经定了"。行动 > 完美规划。
