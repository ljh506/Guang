# 交接文档_成员B_Day12

> 任务来源：项目计划书「十五、五人团队逐日开发任务表」Day 12 行，成员B 当日任务：**优化 AI 识别失败和估价异常的用户提示**（当天目标：UI 与交互优化）。
> 交付目录：`C:\Users\LENOVO\Desktop\拾光Agent\成员B_Day12_15_交付\Day12_交付\`

---

## 一、当日产出

| 文件 | 说明 |
|---|---|
| `user_prompt.py` | 用户提示优化模块：识别失败/低置信度提示 + 估价异常提示 + 组合入口 |
| `test_day12.py` | 自测脚本，**44/44 PASS** |

## 二、使用方式

```python
import sys
sys.path.insert(0, r"C:\Users\LENOVO\Desktop\拾光Agent\成员B_Day12_15_交付\Day12_交付")
from user_prompt import build_recognition_tip, build_price_tip, build_publish_tips

# 识别结果 -> 提示
tip = build_recognition_tip(recognition_result)   # dict{level,title,message,action,...}
# 估价结果 -> 提示
tip = build_price_tip(price_result)               # dict{level,title,message,action,error_code}
# 发布页组合入口
tips = build_publish_tips(recognition_result, price_result)
```

前端（成员C 详情页 / 成员D 发布页）直接渲染 `title / message / action` 字段即可，无需感知内部状态机。

## 三、与前后模块衔接

- **上游**：Day5 `recognition_pipeline.recommend()` 返回结构（`status: auto_fill / manual_confirm / manual_select / fallback`，含 `fallback_reason / raw_label / confidence / available_categories`）；Day7 `price_engine_day7.estimate_price()` 返回结构（成功含 `estimated_min/max/reason_text/price_tip`；失败含 `error:{error_code,message}`）。
- **下游**：成员C / 成员D 前端渲染提示；成员E 可据此编写 UI 交互测试用例。
- **长期记忆复用**：以 `sys.path.insert` 注入前日目录读取上游模块，未复制模块文件，避免契约漂移。

## 四、接口约定

- `build_recognition_tip(result, scene="publish")`：`result=None` 或非 dict 按失败处理；`scene` 支持 `publish` / `detail`。
- 识别 status 映射：`auto_fill`→静默成功；`manual_confirm`→请确认类别；`manual_select`→置信度低请手动选择；`fallback`→按 `fallback_reason` 给可执行动作（服务不可用/超时、无标签、置信度非法/越界、缺图、图无效）。
- `build_price_tip(result, scene="publish")`：成功+`price_tip`→黄色参考提示；成功无 tip→绿色区间提示；失败→按错误码给修正动作。
- 仅标准库，模块内自带冒烟示例。

## 五、自测结果

`python test_day12.py` → **PASS 44 / FAIL 0**（识别 4 状态 + 6 类 fallback 原因、估价 6 错误码 + 成功分支、组合入口、scene 差异全覆盖）。

## 六、遗留事项

- 无。提示文案如需多语言或品牌化，前端可直接在渲染层覆盖 `message` 字段。
