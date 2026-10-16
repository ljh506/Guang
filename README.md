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
2. **AI/算法模块**：
   - **物品类别识别**：封装外部视觉识别服务，将图片识别为平台 10 个一级类别之一，并输出置信度；
   - **价格建议引擎**：按「类别 + 品相」查折扣表，计算建议估价区间（仅供参考）；
   - **交换匹配规则**：基于 asking_price 的价格匹配，规则见 `docs/3_交换匹配规则初稿.md`；
   - **识别链路编排（成员B Day5）**：`recognition_pipeline.py` 串联「backend 识别 → Day4 类别标准化 → 置信度阈值分流 → 兜底」，输出统一 recommend() 结构；`test_day5.py` 全流程自测 PASS=25 FAIL=0；交接文档见 `docs/交接文档_成员B_Day5.md`。


设计原则：**AI 只负责类别识别，不直接决定价格**；真实成交标价 `asking_price` 由用户手动输入，规则引擎仅给出参考区间与提示，不阻断发布。


---


## 当前进度


- Day 1：Git 仓库、FastAPI 骨架、SQLite 连接、User/School 表初版。
- Day 2（成员A）：User/School 基础模型定稿（对齐计划书 §七）；健康检查 API 增加数据库连通检测；集成成员B交付的价格引擎与 AI 客户端至 `backend/app/services/`（自测 PASS=32 FAIL=0）。
- Day 2（成员B）：price_engine / ai_client / test_day2 交付，Day1 规则文档入库。
- Day 3（成员A）：School/User 增删查改 + 选校 API；Pydantic schemas；接入B的 7 所学校 + 5 个用户演示数据；API 验收 PASS=17 FAIL=0。
- Day 3（成员B）：7 所学校 + 5 个用户 CSV、幂等 seed 脚本与 Day3 交接文档交付。
- Day 4（成员A）：Goods 模型 + 发布/列表/详情 API（发布时串联 Day4 校验与 Day2 估价引擎落库 estimated_min/max）；CORS 中间件；API 验收 PASS=26 FAIL=0。
- Day 4（成员B）：category_normalizer（180+ 别名标准化）+ estimate_params（参数校验）交付，自测 PASS=34 FAIL=0。
- Day 4（修复）：price_engine 免费赠送边界修复——is_free=True 且原价>0 时估价现在恒为 0~0（与 B 交接文档约定一致，Day2 回归 32/32 通过）。
- Day 5（成员B）：recognition_pipeline 识别链路交付——复用 Day2 backend 注入机制，将标签映射升级为 Day4 category_normalizer 标准化，实现置信度阈值分流（auto_fill / manual_confirm / manual_select / fallback）与统一 recommend() 返回结构；自测 PASS=25 FAIL=0；Day5 交接文档入库。
- Day 5（成员A）：AI 识别 API 与错误处理（POST /api/v1/recognize，四类识别 + 阈值分流 + 失败兜底）并集成成员B 识别管线，测试全过并推送 GitHub；交接文档见 `docs/交接文档_成员A_Day5.md`。
- Day 6（成员B）：price_engine 完整版交付——10 类别 × 3 品相折扣表全覆盖、months_used 电子产品降档、is_free 免费赠送、asking_price 标价提示；自测 PASS=105 FAIL=0。
- Day 6（成员A）：估价接口 POST /api/v1/estimate；Goods 发布/更新落库估价区间（68 元教材良好 → 27~41，免费赠送 → 0~0）；API 验收 PASS=24 FAIL=0；交接文档见 `docs/交接文档_成员A_Day6.md`。
- Day 7（成员B）：price_engine Day7 边界加固——NaN/inf 不再崩溃、bool/NaN 标价提示、异常 price 文档化；与 Day6 契约向后兼容；自测 PASS=45 FAIL=0。
- Day 7（成员A）：收藏/想要请求 API（Want 模型 + POST /goods/{id}/want + 卖家/买家列表 + PATCH 状态流转 available→reserved）与商品详情 wants_count 状态字段；集成成员B Day7 边界加固引擎；API 验收 PASS=28 FAIL=0，全量回归 254/254 通过；交接文档见 `docs/交接文档_成员A_Day7.md`。
- Day 8（成员B）：chat_rules 交付——17 条快捷消息模板（6 场景 + 发送方约束 + 占位符渲染）与 6 态交易状态机（requested→chatting→matched→negotiating→confirmed/cancelled）；自测 PASS=35 FAIL=0。
- Day 8（成员A）：Message 模型与消息接口（Conversation 会话 + Message 消息 + 快捷消息模板接口 + 交易状态流转接口，集成成员B Day8 chat_rules）；验收链路「想要请求→会话→消息列表→聊天→收发」全通，API 验收 PASS=27 FAIL=0，全量回归（Day2~Day8 十套测试）无 FAIL；交接文档见 `docs/交接文档_成员A_Day8.md`。
- Day 9（成员B）：match_engine 匹配算法交付——意愿 50% + 价格 30% + 同校 20%，三级分级（high≥0.75 / normal≥0.50 / low<0.50），自测 PASS=50 FAIL=0。
- Day 9（成员A）：Exchange 模型与匹配接口（POST /exchange/match 匹配推荐 + POST /exchange/accept 确认匹配 + GET /exchange/matches 匹配记录 + wish 意愿表达接口），集成成员B match_engine；API 验收 PASS=33 FAIL=0，全量回归（Day2~Day9 十三项测试）无 FAIL；交接文档见 docs/交接文档_成员A_Day9.md。
