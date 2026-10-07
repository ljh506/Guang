---
AIGC:
    Label: "1"
    ContentProducer: 001191440300708461136T1XGW3
    ProduceID: 40eb6eba8f783c17143097188cf613e3_8a668311c21711f1a05452540064ee0f
    ReservedCode1: jLvnDWXkkJQL6mU8794J2ipXpshee0vAcHis8fnGRTqBRfzhIEbJ9X6ctZJp/NwxxuT3MhbSjb8shkujdoE4pfyJNReLiGRxh4Ls8dvragOCJ/sTw4LmBAIfqR/Tjf8lcZtzQuDtRbGITjvYyXG00OM7QVGTLy4pZoJbKcLNRvJoF7WhXVu6ji7Nau4=
    ContentPropagator: 001191440300708461136T1XGW3
    PropagateID: 40eb6eba8f783c17143097188cf613e3_8a668311c21711f1a05452540064ee0f
    ReservedCode2: jLvnDWXkkJQL6mU8794J2ipXpshee0vAcHis8fnGRTqBRfzhIEbJ9X6ctZJp/NwxxuT3MhbSjb8shkujdoE4pfyJNReLiGRxh4Ls8dvragOCJ/sTw4LmBAIfqR/Tjf8lcZtzQuDtRbGITjvYyXG00OM7QVGTLy4pZoJbKcLNRvJoF7WhXVu6ji7Nau4=
---



# 拾光Agent · 成员B AI/算法模块

> 校园闲置循环与以物换物平台 —— AI/算法模块（成员B 交付，Day 1 + Day 2）

本项目是「拾光Agent」校园闲置交换平台中由成员B负责的 AI/算法模块，聚焦三个核心能力：

1. **物品类别识别**：封装外部视觉识别服务，将图片识别为平台 10 个一级类别之一，并输出置信度；
2. **价格建议引擎**：按「类别 + 品相」查折扣表，计算建议估价区间（仅供参考）；
3. **交换匹配规则**（Day 3 起落地）：基于 asking_price 的价格匹配，规则见 `docs/3_交换匹配规则初稿.md`。

设计原则：**AI 只负责类别识别，不直接决定价格**；真实成交标价 `asking_price` 由用户手动输入，规则引擎仅给出参考区间与提示，不阻断发布。

---

## 目录结构

```
github_upload/
├── price_engine.py        # 价格规则引擎（建议估价区间 + 标价提示校验）
├── ai_client.py           # AI 识别服务客户端（阈值分流 + 失败兜底，可 mock）
├── test_day2.py           # 自测脚本（32 项用例，覆盖示例/边界/分流/一致性）
├── requirements.txt       # 依赖清单（无第三方依赖，标准库即可）
├── README.md              # 本文档
└── docs/                  # 规则文档与交接文档（Day1 + Day2）
    ├── 1_AI识别类别清单.md         # Day1：10 个一级类别、置信度阈值、兜底策略
    ├── 2_价格规则初稿.md           # Day1：折扣表、估价公式、asking_price 手动标价机制
    ├── 3_交换匹配规则初稿.md       # Day1：匹配权重 50/30/20、阈值、匹配接口草案
    ├── 4_交接文档_成员B_Day1.md    # Day1：面向团队交接说明与风险提示
    └── 交接文档_成员B_Day2.md      # Day2：代码使用方式、接口约定、后续待办
```

---

## 模块功能与使用示例

### 1. price_engine.py —— 价格规则引擎

按「类别 + 品相」查询折扣表（与项目计划书 §四 数字一致），输出建议估价区间与可解释的估价依据文本。

```python
from price_engine import estimate_price, validate_asking_price

# 估价：教材 / 良好 / 原价 68 元
result = estimate_price("textbook", "good", 68)
print(result["estimated_min"], result["estimated_max"])   # 27 41
print(result["reason_text"])
# 「教材」良好，参考原价 68 元，按教材类良好折扣 0.4~0.6 计算，建议估价 27~41 元。

# 用户手填标价校验（仅提示、不阻断）
tip = validate_asking_price(30, 27, 41)   # None，标价在建议区间内
tip = validate_asking_price(10, 27, 41)   # 低于建议区间的提示文案
```

**类别 ID（10 个一级类别）**：`textbook` 教材 / `electronics` 电子产品 / `life_goods` 生活用品 / `clothing` 衣物 / `school_supplies` 文具用品 / `digital_accessory` 数码配件 / `sports` 运动器材 / `furniture` 家具与宿舍用品 / `books_other` 其他书籍资料 / `other` 其他。

**品相**：`new_like` 全新/较新 / `good` 良好 / `fair` 一般。

**边界处理**：原价缺失/非数字/超范围、品相缺省、类别非法均返回结构化错误码 `{"error": {"error_code": "...", "message": "..."}}`；免费赠送（`is_free=True`）估价恒为 0；电子产品可按使用年限 `device_age_months` 微调折扣。

### 2. ai_client.py —— AI 识别服务客户端

封装视觉识别服务（图片 → 类别 + 置信度），不绑定具体第三方服务，通过注入 `backend` 函数解耦。

```python
from ai_client import AIClient

def my_vision_backend(image_path):
    """接入具体视觉识别服务（如腾讯云/百度），返回 label + confidence。"""
    # ... 真实实现 ...
    return {"label": "book", "confidence": 0.93}

client = AIClient(backend=my_vision_backend, timeout_seconds=5.0)
result = client.recognize("photo.jpg")
print(result["status"], result["category_id"], result["confidence"])
```

**统一返回结构**：`status / category_id / category_name / confidence / fallback / fallback_reason / raw_label`。

**置信度阈值分流**：

| 置信度 | status | 含义 |
|---|---|---|
| ≥ 0.80 | `auto_fill` | 自动填充类别 |
| 0.60 ~ 0.80 | `manual_confirm` | 自动填充但提示人工确认 |
| < 0.60 | `manual_select` | 不自动填充，进入手动选择 |
| 服务异常/超时 | `fallback` | 失败兜底，手动选类别，流程不中断 |

**Mock 测试**（无需真实服务）：

```python
from ai_client import MockAIClient

mock = MockAIClient()
mock.add_success("textbook", 0.96)   # -> auto_fill
mock.add_success("t-shirt", 0.70)    # -> manual_confirm
mock.add_failure("模拟超时")          # -> fallback
r = mock.recognize("test.jpg")
```

---

## 测试运行方式

```bash
python test_day2.py
```

预期输出：`===== 结果汇总：PASS=32 FAIL=0 =====`

测试覆盖：
- 计划书示例：68 元 / 良好 / 教材 → 建议区间 27~41 元；
- 边界情况：原价缺失/非数字/超范围、品相缺省/非法、类别非法、免费赠送、电子产品年限微调；
- 标价提示：低于/在区间内/高于区间的 price_tip 逻辑；
- AI 客户端：auto_fill / manual_confirm / manual_select / fallback 全部分流、标签映射、未配置 backend 兜底；
- 一致性：折扣表 10 类别 × 3 品相与 Day1 规则文档完全对齐。

---

## 与 Day1 规则文档的对应关系

| 代码模块 | 对应 Day1 规则文档 | 落地要点 |
|---|---|---|
| `price_engine.py` | 《2_价格规则初稿.md》 | 折扣表数字一致；建议区间仅参考；`asking_price` 用户手填、仅提示不阻断（§4.5）；reason_text 可解释文本（§5）；错误码（§6） |
| `ai_client.py` | 《1_AI识别类别清单.md》 | 10 个一级类别 ID/名称一致；置信度阈值 0.80/0.60 分流（§3）；失败兜底与手动选择（§5）；兜底类别 other |
| `test_day2.py` | 计划书 §四 + Day1 文档 | 68 元示例、折扣表、权重等数字与计划书一致 |
| 匹配规则（待实现） | `docs/3_交换匹配规则初稿.md` | MatchScore = 0.50×类别 + 0.30×价格 + 0.20×同校，基于 `asking_price`，Day 3 起实现 |

匹配规则（MatchScore = 0.50×类别 + 0.30×价格 + 0.20×同校，基于 `asking_price`）将在 Day 3 匹配模块中实现，本目录不包含。

---

## 后续迭代计划

| Day | 计划 |
|---|---|
| Day 4 | 类别标准化：识别标签映射表扩充、类别选择器交互对齐 |
| Day 5 | 识别链路：前端上传 → AI 识别 → 结果确认全流程联调 |
| Day 6 | 折扣完善：折扣表配置化、电子产品年限规则细化、估价接口 POST /estimate 正式落地 |
| Day 9 | 匹配算法：基于 asking_price 的价格接近度评分与匹配接口实现 |

---

## 安全与合规说明

- 本目录代码**不含任何本机绝对路径、密钥、Token 或团队内部敏感信息**（已扫描验证）；
- 接入真实视觉识别服务时，密钥应通过环境变量或配置中心注入，**严禁硬编码进代码**；
- 如需上传公开仓库，建议同时补充开源许可证文件。
*（内容由AI生成，仅供参考）*
*（内容由AI生成，仅供参考）*
