# runtime_strategy.md — Aftelle

> 性质:**架构决策记录**(不是描述)。记录 G0 拍板的 Runtime 策略 + 理由 + 边界。
> 状态:已拍板(2026-06-30)。本决策冻结,变更需新开决策条目并说明理由。

---

## 决策:B —— 本地 Python sidecar

Aftelle(Swift)**不重写 Runtime**,而是在本地运行 Studio 现有的 Python Runtime(FastAPI),Aftelle 通过 HTTP 调 `/runtime` 接口驱动居民。

```
Aftelle (Swift UI + 粒子)
   │  HTTP (本地 localhost)
   ▼
Python Runtime sidecar (复用 Studio 后端)
   └─ Execution Engine → Provider Adapter → (mock / 真实 LLM)
```

---

## 为什么选 B(不选 A Swift 重写 / C 只复用 schema)

1. **不让 Aftelle 变成第二个 Studio**:Runtime/Execution Engine/Provider Registry 已在 Studio 后端实现且通过 6.11 freeze(pytest 208 passed)。Swift 重写等于重做一遍,违背"Aftelle 只做 Runtime Host"。
2. **契约已就绪**:DR v0.3 已冻结,后端 `load-dr`/`step` 已有真实返回。直接复用比重写省数月。
3. **Stage 7 是 MVP + demo**:目标是跑通命脉链路,不是做纯本地引擎。纯 Swift 本地化是 Stage 8+ 才值得的投入。

---

## 这个决策带来的边界(写进红线,所有 AI 遵守)

- Aftelle **禁止**重实现 execution_engine / dr_compiler / provider registry。
- Aftelle **禁止**直连 OpenAI/Claude/Qwen;真实 LLM 只能走后端 `Runtime Config → Provider Registry → Provider Adapter → Execution Engine`。
- Aftelle 与 Runtime 之间**只通过 HTTP 契约**通信(见 runtime_api_contract.md),不依赖后端内部实现。
- Stage 7 Gate 的运行契约版本以 `runtime_api_contract.md` 冻结的 `runtime_api_version = "6.11.0"` 为准。
- sidecar 在**本地 localhost** 运行,不走公网;provider secret 只在后端 Keychain/配置,不进 Aftelle、不进 DR、不进 Git。

---

## 对架构文档的影响

- 架构设计里的"Swift Runtime Kernel"应理解为 **Aftelle 侧的 Runtime 客户端(RuntimeAPIClient)**,不是重写的引擎。
- HostEnv 的 `provider` / `memory` 能力,在 B 方案下由后端 sidecar 提供,Aftelle 侧通过 HTTP 适配。
- 红线 1(大脑不碰平台)仍成立:Aftelle 侧不嵌入业务推理,推理在后端。

---

## 未来迁移(非 Stage 7 范围)

若 Stage 8+ 需要纯本地(无 Python sidecar),届时可评估 A 方案(Swift 重写最小 Runtime),但必须:① 作为新的架构决策立项;② 复用已冻结的 DR 契约和 API 契约(形状不变,实现换 Swift)。**Stage 7 不做此迁移。**
