# 交接文档_成员B_Day13

> 任务来源：项目计划书「十五、五人团队逐日开发任务表」Day 13 行，成员B 当日任务：**准备 AI 识别与估价的演示案例**（20 商品 / 5 用户 / 3 交换 / 聊天记录；衔接 Day3 已完成的学校与用户数据）。
> 交付目录：`C:\Users\LENOVO\Desktop\拾光Agent\成员B_Day12_15_交付\Day13_交付\`

---

## 一、当日产出

| 文件 | 说明 |
|---|---|
| `demo_data.py` | 演示数据生成脚本：一键重建 SQLite 演示库（7 校 / 5 用户 / 20 商品 / 3 组交换 / 聊天记录），CSV 缺失自动回退内置常量 |
| `demo_script.py` | 演示脚本：串联 识别→估价→匹配→解释→协议→提示 全链路，打印完整演示流程 |
| `test_day13.py` | 自测脚本，**30/30 PASS** |
| `shiguang_demo_full.db` | 生成的演示数据库（运行 `demo_data.py` 或自测后生成） |

## 二、使用方式

```python
import sys
sys.path.insert(0, r"C:\Users\LENOVO\Desktop\拾光Agent\成员B_Day12_15_交付\Day13_交付")
from demo_data import build_demo_db
counts = build_demo_db()   # 默认生成同目录 shiguang_demo_full.db，返回数量统计
# counts: {schools, users, goods, wishes, exchanges, chats, db_path}
```

命令行一键演示：`python demo_script.py`（自动注入 Day5/7/8/9/10/12 交付目录跑全链路）。

## 三、数据与验收口径

- 数据库表：`school`(7) / `user`(5) / `goods`(20，归属 5 用户) / `user_wish`(每位用户意愿类别) / `exchange`(3 组，state=negotiating) / `chat`(>=9 条协商聊天记录)。
- 3 组交换均通过 `match_score` 计算 **>= 0.5**（可匹配），用于演示"AI 推荐交换"。
- 衔接 Day3：优先读取 `成员B_Day3_交付\demo_schools.csv` / `demo_users.csv` 与 `shiguang_demo.db` 的学校/用户数据；缺失时回退内置 7 校 5 用户常量。

## 四、与前后模块衔接

- **上游**：Day3 演示数据（学校/用户）、Day5 识别、Day7 估价、Day8 状态机、Day9 匹配、Day10 解释/协议、Day12 提示模块。
- **下游**：成员A 用 `shiguang_demo_full.db` 联调后端接口；成员C/D 用演示数据走发布/详情/交换页面；成员E 用它构造验收用例。

## 五、自测结果

`python test_day13.py` → **PASS 30 / FAIL 0**（数据量验收 7/5/20/3/聊天、表结构、3 组交换匹配度 >=0.5、用户商品归属、CSV 回退分支）。

## 六、遗留事项

- 演示 DB 为静态种子数据，实际发布/交换流程仍走成员A 的 FastAPI 接口；如需"重置演示数据"直接重新运行 `demo_data.py`（幂等重建）。
