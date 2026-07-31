# Abstract Bust Blueprint · v0.1 → v0.2 变更说明

## 版本边界

- `abstract_bust_v0_1` 永久冻结，算法、Schema、Fixture、Golden 和旧 DR 行为均不修改。
- `abstract_bust_v0_2` 是 Studio 独立定义的新协议，不自动迁移或重新解释 v0.1。
- Aftelle 在收到完整 v0.2 交付包后按 `generator_version` 增加独立 Runtime Adapter。

## 字段变化

- 新增顶层可选输入、规范化后必有的整数 `particle_count`：
  - minimum：`6000`
  - default：`12000`
  - maximum：`24000`
- 新增必填 `head.depth`，表示头颅中心线到前后外轮廓的半深度：
  - minimum：`0.18`
  - default：`0.23`
  - maximum：`0.28`
- 其他字段名称、嵌套层级、枚举和合法范围继续复用 v0.1。

## 默认配置

v0.2 在 v0.1 合法范围内重平衡默认头部、五官、颈部、肩部、上胸和轮廓参数，以服务 C1 人形辨识目标。完整默认值以 v0.2 `fixtures/default.json` 为唯一事实源。

## Preset

- 新增独立 youthful、balanced、mature Fixtures。
- presentation、age_tendency 和 hair Fixtures 均为完整合法 Blueprint。
- 应用 Preset 时保留调用前的 `seed` 与 `particle_count`。
- 恢复完整默认值时恢复 default fixture 中的 seed 与 `particle_count=12000`。
- presentation 与 age_tendency 不再触发未写入 Blueprint 数值的隐藏形体偏移。

## 运行边界

- 相同版本、规范化 Blueprint、seed 和 particle_count 必须确定。
- particle_count 不变时，形体变化必须保持稳定索引能力。
- particle_count 改变允许重建粒子 Buffer。
- v0.2 实现不得写死 12000 或固定长度 TypedArray。

## 延后内容

C2 不提供生成器、区域配额、PRNG、索引公式、Golden、digest、坐标 Oracle、Three.js 接入、DR 切换或 Aftelle Adapter。
