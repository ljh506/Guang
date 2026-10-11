# 交接文档 · 成员B · Day 5

- 交付人：成员B
- 交付日期：2026-10-10（第五天）
- 交付目标：**图片 → 类别 → 置信度 的 AI 识别链路**
- 交付目录：`C:\Users\LENOVO\Desktop\拾光Agent\成员B_Day5_交付\`

---

## 1. 本日产出清单

| 文件 | 说明 |
|---|---|
| `recognition_pipeline.py` | 识别链路主模块：backend 识别 → category_normalizer 标准化 → 阈值分流 → 兜底 |
| `test_day5.py` | 自测脚本：链路全流程 **25 项 PASS / 0 FAIL** |
| `交接文档_成员B_Day5.md` | 本文档 |

---

## 2. 链路架构（Day2 → Day4 → Day5）

```
输入图片（image_path / image_bytes，复用 Day4 EstimateParams 预留字段）
   │
   ▼
recognition_pipeline  ── backend 注入（复用 Day2 机制）
   │  backend(image_path) -> {"label": str, "confidence": float}
   │  失败抛异常（超时/网络/服务错误）
   ▼
category_normalizer.normalize(label)   ← Day4 增强版标准化（同义词/关键词/兜底）
   │  输出 category_id + confidence_adjust
   ▼
阈值分流（与 Day2 一致）：
   │  confidence >= 0.80      -> auto_fill      （自动填充）
   │  0.60 ~ 0.80             -> manual_confirm （自动填充但提示人工确认）
   │  < 0.60                  -> manual_select  （手动选择）
   │  matched_by == fallback  -> 强制 manual_select（未知类别即使高置信度也不自动填充）
   │  服务异常/超时/数据非法  -> fallback
   ▼
统一返回结构 recommend()
```

**与 Day2 的衔接**：Day2 `ai_client` 提供 backend 注入机制与 `MockAIClient`；Day5 复用该机制，将标签映射从 Day2 轻量 `map_label_to_category` 升级为 Day4 `category_normalizer.normalize`（同义词表 + 关键词包含 + 兜底 + 置信度调整）。Day2 `AIClient` 实例（含 `MockAIClient`）可直接作为 pipeline 的 backend 对象传入（自动走其 `recognize` 方法，结果中的 `raw_label/confidence` 被兼容读取）。

---

## 3. recognition_pipeline 使用方式

### 3.1 基本用法

```python
from recognition_pipeline import RecognitionPipeline, MockBackend

# 接入真实服务：实现 backend 约定即可
def my_vision_backend(image_path):
    # 调用第三方视觉识别服务，返回 {"label": "textbook", "confidence": 0.95}
    return {"label": "textbook", "confidence": 0.95}

pipeline = RecognitionPipeline(backend=my_vision_backend, timeout_seconds=5.0)

# 方式 A：图片路径
result = pipeline.recommend(image_path="C:/photos/math_book.jpg")

# 方式 B：图片字节（前端 wx.uploadFile / 后端接收 bytes 后直接传入）
result = pipeline.recommend(image_bytes=b"\xff\xd8...")

# 方式 C：无输入 -> fallback 兜底（返回可手动选择的类别列表）
result = pipeline.recommend()
```

### 3.2 统一返回结构（供前端发布页直接渲染）

```json
{
  "category_id": "textbook",
  "category_name": "教材",
  "confidence": 0.95,
  "need_confirm": false,
  "matched_by": "alias",
  "fallback": false,
  "available_categories": [
    {"category_id": "textbook", "category_name": "教材"},
    {"category_id": "electronics", "category_name": "电子产品"},
    {"category_id": "life_goods", "category_name": "生活用品"},
    {"category_id": "clothing", "category_name": "衣物"},
    {"category_id": "stationery", "category_name": "文具用品"},
    {"category_id": "digital_accessories", "category_name": "数码配件"},
    {"category_id": "sports_equipment", "category_name": "运动器材"},
    {"category_id": "furniture", "category_name": "家具与宿舍用品"},
    {"category_id": "other_books", "category_name": "其他书籍/资料"},
    {"category_id": "other", "category_name": "其他"}
  ],
  "status": "auto_fill",
  "fallback_reason": null,
  "raw_label": "textbook"
}
```

### 3.3 字段语义

| 字段 | 类型 | 语义 |
|---|---|---|
| `category_id` | str/None | 识别出的类别（Day4 统一体系 10 类）；fallback 时为 None |
| `category_name` | str/None | 类别中文名 |
| `confidence` | float/None | 标准化调整后的置信度 0~1（兜底 other 会 -0.10） |
| `need_confirm` | bool | **前端核心开关**：True=需要人工介入（确认/选择/兜底） |
| `matched_by` | str/None | alias（同义词命中）/ keyword（关键词命中）/ fallback（兜底） |
| `fallback` | bool | 服务异常/超时兜底（区别于业务兜底 other） |
| `available_categories` | list | 10 个一级类别 [{category_id, category_name}]，手动选择下拉直接用 |
| `status` | str | 细分：auto_fill / manual_confirm / manual_select / fallback |
| `fallback_reason` | str/None | 兜底原因说明（前端可展示） |
| `raw_label` | str/None | AI 原始标签（便于复盘） |

前端渲染建议：
- `need_confirm == False`（auto_fill）：类别高亮显示，用户可改但默认已填。
- `need_confirm == True` 且 `status == manual_confirm`：自动填充类别 + 提示"识别置信度中等，请确认类别"。
- `need_confirm == True` 且 `status == manual_select`：弹出类别选择器（用 `available_categories` 渲染下拉）。
- `fallback == True`：展示 `fallback_reason` + 类别选择器。

---

## 4. 前端推荐接口草案（POST /recognize）

> ⚠️ **字段命名严格按本草案**：请求/响应字段与后端不一致会静默失败（联调时请逐字段对齐，并由测试成员交叉验证）。

**请求**
```
POST /recognize
Content-Type: multipart/form-data

image: <file>           # 上传图片（后端读 bytes）
```

**响应（HTTP 200，统一 JSON）**
```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "category_id": "textbook",
    "category_name": "教材",
    "confidence": 0.95,
    "need_confirm": false,
    "matched_by": "alias",
    "fallback": false,
    "available_categories": [
      {"category_id": "textbook", "category_name": "教材"},
      {"category_id": "electronics", "category_name": "电子产品"},
      {"category_id": "life_goods", "category_name": "生活用品"},
      {"category_id": "clothing", "category_name": "衣物"},
      {"category_id": "stationery", "category_name": "文具用品"},
      {"category_id": "digital_accessories", "category_name": "数码配件"},
      {"category_id": "sports_equipment", "category_name": "运动器材"},
      {"category_id": "furniture", "category_name": "家具与宿舍用品"},
      {"category_id": "other_books", "category_name": "其他书籍/资料"},
      {"category_id": "other", "category_name": "其他"}
    ]
  }
}
```

- 后端实现建议：接收图片 bytes → `RecognitionPipeline.recommend(image_bytes=...)` → 序列化返回 `data`。
- `code != 0` 时为系统级错误（如 413 图片过大），前端展示 `message` 并走手动选择。

---

## 5. 与估价引擎的衔接（Day5 输出 → Day6 完整链路）

```python
# 识别后可直接进入估价（Day4 EstimateParams 校验 + Day2 price_engine 估价）
from estimate_params import EstimateParams
from price_engine import estimate_price  # Day2 交付

# 识别结果 -> 估价输入（类别先用 to_engine_category 映射回 Day2 折扣表 ID）
from category_normalizer import to_engine_category

params = EstimateParams(
    category=result["category_id"],        # Day4 统一类别
    condition="good",                      # 品相由用户选择（前端）
    original_price=68,
    asking_price=30,
    image_path=image_path,                 # 复用预留字段
)
check = params.validate()                  # 校验错误码与 Day2 一致
if check["valid"]:
    engine_result = estimate_price(
        category=to_engine_category(params.category),
        condition=params.condition,
        original_price=params.original_price,
        ...
    )
```

---

## 6. 待办事项（后续天）

- **Day6（完善折扣规则与区间计算）**：基于 Day4 标准化类别完善 Day2 折扣表的区间计算，确保 `to_engine_category()` 映射的 10 类在折扣表全覆盖；同步实现估价接口（POST /estimate）。
- **Day9（匹配算法）**：匹配公式 MatchScore = 0.50×类别意愿 + 0.30×价格 + 0.20×同校（高匹配 0.75 / 普通 0.50），价格维度基于用户 `asking_price`。
- **Day8（Goods 表）**：确认 Goods 表存储 `asking_price`（用户手填真实标价），识别结果 `category_id` 直接入库。

---

## 7. 自测验证

```
python test_day5.py
结果：PASS=25 FAIL=0（覆盖高/中/低置信度分流、未知标签兜底、服务异常兜底、
      image_path/image_bytes 输入、need_confirm 判定、Day2 MockAIClient 兼容等）
```

注意：test_day5.py 会引用 Day2 交付目录（`成员B_Day2_交付\ai_client.py`）与 Day4 交付目录（`成员B_Day4_交付\category_normalizer.py`），路径已内置，请保持目录结构不变。
