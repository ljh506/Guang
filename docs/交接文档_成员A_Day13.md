# 交接文档_成员A_Day13

> 任务来源：项目计划书「十五、五人团队逐日开发任务表」Day 13 行，成员A 当日任务：**比赛 Demo 数据（后端落库）**。
> 依赖：成员B Day13 交付 `D:\desk\成员B_Day12_15_交付\Day13_交付\demo_data.py`（7 校 / 5 用户 / 20 商品 / 3 交换 / 聊天记录）。

---

## 一、当日产出

| 文件 | 说明 |
|---|---|
| `backend/scripts/demo_data.py` | 成员B Day13 交付副本（演示数据常量 + DAY3 CSV 缺失时的内置回退） |
| `backend/scripts/seed_demo.py` | 演示数据幂等种子脚本（衔接后端 FastAPI + SQLite） |
| `backend/tests/test_day13_demo_api.py` | Day13 后端验收测试（演示数据 API 查询 / 匹配 / 状态），**12 PASS / 0 FAIL** |
| `docs/交接文档_成员A_Day13.md` | 本交接文档 |

## 二、实现要点

- **固定 id 契约**：演示学校 id=1..7、演示用户 id=1..5、演示商品 id=1..20，与 Day3 种子数据（学校 id=1..7、Demo 用户 id=1..5）完全一致，保证 Day3/Day4 验收脚本的固定 id 引用（`user_id=1/2/3`、`school_id=1/3`）继续有效。
- **幂等重建**：先清除既有演示种子（按名称 + 固定 id 双重标识，逆依赖序删除：消息→会话→交换→想要→商品→用户→学校），再重建，可重复运行。
- **估价落库**：逐商品调用 `price_engine.estimate_price` 生成建议区间与依据文本，演示「估价」能力（如高等数学 68 元 → 27~41）。
- **匹配落库**：3 组演示交换调用 `match_engine.match_score` 计算匹配度与分级（EX1=0.781 high、EX2/EX3=0.500 normal），交换状态映射 negotiating→open、confirmed→confirmed，confirm_a/b 落库。
- **会话与消息**：3 组交换各建 1 条会话，聊天记录按 `DEMO_CHATS` 落库；EX1 演示链路附带 1 条 accepted 想要请求。

## 三、运行方式

```bash
cd backend
python scripts/seed_demo.py        # 重建演示数据（幂等）
python tests/test_day13_demo_api.py  # 验收：12 PASS / 0 FAIL
```

## 四、验收结论

- `test_day13_demo_api.py`：**12 PASS / 0 FAIL**（演示商品可查、估价区间与依据非空、3 组交换匹配度 ≥0.5、状态映射正确、EX1 高匹配推荐链路通）。
- 版本：1.0.0 → 1.1.0。

## 五、衔接说明

- 供比赛演示：演示数据已写入后端 `shiguang.db`，API 可直接查询 7 校 / 5 用户 / 20 商品 / 3 交换。
- Day14 比赛材料、Day15 封版回归均以本数据为演示基线。
*（内容由AI生成，仅供参考）*
