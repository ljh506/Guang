# 交接文档_成员B_Day11.md

- 成员：成员B（AI识别/估价/匹配）
- 交付日：Day 11
- 计划书来源：《拾光Agent_15天项目计划书》「十五、五人团队逐日开发任务表」Day 11 行
- 当日任务：**检查 AI、估价、匹配三个核心算法**（当天目标：全链路联调日，选校→发布→AI→估价→漂流→想要→聊天→交换→协议完整跑通）
- 交付目录：`C:\Users\LENOVO\Desktop\拾光Agent\成员B_Day10_11_交付\`

## 1. 当日产出

| 文件 | 说明 |
|---|---|
| `algorithm_check.py` | 核心算法一致性检查模块（Day11 核心交付） |
| `test_day11.py` | Day11 自测脚本，27/27 PASS |

## 2. 检查范围与结果

`run_all_checks()` 返回结构化报告：`{"checks": [...], "passed": n, "failed": n, "summary": str}`。每项检查含 `name / passed / detail`。

### 2.1 估价算法（Day6 price_engine / Day7 price_engine_day7）

| 检查项 | 结论 | 说明 |
|---|---|---|
| 折扣表与计划书 §四 一致 | PASS | 教材/电子产品/生活用品/衣物 四类四品相折扣区间与计划书完全一致 |
| 计划书示例回归 | PASS | 68 元/良好/教材 → 27~41 元，reason_text 含折扣区间与计算过程 |
| 边界复核 | PASS | NaN→INVALID_FORMAT（不再崩溃）、inf→OUT_OF_RANGE、负数→INVALID_FORMAT、0 元非免费→INVALID_FORMAT、布尔原价→INVALID_FORMAT、超 10 万→OUT_OF_RANGE、极小价保底 1 元、免费赠送（原价缺失）→0 元 |
| 电子产品年限微调/降档 | PASS | 6 个月→0.70~0.80 档、36 个月→降档良好档 0.50~0.70、负数年限忽略走原始档 |

### 2.2 匹配算法（Day9 match_engine）

| 检查项 | 结论 | 说明 |
|---|---|---|
| 权重 50/30/20 与阈值 0.75/0.50 | PASS | WEIGHT_CATEGORY_WISH=0.5、WEIGHT_PRICE=0.3、WEIGHT_SCHOOL=0.2（合计 1.0）；THRESHOLD_HIGH=0.75、THRESHOLD_NORMAL=0.50 |
| 计划书示例回归 | PASS | 30/32 元同校双向意愿 → 综合匹配度 >0.75，级别 high |
| 边界复核 | PASS | 缺失意愿/标价返回 None（安全语义不抛异常）、双方免费赠送（0 元）保持高匹配、跨校同校维度=0、单向意愿类别得分 < 双向（1.0）、完全相同物品得分 1.0 |

### 2.3 AI 识别算法（Day5 recognition_pipeline / Day4 统一类别体系）

| 检查项 | 结论 | 说明 |
|---|---|---|
| 识别输出结构与类别表一致性 | PASS | `build_available_categories()` 返回类别表包含 Day4 统一 10 类（含计划书核心四类：教材/电子产品/生活用品/衣物） |

## 3. 使用方式

```python
import sys
sys.path.insert(0, r"C:\Users\LENOVO\Desktop\拾光Agent\成员B_Day10_11_交付")
from algorithm_check import run_all_checks

report = run_all_checks()
print(report["summary"])      # 算法检查完成：通过 8 / 失败 0 / 共 8 项
for c in report["checks"]:
    print("[%s] %s -> %s" % ("PASS" if c["passed"] else "FAIL", c["name"], c["detail"]))
```

命令行自测：

```bash
python algorithm_check.py
python test_day11.py   # PASS: 27 / FAIL: 0 / 总用例: 27，退出码 0
```

## 4. 关键决策与约定

- **跨目录注入**：`algorithm_check.py` 自动注入 Day4/Day5/Day6/Day7/Day8/Day9 交付目录到 `sys.path`（复用前日模块而非复制，避免字段契约漂移）。
- **检查即报告，不改代码**：本模块只读校验已有核心算法，不修改任何模块逻辑；发现不一致仅上报，修复由各日负责人处理。
- **可扩展**：新增检查项只需向 `CHECK_FUNCS` 列表追加函数（返回 `(name, passed, detail)`），`run_all_checks` 自动纳入汇总。

## 5. 与其他成员衔接

- **成员A（后端/状态机）**：全链路联调中「交换→协议」环节依赖 Day10 协议校验与 Day8 状态机，本日检查已确认匹配/估价算法与计划书一致，联调阻塞点应在接口层而非算法层。
- **成员C/D（前端页面）**：Day10 `match_explanation.py` 产出的解释文本/协议文本可直接渲染；本日检查确认其依赖的 Day9 匹配分级在 0.75/0.50 阈值下行为稳定。

## 6. 遗留事项

- AI 识别算法仅检查了**类别表一致性**与**输出结构**；模型识别准确率/召回率评测不属成员B本日范围（需真实图片样本集）。
- 估价折扣表扩展六类（文具/数码配件/运动器材/家具/其他书籍/其他）为自拟合理值，计划书仅固化四类；如需调整请以产品评审结果为准。
- 全链路联调若发现算法层以外的接口问题，建议优先排查各日模块的字段命名（如 `wish_category_id` vs `category_id`）与状态流转参数。
