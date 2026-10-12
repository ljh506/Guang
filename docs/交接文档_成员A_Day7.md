# 交接文档 · 成员A · Day7

> 拾光Agent 15天项目 · 当日主题：商品详情与我想要
> 交付人：成员A（后端）｜日期：2026-10-12
> 对应计划书：十五、五人团队逐日开发任务表 · Day 7 行
> 成员A Day7 任务：**完成收藏/想要请求 API 和状态字段**

---

## 1. 当日目标与完成情况

| 计划书 Day7 成员A 任务 | 完成情况 |
|---|---|
| 完成收藏/想要请求 API | ✅ 新增 Want 模型 + 4 个接口（发起/卖家列表/买家列表/状态更新） |
| 完成状态字段 | ✅ Want.status 四态（pending/accepted/rejected/cancelled）+ Goods 状态联动（available→reserved） |
| 集成成员B Day7 交付 | ✅ 替换 `services/price_engine.py` 为成员B 边界加固版（45 自测用例入库） |
| 商品详情返回想要人数 | ✅ GoodsOut.wants_count 字段（详情接口返回） |

当天验收链路（计划书示例）：用户A发布 → 用户B浏览 → 点击「我想要」→ 产生请求 ✅ 已由测试覆盖。

---

## 2. 新增/改动文件清单

### 2.1 新增

| 文件 | 说明 |
|---|---|
| `backend/app/routers/wants.py` | 想要请求 API（4 个端点） |
| `backend/app/models.py`（追加 Want 类） | Want 表：goods_id / requester_id / status / message / created_at / updated_at |
| `backend/app/schemas.py`（追加） | WantCreate / WantStatusUpdate / WantOut / WantListOut |
| `backend/tests/test_day7_want_api.py` | Day7 想要 API 验收测试（28 用例） |
| `backend/tests/test_day7_engine.py` | 成员B Day7 引擎自测入库（45 用例，import 适配为 `app.services.price_engine`） |
| `docs/交接文档_成员A_Day7.md` | 本文档 |

### 2.2 修改

| 文件 | 改动 |
|---|---|
| `backend/app/main.py` | 版本 0.5.0→0.6.0；注册 wants 路由 |
| `backend/app/routers/goods.py` | import Want；`_goods_to_out` 支持 wants_count；详情接口返回想要人数；**免费赠送适配**（见 §4） |
| `backend/app/services/price_engine.py` | **整体替换**为成员B Day7 边界加固版（来源：`D:\desk\成员B_Day7_交付\price_engine_day7.py`） |
| `backend/app/schemas.py` | GoodsOut 增加 `wants_count: Optional[int]` |
| `README.md` | 补 Day6/Day7 进度记录 |

---

## 3. 接口契约（Day7 新增）

| 方法 | 路径 | 说明 | 请求体 | 响应 |
|---|---|---|---|---|
| POST | `/api/v1/goods/{goods_id}/want` | 发起想要请求（默认 pending） | `{"user_id": int, "message": str?}` | 201 `{"want": WantOut}` |
| GET | `/api/v1/goods/{goods_id}/wants` | 商品收到的想要请求（卖家视角，支持 ?status= 过滤 + 分页） | — | `{"total", "page", "page_size", "items"}` |
| GET | `/api/v1/users/{user_id}/wants` | 我发出的想要请求（「我想要的」列表，含商品名） | — | `{"total", "page", "page_size", "items"}` |
| PATCH | `/api/v1/wants/{want_id}` | 更新状态 | `{"status": "pending\|accepted\|rejected\|cancelled"}` | 200 `{"want": WantOut}` |

**WantOut 字段**：id / goods_id / requester_id / status / message / goods_name / requester_nickname / created_at / updated_at

### 状态字段语义

- `pending`：已提交（默认）
- `accepted`：卖家接受 → 商品状态 `available → reserved`（被保留）
- `rejected`：卖家拒绝（终态）
- `cancelled`：买家取消（终态）

### 业务规则

1. 不能对自己的商品发起想要；已存在 pending 请求不可重复发起；商品 removed 不可发起。
2. 请求处于终态（rejected/cancelled）不可再变更；accepted 不可重复接受、不可转 rejected（仅可取消）。
3. 接受请求时商品必须为 `available`（若期间商品已 removed/exchanged 则拒绝接受）。
4. 商品详情 `wants_count` = pending + accepted 请求数（买家取消/卖家拒绝不计）。

---

## 4. 集成适配说明（重要）

### 4.1 引擎替换（成员B Day7 → 项目）

`price_engine_day7.py` 与 Day6 引擎签名完全一致（`estimate_price(category, condition, original_price, months_used, is_free, asking_price)`），
仅加固：NaN/inf 不再崩溃（返回 PRICE_INVALID_FORMAT）、bool/NaN 标价提示、异常 price 文档化、months_used 文档化。
**直接整体替换 `backend/app/services/price_engine.py`，无调用方改动。**

### 4.2 免费赠送 0~0 适配（回归修复）

⚠️ 成员B Day7 引擎的 `is_free` 仅处理**原价缺失/非法**场景；对「免费赠送 + 有效正数原价」（如 45 元）不再强制归零
（Day6 引擎同样如此），导致 Day4 验收基线「免费赠送 → 0~0」（test_day4_api 用例）回归失败。

**适配**：`goods.py::_compute_estimate` 对 `trade_type == "free"` 在 API 层强制返回 `0~0` 与
「该物品选择免费赠送，估价为 0 元。」文案（与引擎 build_reason_text 的 free 分支一致）。
引擎交付物本身未改动，成员B Day7 引擎 45 用例不受影响。

> 建议：后续成员B 可在引擎内部统一 is_free 语义（is_free=True 时无论原价有效与否均归零），
> 则 API 层适配可移除。

---

## 5. 测试结果（全量回归）

| 测试文件 | 用例 | 结果 |
|---|---|---|
| `tests/test_day7_want_api.py`（Day7 新增） | 28 | ✅ PASS=28 FAIL=0 |
| `tests/test_day7_engine.py`（成员B Day7 入库） | 45 | ✅ PASS=45 FAIL=0 |
| `tests/test_day2.py` | 32 | ✅ PASS=32 FAIL=0 |
| `tests/test_day3.py` | 17 | ✅ PASS=17 FAIL=0 |
| `tests/test_day4.py` | 34 | ✅ PASS=34 FAIL=0 |
| `tests/test_day4_api.py`（真实服务器） | 26 | ✅ PASS=26 FAIL=0 |
| `tests/test_day5_api.py` | 20 | ✅ PASS=20 FAIL=0 |
| `tests/test_day5_pipeline.py` | 28 | ✅ PASS=28 FAIL=0 |
| `tests/test_day6_estimate_api.py` | 24 | ✅ PASS=24 FAIL=0 |
| **合计** | **254** | **✅ 254/254 通过** |

运行方式（Anaconda 环境 shiguang）：
```bash
cd /d D:\desk\ShingGuang
C:\Users\HUAWEI\mini\envs\shiguang\python.exe backend/tests/test_day7_want_api.py
# test_day4_api.py 需先启动服务器（backend 目录）：
cd backend && C:\Users\HUAWEI\mini\envs\shiguang\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

---

## 6. 协同注意点（给后续成员）

1. **DB 表**：`Want` 表由 `Base.metadata.create_all` 自动建表，无需迁移脚本；`models.py` 中 `Want` 类已导入（main.py 的 `import models` 保证建表）。
2. **字段约定**：Want 状态枚举为 `pending/accepted/rejected/cancelled`；Goods 状态沿用 `available/reserved/exchanged/removed`（Day4 定义）。
3. **测试 DB 隔离**：TestClient 跑在项目根 cwd 使用根目录 `shiguang.db`（空库），需自建 school/user；依赖种子数据（user_id=1）的测试需打真实服务器。
4. **服务器**：Day7 联调时本机 8000 端口已由新版 uvicorn（version 0.6.0）监听；若重启请以 backend 为工作目录启动。
5. **免费赠送**：发布/更新商品时若 `trade_type=free`，估价恒为 0~0（§4.2 适配），勿绕过 goods.py `_compute_estimate` 直接调引擎。
