# 交接文档_成员A_Day15

> 任务来源：项目计划书「十五、五人团队逐日开发任务表」Day 15 行，成员A 当日任务：**封版（只修 Bug 不新增功能）+ 全量回归 + GitHub 同步**。
> 依赖：成员B Day15 交付 `D:\desk\成员B_Day12_15_交付\Day15_交付\final_regression.py` + `手动兜底处理说明.md`。

---

## 一、当日产出

| 文件 | 说明 |
|---|---|
| `backend/scripts/final_regression.py` | 成员B Day15 最终回归脚本副本（复用 Day11 核心检查 + 跨日链路冒烟 + Day13 演示数据回归） |
| `docs/手动兜底处理说明.md` | 成员B 手动兜底手册归档（AI 识别 / 估价异常 / 匹配与交换人工介入 / 数据回退） |
| `backend/scripts/seed_demo.py` | **修复**：演示数据改为固定 id 契约（学校 1-7 / 用户 1-5 / 商品 1-20），修复历史 clear_demo 误删同名种子学校导致 Day3/Day4 固定 id 引用失效的问题 |
| `docs/交接文档_成员A_Day15.md` | 本交接文档 |

## 二、封版回归结论

**全量回归（Day2~Day15，21 个测试脚本）全部通过，0 FAIL**：

| 阶段 | 脚本 | 结果 |
|---|---|---|
| Day2 | test_day2 | 32/32 |
| Day3 | test_day3 | 17/17 |
| Day4 | test_day4 / test_day4_api | 34/34、26/26 |
| Day5 | test_day5_api / test_day5_pipeline | 20/20、28/28 |
| Day6 | test_day6_estimate_api | 24/24 |
| Day7 | test_day7_engine / test_day7_want_api | 45/45、28/28 |
| Day8 | test_day8_chat_rules / test_day8_message_api | 35/35、27/27 |
| Day9 | test_day9_exchange_api / test_day9_match_engine | 33/33、全过 |
| Day10 | test_day10_exchange_api / test_day10_match_explanation | 28/28、全过 |
| Day11 | test_day11_full_flow_api / test_day11_algorithm_check | 27/27、全过 |
| Day12 | test_day12_prompt_api / test_day12_user_prompt | 29/29、44/44 |
| Day13 | test_day13_demo_api | 12/12 |
| Day14 | test_day14_doc_check | 24/24 |

## 三、封版修复说明（只修 Bug，不新增功能）

- **问题**：接入 Day13 演示数据后，`test_day3.py` / `test_day4_api.py` 大量 FAIL（学校/用户固定 id 引用失效，如 `user_id=1` 不存在、`school_id=1` 不存在）。
- **根因**：旧版 `seed_demo.py` 的 clear_demo 按学校名删除时误删了 Day3 同名种子学校（清华等 7 校，id 1-7），重建时使用自增 id 导致演示实体 id 漂移（学校 30-36、用户非 1-5），破坏固定 id 契约。
- **修复**：重构 `seed_demo.py` 为固定 id 幂等写入（学校 id=1..7、用户 id=1..5、商品 id=1..20），与 Day3 种子数据保持一致；clear 阶段以「名称 + 固定 id」双重标识清理。修复后 `test_day3` 17/17、`test_day4_api` 26/26，全量回归无 FAIL。
- 版本：1.1.0 → **1.2.0（封版）**。

## 四、GitHub 同步

- 提交信息：Day12~Day15 成员A（提示集成 / 演示数据 / 比赛材料 / 封版回归），version 1.0.0 → 1.2.0。
- 仓库：https://github.com/ljh506/Guang.git

## 五、遗留事项

- 15 天竞赛收官。成员E 验收可直接复跑 `backend/tests/test_*.py` 全量回归，或运行 `python scripts/final_regression.py` 做跨日链路冒烟。
*（内容由AI生成，仅供参考）*
