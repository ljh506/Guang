---
AIGC:
    Label: "1"
    ContentProducer: 001191440300708461136T1XGW3
    ProduceID: 40eb6eba8f783c17143097188cf613e3_7e5ba6bfc16f11f1a05452540064ee0f
    ReservedCode1: vqnl4IdbvGaIXO4DBM/Ed55hAqv0f9mIYwYdGkA+d5JVLxf9ehpQcTgtqcI09Q3y5QBnBmAQesLThqRNLJTLIVADk7SMHYHmAyOR4H3YxrlbuxUtBaTivxmnGfR4we4vFQYNGC7Zt+h6CxfvT1qrdlSfvtpaEoZFI4tYDikb0NN4SFbEnYNmTu8QefY=
    ContentPropagator: 001191440300708461136T1XGW3
    PropagateID: 40eb6eba8f783c17143097188cf613e3_7e5ba6bfc16f11f1a05452540064ee0f
    ReservedCode2: vqnl4IdbvGaIXO4DBM/Ed55hAqv0f9mIYwYdGkA+d5JVLxf9ehpQcTgtqcI09Q3y5QBnBmAQesLThqRNLJTLIVADk7SMHYHmAyOR4H3YxrlbuxUtBaTivxmnGfR4we4vFQYNGC7Zt+h6CxfvT1qrdlSfvtpaEoZFI4tYDikb0NN4SFbEnYNmTu8QefY=
---



# 交接文档 · 成员B Day 1（AI/算法）

> 交付时间：Day 1（需求冻结日）
> 面向对象：成员A（后端）、成员C（前端A）、成员D（前端B）、成员E（UI/测试/材料）
> 目的：说明成员B Day 1 产出、Day 2 起的接口约定、数据表字段建议、风险与兜底，便于全员按统一口径开发。

## 1. Day 1 产出清单

| 文件 | 内容 | 后续落点 |
|---|---|---|
| 1_AI识别类别清单.md | 10 个一级类别（含典型物品、关键词、置信度阈值、兜底策略） | Day 2 落地为 `categories.py`；Day 4 与D确认选择器 |
| 2_价格规则初稿.md | 折扣表（计划书四类+扩展）、品相分级、**建议估价区间计算**、reason_text 模板、**用户手动标价（asking_price）机制与校验提示**、边界处理、估价接口草案 | Day 2 落地 `price_engine.py` 初版；Day 6 完成估价接口 |
| 3_交换匹配规则初稿.md | 匹配维度 50/30/20、打分规则（**价格维度基于用户真实标价 asking_price**）、阈值 0.75/0.50、match_reason 模板、匹配接口草案 | Day 2 占位 `matcher.py`；Day 9 完成匹配算法 |

## 2. 需要各成员配合的事项

### 2.1 成员A（后端）

- **估价接口（POST /estimate）**：入参 `category_id / condition / original_price / is_free(可选) / device_age_months(可选)` → 出参 `estimated_min / estimated_max / reason_text / rule_ref / price_tip(可选)`。其中 `estimated_min / estimated_max` 为**建议估价区间（参考价）**，仅供展示；**真实标价 asking_price 由用户在发布页手动输入**，随发布接口（POST /goods）提交，不由 /estimate 生成。字段定义详见 2_价格规则初稿.md §7。
- **匹配接口（POST /exchange/match）**：入参 `user_id / goods_id` → 出参 `match_score / score_detail / match_reason` 列表。字段定义详见 3_交换匹配规则初稿.md §6。
- **意愿表达接口（POST /exchange/wish）**：`{user_id, wish_category_id}`，Day 9 前就位即可。
- 请求成员A：Day 2 建 `Goods` 表时按 §3 字段建议预留 `category/condition/estimated_min/estimated_max/asking_price/wish_category_id` 等字段；错误码规范按计划书风格统一 `{success, error_code, message}`。

### 2.2 成员C / 成员D（前端）

- **类别选择器**（成员D 发布页）：选项 = AI识别类别清单 §2 的 10 个类别；AI识别失败/低置信度时必须可用（手动选择）。
- **估价展示与真实标价**（成员D 发布/估价页）：展示建议区间 `estimated_min ~ estimated_max` + `reason_text` 原文（**不要前端自行拼装估价依据**）；**发布页在建议区间下方提供真实标价输入框（asking_price）**，用户手动填写真实成交价格，引擎不强制约束；仅在校验超区间时展示提示文案（如"您的标价高于建议区间，可能影响交换成功率"），**不阻断发布**。
- **置信度展示**（成员D 发布页 / 成员C 详情页）：`confidence >= 0.80` 高亮；0.60~0.80 提示"请人工确认"；< 0.60 进入手动选择。
- **匹配结果**（成员D 交换页）：展示 `match_score` 百分比 + `match_reason`；>= 75% 显示"高匹配"标签。
- 请求前端：字段命名严格按接口草案，前后端字段不一致会静默失败（参考历史踩坑：接口字段契约不一致导致功能不可见）。

### 2.3 成员E（测试 / 材料）

- 验收样例（价格）：`textbook + good + 68元 → 27~41元`（计划书示例，必须通过）。
- 测试用例建议：每个类别 × 三个品相至少 1 组；AI 失败手动选择场景至少 1 组；免费赠送场景 1 组；异常原价（空、负数、>100000、非数字）各 1 组。
- 匹配测试数据（Day 9 提供）：3 组可匹配（双向意愿）+ 2 组不可匹配。

## 3. 数据表字段建议（Goods 表，供成员A参考）

| 字段 | 类型 | 取值 / 说明 |
|---|---|---|
| category | TEXT | 10 个类别ID之一（见类别清单），来自AI识别或手动选择；原始识别结果建议另存 `ai_category` 用于复盘 |
| condition | TEXT | `new_like` / `good` / `fair`，必填，用户选择 |
| original_price | REAL/INTEGER | 元，必填（免费赠送填 0） |
| estimated_min / estimated_max | REAL/INTEGER | **建议估价区间（参考价）**，由估价接口写入，仅作展示参考，**不约束真实标价** |
| asking_price | REAL/INTEGER | **用户手填真实成交标价**，发布时必填；匹配算法价格维度以此计算 |
| wish_category_id | TEXT | 可选，用户"想换什么类别"的意愿表达（交换模块用） |
| is_free | INTEGER | 0/1，免费赠送标记 |

> User / School / Exchange / Message 表沿用计划书 §七；Exchange 表建议增加 `match_score`、`match_reason` 字段（可选，便于回显与复盘）。

## 4. 关键约定汇总（全员必读）

| 主题 | 约定 |
|---|---|
| 类别ID | 英文 snake_case（textbook / electronics / life_goods / clothing / school_supplies / digital_accessory / sports / furniture / books_other / other），全链路统一 |
| 品相 | new_like / good / fair 三档，禁止默认猜测 |
| 价格 | 规则引擎输出**建议估价区间** [min, max] + reason_text（仅参考展示）；**真实标价 asking_price 由用户手动填写**，超出建议区间仅提示不阻断；匹配价格维度基于 asking_price |
| 匹配 | 权重 类别/意愿50% + 价格30% + 同校20%；高匹配阈值 0.75 |
| 兜底 | AI 失败不阻断发布；免费赠送估价 [0,0] |
| 错误 | 统一 `{success, error_code, message}` 结构 |

## 5. 风险与兜底说明

| 风险 | 影响 | 兜底方案 |
|---|---|---|
| AI识别服务不可用/超时 | 发布流程卡住 | 手动类别选择器兜底，不阻断发布（计划书 §十七 责任边界） |
| 免费视觉服务标签不稳定 | 类别映射错乱 | 成员B维护标签→类别ID映射表；无法映射归入 `other` |
| 估价异常（原价缺失/超范围） | 接口报错 | 返回 400 + 明确错误码，前端提示用户修正；免费赠送走 [0,0] |
| 用户标价远超建议区间 | 交换成功率低 | **仅提示不阻断**（price_tip）；匹配算法基于真实标价自然降分 |
| 匹配数据不足 | 推荐列表为空 | 前端展示"暂无匹配，去漂流墙逛逛"，不报错 |
| 前后端字段不一致 | 功能静默失效 | 按 §2 接口草案逐字段对齐；联调时成员E交叉验证 |
| 折扣表与演示案例不符 | 答辩数据矛盾 | Day 6 用计划书示例（68元/良好/教材→27~41）强制校验 |

## 6. Day 2 起成员B计划

| 日期 | 任务 |
|---|---|
| Day 2 | `price_engine.py` 初版 + AI 接口调用封装（含标签映射） |
| Day 3 | 演示学校数据 / 测试用户数据（配合A） |
| Day 4 | 类别标准化 + 估价输入参数定义（配合D） |
| Day 5 | 图片→类别→置信度 AI 识别链路跑通 |
| Day 6 | 估价接口 + Goods 价格字段保存（**含 asking_price**）+ 5 组演示案例核对（建议区间 27~41 + 用户手填标价 30 场景） |
| Day 9 | 匹配算法落地（50/30/20） |

> 阻塞问题（当前）：无。待成员A确认 Goods 表字段后同步推进。
*（内容由AI生成，仅供参考）*
*（内容由AI生成，仅供参考）*
