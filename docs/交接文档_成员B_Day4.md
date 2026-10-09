# 交接文档 · 成员B · Day 4

- 交付人：成员B
- 交付日期：2026-10-09（第四天）
- 交付目标：**类别标准化** + **估价输入参数定义**
- 交付目录：`C:\Users\LENOVO\Desktop\拾光Agent\成员B_Day4_交付\`

---

## 1. 本日产出清单

| 文件 | 说明 |
|---|---|
| `category_normalizer.py` | 类别标准化模块：AI 原始标签/关键词 → Day4 统一 10 类体系 |
| `estimate_params.py` | 估价输入数据模型（dataclass）与 `validate()` 校验 |
| `test_day4.py` | 自测脚本：类别标准化 20 用例 + 参数校验 14 用例，共 **34 项 PASS / 0 FAIL** |
| `交接文档_成员B_Day4.md` | 本文档 |

---

## 2. Day4 统一类别体系（10 个一级类别）

```
textbook / electronics / life_goods / clothing / stationery /
digital_accessories / sports_equipment / furniture / other_books / other
```

> 说明：Day4 类别体系与 Day1 类别清单在命名上有差异（stationery↔school_supplies、digital_accessories↔digital_accessory、sports_equipment↔sports、other_books↔books_other）。本模块以 **Day4 命名**为统一输出，并通过 `to_engine_category()` 自动映射为 **Day2 price_engine 使用的类别 ID**，保证折扣表直接可用，无需修改 Day2 引擎。

---

## 3. category_normalizer 使用方式

```python
from category_normalizer import normalize, to_engine_category

# 1) 标准化 AI 原始标签
result = normalize("高数教材")
# -> {
#     "category_id": "textbook",
#     "category_name": "教材",
#     "confidence_adjust": 0.0,   # 兜底 other 时为负，提示置信度不可靠
#     "matched_by": "alias"       # alias / keyword / fallback
# }

# 2) 未知输入兜底
normalize("unknown_xyz_123")
# -> {"category_id": "other", "matched_by": "fallback", "confidence_adjust": -0.10}

# 3) 喂给 Day2 估价引擎（折扣表使用 Day2 类别 ID）
engine_category = to_engine_category(result["category_id"])
```

能力矩阵：
- **同义词/别名表**：覆盖中英文标签（Math Book / Textbook / 高数教材 / iPhone / 耳机 / 充电宝 / 篮球 / 小说 等 180+ 条）。
- **关键词包含匹配**：未精确命中但含特征词时命中（如"高等数学教材第2版"含"教材"→textbook）。
- **大小写/空格鲁棒**：`_norm_key` 统一小写、去首尾空格、空格转下划线，T-Shirt / "  水杯  " 均可正确识别。
- **兜底**：未知、None、空串一律归 `other`，`confidence_adjust=-0.10` 供上游降权。

---

## 4. estimate_params 使用方式

```python
from estimate_params import EstimateParams

params = EstimateParams(
    category="textbook",        # 必填：Day4 统一类别 ID（建议先用 normalize 标准化）
    condition="good",           # 必填：new_like / good / fair
    original_price=68,          # 必填：数字，>0
    asking_price=30,            # 选填：用户手填真实标价
    months_used=None,           # 选填：使用年限（月），电子产品用
    image_path=None,            # 选填：Day5 识别链路预留
    image_bytes=None,           # 选填：Day5 识别链路预留
)

result = params.validate()
# -> {"valid": True, "errors": []}
# 或 {"valid": False, "errors": [{"error_code": "CATEGORY_INVALID", "message": "..."}, ...]}
```

### 错误码清单（与 Day2 price_engine 保持一致）

| 错误码 | 触发条件 |
|---|---|
| `PRICE_ORIGINAL_REQUIRED` | 原价缺失 |
| `PRICE_INVALID_FORMAT` | 原价非数字 / ≤0 / 标价非数字 / 使用年限非法 |
| `PRICE_OUT_OF_RANGE` | 原价 > 100000 |
| `CONDITION_REQUIRED` | 品相为空 |
| `CONDITION_INVALID` | 品相不在 new_like/good/fair |
| `CATEGORY_INVALID` | 类别为空或不在 10 类体系 |

校验特点：多错误**累积返回**（不会因首个错误中断），便于前端一次提示全部问题。

---

## 5. 与 Day2 / Day1 的衔接说明

```
AI 原始标签
   │  category_normalizer.normalize()   ← Day4 新增（增强版映射）
   ▼
Day4 统一 category_id
   │  category_normalizer.to_engine_category()
   ▼
Day2 price_engine 类别 ID（textbook/school_supplies/...）
   │  EstimateParams.validate()          ← Day4 新增（参数校验）
   ▼
price_engine.estimate(...)                ← Day2 估价引擎
```

- **字段命名**：category / condition / original_price / asking_price / months_used 与 Day1 规则文档、Day2 price_engine 完全一致；错误码复用 Day2 六种错误码，无新增码。
- **对 ai_client**：Day2 `ai_client.map_label_to_category()` 为轻量映射，本模块为其增强替代；建议 Day5 起统一走 `category_normalizer.normalize()`，接口返回值含 `confidence_adjust` 可直接参与置信度调整。

---

## 6. 待办事项（后续成员/后续天）

- **Day5（图片识别链路）**：接入 `category_normalizer.normalize()`，图片 → 类别 → 置信度全链路；`EstimateParams.image_path / image_bytes` 字段已预留。
- **Day6（折扣完善）**：基于 Day4 标准化类别完善 Day2 折扣表的区间计算与明细规则（教材良好 0.4~0.6 等），确保 `to_engine_category()` 映射的类别在折扣表全覆盖。
- **前端对接**：校验错误直接透出 `error_code + message` 提示用户；`asking_price` 仅作展示参考，不阻断估价。

---

## 7. 自测验证

```
python test_day4.py
结果：PASS=34 FAIL=0（类别标准化 20 项 + 参数校验 14 项）
```
