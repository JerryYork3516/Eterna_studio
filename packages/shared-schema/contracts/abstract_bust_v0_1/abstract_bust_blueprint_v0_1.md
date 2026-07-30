# Abstract Bust Blueprint · 最终运行协议 · v0.1

> Studio Visual Builder 与 Aftelle Metal Runtime 共用的唯一抽象半身协议。本版本冻结静态形体、坐标、派生锚点、校验和确定性规则；不代表已接入 DR 或 Studio。

---

## 1. 版本、边界与字段层级

- `generator_version` 固定为 `abstract_bust_v0_1`。
- 固定 `12000` 个粒子，粒子索引不随 Blueprint、preset 或 Morph 改变。
- 形体仅为抽象粒子体积与轮廓；眼、鼻、嘴、颧、下颌和发型均不生成写实细节。
- `mouth` 只定义静态基础形态；Speaking、嘴型同步、骨骼和动画不属于本协议。
- `age_tendency` 只改变视觉轮廓，不表示、读取或复制居民身份年龄。
- `presentation` 是温和基准 preset 标签，不定义性别身份，也不触发未写入 Blueprint 的隐藏形体规则。
- Aftelle 当前只在 ParticleCore 内部 Loader 与 Debug Preview 使用本协议；不读取真实 DR，不修改 Runtime API 或 DR schema。

唯一字段树：

```text
AbstractBustBlueprint
├── generator_version
├── presentation
├── age_tendency
├── seed
├── head { width, height, roundness }
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

修改字段名、范围、枚举、索引配额、散列、坐标或几何公式时，必须发布新的 `generator_version`，不得静默改变 v0.1。

---

## 2. 必填、可选、默认值与范围

必填顶层字段：`generator_version`、`presentation`、`seed`、`head`、`neck`、`shoulders`、`torso`、`hair`。必填对象出现后，其子字段全部必填。

可选顶层字段：

- `age_tendency`：缺失时为 `balanced`。
- `face`：缺失时补整组默认面部参数。
- `contour`：缺失时补整组默认轮廓参数。

| JSON 字段 | 默认值 | 合法范围 / 枚举 |
|---|---:|---|
| `generator_version` | `abstract_bust_v0_1` | 仅此值 |
| `presentation` | `neutral` | `neutral` / `feminine` / `masculine` |
| `age_tendency` | `balanced` | `youthful` / `balanced` / `mature` |
| `seed` | `2818040094` | integer `1...4294967295` |
| `head.width` | `0.265` | `0.22...0.32` |
| `head.height` | `0.340` | `0.29...0.40` |
| `head.roundness` | `0.500` | `0...1` |
| `face.eyes.vertical_position` | `0.170` | `0.08...0.26` |
| `face.eyes.spacing` | `0.190` | `0.14...0.24` |
| `face.eyes.size` | `0.045` | `0.025...0.065` |
| `face.eyes.tilt` | `0.000` | `-0.35...0.35` radians |
| `face.eyes.contour_strength` | `0.420` | `0...1` |
| `face.nose.vertical_position` | `-0.020` | `-0.12...0.08` |
| `face.nose.width` | `0.052` | `0.035...0.075` |
| `face.nose.length` | `0.105` | `0.075...0.14` |
| `face.nose.prominence` | `0.028` | `0...0.06` |
| `face.mouth.vertical_position` | `-0.320` | `-0.42...-0.22` |
| `face.mouth.width` | `0.135` | `0.09...0.17` |
| `face.mouth.curvature` | `0.040` | `-0.30...0.30` |
| `face.mouth.contour_strength` | `0.380` | `0...1` |
| `face.cheeks.width` | `0.300` | `0.24...0.36` |
| `face.cheeks.vertical_position` | `-0.080` | `-0.16...0.04` |
| `face.cheeks.prominence` | `0.018` | `0...0.05` |
| `face.jaw.width` | `0.205` | `0.17...0.25` |
| `face.jaw.taper` | `0.060` | `0...0.30` |
| `face.jaw.length` | `0.025` | `0...0.06` |
| `face.jaw.roundness` | `0.620` | `0...1` |
| `neck.width` | `0.160` | `0.13...0.20` |
| `neck.length` | `0.200` | `0.15...0.24` |
| `shoulders.width` | `0.600` | `0.52...0.68` |
| `shoulders.slope` | `0.085` | `0.04...0.14` |
| `torso.width` | `0.540` | `0.45...0.62` |
| `torso.thickness` | `0.280` | `0.22...0.34` |
| `torso.length` | `0.760` | `0.64...0.88` |
| `torso.taper` | `0.300` | `0.18...0.40` |
| `hair.style` | `none` | `none` / `short` / `medium` / `long` / `tied` |
| `hair.volume` | `0.550` | `0.20...1` |
| `hair.length` | `0.500` | `0.15...1` |
| `contour.softening` | `0.900` | `0.75...1` |
| `contour.asymmetry` | `0.009` | `0...0.018` |

所有生成计算使用 IEEE-754 Float32。JSON 数字必须有限；`NaN`、`Inf` 和 `-Inf` 非法。

---

## 3. Preset、发型与视觉年龄倾向

三组 presentation preset 位于 Fixtures 目录。差异保持克制：

- `neutral`：均衡头颈肩比例、无发型体积。
- `feminine`：略圆的头部、略窄肩颈与 medium 抽象发型。
- `masculine`：略宽肩颈、略清晰下颌与 short 抽象发型。

五种发型均只生成体积轮廓：

- `none`：不划分 hair 粒子。
- `short`：贴近头顶和上侧面的帽状体积。
- `medium`：延伸至下颌附近。
- `long`：沿侧后方向延伸至肩颈区域。
- `tied`：短帽主体加后侧聚拢体积。

年龄视觉倾向仅施加固定、温和的派生偏移：

| 倾向 | 头部圆润度 | 下颌宽度 | 颧部突出 | 鼻长派生 | 下巴长度 |
|---|---:|---:|---:|---:|---:|
| `youthful` | `+0.08` | `-0.008` | `-0.003` | `-0.006` | `-0.003` |
| `balanced` | `0` | `0` | `0` | `0` | `0` |
| `mature` | `-0.06` | `+0.008` | `+0.006` | `+0.008` | `+0.004` |

派生后仍按相应字段范围 clamp。年龄倾向不生成皱纹、皮肤材质或写实生理特征。

---

## 4. 统一坐标系与标准参考尺寸

- 右手局部坐标系。
- 原点：`(0, 0, 0)`，位于默认中心轴附近、颈根与上胸过渡高度。
- `+X`：居民自身右侧；`-X`：居民自身左侧。
- `+Y`：向上。
- `+Z`：朝正面观察者；面部轮廓位于正 Z 半空间。
- 归一化单位：一个程序化形体单位；渲染器可整体缩放，但不得分别缩放轴。
- 生成器不使用像素、屏幕尺寸或 Metal clip-space 作为协议输入。

默认 neutral 的参考尺寸：

| 参考项 | 数值 |
|---|---:|
| 头部中心 | `(0.0027, 0.5900, 0)` |
| 标准头高 | `2 × head.height = 0.6800` |
| 标准头宽 | `2 × head.width = 0.5300` |
| 颈宽 | `2 × neck.width = 0.3200` |
| 颈长 | `0.2000` |
| 标准肩宽 | `2 × shoulders.width = 1.2000` |
| 胸腔前后厚度基准 | `2 × torso.thickness = 0.5600` |
| 躯干长 | `0.7600` |
| 默认整体锚点边界 | `X [-0.6123, 0.6247]`、`Y [-1.0999, 0.9299]`、`Z [-0.3084, 0.3310]` |

`head.width`、`head.height`、`neck.width`、`shoulders.width`、`torso.width` 和 `torso.thickness` 是中心线到外轮廓的半径/半尺寸；表中的“标准宽、高、厚”按两倍参数表示。

---

## 5. 视觉锚点派生公式

先对 Blueprint 执行默认补全和 clamp。记：

```text
cx = contour.asymmetry × 0.30
HC = (cx, 0.59, 0)
HD = torso.thickness × 0.82
NB = (cx, HC.y - head.height - neck.length, 0)
SY = NB.y + 0.08 - shoulders.slope
```

统一锚点：

```text
head_center    = HC
head_top       = HC + (0, head.height, 0)
neck_base      = NB
shoulder_left  = (cx - shoulders.width, SY, 0)
shoulder_right = (cx + shoulders.width,
                  SY + contour.asymmetry × 0.30, 0)
chest_center   = (cx, NB.y - 0.20, torso.thickness × 0.08)
torso_center   = (cx,
                  HC.y - head.height - neck.length
                       - 0.39 - torso.length × 0.5,
                  0)

eye_y          = HC.y + face.eyes.vertical_position × head.height
eye_z          = HD × (0.88 + face.eyes.contour_strength × 0.06)
eye_left       = (cx - face.eyes.spacing × 0.5, eye_y, eye_z)
eye_right      = (cx + face.eyes.spacing × 0.5, eye_y, eye_z)

nose_center    = (cx,
                  HC.y + face.nose.vertical_position × head.height
                       - age_nose_length_offset × 0.15,
                  HD × 0.90 + face.nose.prominence × 0.45)
nose_geometry_length
               = clamp(face.nose.length + age_nose_length_offset,
                       0.075, 0.14)
mouth_center   = (cx,
                  HC.y + face.mouth.vertical_position × head.height,
                  HD × 0.88 + face.mouth.contour_strength × 0.004)

cheek_y        = HC.y + face.cheeks.vertical_position × head.height
cheek_z        = HD × 0.82
                 + max(0, face.cheeks.prominence
                          + age_cheek_prominence_offset)
cheek_left     = (cx - face.cheeks.width × 0.5, cheek_y, cheek_z)
cheek_right    = (cx + face.cheeks.width × 0.5, cheek_y, cheek_z)

chin_center    = (cx,
                  HC.y - head.height - face.jaw.length
                       - age_chin_length_offset,
                  HD × 0.18)
```

Studio WebGL 与 Aftelle Metal 必须使用这些名称、方向和公式。锚点由 Blueprint 派生，不写入 DR。

---

## 6. Loader 校验与球体 fallback

校验顺序和行为固定：

1. JSON 无法解析或根不是 object：拒绝。
2. 任意层出现未知额外字段：拒绝；v0.1 选择严格拒绝，不忽略。
3. 缺失必填字段或必填对象子字段：拒绝。
4. `generator_version` 未知：拒绝。
5. `presentation`、`age_tendency` 或 `hair.style` 未知：拒绝。
6. 缺失可选字段：补第 2 节默认值。
7. `NaN`、`Inf`、错误 JSON 类型、非整数 seed：拒绝。
8. 有限但越界数字：clamp 到合法范围。
9. 校验成功：生成 `abstractBust` 锚点；拒绝：目标切换为 sphere。

拒绝与 sphere fallback 不重建粒子。JSON Schema 描述规范化后的合法交换对象，因此会拒绝越界值；Runtime Loader 为兼容有限输入，仍按第 8 条 clamp。

---

## 7. 确定性、索引配额与 Golden

1. 固定粒子数 `12000`，固定索引顺序。
2. 索引配额：头部总区 `22%`、抽象面部 `1.5%`、颈部 `5.5%`、肩胸 `27%`、躯干为剩余部分。面部和 hair 均从头部总区中划分，不改变后续区域起点。
3. `none` 的 hair 配额为 0；其他发型：

```text
hair_ratio_within_head = mix(0.22, 0.42, hair.volume)
hair_count = floor(head_count × hair_ratio_within_head)
```

4. 采样使用固定索引、黄金角 `2.3999631`、Float32 数学和固定 salt。
5. 固定散列：

```text
value = seed + index × 0x9E3779B97F4A7C15 + salt
value = (value xor (value >> 30)) × 0xBF58476D1CE4E5B9
value = (value xor (value >> 27)) × 0x94D049BB133111EB
value = value xor (value >> 31)
signed_unit = Float32(value / UInt64.max) × 2 - 1
```

6. Golden digest 为逐索引读取 `x/y/z` Float32 little-endian bit pattern 后计算 FNV-1a 64：

| Fixture | Digest |
|---|---|
| `default.json` | `a8d8df344c507342` |
| `neutral.json` | `a8d8df344c507342` |
| `feminine.json` | `82687870d3f143d6` |
| `masculine.json` | `a36d71fbe04c1bfb` |
| `hair_none.json` | `a8d8df344c507342` |
| `hair_short.json` | `131f78a9633ad3a5` |
| `hair_medium.json` | `7cb039bd9d9f4164` |
| `hair_long.json` | `fb7360f1490bb06c` |
| `hair_tied.json` | `3ee009cdb1e91a21` |

同一规范化 Blueprint、seed、粒子数、Float32 实现必须逐索引生成相同锚点和 digest。JavaScript/WebGL 移植不得先以 Float64 完成整条几何链后才转 Float32。

---

## 8. 协议交付路径

- JSON Schema：`docs/schemas/abstract_bust_blueprint_v0_1.schema.json`
- 默认、presentation、hair Fixtures：`docs/fixtures/abstract_bust_v0_1/`
- Golden 清单：`docs/fixtures/abstract_bust_v0_1/golden_manifest.json`
- Aftelle 数值基线：`apps/macos/Aftelle/ParticleCore/AbstractBustAnchorGenerator.swift`
- Schema / Fixture 校验：`tools/particle_shape/check_abstract_bust_schema.py`
- 生成、Loader、Golden、Morph 回归：`tools/particle_shape/check_abstract_bust.swift`

---

## 9. Studio 标准 JSON 示例

```json
{
  "generator_version": "abstract_bust_v0_1",
  "presentation": "neutral",
  "age_tendency": "balanced",
  "seed": 2818040094,
  "head": {
    "width": 0.265,
    "height": 0.34,
    "roundness": 0.5
  },
  "face": {
    "eyes": {
      "vertical_position": 0.17,
      "spacing": 0.19,
      "size": 0.045,
      "tilt": 0,
      "contour_strength": 0.42
    },
    "nose": {
      "vertical_position": -0.02,
      "width": 0.052,
      "length": 0.105,
      "prominence": 0.028
    },
    "mouth": {
      "vertical_position": -0.32,
      "width": 0.135,
      "curvature": 0.04,
      "contour_strength": 0.38
    },
    "cheeks": {
      "width": 0.3,
      "vertical_position": -0.08,
      "prominence": 0.018
    },
    "jaw": {
      "width": 0.205,
      "taper": 0.06,
      "length": 0.025,
      "roundness": 0.62
    }
  },
  "neck": {"width": 0.16, "length": 0.2},
  "shoulders": {"width": 0.6, "slope": 0.085},
  "torso": {
    "width": 0.54,
    "thickness": 0.28,
    "length": 0.76,
    "taper": 0.3
  },
  "hair": {"style": "none", "volume": 0.55, "length": 0.5},
  "contour": {"softening": 0.9, "asymmetry": 0.009}
}
```

该 JSON 是 Studio 后续预览和蓝图工作的交换标准，不代表 Aftelle 已接入 DRLoader 或真实 DR。
