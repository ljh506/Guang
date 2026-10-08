# 成员A · Day 3 交付说明

- 日期：2026-10-08
- 角色：后端负责人（成员A）
- 依据：拾光Agent 15天计划书 §十五 Day3 —— A：完成用户/学校增删查、选择学校 API

## 验收目标

> 选择学校 → 进入首页 → 用户信息能保存

已通过自动化测试（`backend/tests/test_day3.py`）：**PASS=17 FAIL=0**

## 今日完成

1. **Pydantic Schemas** — `backend/app/schemas.py`
   - SchoolBase / SchoolCreate / SchoolUpdate / SchoolOut
   - UserBase / UserCreate / UserUpdate / UserOut
   - SelectSchoolRequest / SelectSchoolResponse（Day3 选校主流程）
2. **学校 CRUD 路由** — `backend/app/routers/schools.py`
   - `GET /api/v1/schools` 列表
   - `GET /api/v1/schools/{id}` 详情
   - `POST /api/v1/schools` 新增（含唯一名校验 409）
   - `PATCH /api/v1/schools/{id}` 部分更新
   - `DELETE /api/v1/schools/{id}` 删除
3. **用户 CRUD + 选校路由** — `backend/app/routers/users.py`
   - `GET /api/v1/users[?school_id=N]` 列表（可按学校过滤）
   - `GET /api/v1/users/{id}` 详情
   - `POST /api/v1/users` 创建（必须指定 school_id，Day3「保存用户信息」）
   - `PATCH /api/v1/users/{id}` 更新昵称/头像/学校
   - `DELETE /api/v1/users/{id}` 删除
   - `POST /api/v1/users/{id}/select-school` **Day3 选校主流程**，返回用户与学校信息
4. **集成成员B Day3 演示数据**
   - `backend/data/schools.csv`（7 所高校，真实坐标）
   - `backend/data/users.csv`（5 个大学生风格用户）
   - `backend/scripts/seed_data.py`（幂等：先清空后插入，可重复运行）
   - 实际导入：School=7、User=5
5. **重启后端并验收通过**
   - 端口：`127.0.0.1:8000`（昨日进程已停）
   - `GET /api/v1/health` → `{"status":"ok","database":"ok"}`
   - Day3 验收测试 17/17 通过

## 对团队成员的对接说明

- **成员C（前端A）**：
  - 学校下拉：`GET /api/v1/schools`（按 id 升序，7 所）
  - 选校主流程：用户选择学校 → `POST /api/v1/users` 或 `POST /api/v1/users/{id}/select-school`
- **成员D（前端B）**：
  - 我的页/学校切换：调 `/users/{id}/select-school`
  - 列表过滤：支持 `?school_id=N` 同校浏览
- **成员B（AI/算法）**：
  - 演示数据已写入 `backend/shiguang.db`（表名 `schools` / `users`，与计划书 §七一致）
  - 后续 Day4~13 数据扩展沿用 `backend/scripts/seed_data.py` 的写法
- **测试同学**：直接运行 `python backend/tests/test_day3.py` 复验 17 项接口

## API 速查

| 方法 | 路径 | 用途 |
|---|---|---|
| GET | `/api/v1/schools` | 学校列表 |
| GET | `/api/v1/schools/{id}` | 学校详情 |
| POST | `/api/v1/schools` | 新增学校 |
| PATCH | `/api/v1/schools/{id}` | 更新学校 |
| DELETE | `/api/v1/schools/{id}` | 删除学校 |
| GET | `/api/v1/users?school_id=N` | 用户列表（可按学校过滤） |
| GET | `/api/v1/users/{id}` | 用户详情 |
| POST | `/api/v1/users` | 创建用户（需带 school_id） |
| PATCH | `/api/v1/users/{id}` | 更新用户 |
| DELETE | `/api/v1/users/{id}` | 删除用户 |
| POST | `/api/v1/users/{id}/select-school` | **选校主流程** |

## 后续

- Day4（成员A）：Goods 模型 + 发布/列表/详情 API
- Day3 禁止改动：后端 Day11 前允许扩展，但 Day13 起禁止新增核心功能
