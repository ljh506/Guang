# 交接文档_成员A_Day5

> 拾光Agent 项目 · 第 5 天 · 成员A 交付说明
> 日期：2026-10-11
> 交付内容：**AI 识别 API 与错误处理**（后端集成 + 测试 + 文档）

## 1. 本日任务与验收

计划书第 5 天分配成员A任务：**增加 AI 识别 API 和错误处理**。

验收标准（计划书）：
- 至少 **教材 / 电子 / 生活 / 衣物** 四类可识别（识别链路测试已覆盖）；
- 识别失败时用户**可手动选择类别**（fallback 兜底 + 10 类下拉列表）。

## 2. 前置：成员B_Day5_交付 集成说明

成员B已交付（`D:\desk\成员B_Day5_交付`）：

| 文件 | 说明 | 本日处理 |
|---|---|---|
| `recognition_pipeline.py` | 识别链路主模块（backend 注入 + 阈值分流 + 兜底） | 集成至 `backend/app/services/recognition_pipeline.py`（仅适配项目内相对导入，业务逻辑保持成员B原样） |
| `test_day5.py` | 链路 25 项自测 | 拆分为项目内两份测试（见 §4） |
| `交接文档_成员B_Day5.md` | 接口草案与部署建议 | 按草案实现 `POST /api/v1/recognize` |

## 3. 本次改动文件清单

### 3.1 新增文件

| 文件 | 说明 |
|---|---|
| `backend/app/services/recognition_pipeline.py` | 成员B识别链路集成版：`RecognitionPipeline.recommend(image_path/image_bytes)` 统一返回结构（category_id / confidence / need_confirm / status / fallback / available_categories 等）；含 MockBackend 测试后端 |
| `backend/app/routers/recognize.py` | AI 识别 API 路由：`POST /api/v1/recognize`（multipart 上传 image），系统级错误处理（400/413 + 统一 detail.code） |
| `backend/tests/test_day5_pipeline.py` | 链路单元测试 28 项（对齐成员B test_day5.py） |
| `backend/tests/test_day5_api.py` | API 验收测试 20 项（TestClient + Mock 注入） |
| `docs/交接文档_成员A_Day5.md` | 本说明 |

### 3.2 修改文件

| 文件 | 改动 |
|---|---|
| `backend/app/main.py` | 注册 `recognize` 路由，API 版本升 0.3.0 → 0.4.0 |
| `backend/requirements.txt` | 新增 `python-multipart==0.0.20`（文件上传解析）、`httpx==0.28.1`（API 测试依赖） |

## 4. 接口说明

```
POST /api/v1/recognize
Content-Type: multipart/form-data
字段：image（图片文件，JPG/PNG/WebP/GIF/BMP，≤5MB）
```

**成功响应（HTTP 200，业务统一 JSON）：**

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "category_id": "textbook",
    "category_name": "教材",
    "confidence": 0.95,
    "need_confirm": false,
    "matched_by": "keyword",
    "fallback": false,
    "available_categories": [{"category_id": "...", "category_name": "..."}, "...共10类"],
    "status": "auto_fill",
    "fallback_reason": null,
    "raw_label": "textbook"
  }
}
```

**状态流（status 字段，与 Day2 阈值一致）：**

| status | 条件 | 前端行为 |
|---|---|---|
| `auto_fill` | 置信度 ≥ 0.80 且类别非兜底 | 自动填充，无需确认 |
| `manual_confirm` | 0.60 ≤ 置信度 < 0.80 | 自动填充但需用户确认 |
| `manual_select` | 置信度 < 0.60 或未知标签高置信 | 展示 10 类下拉由用户选择 |
| `fallback` | AI 服务异常/超时/数据非法 | 手动选择类别（发布不阻断） |

**系统级错误（前端展示 message 后走手动选择）：**

| HTTP | code | 场景 |
|---|---|---|
| 400 | 40001 | 缺少图片 / 格式不支持 |
| 400 | 40003 | 读取上传图片失败 |
| 400 | 40004 | 图片内容为空 |
| 413 | 41301 | 图片超过 5MB |

## 5. 验证结果

| 测试 | 结果 |
|---|---|
| `test_day5_pipeline.py`（四类识别 + 阈值分流 + 兜底 + 兼容性） | 28/28 PASS |
| `test_day5_api.py`（API 集成 + 错误处理） | 20/20 PASS |
| 真实 uvicorn 启动 + curl 上传 | 200 fallback 结构 / 413 超大拦截 / 400 无文件 均符合预期 |
| 回归 `test_day2.py` / `test_day3.py` / `test_day4.py` / `test_day4_api.py` | 32/32、17/17、34/34、26/26 全部通过 |

**验收结论：** 教材/电子/生活/衣物四类均可识别（auto_fill）；识别失败返回 fallback + 10 类列表，用户可手动选择，满足验收标准。

## 6. 环境与运行

- 后端环境：Anaconda 环境 `shiguang`（Python 3.11.17，fastapi/uvicorn/sqlalchemy/pydantic）
- 已安装依赖：`python-multipart==0.0.20`、`httpx==0.28.1`
- 启动：`cd backend && C:\Users\HUAWEI\mini\envs\shiguang\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000`
- 测试：`C:\Users\HUAWEI\mini\envs\shiguang\python.exe backend\tests\test_day5_api.py`（同理 test_day5_pipeline.py）

## 7. 后续（成员B/成员C 注意）

- 接入真实视觉服务时，替换 `backend/app/routers/recognize.py` 中的 `_default_vision_backend`（或直接注入 `RecognitionPipeline(backend=...)`）即可，接口结构不变；
- 前端上传接口见成员B交接文档 §3，与 `POST /api/v1/recognize` 完全对齐；
- 微信小程序上传可能携带 `application/octet-stream` MIME，本接口已兼容（按扩展名白名单兜底）。
