---
AIGC:
    Label: "1"
    ContentProducer: 001191440300708461136T1XGW3
    ProduceID: 0aefa33c1a2af1417088275368d75db0_00c9464ac6f411f1a08152540064ee0f
    ReservedCode1: 6DUkR7tvwt284fQmjT/76ddADaDJNC5gCP8qvoaqyptEahvkD6R8lspVmj7IGOlEO9IuotdUnNnduHYKZI5yibPwJaNlUHUbRT7AjTDJXnAwWK0TdA81ChbOusZiJT3RgJfpOwT/+gcPdDEzJzB+XMnjW8tCflnxc04SbigSLxDfDGTBaHYslR0HEyw=
    ContentPropagator: 001191440300708461136T1XGW3
    PropagateID: 0aefa33c1a2af1417088275368d75db0_00c9464ac6f411f1a08152540064ee0f
    ReservedCode2: 6DUkR7tvwt284fQmjT/76ddADaDJNC5gCP8qvoaqyptEahvkD6R8lspVmj7IGOlEO9IuotdUnNnduHYKZI5yibPwJaNlUHUbRT7AjTDJXnAwWK0TdA81ChbOusZiJT3RgJfpOwT/+gcPdDEzJzB+XMnjW8tCflnxc04SbigSLxDfDGTBaHYslR0HEyw=
---

# 交接文档_成员A_Day9

> 项目：拾光Agent · 大学校园智能闲置循环平台
> 成员：成员A（后端）
> 日期：2026-10-16（Day 9）
> 仓库：https://github.com/ljh506/Guang.git

## 一、任务来源依据

- 来源：`拾光Agent_15天项目计划书.docx` 第十五节「五人团队逐日开发任务表」Day 9 行。
- Day9 团队目标：**匹配与协议**（交换匹配 → 协议生成）。
- 成员A 当日任务：**完成 Exchange 模型和匹配接口**。
- 当天验收：A/B 物品互相匹配出现高匹配推荐。

## 二、交付清单

| 文件 | 说明 |
|---|---|
| `backend/app/models.py` | Goods 增加 wish_category_id 列；新增 Exchange 模型 |
| `backend/app/schemas.py` | 新增 Exchange 匹配相关 schemas（match/accept/wish/推荐/记录） |
| `backend/app/routers/exchange.py` | 交换匹配 API（新建） |
| `backend/app/services/match_engine.py` | 集成成员B Day9 交付（匹配算法，相对导入适配） |
| `backend/app/routers/goods.py` | 商品发布落库/序列化 wish_category_id（含输出修复） |
| `backend/tests/test_day9_exchange_api.py` | Exchange 接口验收测试（新建，33 用例） |
| `backend/tests/test_day9_match_engine.py` | 成员B Day9 自测适配版（50 用例） |
| `backend/app/main.py` | 注册 exchange 路由，版本 0.7.0 → 0.8.0 |
| `docs/交接文档_成员A_Day9.md` | 本文档 |
| `README.md` | 追加 Day9 进度 |

## 三、完成内容

### 3.1 Exchange 模型（models.py）

- `Goods.wish_category_id`：商品「想换什么」的意愿表达（Day4 十类之一），供匹配引擎使用。
- `Exchange`：匹配记录模型，字段 goods_id / user_id / target_goods_id / target_user_id / match_score / level（high|normal）/ status（open 等）/ created_at。承载「发起方商品 ↔ 目标商品」的匹配关系，供去重与 Day10 协议衔接。

### 3.2 匹配接口（routers/exchange.py，5 个端点）

| 接口 | 说明 |
|---|---|
| `POST /api/v1/exchange/match` | 匹配推荐：对自己发布的商品，对全站可交换商品按 意愿50%+价格30%+同校20% 打分，返回降序推荐（含 score_detail / weights / match_reason / 目标商品名/类别/标价/昵称） |
| `POST /api/v1/exchange/accept` | 确认匹配：校验匹配度≥0.50 后落 Exchange 记录（open）；返回 Day8 状态机建议（高匹配 chatting→matched） |
| `GET /api/v1/exchange/matches?user_id=` | 我发起的匹配记录列表（可过滤 status，分页） |
| `POST /api/v1/exchange/wish` | 意愿表达：设置商品想换的类别（仅自己的商品，Day4 十类校验） |
| `GET /api/v1/exchange/wish/{goods_id}` | 查看商品当前想换的类别 |

### 3.3 成员B 交付集成

- 将 `D:\desk\成员B_Day9_交付` 中 `match_engine.py` 复制到 `backend/app/services/match_engine.py`，导入改为 `app.services` 内相对导入（`from .chat_rules import`，复用 Day8 状态机），并加异常降级。
- 引擎契约（未修改算法本体）：
  - `MatchScore = 0.50×类别/意愿 + 0.30×价格接近 + 0.20×同校`
  - 分级：≥0.75 high / ≥0.50 normal / <0.50 low（low 不进推荐列表）
  - 排序：总分降序 → 价格接近度降序 → 发布时间近者优先；单次最多 20 条
- 适配点：后端查询 Goods 时补充「可交换状态过滤」「已参与未完成交换的商品剔除」，并把 open Exchange 的 (user_id, goods_id) 作为 existing_pairs 传给引擎去重；返回前为每条推荐附带展示字段。

### 3.4 验收与回归

- `test_day9_match_engine.py`（成员B 自测适配版）：PASS 50 / FAIL 0。
- `test_day9_exchange_api.py`（成员A 验收，33 用例）：PASS 33 / FAIL 0，核心链路「A 教材(30元/想换篮球) ↔ B 篮球(32元/想换教材)，同校」match_score≈0.98125 / level=high，双向互相出现在对方高匹配推荐。
- 全量回归（Day2~Day9 十三项测试）无 FAIL；依赖服务器的 test_day3 / test_day4_api 在种子库上 PASS=17/26。
- 本地 SQLite 已 ALTER TABLE goods ADD COLUMN wish_category_id；为消除历史测试数据累积导致的基线偏差，回归前已用 `scripts/seed_data.py` 重置学校/用户种子（原库备份见会话 temp 目录）。

## 四、接口示例

```
POST /api/v1/exchange/match
{"user_id": 1, "goods_id": 12}
→ {"success": true, "data": [{"target_goods_id": 13, "target_user_id": 2,
   "match_score": 0.98125, "level": "high", "score_detail": {...},
   "weights": {"category_wish": 0.5, "price": 0.3, "school": 0.2},
   "match_reason": "...", "target_goods_name": "篮球（八成新）", ...}]}
```

*（内容由AI生成，仅供参考）*
