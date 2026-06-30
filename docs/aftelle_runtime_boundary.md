# Aftelle Runtime Boundary

> 本文档固化 Aftelle Desktop 编排系统的**不可破坏约束(Invariants)**。
> 它不描述功能,只定义边界。其存在目的是:**让 Stage 8+ 是"往骨架上挂东西",而不是"拆骨架重写"**。
> 每新增一个功能,先对照本文档判断是否越界。越界 = 推翻成本。

- **状态**: G0 前置 / Foundation Lock 候选
- **适用阶段**: Stage 7 起,长期有效
- **修改规则**: 本文档中的 Invariant 一旦锁定,变更等同架构推翻,需显式 ESC 评审,不得在功能开发中顺手改动。

---

## 0. 前置:G0 Runtime 选型(本文档的前提)

本文档描述的一切——常驻循环、后台 tick、自驱唤醒、活态持久化——**默认存在一个能后台常驻、能自主推进时间的进程**。

由此直接得出 G0 runtime 决策的判据:

| 选项 | 是否满足本文档 |
|---|---|
| Schema-only | ❌ 撑不起常驻 tick 循环,无法自驱唤醒,本文档第 1 条 Invariant 直接塌陷 |
| Python sidecar / 专用常驻 runtime | ✅ 可常驻、可后台 tick |
| Swift 重写 | ✅ 可行,但成本另议 |

**结论**: 本编排设计本身即是排除 schema-only 的证据。
Swift + Metal 承担可视化(粒子 / 二次元 / AR 身体),**不承担编排循环与 Provider 调用**。

> ⚠️ 本文档的其余部分,只有在 G0 runtime 锁定为"可常驻进程"后才成立。
> 顺序:**先锤 G0 → 再定稿 v4 文档**。G0 不锤,以下皆为沙上建塔。

---

## 1. 四条不可破坏约束(Invariants)

### INV-1 · Kernel 是循环,不是管线;且 Kernel 拥有时间

编排系统的形状是**循环**,不是从 `User Input` 流向 `Provider` 的单向瀑布。

- 拥有时间的 **Substrate / 调度器是整个系统的底座**,不是某一编排层的子模块。
- 唤醒源至少三种:**外部事件**、**定时**、**内驱(drive 越阈值)**。
- 必须存在**回环**:反思 / 巩固阶段写回活态。没有回环,居民只有一次次被召唤,没有连续性。
- 「没人理它时它仍在 tick」是活人感的第一来源,也是反应式工具与"活的存在"的分界线。

**越界信号**: 出现"无用户输入则系统静止"的设计;`Timing Controller` 被降级为某一层内部模块。

---

### INV-2 · 基因组与活态分开持久化

居民有两种状态,**生命周期、读写频率、归属、存储位置都不同,不得合并存放**:

| | 基因组(Genome) | 活态(Live State) |
|---|---|---|
| 内容 | identity / personality / 13 层定义 | mood / energy / attention / drives / per-人关系 / 当前牵挂 |
| 来源 | `.digital_resident` 文件 | runtime 运行时产生 |
| 性质 | 准静态,读为主 | 高频读写,持续突变 |
| 归属 | 这个居民"是谁" | 这个实例"此刻的生理状态" |

**越界信号**: `identity` 与 `mood` 出现在同一个状态结构 / 同一张表 / 同一份持久化里。
合并 = 以后加"灵魂"只能靠重构。

> 附:核对 Memory 层是否只建模了"积累的知识",而漏掉了情感 / drive 活态。若漏,这是缺口。

---

### INV-3 · Execution Engine 是唯一 Runtime 入口

所有对外副作用——Provider 调用、Tool、Memory 写入、TTS、Visual、未来的 Agent 动作——**必须经由同一个 Execution Engine**。

- UI **不直接**调用 Provider。
- 这道门是 **Control 层(shadow / dry-run / 审批门 / append-only 审计日志)挂钩子的唯一集成点**。
- 「以后扩展不是重写」的真正保障在这里,而不在协议数量。

**越界信号**: 任何模块绕过 Execution Engine 直连 Provider / Tool / TTS。这是必须立即拍掉的破口。

---

### INV-4 · I/O 抽象是 environment→resident,不是 user→resident

居民感知的是**来自世界的事件**,用户只是事件源之一。

- 不得把交互硬编码成 `user message → reply`。
- 写成 `environment → resident`,以后加别的居民 / 别的事件源,只是**新增一种事件类型**,而非撕掉重写。
- 这是 Stage 7 唯一需要做的"社会准备"。其余社会体系(共享世界、居民间总线、寻址)Stage 9/10 再说,现在碰即过度准备。

**越界信号**: 对话循环里出现写死的 `user`/`assistant` 二元结构,无法容纳第三方事件源。

---

## 2. 心智模型更正:编排是 Policy,不是 Layer

四个编排("生命 / 对话 / Agent / 社会")**不是串行堆叠、每轮必经的"层"**。

正确模型:**一个薄 kernel 循环,每次 tick 按需咨询若干 policy / 子系统**。

- 它们是循环的**顾问**,不是管线的**工段**。
- "Layer" 暗示堆叠与必经;"Policy/子系统" 暗示按需调用。后者才对。
- 特别地:`Dialogue → Agent → Social` 不存在固有先后。行动产生的结果往往才是要说的内容——"决定说什么"不必先于"决定做什么"。

---

## 3. Content-Agnostic 命门

**Kernel 永远 content-agnostic。** 同一个循环跑所有居民,差异全在 `.digital_resident` 文件里。

- 通用的是**机制**:appraisal 更新情绪、drive 驱动行为、循环 tick。
- 个性化的是**映射**:情绪 → 视觉 / 语音 / 节奏的对应关系,是 **DR 文件里的 per-resident 数据**,**不进 kernel**。

示例(说明用,**不得写进 kernel**):
> 用户焦虑 → 情绪转 concerned → 粒子收束 → 回复前停顿 0.6s → 声音变轻 → 先安抚再给方案 → 写入关系记忆。
> 此处机制(appraisal、情绪更新)通用;每一步的具体映射(0.6s、粒子收束)必须是 per-resident 数据。

**越界信号**: 任何具体居民的情绪表现 / 口吻 / 节奏被硬编码进 kernel,导致所有居民一个样。

---

## 4. 协议冻结边界:冻 6 个 / 留缝 5 个

协议的意义在于**被使用所验证**。给没用过的协议浇混凝土 = cargo cult = 注定重写。

### 现在冻(Stage 7 真正会跑)

- `ResidentState`
- `EmotionState`
- `VisualState` — 驱动粒子 / 二次元 / AR 身体
- `MemoryEvent` — 驱动长期关系
- `TraceEvent` — 解释每一步为何发生(与 AI Control 审计日志同线)
- `DialogueIntent`

### 现在只留缝,勿定字段(标注 reserved,Stage 8+ 定义)

- `ActionRequest` — 未来 Agent 执行入口(以后流过 Execution Engine 这道门的载荷)
- `Observation` — 未来 Agent 看结果
- `PermissionDecision`
- `TaskState`
- `SocialMessage` — 未来多居民通信(以后只是 environment 事件总线上的一种新事件)

> 留缝的方式不是定义空结构,而是确保**门(INV-3)与事件抽象(INV-4)存在**。
> 这两个边界在,上述 5 个协议以后只是"新增载荷 / 新增事件类型",不触碰骨架。

---

## 5. 记忆边界(多居民,概念现在锁,实现 Stage 9+)

多居民必须有三种记忆边界,**概念现在锁定,防止以后串人格 / 串记忆**:

- **Private Memory** — 居民自己的记忆,他人不可见
- **Shared Session Context** — 当前会话共享上下文
- **Public Transcript** — 用户可见的对话记录

> 定义入 schema 文档;"为什么"入产品文档;本文档只锁"这三者边界不可混"。

---

## 6. 诚实性边界(显式设计参数)

"像真人"越成功,"用户是否知道这不是人"越尖锐——尤其叠加 Stage 8 自主社媒运营。

- 居民的**自我披露策略**应是一个**显式设计参数**,不得默认掉。
- 这是诚实性约束,不只是技术目标。不要求收手,要求别让这条边界隐形。

---

## 7. 反模式清单(对照自查)

不要这样:
- LLM 直接决定一切
- 居民自由乱聊、无收敛机制
- 工具调用直接塞进聊天逻辑
- 记忆全写进 prompt
- UI 直接调用 Provider
- 每加功能就改 Runtime 主链路
- 给 Stage 9/10/11 的内部模块提前命名(架构幻想 / 过度准备)

要这样:
- 状态驱动情绪
- 策略驱动对话
- 权限驱动行动
- Trace 解释决策
- Memory 保持连续
- Visual State 表达身体
- Action / Observation 留缝给 Agent
- SocialMessage 留缝给多居民社会

---

## 附:落点对照(本文档与 v4 套件的关系)

| 内容 | 主文档 | 本文档作用 |
|---|---|---|
| G0 runtime 选型 | G0 决策记录 | 提供判据(§0) |
| 4 条 Invariants | 架构文档 | 此处为权威定义(§1) |
| Policy ≠ Layer 心智模型 | 架构文档 | 纠正瀑布图(§2) |
| content-agnostic 映射 | 产品设计文档 | 锁定 kernel 边界(§3) |
| 冻 6 / 留缝 5 | SCHEMA_CONTRACT | 锁定冻结范围(§4) |
| 三种记忆边界 | schema + 产品文档 | 锁定不可混(§5) |

> 本文档是**边界的单一事实来源**。其他文档可引用本文档,不得与之冲突。冲突即推翻信号。
