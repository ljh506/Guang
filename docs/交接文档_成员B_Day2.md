---
AIGC:
    Label: "1"
    ContentProducer: 001191440300708461136T1XGW3
    ProduceID: 40eb6eba8f783c17143097188cf613e3_03c35057c20611f1bc7f525400638852
    ReservedCode1: nXLN+J1vqa7XiPImDesCzq1uZL5rgAm3BuR6UsI0KbiF20zDCju1AUE7CYXGGf7WjiX8X07Cftuifcm/igmHmexYudNZERFOhKZBph7/crC7xaSFT7krsAntlm4HmYythU4OdE9G3NWYoiCWR4ezFOU3sPAdVLwMyV+oR24JYWw+SOFMjm3+f1YZTmw=
    ContentPropagator: 001191440300708461136T1XGW3
    PropagateID: 40eb6eba8f783c17143097188cf613e3_03c35057c20611f1bc7f525400638852
    ReservedCode2: nXLN+J1vqa7XiPImDesCzq1uZL5rgAm3BuR6UsI0KbiF20zDCju1AUE7CYXGGf7WjiX8X07Cftuifcm/igmHmexYudNZERFOhKZBph7/crC7xaSFT7krsAntlm4HmYythU4OdE9G3NWYoiCWR4ezFOU3sPAdVLwMyV+oR24JYWw+SOFMjm3+f1YZTmw=
---

# 交接文档 · 成员B Day2 交付

- 作者：成员B（AI/算法）
- 日期：2026-10-07
- 交付目录：`C:\Users\LENOVO\Desktop\拾光Agent\成员B_Day2_交付\`
- 前置依据：Day1 三份规则文档（AI识别类别清单 / 价格规则初稿 / 交换匹配规则初稿）已定稿，本日代码与其字段命名、机制完全对齐。

---

## 1. 本日交付物清单

| 文件 | 说明 | 运行方式 |
|---|---|---|
| `price_engine.py` | 价格规则引擎初版：类别+品相 → 建议估价区间（estimated_min/estimated_max）+ 估价依据文本（reason_text） | `python price_engine.py`（自带自测） |
| `ai_client.py` | AI 识别服务客户端初版：图片→类别+置信度，阈值分流与失败兜底，可注入 backend 进行 mock | `python ai_client.py`（自带自测） |
| `test_day2.py` | 自测脚本：计划书示例 + 边界情况 + 阈值分流 + 一致性校验，**32 项全部 PASS** | `python test_day2.py` |
| `交接文档_成员B_Day2.md` | 本文档 | — |

> 已执行验证结果：`PASS=32 FAIL=0`（覆盖：68元/良好/教材→27~41、原价缺失/非数字/超范围、品相缺省/非法、类别非法、免费赠送、电子产品年限微调、asking_price 区间提示、auto_fill/manual_confirm/manual_select/fallback 全部分流、标签映射、折扣表与 Day1 一致性）。

---

## 2. 关键机制约定（对齐 Day1）

1. **建议区间 ≠ 真实标价**：`estimate_price()` 输出的 `estimated_min/estimated_max` 仅是建议估价区间（参考价）。真实成交标价 `asking_price` 由用户在发布页**手动输入**，引擎不约束、不阻断。
2. **标价提示不阻断**：`validate_asking_price()` 仅在标价低于区间或高于区间时返回 `price_tip` 提示文案，超出区间仍允许发布。
3. **匹配用 asking_price**：Day3 匹配模块（交换匹配规则初稿）价格维度读取 `Goods.asking_price`，**不使用**建议区间。建议区间仅用于前端展示与引导。
4. **字段命名统一**：`category / condition / original_price` → `estimated_min / estimated_max / reason_text`；AI 识别返回 `category_id / category_name / confidence`。

---

## 3. price_engine 使用方式

### 3.1 核心接口

```python
from price_engine import estimate_price, validate_asking_price

# 估价：教材 / 良好 / 原价68元
result = estimate_price("textbook", "good", 68)
# -> {
#   "estimated_min": 27, "estimated_max": 41,
#   "reason_text": "「教材」良好，参考原价 68 元，按教材类良好折扣 0.4~0.6 计算，建议估价 27~41 元。",
#   "rule_ref": {"category": "textbook", "condition": "good", "low": 0.4, "high": 0.6},
# }

# 标价校验（仅提示不阻断）
tip = validate_asking_price(30, 27, 41)   # None（在区间内）
tip = validate_asking_price(10, 27, 41)   # "您的标价低于建议区间..."
```

### 3.2 参数说明

| 参数 | 取值 | 说明 |
|---|---|---|
| `category_id` | 10 个类别ID（见 `CATEGORY_NAMES`） | 非法 → 错误 `CATEGORY_INVALID` |
| `condition` | `new_like` / `good` / `fair` | 缺省 → `CONDITION_REQUIRED`；非法 → `CONDITION_INVALID` |
| `original_price` | 数字或数字字符串（元） | 缺失 → `PRICE_ORIGINAL_REQUIRED`；非数字 → `PRICE_INVALID_FORMAT`；>100000 → `PRICE_OUT_OF_RANGE` |
| `is_free` | 免费赠送标记 | 免费时估价恒为 0~0 元 |
| `device_age_months` | 电子产品使用月数（可选） | 仅 `electronics + new_like` 生效，做折扣微调（≤6月 0.70~0.78 / ≤18月 0.75~0.82 / >18月 0.80~0.85） |

### 3.3 错误返回

失败统一返回：`{"error": {"error_code": "XXX", "message": "中文说明"}}`，错误码见 `ERROR_CODES`。

### 3.4 折扣表速查（与计划书 §四 一致）

| 类别 | 全新/较新 | 良好 | 一般 |
|---|---|---|---|
| 教材 | 0.6~0.8 | **0.4~0.6** | 0.2~0.4 |
| 电子产品 | 0.7~0.85 | 0.5~0.7 | 0.1~0.5 |
| 生活用品 | 0.5~0.7 | 0.4~0.5 | 0.1~0.4 |
| 衣物 | 0.4~0.6 | 0.3~0.4 | 0.15~0.3 |
| 文具用品 | 0.5~0.7 | 0.4~0.5 | 0.15~0.35 |
| 数码配件 | 0.5~0.7 | 0.3~0.5 | 0.1~0.3 |
| 运动器材 | 0.5~0.7 | 0.35~0.5 | 0.15~0.3 |
| 家具与宿舍用品 | 0.5~0.7 | 0.35~0.5 | 0.15~0.35 |
| 其他书籍/资料 | 0.4~0.6 | 0.3~0.4 | 0.15~0.3 |
| 其他 | 0.4~0.6 | 0.3~0.5 | 0.1~0.3 |

---

## 4. ai_client 使用方式

### 4.1 接入真实服务

```python
from ai_client import AIClient

def my_vision_backend(image_path):
    """调用第三方识别服务，返回 {"label": str, "confidence": float}。"""
    # ... 接入具体服务（腾讯云/百度等）...
    return {"label": "book", "confidence": 0.93}

client = AIClient(backend=my_vision_backend, timeout_seconds=5.0)
result = client.recognize("C:/path/to/photo.jpg")
```

### 4.2 统一返回结构

| 字段 | 说明 |
|---|---|
| `status` | `auto_fill` / `manual_confirm` / `manual_select` / `fallback` |
| `category_id` | 类别ID；fallback 时可能为 None（前端弹手动选择） |
| `category_name` | 类别中文名 |
| `confidence` | 置信度 0~1 |
| `fallback` | bool，是否需要手动选择兜底 |
| `fallback_reason` | 兜底原因中文说明 |
| `raw_label` | 第三方原始标签（便于复盘） |

### 4.3 阈值分流规则（Day1 §3）

| 置信度 | status | 前端行为 |
|---|---|---|
| ≥ 0.80 | `auto_fill` | 自动填充类别，高亮展示 |
| 0.60 ~ 0.80 | `manual_confirm` | 自动填充但提示"请人工确认" |
| < 0.60 | `manual_select` | 不自动填充，弹出类别手动选择 |
| 服务异常/超时/数据非法 | `fallback` | 返回兜底标记，发布流程不中断，手动选类别 |

### 4.4 Mock 测试

```python
from ai_client import MockAIClient

mock = MockAIClient()
mock.add_success("textbook", 0.96)   # -> auto_fill
mock.add_success("t-shirt", 0.70)    # -> manual_confirm
mock.add_failure("模拟超时")          # -> fallback
r = mock.recognize("test.jpg")
```

---

## 5. 预估接口对接约定（供其他成员联调）

### 5.1 估价接口 `POST /estimate`

请求：

```json
{
  "category_id": "textbook",
  "condition": "good",
  "original_price": 68
}
```

响应：

```json
{
  "estimated_min": 27,
  "estimated_max": 41,
  "reason_text": "「教材」良好，参考原价 68 元，按教材类良好折扣 0.4~0.6 计算，建议估价 27~41 元。"
}
```

错误响应：`{"error": {"error_code": "PRICE_INVALID_FORMAT", "message": "..."}}`

### 5.2 标价校验（发布页）

- 前端展示建议区间 `estimated_min/estimated_max`；
- 用户输入 `asking_price` 后调 `validate_asking_price()` 获得 `price_tip`（可空），仅提示不阻断；
- 发布保存字段：`Goods.asking_price = 用户输入值`。

### 5.3 AI 识别接口 `POST /recognize`

请求：`{"image_path": "..."}`（或图片二进制）
响应：status + category_id + category_name + confidence + fallback + fallback_reason

---

## 6. 待 Day4 / Day6 完善事项

1. **Day4（成员C对接）**：匹配模块读取 `Goods.asking_price`，价格维度权重 50 分；需要成员B提供 `asking_price` 的存取约定（字段已对齐，Goods 表落库即可）。
2. **Day4（匹配接口）**：匹配规则初稿中的 `match_score / score_detail / match_reason` 由匹配模块输出，价格维度输入为 `asking_price`，本引擎不再参与。
3. **Day6（扩展）**：
   - `price_engine.py` 扩展折扣表配置化（当前为常量字典，可改为 JSON/数据库）；
   - 电子产品年限微调规则细化（当前为三段式初版）；
   - 多图识别（当前单图）；识别结果二次确认回流训练数据；
   - 折扣表按热销品类动态调优。
4. **真实服务接入**：`ai_client.py` 的 backend 目前默认抛异常（走兜底），需服务端接入真实视觉识别 API 并补充标签映射表 `CATEGORY_ALIASES`。
5. **并发/性能**：识别服务超时（默认 5s）与失败重试策略待联调确认。

---

## 7. 风险与兜底说明

| 风险 | 兜底方案 |
|---|---|
| 视觉识别服务不可用/超时/失败 | `ai_client.recognize()` 捕获所有异常 → `fallback` 返回，前端弹手动类别选择，发布流程不中断 |
| 置信度低（<0.60） | `manual_select` 不自动填充，避免误分类 |
| 置信度中等（0.60~0.80） | `manual_confirm` 自动填充 + 人工确认提示 |
| 原价缺失/非法/超范围 | `estimate_price()` 返回明确错误码，前端拦截提示，不产出错误估价 |
| 品相缺省 | 引擎**不猜测默认品相**，返回 `CONDITION_REQUIRED`，必须用户显式选择 |
| 未知识别标签 | 映射到 `other` 兜底类别，保证流程继续 |
| 标价脱离建议区间 | 仅 `price_tip` 提示，不阻断发布（产品决策：尊重用户自主标价） |

---

## 8. 对团队其他成员的操作提示

- **成员A（前端/产品）**：发布页展示 `estimated_min/estimated_max` 为建议区间，`asking_price` 输入框必填手填；AI 识别结果按 status 区分自动填充/确认/手选/兜底四态渲染；`price_tip` 黄色提示不阻断。
- **成员C（匹配/后端）**：交换匹配价格维度读 `Goods.asking_price`，勿用建议区间；匹配分值建议权重 50 分（价格）、30 分（品类）、20 分（其他），按 Day1 匹配规则初稿执行。
- **测试同学**：可直接运行 `python test_day2.py` 复验；新增用例建议沿用 `check()` 断言风格。

---

## 9. 复验命令

```powershell
cd C:\Users\LENOVO\Desktop\拾光Agent\成员B_Day2_交付
python test_day2.py
```

预期输出：`===== 结果汇总：PASS=32 FAIL=0 =====`
*（内容由AI生成，仅供参考）*
