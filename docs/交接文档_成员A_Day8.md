# 交接文档_成员A_Day8

> 项目：拾光Agent · 大学校园智能闲置循环平台
> 成员：成员A（后端）
> 日期：2026-10-13（Day 8）
> 仓库：https://github.com/ljh506/Guang.git

## 一、任务来源依据

- 来源：`拾光Agent_15天项目计划书.docx` 第十五节「五人团队逐日开发任务表」Day 8 行。
- Day8 团队目标：**轻量聊天**（请求→聊天→快捷消息）。
- 成员A 当日任务：**完成 Message 模型和消息接口**。
- 当天验收：想要请求 → 消息列表 → 聊天 → 发送/接收演示消息。

## 二、交付清单

| 文件 | 说明 |
|---|---|
| `backend/app/models.py` | 新增 Conversation / Message 模型 |
| `backend/app/schemas.py` | 新增聊天相关 Pydantic schemas |
| `backend/app/routers/chat.py` | 轻量聊天 API（新建） |
| `backend/app/services/chat_rules.py` | 集成成员B Day8 交付（快捷消息 + 交易状态机） |
| `backend/tests/test_day8_message_api.py` | 消息接口验收测试（新建，27 用例） |
| `backend/tests/test_day8_chat_rules.py` | 成员B Day8 自测适配版（35 用例） |
| `backend/app/main.py` | 注册 chat 路由，版本 0.6.0 → 0.7.0 |
| `docs/交接文档_成员A_Day8.md` | 本文档 |
| `README.md` | 追加 Day8 进度 |

## 三、完成内容

### 3.1 Message 模型与会话模型（models.py）

- `Message`：对齐计划书 §七（id、sender_id、receiver_id、content、created_at）——以会话归属 + 对端推导实现，存 sender_id / content / is_read / created_at，避免 15 天内开发复杂实时 IM。
- `Conversation`：会话/交易载体，字段 goods_id / want_id（关联 Day7 想要请求）/ buyer_id / seller_id / trade_state（成员B Day8 状态机）/ created_at / updated_at。一个「想要→聊天→匹配→交换→确认」的完整交易链路承载在一个会话上，供 Day9 匹配、Day10 协议共用。

### 3.2 消息接口（routers/chat.py，7 个端点）

| 接口 | 说明 |
|---|---|
| `GET /api/v1/quick-messages?scene=&sender=` | 快捷消息模板（集成成员B chat_rules，含场景元信息） |
| `POST /api/v1/conversations` | 创建会话（买卖双方 + 商品，可关联 want_id；已有进行中会话自动复用） |
| `GET /api/v1/conversations?user_id=` | 消息列表：最后一条消息 / 未读数 / 交易状态（含中文名）/ 对方昵称 |
| `GET /api/v1/conversations/{id}/messages` | 聊天记录（分页，页内按时间正序） |
| `POST /api/v1/conversations/{id}/messages` | 发送消息（仅会话参与者；首条消息自动 `requested → chatting`） |
| `POST /api/v1/conversations/{id}/read` | 标记已读（对方消息清零） |
| `PATCH /api/v1/conversations/{id}/state` | 交易状态流转（成员B `validate_transition` 白名单校验，非法流转 400） |

### 3.3 成员B 交付集成

- 成员B Day8 交付 `chat_rules.py`（17 条快捷消息 + 6 态交易状态机）整体入库至 `backend/app/services/chat_rules.py`；
- `GET /quick-messages` 直接返回模板供前端 C（消息列表）/ D（聊天页快捷按钮）渲染；
- 交易状态字段落在 `conversations.trade_state`，发送首条消息自动 `requested → chatting`，其余流转统一走 `PATCH /conversations/{id}/state` 状态机校验；
- 成员B 自测 `test_day8.py` 适配为 `tests/test_day8_chat_rules.py`（import 路径适配 app.services）。

## 四、测试结果

- 成员B chat_rules 适配版：**PASS=35 FAIL=0**
- 消息接口验收：**PASS=27 FAIL=0**（★验收链路：卖家发布 → 买家想要 → 卖家接受 → 创建会话 → 买家发送 → 卖家消息列表见未读 → 聊天记录读取 → 卖家回复 → 双方收发 2 条；非法发送/空内容/非法状态流转/终态保护全覆盖）
- 全量回归（Day2~Day8 共 11 套测试）：**无 FAIL**（Day2 32 / Day3 34 / Day4 20 / Day4_api 26 / Day5_api 28 / Day5_pipeline / Day6 24 / Day7_engine 45 / Day7_want 28 / Day8_rules 35 / Day8_message 27）
- uvicorn 已重启验证：`GET /` 返回 version 0.7.0

## 五、与其他成员的衔接

- **前端成员C（消息列表页）**：`GET /api/v1/conversations?user_id=X`，字段 last_message / unread_count / trade_state_name / goods_name 直接渲染。
- **前端成员D（聊天页/快捷回复）**：`GET /api/v1/quick-messages?scene=&sender=` 渲染快捷按钮；占位符模板（price_offer 的 {amount}、meet_time 的 {time}）由前端收集参数渲染后作为 content 调用发送消息接口。
- **测试成员E**：验收链路即本测试「想要请求→消息列表→聊天→发送/接收演示消息」；`PATCH /conversations/{id}/state` 可用状态机校验。
- **Day9（成员B 匹配）**：匹配命中后调用 `PATCH /conversations/{id}/state` 传 `matched`（状态机已放行 chatting→matched）。
- **Day10（协议）**：`negotiating → confirmed` 已放行，无需改状态定义。

## 六、运行方式

```powershell
cd D:\desk\ShingGuang\backend
C:\Users\HUAWEI\mini\envs\shiguang\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
# 测试
C:\Users\HUAWEI\mini\envs\shiguang\python.exe tests\test_day8_message_api.py
```
