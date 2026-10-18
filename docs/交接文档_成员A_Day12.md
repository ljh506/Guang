# 交接文档_成员A_Day12

> 项目：拾光Agent · 大学校园智能闲置循环平台
> 成员：成员A（后端）
> 日期：2026-10-18（Day 12）
> 仓库：https://github.com/ljh506/Guang.git

## 一、任务来源依据

- 来源：`拾光Agent_15天项目计划书.docx` 第十五节「五人团队逐日开发任务表」Day 12 行。
- Day12 团队目标：**UI 与交互优化**（AI 识别失败和估价异常的用户提示）。
- 成员A 当日任务：**集成成员B 提示模块到后端识别/估价接口，输出前端可直接渲染的 tips 提示字段**。
- 当天验收：识别失败/估价异常时，页面给出清晰、可执行的提示。

## 二、交付清单

| 文件 | 说明 |
|---|---|
| `backend/app/services/user_prompt.py` | 成员B Day12 交付集成（原样复制，仅标准库依赖） |
| `backend/app/routers/recognize.py` | 识别接口返回 `data.tips`（识别提示） |
| `backend/app/routers/estimate.py` | 估价接口返回 `tips`（估价提示，成功/失败均带） |
| `backend/app/main.py` | 版本 0.9.0 → 1.0.0 |
| `backend/tests/test_day12_prompt_api.py` | 成员A 提示接口验收测试（29 用例） |
| `backend/tests/test_day12_user_prompt.py` | 成员B Day12 自测适配版（44 用例） |
| `docs/交接文档_成员A_Day12.md` | 本文档 |
| `README.md` | 追加 Day12 进度 |

## 三、完成内容

### 3.1 提示模块集成（services/user_prompt.py）

- 原样集成成员B `user_prompt.py`：`build_recognition_tip` / `build_price_tip` / `build_publish_tips`。
- 输出统一结构 `{level: good|warn|error, title, message, action, ...}`，前端无需感知内部状态机即可渲染。

### 3.2 接口返回改造

| 接口 | 改造 | tips 语义 |
|---|---|---|
| `POST /api/v1/recognize` | `data.tips` 字段 | auto_fill=good / manual_confirm、manual_select=warn / fallback=error（按原因给可执行动作） |
| `POST /api/v1/estimate` | 顶层 `tips` 字段 | 成功且标价在区间内=good；标价低于/高于区间=warn；失败=error 且携带 `error_code`（与 `error.error_code` 一致） |

- 兼容性：原返回字段（data 结构 / error 结构）完全不变，仅新增 tips，不破坏前端既有联调。

### 3.3 验收与回归

- `test_day12_prompt_api.py`（成员A 验收，29 用例）：PASS 29 / FAIL 0。
  - 核心链路：识别无 backend → fallback → `data.tips.level=error` + action 可执行；估价原价缺失 → `error_code=PRICE_ORIGINAL_REQUIRED` + tips 携带同 error_code + 修正动作。
- `test_day12_user_prompt.py`（成员B 自测适配版，44 用例）：PASS 44 / FAIL 0。
- 识别失败/估价异常均不阻断发布，符合「识别失败也能继续发布」的验收标准。

## 四、接口示例

```
POST /api/v1/estimate
{"category": "textbook", "condition": "good", "original_price": null}
→ {"success": false, "error": {"error_code": "PRICE_ORIGINAL_REQUIRED", "message": "请填写参考原价"},
   "tips": {"level": "error", "title": "请填写参考原价",
            "message": "估价需要物品的参考原价（如购买价格），请填写后重新估价。",
            "action": "填写参考原价", "error_code": "PRICE_ORIGINAL_REQUIRED"}}
```

*（内容由AI生成，仅供参考）*
