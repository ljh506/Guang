# -*- coding: utf-8 -*-
"""Day5 后端 API 验收测试：POST /api/v1/recognize。

通过替换 recognize 模块级 pipeline 注入 Mock backend，验证：
- 四类高置信自动填充（auto_fill）
- 中等/低置信人工介入（manual_confirm / manual_select）
- 服务异常兜底 fallback（200 + 手动选择列表，发布不阻断）
- 系统级错误：无文件 400 / 空内容 400 / 不支持格式 400 / 超大 413

运行：C:\\Users\\HUAWEI\\mini\\envs\\shiguang\\python.exe backend/tests/test_day5_api.py
"""
import os
import sys

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BACKEND_DIR)

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402
from app.routers import recognize as recognize_router  # noqa: E402
from app.services.recognition_pipeline import RecognitionPipeline, MockBackend  # noqa: E402

PASS, FAIL = 0, 0
client = TestClient(app)


def check(name, cond, detail=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print("[PASS]", name)
    else:
        FAIL += 1
        print("[FAIL]", name, "->", detail)


def set_mock(*predefs):
    """替换模块级 pipeline 为预置 Mock backend。predefs 元素：
    ("success", label, conf) / ("failure", reason)"""
    mock = MockBackend()
    for p in predefs:
        if p[0] == "success":
            mock.add_success(p[1], p[2])
        else:
            mock.add_failure(p[1])
    recognize_router._pipeline = RecognitionPipeline(backend=mock)
    return mock


def upload(filename="test.jpg", content_type="image/jpeg", data=b"\xff\xd8fake-jpeg"):
    return client.post(
        "/api/v1/recognize",
        files={"image": (filename, data, content_type)},
    )


# 0. 路由已注册
set_mock(("success", "textbook", 0.95))
r = client.get("/api/v1/recognize").status_code
check("GET /recognize 不可用（仅 POST）", r in (405, 404), r)

# 1. ★ 四类高置信 -> auto_fill
four_cases = [
    ("textbook", 0.95, "textbook", "教材"),
    ("laptop", 0.90, "electronics", "电子产品"),
    ("cup", 0.88, "life_goods", "生活用品"),
    ("t-shirt", 0.92, "clothing", "衣物"),
]
for label, conf, want_cid, want_cname in four_cases:
    set_mock(("success", label, conf))
    resp = upload()
    body = resp.json()
    d = body.get("data", {})
    check(f"POST /recognize [{label}] 200 + code=0",
          resp.status_code == 200 and body.get("code") == 0, body)
    check(f"[{label}] 识别为 {want_cname}（auto_fill）",
          d.get("category_id") == want_cid
          and d.get("category_name") == want_cname
          and d.get("status") == "auto_fill"
          and d.get("need_confirm") is False, d)

# 2. 中等置信 -> manual_confirm（自动填充但提示确认）
set_mock(("success", "textbook", 0.70))
resp = upload()
d = resp.json().get("data", {})
check("中等置信 0.70 -> manual_confirm + need_confirm=True",
      d.get("status") == "manual_confirm" and d.get("need_confirm") is True
      and d.get("category_id") == "textbook", d)

# 3. 低置信 -> manual_select（不自动填充）
set_mock(("success", "umbrella", 0.40))
resp = upload()
d = resp.json().get("data", {})
check("低置信 0.40 -> manual_select + need_confirm=True",
      d.get("status") == "manual_select" and d.get("need_confirm") is True, d)

# 4. 未知标签高置信 -> manual_select（避免误填充）
set_mock(("success", "weird_label_xyz", 0.99))
resp = upload()
d = resp.json().get("data", {})
check("未知标签高置信 -> manual_select + matched_by=fallback",
      d.get("status") == "manual_select" and d.get("matched_by") == "fallback", d)

# 5. 服务异常 -> fallback 兜底（200 + 手动选择列表，发布不阻断）
set_mock(("failure", "模拟超时"))
resp = upload()
body = resp.json()
d = body.get("data", {})
check("AI 服务异常 -> HTTP 200（业务兜底不报错）", resp.status_code == 200, resp.status_code)
check("fallback=True + category_id=None", d.get("fallback") is True
      and d.get("category_id") is None, d)
check("fallback 带原因 + 10 类手动列表",
      bool(d.get("fallback_reason")) and len(d.get("available_categories", [])) == 10, d)

# 6. 系统级错误：无文件
set_mock(("success", "textbook", 0.95))
resp = client.post("/api/v1/recognize", files={})
check("无文件 -> 400 code=40001", resp.status_code == 400
      and resp.json().get("detail", {}).get("code") == 40001, resp.text)

# 7. 系统级错误：空内容
resp = upload(data=b"")
check("空内容 -> 400 code=40004", resp.status_code == 400
      and resp.json().get("detail", {}).get("code") == 40004, resp.text)

# 8. 系统级错误：不支持格式（MIME 与扩展名均不符）
resp = upload(filename="a.txt", content_type="text/plain")
check("不支持格式 -> 400 code=40001", resp.status_code == 400
      and resp.json().get("detail", {}).get("code") == 40001, resp.text)

# 9. 系统级错误：超大图片（>5MB）
big = b"\xff\xd8" + b"\x00" * (5 * 1024 * 1024 + 1)
resp = upload(data=big)
check("超大图片 -> 413 code=41301", resp.status_code == 413
      and resp.json().get("detail", {}).get("code") == 41301, resp.text)

# 10. 未知 MIME（octet-stream）+ 合法扩展名 -> 放行识别（兼容 wx.uploadFile）
set_mock(("success", "textbook", 0.95))
resp = upload(content_type="application/octet-stream")
check("octet-stream + .jpg -> 200（微信上传兼容）",
      resp.status_code == 200 and resp.json().get("data", {}).get("category_id") == "textbook",
      resp.text)

print()
print(f"===== 结果汇总：PASS={PASS} FAIL={FAIL} =====")
sys.exit(0 if FAIL == 0 else 1)
