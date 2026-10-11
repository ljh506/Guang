# 交接文档_成员A_Day6

> 拾光 Agent 15 天项目 · 第 6 天 · 成员A 交付说明
> 日期：2026-10-11 ｜ 成员A（后端）

## 一、Day6 成员A 任务（源自计划书）

1. 完成估价接口（商品估价 API），前端可按类别/品相/原价实时询价；
2. Goods 价格字段保存：发布商品时建议估价区间与依据文本落库，更新商品触发重估；
3. 集成成员B Day6 完整版价格引擎（统一 10 类体系、months_used 年限微调、price_tip、旧 ID 兼容）。

**验收标准**：68 元教材 + 良好品相 → 27~41 元。

## 二、本次改动文件

| 文件 | 改动说明 |
| --- | --- |
| `backend/app/services/price_engine.py` | 用成员B Day6 完整版引擎覆盖旧引擎（成员B 交付，105 用例自测通过） |
| `backend/app/routers/goods.py` | `_compute_estimate` 适配 Day6 引擎：去掉 `to_engine_category` 二次映射，`device_age_months` → `months_used`；发布/更新商品时建议区间 + 依据文本落库；若引擎返回错误则 422 |
| `backend/app/routers/estimate.py` | **新增** 估价接口 `POST /api/v1/estimate`（字段契约与成员B 约定一致） |
| `backend/app/main.py` | 注册 estimate 路由；版本号 0.4.0 → 0.5.0 |
| `backend/tests/test_day6_estimate_api.py` | **新增** Day6 API 测试（估价接口 + 发布落库 + 更新重估），24 例 |
| `backend/tests/test_day2.py` | 电子产品 3 个月年限断言 700~780 → 700~800（Day6 引擎规则升级，见下） |

## 三、新增接口：POST /api/v1/estimate

纯计算接口，不写库；发布落库走 POST /api/v1/goods。

**请求**
```json
{
  "category": "textbook",        // Day4 统一类别 ID（10 类）
  "condition": "good",           // new_like / good / fair
  "original_price": 68,          // 参考原价；字符串数字亦可
  "months_used": null,           // 电子产品使用年限（月），可选
  "is_free": false,              // 免费赠送
  "asking_price": 50             // 用户手填标价，可选，用于 price_tip
}
```

**成功**
```json
{
  "success": true,
  "data": {
    "estimated_min": 27,
    "estimated_max": 41,
    "reason_text": "原价 68 元 × 「教材」良好折扣 0.4~0.6 = 27~41 元。",
    "rule_ref": {"category": "textbook", "condition": "good", "low": 0.4, "high": 0.6},
    "price_tip": null
  }
}
```

**失败**（HTTP 200 业务包裹，前端按 success 分流）
```json
{
  "success": false,
  "error": {"error_code": "PRICE_ORIGINAL_REQUIRED", "message": "..."}
}
```
错误码沿用 Day2/Day4：`CATEGORY_INVALID` / `CONDITION_REQUIRED` / `CONDITION_INVALID` / `PRICE_ORIGINAL_REQUIRED` / `PRICE_INVALID_FORMAT` / `PRICE_OUT_OF_RANGE`。

## 四、验收示例（计划书）

- 68 元教材 + 良好 → 27~41 ✔（接口与商品发布落库均验证）
- 免费赠送 → 0~0
- 电子产品 + months_used：new_like/2000 元/9 个月 → 1300~1500（0.65~0.75）；>24 个月自动降档良好档并写入 reason_text
- asking_price 低于/高于建议区间 → price_tip 提示

## 五、测试结果

| 测试 | 结果 |
| --- | --- |
| 成员B `test_day6.py`（引擎自测） | PASS=105 FAIL=0 |
| `test_day6_estimate_api.py`（新增） | PASS=24 FAIL=0 |
| 回归 `test_day2.py` / `test_day3.py` / `test_day4.py` / `test_day4_api.py` / `test_day5_api.py` / `test_day5_pipeline.py` | 全部通过（32/17/34/26/20/28） |

运行方式（Anaconda shiguang 环境，项目根目录）：
```
C:\Users\HUAWEI\mini\envs\shiguang\python.exe backend/tests/test_day6_estimate_api.py
```

## 六、协同注意点

1. **Day2 断言更新**：Day6 引擎对电子产品年限微调规则升级——3 个月内使用不再线性压价（全新档保持 0.7~0.8），故 `test_day2.py` 的 700~780 更新为 700~800。引擎行为以成员B Day6 交付为准。
2. **TestClient 独立数据库**：TestClient 以项目根为 cwd 时使用根目录 `shiguang.db`（仅建表无种子），故 Day6 测试内置 school/user 创建，不依赖种子数据；Day4 API 测试需先启动服务器（cd backend && uvicorn）访问 backend/shiguang.db。
3. **免费赠送落库**：GoodsCreate 的 original_price 约束为 >0，前端免费发布可传 0.01（引擎 is_free 分支返回 0~0）或后续放开 schema 约束。
4. **错误码/包裹层**：POST /estimate 遵循成员B《交接文档_成员B_Day6.md §五》字段契约（success/data/error）；goods 发布链路仍走原有 422 detail={"errors":[...]} 风格，两者并存，前端按接口分别处理。
