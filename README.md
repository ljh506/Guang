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



# 拾光Agent · 大学校园智能闲置循环平台

> 校园闲置循环与以物换物平台 —— 后端服务 + AI/算法模块

本仓库包含两部分：

1. **后端服务（成员A）**：FastAPI + SQLite，用户/学校/商品/交换 API；
2. **AI/算法模块（成员B）**：
   - **物品类别识别**：封装外部视觉识别服务，将图片识别为平台 10 个一级类别之一，并输出置信度；
   - **价格建议引擎**：按「类别 + 品相」查折扣表，计算建议估价区间（仅供参考）；
   - **交换匹配规则**：基于 asking_price 的价格匹配，规则见 `docs/3_交换匹配规则初稿.md`。

设计原则：**AI 只负责类别识别，不直接决定价格**；真实成交标价 `asking_price` 由用户手动输入，规则引擎仅给出参考区间与提示，不阻断发布。

---

## 当前进度

- Day 1：Git 仓库、FastAPI 骨架、SQLite 连接、User/School 表初版。
- Day 2（成员A）：User/School 基础模型定稿（对齐计划书 §七）；健康检查 API 增加数据库连通检测；集成成员B交付的价格引擎与 AI 客户端至 `backend/app/services/`（自测 PASS=32 FAIL=0）。
- Day 2（成员B）：price_engine / ai_client / test_day2 交付，Day1 规则文档入库。
- Day 3（成员B）：data 演示数据交付（seed_data.py / demo_schools.csv / demo_users.csv），Day3 交接文档入库。

---

## 目录结构

```
Guang/
├── backend/                    # 后端服务（成员A，FastAPI + SQLite）
│   ├── app/
│   │   ├── main.py             # FastAPI 入口（/ 与 /api/v1/health）
│   │   ├── models.py           # User / School 模型
│   │   ├── database.py         # SQLite 连接与会话
│   │   ├── routers/health.py   # 健康检查（服务 + 数据库连通检测）
│   │   └── services/           # 成员B算法模块正式集成位置
│   │       ├── price_engine.py # 价格规则引擎（建议估价区间 + 标价提示校验）
│   │       └── ai_client.py    # AI 识别服务客户端（阈值分流 + 失败兜底，可 mock）
│   ├── tests/test_day2.py      # Day2 集成自测脚本（32 项用例）
│   ├── requirements.txt        # 后端依赖清单
│   └── shiguang.db             # SQLite 数据库（运行时生成）
├── price_engine.py             # 成员B原始交付副本（正式集成位于 backend/app/services/）
├── ai_client.py                # 成员B原始交付副本
├── test_day2.py                # 成员B自测脚本副本
├── requirements.txt            # 算法模块依赖（无第三方依赖，标准库即可）
├── data/                       # Day3 演示数据与用户数据（成员B）
│   ├── seed_data.py            # SQLite 幂等初始化脚本（建表 + 演示数据）
│   ├── demo_schools.csv        # 演示高校数据（7 所）
│   └── demo_users.csv          # 演示用户数据（5 个）
├── 成员A_Day2_交付说明.md      # 成员A Day2 交付说明
└── docs/                       # 规则文档与交接文档（Day1 + Day2 + Day3）
    ├── 1_AI识别类别清单.md     # Day1：10 个一级类别、置信度阈值、兜底策略
    ├── 2_价格规则初稿.md       # Day1：折扣表、估价公式、asking_price 手动标价机制
    ├── 3_交换匹配规则初稿.md   # Day1：匹配权重 50/30/20、阈值、匹配接口草案
    ├── 4_交接文档_成员B_Day1.md # Day1：面向团队交接说明与风险提示
    ├── 交接文档_成员B_Day2.md  # Day2：成员B 交接说明
    └── 交接文档_成员B_Day3.md  # Day3：成员B 交接说明
```

---

## 后端启动方式（成员A）

### 环境要求

- Python 3.11+
- Anaconda

### 创建并激活环境

```bash
conda create -n shiguang python=3.11 -y
conda activate shiguang
pip install -r backend/requirements.txt
```

### 启动

```bash
cd backend
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

验证：`GET http://127.0.0.1:8000/api/v1/health` 返回 `{"status":"ok","database":"ok"}`。

---

## 模块功能与使用示例（成员B）

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
python test_day2.py          # 成员B原始脚本（仓库根目录）
python backend/tests/test_day2.py   # 集成进后端工程后的脚本
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

---

## 后续迭代计划

| Day | 计划 |
|---|---|
| Day 3 | 用户/学校增删查、选择学校 API（成员A） |
| Day 4 | 类别标准化：识别标签映射表扩充、类别选择器交互对齐 |
| Day 5 | 识别链路：前端上传 → AI 识别 → 结果确认全流程联调 |
| Day 6 | 折扣完善：折扣表配置化、电子产品年限规则细化、估价接口 POST /estimate 正式落地 |
| Day 9 | 匹配算法：基于 asking_price 的价格接近度评分与匹配接口实现 |

---

## 安全与合规说明

- 本仓库代码**不含任何密钥、Token 或团队内部敏感信息**；
- 接入真实视觉识别服务时，密钥应通过环境变量或配置中心注入，**严禁硬编码进代码**；
- 如需上传公开仓库，建议同时补充开源许可证文件。
