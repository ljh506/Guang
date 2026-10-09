# 成员A · Day 4 交付说明

- 日期：2026-10-09
- 角色：后端负责人（成员A）
- 依据：拾光Agent 15天计划书 §十五 Day4 —— A：完成Goods模型、发布/列表/详情API

## 验收目标

> 能发布一件商品，并在漂流墙看到

已通过自动化测试（`backend/tests/test_day4_api.py`）：**PASS=26 FAIL=0**

## 今日完成

1. **Goods 模型** — `backend/app/models.py`
   - 对齐计划书 §七：id、user_id、school_id、name、category、description、image、original_price、estimated_min、estimated_max、condition、status、created_at
   - 增补 Day2/Day4 约定字段：`asking_price`（用户手填标价，Day9 匹配用）、`reason_text`（估价依据）、`trade_type`（sell 出售 / free 免费赠送 / exchange 以物换物，对齐计划书 §三.8）
2. **商品 API** — `backend/app/routers/goods.py`
   - `GET /api/v1/goods` 漂流墙列表（school_id / category / status / trade_type / user_id / keyword 过滤 + 分页）
   - `GET /api/v1/goods/{id}` 详情
   - `POST /api/v1/goods` **发布**（Day4 核心）
   - `PATCH /api/v1/goods/{id}` 更新（改类别/品相/原价/交易方式自动重算估价；status 流转 available/reserved/exchanged/removed）
   - `DELETE /api/v1/goods/{id}` 删除
   - `GET /api/v1/goods/categories` Day4 十类清单（前端发布页选择器）
3. **发布链路串联成员B全部模块**
   - Day4 `estimate_params.validate()` 参数校验（多错误累积，422 一次返回全部问题）
   - Day4 `category_normalizer.to_engine_category()` 类别映射
   - Day2 `price_engine.estimate_price()` 生成 estimated_min/max + reason_text 落库
   - Day2 `validate_asking_price()` 生成 price_tip（仅提示不阻断）
4. **集成成员B Day4 模块**
   - `backend/app/services/category_normalizer.py`、`estimate_params.py`
   - `backend/tests/test_day4.py`（自测 PASS=34 FAIL=0）
5. **修复 price_engine 免费赠送边界 bug**
   - 现象：`is_free=True` 且原价>0 时估价走了折扣分支（4~18），与 reason_text"估价为 0 元"和交接文档"免费时估价恒为 0~0"矛盾
   - 修复：`if price == 0 or is_free:` 走 0~0 分支
   - 回归：Day2 自测 32/32 通过，未破坏既有用例
   - ⚠️ **请成员B知晓**：其原始交付目录的 `price_engine.py`（根目录副本）仍有此问题，Day5 请同步

## 发布接口示例

请求 `POST /api/v1/goods`：
```json
{
  "user_id": 1,
  "name": "高等数学（上册）第2版",
  "category": "textbook",
  "condition": "good",
  "original_price": 68,
  "asking_price": 30,
  "trade_type": "sell"
}
```

响应（201）：
```json
{
  "goods": {
    "id": 1, "school_id": 1, "category_name": "教材",
    "estimated_min": 27, "estimated_max": 41,
    "reason_text": "「教材」良好，参考原价 68 元，按教材类良好折扣 0.4~0.6 计算，建议估价 27~41 元。",
    "asking_price": 30, "status": "available", ...
  },
  "price_tip": null,
  "estimate": {"estimated_min": 27, "estimated_max": 41, "reason_text": "…"}
}
```

计划书示例验证：68 元教材 + 良好品相 → **27~41 元** ✅

## 对其他成员的对接说明

- **成员C（漂流墙）**：`GET /api/v1/goods?school_id=N`（本校商品卡片流，含 total/page/page_size 分页）；分类筛选加 `&category=`；详情页 `GET /api/v1/goods/{id}`
- **成员D（发布页）**：
  - 类别选择器：`GET /api/v1/goods/categories`（10 类，含中文名）
  - 提交发布：`POST /api/v1/goods`；`price_tip` 非空时黄色提示（不阻断）
  - 错误处理：422 响应 `detail.errors[]` 为数组，含 `error_code + message`，可一次性展示全部问题
- **测试同学**：`python backend/tests/test_day4_api.py` 复验 26 项；`python backend/tests/test_day4.py` 复验B模块 34 项

## 测试汇总

| 套件 | 结果 |
|---|---|
| Day2 回归（price_engine 修复后） | PASS=32 FAIL=0 |
| Day4 B 模块自测 | PASS=34 FAIL=0 |
| Day4 API 验收 | PASS=26 FAIL=0 |

## Day5 预告（成员A）

- AI 识别 API（`POST /api/v1/recognize`）：图片上传 → `ai_client`（Day5 起改用 `category_normalizer.normalize()` 标准化）→ 类别 + 置信度 + 阈值分流
- 发布页错误兜底：识别失败时 fallback 手动选类别
