# 拾光Agent · 交接文档 成员B Day 9（匹配算法）

> 版本：v1.0（Day 9 正式交付）
> 成员：成员B | 日期：2026-10-14
> 交付目录：`C:\Users\LENOVO\Desktop\拾光Agent\成员B_Day9_交付\`

---

## 1. 本日任务与产出

计划书 Day 9 任务：**完成匹配算法**——类别匹配 / 用户意愿匹配 / 价格区间接近 / 同校优先，匹配度 = 类别/意愿 50% + 价格接近 30% + 同校 20%。

| 文件 | 说明 | 状态 |
|---|---|---|
| `match_engine.py` | 匹配算法模块（可解释规则，仅标准库） | ✅ 完成 |
| `test_day9.py` | 自测脚本，50 个用例 | ✅ 50/50 PASS |
| `交接文档_成员B_Day9.md` | 本交接文档 | ✅ 完成 |

### 1.1 自测结果

```
PASS: 50 / FAIL: 0 / 总用例: 50
全部通过
```

运行方式：`python test_day9.py`（退出码 0 = 全部通过）。

---

## 2. match_engine.py 使用方式

### 2.1 核心公式（与计划书 §五 / Day1 初稿一致）

```
MatchScore = 0.50 × Score_category_wish + 0.30 × Score_price + 0.20 × Score_school
```

| 维度 | 权重 | 打分规则 |
|---|---|---|
| 类别/意愿 `category_wish` | 0.50 | 双向完全匹配 1.0 / 双向类别匹配（无意愿同类）0.9 / 单向匹配 0.5 / 完全不匹配 0.0（不入候选） |
| 价格接近 `price` | 0.30 | `Score = 1 - |a-b|/max(a,b)`，基于 **Goods.asking_price（用户手填真实标价）**；标价相同 1.0；双方免费 1.0；单方免费 0.3；标价缺失/非法 0.0 |
| 同校优先 `school` | 0.20 | school_id 相同 1.0；不同/缺失 0.0 |

- 建议估价区间 `estimated_min / estimated_max` 仅作展示字段接收，**不参与匹配得分**（Day1 细则 §3.2 明确）。
- 阈值：`>= 0.75` 高匹配 high；`>= 0.50` 普通 normal；`< 0.50` 低 low（不进推荐列表）。
- 排序：总分降序 → 同分按价格接近度降序 → 再按发布时间近者优先；单次最多 20 条。
- 去重：同一对 (user, goods) 已存在未完成 Exchange 记录时不重复生成推荐（`existing_pairs` 参数）。

### 2.2 输入商品字段（Goods 字典）

| 字段 | 必填 | 说明 |
|---|---|---|
| `category_id` | 是 | 物品类别，来自 Day5 识别链路（Day4 统一 10 类体系） |
| `wish_category_id` | 否 | 用户想换的类别（str 或 list），缺失则回退到双向类别匹配 0.9 |
| `asking_price` | 是 | 用户手填真实标价（非负浮点数；0 = 免费赠送） |
| `school_id` | 是 | 学校 id，同校优先依据 |
| `status` | 否 | 物品状态；不在 `EXCHANGEABLE_STATUS`（默认 on_sale/active/available/可交换）则不进入候选 |
| `estimated_min / estimated_max` | 否 | 建议估价区间，仅透传展示，不参与得分 |
| `publish_time` | 否 | 排序用（同分按近者优先） |
| `goods_id / user_id` | 否 | 返回 target_goods_id / target_user_id、去重用 |

### 2.3 示例

```python
import sys
sys.path.insert(0, r"C:\Users\LENOVO\Desktop\拾光Agent\成员B_Day9_交付")
from match_engine import match_score, recommend

# 发起方商品
A = {"category_id": "textbook", "wish_category_id": "physics",
     "asking_price": 30, "school_id": 1, "status": "on_sale",
     "goods_id": 12, "user_id": 1, "publish_time": 100}
# 候选商品
B = {"category_id": "physics", "wish_category_id": "textbook",
     "asking_price": 32, "school_id": 1, "status": "on_sale",
     "goods_id": 20, "user_id": 2, "publish_time": 200}

m = match_score(A, B)
print(m["match_score"])      # 0.9812（≈98%，高匹配）
print(m["level"])            # "high"
print(m["score_detail"])     # {"category_wish": 1.0, "price": 0.9375, "school": 1.0}
print(m["match_reason"])     # 双方意愿匹配（textbook↔physics），双方标价 30 元与 32 元接近度 94%，同校，综合匹配度 98%。

recs = recommend(A, [B])     # 按匹配度降序返回推荐列表（>=0.50，最多 20 条）
```

### 2.4 推荐分级与状态衔接

```python
from match_engine import on_match

on_match("chatting", m["match_score"])
# {"valid": True, "from_state": "chatting", "to_state": "matched",
#  "reason": "...Day9 匹配命中", "score": 0.9812, "level": "high"}
```

- 高匹配（>=0.75）且当前状态为 `chatting` → 建议流转到 `matched`；
- 普通匹配（0.50~0.75）→ 不自动流转，可人工发起；
- 低匹配（<0.50）→ 不进推荐列表。

---

## 3. 与历史交付的衔接

### 3.1 与 Day1 匹配规则初稿
- 权重 50/30/20、阈值 0.75/0.50、`match_reason` 模板、`POST /exchange/match` 接口结构均按《3_交换匹配规则初稿.md》落地；
- 价格维度严格基于 `Goods.asking_price`（用户手填真实标价），未引入 AI 定价参与得分。

### 3.2 与 Day8 状态机（chat_rules.py）
- `chatting -> matched` 流转由本模块 `on_match()` 触发（Day8 已预留该合法流转）；
- `match_engine.py` 在可导入 `chat_rules` 时直接复用 `validate_transition()`，导入失败自动降级，不影响匹配计算。

### 3.3 与 Day5 识别链路（recognition_pipeline.py）
- 匹配输入的 `category_id` 来自 Day5 输出（Day4 统一 10 类体系）；`estimated_min/estimated_max` 由 Day7 price_engine 保障非负整数、异常不崩，本模块仅透传。

### 3.4 供后端（成员A）的接口约定（POST /exchange/match）

```
请求：
{ "user_id": 1, "goods_id": 12 }   // asking_price 由 Goods 表提供

响应：
{
  "success": true,
  "data": [
    {
      "target_goods_id": 20,
      "target_user_id": 2,
      "match_score": 0.9812,
      "score_detail": {"category_wish": 1.0, "price": 0.9375, "school": 1.0},
      "weights": {"category_wish": 0.5, "price": 0.3, "school": 0.2},
      "level": "high",             // high / normal / low
      "match_reason": "双方意愿匹配（textbook↔physics），双方标价 30 元与 32 元接近度 94%，同校，综合匹配度 98%。"
    }
  ]
}
```

- 意愿表达接口：`POST /exchange/wish` `{user_id, wish_category_id}`（存用户"想换什么"）；
- 错误响应统一 `{"success": false, "error_code": "...", "message": "..."}`；
- 后端落地：查询 Goods 时补 `status` 可交换过滤、`existing_pairs` 未完成交换去重，再调用 `recommend()`。

---

## 4. 待后续成员事项

### 4.1 待 Day11（算法检查）
- 权重/阈值与计划书一致性复核（当前 50/30/20、0.75/0.50 已对齐 Day1）；
- 建议抽样验证：3 组可匹配 + 2 组不可匹配测试数据（配合成员E），确认 `match_reason` 文案与分数一致性；
- 确认 `recommend()` 排序在真实数据规模下的稳定性（同分 ±0.001 的次序）。

### 4.2 待 Day13（演示案例）
- 使用计划书高匹配示例（教材 30 元 ↔ 物理 32 元、同校）作为演示主案例，预期输出约 98% 高匹配；
- 准备演示数据时确保 `asking_price` 为用户手填标价，避免 estimated 区间被误用于演示说明。

---

*（内容由AI生成，仅供参考）*
