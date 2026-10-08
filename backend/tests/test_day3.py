# -*- coding: utf-8 -*-
"""Day3 后端 API 验收测试：选校主流程 + School/User 增删查改。"""
import json
import sys
import urllib.error
import urllib.request

BASE = "http://127.0.0.1:8000/api/v1"
PASS, FAIL = 0, 0


def _req(method, path, body=None, expect=200):
    url = BASE + path
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, method=method,
                                 headers={"Content-Type": "application/json",
                                          "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req) as r:
            return r.status, json.loads(r.read().decode("utf-8") or "null")
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode("utf-8") or "null")


def check(name, cond, detail=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print("[PASS]", name)
    else:
        FAIL += 1
        print("[FAIL]", name, "->", detail)


# 1. 学校列表（应包含 B 的 7 所演示学校）
code, schools = _req("GET", "/schools")
check("GET /schools 返回 7 所", code == 200 and len(schools) == 7, (code, len(schools)))
check("首条学校=清华大学", schools and schools[0]["name"] == "清华大学", schools[0] if schools else None)

# 2. 用户列表
code, users = _req("GET", "/users")
check("GET /users 返回 5 个", code == 200 and len(users) == 5, (code, len(users)))

# 3. 选校主流程：创建用户→选择学校→保存
code, u = _req("POST", "/users",
               {"nickname": "Day3测试用户", "school_id": 1},
               expect=201)
check("创建用户(清华大学)成功", code == 201 and u["school_id"] == 1, u)
uid = u["id"]

# 4. 切换学校（选校主流程）
code, sel = _req("POST", f"/users/{uid}/select-school", {"school_id": 3})
check("选校切换至浙江大学", code == 200 and sel["school"]["id"] == 3 and sel["user"]["school_id"] == 3, sel)

# 5. 按 school 过滤用户
code, filtered = _req("GET", "/users?school_id=3")
check("school_id=3 过滤出橙子不吃皮",
      code == 200 and any(u_["id"] == 3 for u_ in filtered), filtered)

# 6. 选校不存在的学校应 400
code, _ = _req("POST", f"/users/{uid}/select-school", {"school_id": 9999})
check("选校不存在学校 → 400", code == 400, code)

# 7. 更新用户昵称
code, upd = _req("PATCH", f"/users/{uid}", {"nickname": "Day3改昵"})
check("PATCH 用户昵称", code == 200 and upd["nickname"] == "Day3改昵", upd)

# 8. 创建/查询/更新/删除学校（CRUD 完整性）
code, s = _req("POST", "/schools",
               {"name": "拾光测试大学", "latitude": 0.0, "longitude": 0.0},
               expect=201)
check("创建学校 201", code == 201 and s["name"] == "拾光测试大学", s)
sid = s["id"]

code, got = _req("GET", f"/schools/{sid}")
check("查询学校", code == 200 and got["id"] == sid, got)

code, p = _req("PATCH", f"/schools/{sid}", {"name": "拾光测试大学-改"})
check("更新学校名", code == 200 and p["name"].endswith("改"), p)

# 重复名应 409
code, _ = _req("POST", "/schools",
               {"name": "拾光测试大学-改", "latitude": 1.0, "longitude": 1.0},
               expect=409)
check("重复学校名 → 409", code == 409, code)

code, _ = _req("DELETE", f"/schools/{sid}")
check("删除学校 204", code == 204, code)

# 9. 错误路径
code, _ = _req("GET", "/users/9999")
check("查询不存在用户 → 404", code == 404, code)
code, _ = _req("GET", "/schools/9999")
check("查询不存在学校 → 404", code == 404, code)
code, _ = _req("POST", "/users", {"nickname": "x"}, expect=400)  # 缺 school_id
check("缺 school_id → 422", code in (400, 422), code)

# 10. 清理测试用户
code, _ = _req("DELETE", f"/users/{uid}")
check("删除用户 204", code == 204, code)

print()
print(f"===== 结果汇总：PASS={PASS} FAIL={FAIL} =====")
sys.exit(0 if FAIL == 0 else 1)
