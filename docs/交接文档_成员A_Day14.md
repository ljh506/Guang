# 交接文档_成员A_Day14（比赛材料归档与一致性核对）

- 日期：2026-10-18（Day12~15 合并执行日）
- 项目：拾光Agent 平台（FastAPI + SQLite，后端 ShingGuang）
- 交接人：成员A（后端负责人）

## 一、本次工作内容

1. 归档比赛材料：将成员B《拾光Agent_成员B算法原理说明.md》收入后端文档目录 `docs/算法原理说明.md`。
2. 以后端代码为唯一权威来源，对文档关键常量与后端 services 实现做一致性核对（等价于成员B 自测 test_day14.py 的后端版）：
   - 识别阈值：`recognition_pipeline.THRESHOLD_AUTO_FILL=0.80`、`THRESHOLD_MANUAL_CONFIRM=0.60`
   - 匹配权重：`match_engine.WEIGHT_CATEGORY_WISH=0.5 / WEIGHT_PRICE=0.3 / WEIGHT_SCHOOL=0.2`
   - 分级阈值：`THRESHOLD_HIGH=0.75 / THRESHOLD_NORMAL=0.50`
   - 估价折扣：`price_engine.DISCOUNT_TABLE` 教材 0.60~0.80 / 0.40~0.60 / 0.20~0.40
   - 估价错误码：`price_engine.ERROR_CODES`（6 个错误码齐全）
   - 原价上限：`MAX_ORIGINAL_PRICE=100000`
   - 类别体系：`category_normalizer.CATEGORY_IDS` 共 10 类

## 二、验收结果

- 文档结构：8 个章节全部齐全
- 常量核对：24 PASS / 0 FAIL（`backend/tests/test_day14_doc_check.py`）

## 三、版本与进度

- 版本：1.1.0（Day13 演示数据接入后保持）
- README.md 已追加 Day13/Day14 进度行

## 四、说明

- 文档为比赛答辩材料（算法原理部分），代码仍为唯一权威来源；若后续修改任何常量，请同步更新 `docs/算法原理说明.md` 并重跑 `test_day14_doc_check.py`。
- 演示数据（Day13）与比赛演示脚本：`backend/scripts/seed_demo.py`、`backend/scripts/demo_data.py`。
