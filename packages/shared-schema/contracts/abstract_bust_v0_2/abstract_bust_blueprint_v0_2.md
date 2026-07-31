# Abstract Bust Blueprint · Studio 形体协议 · v0.2

> Studio 定义的抽象粒子肖像形体协议。v0.2 冻结字段、默认配置、Preset 语义和解析规则；粒子生成算法、区域配额、PRNG、索引公式、坐标 Oracle 与 Golden 留待 C3/C4。

---

## 1. 产品定位与版本

- `generator_version` 固定为 `abstract_bust_v0_2`。
- 视觉目标是“肩部或上胸以上、具有人形辨识度的抽象粒子肖像”。
- `abstract_bust_v0_1` 永久冻结，继续服务旧 Visual Asset 与旧 DR；v0.2 不迁移、不覆盖、不重新解释 v0.1。
- Studio 决定默认形体、Preset、视觉语义和居民最终 Blueprint。
- Aftelle 后续按 `generator_version` 选择 Runtime Adapter，并按完整 Blueprint 重建形体。

唯一字段树：

```text
AbstractBustBlueprintV2
├── generator_version
├── particle_count
├── presentation
├── age_tendency
├── seed
├── head { width, height, depth, roundness }
├── face
│   ├── eyes { vertical_position, spacing, size, tilt, contour_strength }
│   ├── nose { vertical_position, width, length, prominence }
│   ├── mouth { vertical_position, width, curvature, contour_strength }
│   ├── cheeks { width, vertical_position, prominence }
│   └── jaw { width, taper, length, roundness }
├── neck { width, length }
├── shoulders { width, slope }
├── torso { width, thickness, length, taper }
├── hair { style, volume, length }
└── contour { softening, asymmetry }
```

v0.2 相比 v0.1 只增加 `particle_count` 和 `head.depth`。头颅、五官、颈肩、上胸和发型的其余控制继续复用原有嵌套字段。

---

## 2. 必填、可选与规范化

必填顶层字段：

- `generator_version`
- `presentation`
- `seed`
- `head`
- `neck`
- `shoulders`
- `torso`
- `hair`

必填对象出现后，其 Schema `required` 中的子字段全部必填；`head.depth` 是 v0.2 的必填头部字段。

允许缺失并补默认值的顶层字段：

- `particle_count`
- `age_tendency`
- `face`
- `contour`

规范化规则：

1. JSON 无法解析或根不是 object：拒绝。
2. 任意层未知字段：拒绝。
3. 缺失必填字段：拒绝。
4. 未知 `generator_version` 或枚举：拒绝。
5. 错误类型、浮点 particle_count、字符串数字、`NaN`、`Infinity`：拒绝。
6. 允许缺失的字段从 v0.2 Schema/default fixture 补全。
7. 有限越界数值和整数按 Schema clamp。
8. 成功输出完整嵌套 Blueprint，不生成旧平铺字段。

默认值只来自 `fixtures/default.json`；类型、枚举、范围、必填和可选规则只来自 v0.2 Schema。实现不得维护私有默认值、范围或枚举。

---

## 3. particle_count

- 类型：整数。
- minimum：`6000`。
- default：`12000`。
- maximum：`24000`。
- 缺失时补 `12000`。
- 小于 minimum 或大于 maximum 的整数按 Schema clamp。
- 浮点数、字符串、布尔值、`NaN` 和 `Infinity` 拒绝。
- `particle_count` 不表达居民年龄、presentation 或形体语义。

Preset 默认保留当前 Blueprint 的 `particle_count` 和 `seed`；只有恢复完整 default fixture 才将二者恢复为默认值。

运行边界：

- 相同 `generator_version`、规范化 Blueprint、`seed` 和 `particle_count` 必须产生确定输出。
- 形体参数变化且 `particle_count` 不变时，后续生成器必须保持稳定索引和复用粒子 Buffer 的能力。
- `particle_count` 改变允许重建粒子 Buffer，不属于普通形体 Morph。
- Studio、Aftelle、后续生成器和 UI 必须读取规范化 Blueprint，不得写死 `12000` 或固定长度 TypedArray。
- DR 只保存 Blueprint 与 `particle_count`，不保存粒子坐标。

---

## 4. 形体字段语义

- `head.width`、`head.height`、`head.depth`、`neck.width`、`shoulders.width`、`torso.width` 与 `torso.thickness` 是中心线到外轮廓的半尺寸。
- `head.depth` 独立定义头颅前后半深度，解除 v0.1 对 `torso.thickness` 的隐式耦合。
- `head.depth` 的冻结范围依据 v0.1 生成器既有隐式关系 `torso.thickness × 0.82`：v0.1 默认值对应 `0.28 × 0.82 = 0.2296`，合法包络对应 `0.22 × 0.82 = 0.1804` 至 `0.34 × 0.82 = 0.2788`；v0.2 因此冻结为默认 `0.23`、范围 `0.18...0.28`。
- `presentation` 与 `age_tendency` 是 Studio Preset 标签，不触发 Blueprint 数值之外的隐藏形体偏移。
- `hair.style` 是明确的抽象体积类别；不生成单根发丝、材质或物理动画。
- v0.2 使用与 v0.1 一致的局部方向语义：`+X` 为居民右侧、`+Y` 向上、`+Z` 朝观察者。具体几何公式和坐标结果留待 C3。

除 `head.depth` 外，所有复用字段沿用 v0.1 的合法范围。v0.2 default 在这些范围内进行克制重平衡，以缩短加宽颈部、增加肩斜、缩短上胸并增强抽象五官层次。

---

## 5. Preset 与 Fixtures

v0.2 提供三类完整合法 Fixture：

- presentation：`neutral`、`feminine`、`masculine`
- age_tendency：`youthful`、`balanced`、`mature`
- hair：`none`、`short`、`medium`、`long`、`tied`

Fixture 本身显式包含默认 `seed` 和 `particle_count`，可独立解析。应用 Preset 时：

1. 读取并规范化对应完整 Fixture；
2. 用 Fixture 替换形体配置；
3. 恢复调用前 Blueprint 的 `seed` 与 `particle_count`；
4. 再次规范化输出。

恢复完整默认值直接读取 `fixtures/default.json`，因此 seed 恢复为 `2818040094`，particle_count 恢复为 `12000`。

presentation 的视觉差异不得依赖发型、颜色或服装；三份 presentation Fixture 均使用 `hair.style=none`。年龄 Fixture 不使用皱纹、皮肤老化或写实年龄特征。发型 Fixture 只改变抽象发型体积。

---

## 6. 当前排除项

v0.2 C2 不定义或交付：

- 粒子生成算法、区域配额、PRNG、索引公式；
- Golden Manifest、digest、坐标 Oracle 或粒子坐标；
- Three.js 预览、相机、颜色、材质；
- Morph、呼吸、流动、Thinking / Speaking 或表情动画；
- 服装、全身、写实人像、二次元或 AR；
- Aftelle Runtime Adapter；
- Layer 10、Visual Asset、绑定或 DR 编译切换。

这些内容不得进入 v0.2 Blueprint。

---

## 7. 版本路由

统一入口必须先读取 `generator_version`：

```text
abstract_bust_v0_1 -> v0.1 parser
abstract_bust_v0_2 -> v0.2 parser
其他或缺失          -> reject
```

路由只负责精确分派，不自动迁移 v0.1、不补写新版本、不使用 v0.2 Parser 解释旧 Blueprint。现有产品主链继续使用 v0.1，直到后续节点显式切换。
