# -*- coding: utf-8 -*-
"""Day5 识别链路单元测试（项目内版，对齐成员B test_day5.py 25 项覆盖）。

覆盖：教材/电子/生活/衣物四类高置信自动填充、阈值分流（confirm/select）、
服务异常兜底、未知标签强制人工、image_bytes 输入、Day2 MockAIClient 兼容。
运行：C:\\Users\\HUAWEI\\mini\\envs\\shiguang\\python.exe backend/tests/test_day5_pipeline.py
"""
import os
import sys

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BACKEND_DIR)

from app.services.recognition_pipeline import (  # noqa: E402
    RecognitionPipeline, MockBackend, build_available_categories)
from app.services.ai_client import MockAIClient  # noqa: E402

PASS, FAIL = 0, 0


def check(name, cond, detail=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print("[PASS]", name)
    else:
        FAIL += 1
        print("[FAIL]", name, "->", detail)


# 0. 兜底类别列表
cats = build_available_categories()
ids = [c["category_id"] for c in cats]
check("available_categories 含 10 类", len(cats) == 10, len(cats))
check("含教材/电子/生活/衣物四类（验收核心）",
      {"textbook", "electronics", "life_goods", "clothing"} <= set(ids), ids)

# 1. ★ 验收：四类高置信度自动填充
cases = [
    ("textbook", 0.95, "textbook", "教材"),
    ("laptop", 0.90, "electronics", "电子产品"),
    ("cup", 0.88, "life_goods", "生活用品"),
    ("t-shirt", 0.92, "clothing", "衣物"),
]
for label, conf, want_cid, want_cname in cases:
    mock = MockBackend()
    mock.add_success(label, conf)
    r = RecognitionPipeline(backend=mock).recommend(image_bytes=b"\xff\xd8mock")
    check(f"[{label}] 高置信识别为 {want_cname}",
          r["category_id"] == want_cid and r["category_name"] == want_cname, r)
    check(f"[{label}] status=auto_fill 无需人工确认",
          r["status"] == "auto_fill" and r["need_confirm"] is False, r)

# 2. 阈值分流：0.60~0.80 -> manual_confirm
mock = MockBackend()
mock.add_success("textbook", 0.70)
r = RecognitionPipeline(backend=mock).recommend(image_bytes=b"\xff\xd8mock")
check("中等置信 0.70 -> manual_confirm", r["status"] == "manual_confirm", r)
check("manual_confirm 时 need_confirm=True", r["need_confirm"] is True, r)
check("manual_confirm 仍给出类别（可自动填充待确认）",
      r["category_id"] == "textbook", r)

# 3. 阈值分流：<0.60 -> manual_select
mock = MockBackend()
mock.add_success("umbrella", 0.40)
r = RecognitionPipeline(backend=mock).recommend(image_bytes=b"\xff\xd8mock")
check("低置信 0.40 -> manual_select", r["status"] == "manual_select", r)
check("manual_select 时 need_confirm=True", r["need_confirm"] is True, r)

# 4. 未知标签即使高置信也强制 manual_select（标准化兜底）
mock = MockBackend()
mock.add_success("weird_label_xyz", 0.99)
r = RecognitionPipeline(backend=mock).recommend(image_bytes=b"\xff\xd8mock")
check("未知标签高置信 -> manual_select（matched_by=fallback）",
      r["status"] == "manual_select" and r["matched_by"] == "fallback", r)

# 5. 服务异常 -> fallback 兜底（可继续发布）
mock = MockBackend()
mock.add_failure("模拟超时")
r = RecognitionPipeline(backend=mock).recommend(image_bytes=b"\xff\xd8mock")
check("服务异常 -> fallback=True", r["fallback"] is True, r)
check("fallback 时 category_id=None", r["category_id"] is None, r)
check("fallback 带原因说明", bool(r["fallback_reason"]), r)
check("fallback 返回 10 类供手动选择", len(r["available_categories"]) == 10, r)
check("fallback 时 need_confirm=True", r["need_confirm"] is True, r)

# 6. 无输入 -> fallback
r = RecognitionPipeline(backend=MockBackend()).recommend()
check("无输入 -> fallback（缺少图片输入）", r["fallback"] is True, r)

# 7. 置信度非法/越界 -> fallback
for bad_conf in ("abc", 1.5, -0.1):
    mock = MockBackend()
    mock.add_success("textbook", bad_conf)
    r = RecognitionPipeline(backend=mock).recommend(image_bytes=b"\xff\xd8mock")
    check(f"置信度 {bad_conf} -> fallback", r["fallback"] is True, r)

# 8. backend 返回无标签 -> fallback
mock = MockBackend()
mock._results.append({"type": "success", "label": None, "confidence": 0.9})
r = RecognitionPipeline(backend=mock).recommend(image_bytes=b"\xff\xd8mock")
check("backend 无标签 -> fallback", r["fallback"] is True, r)

# 9. image_path 输入方式
mock = MockBackend()
mock.add_success("textbook", 0.95)
r = RecognitionPipeline(backend=mock).recommend(image_path="C:/fake/math.jpg")
check("image_path 输入 -> auto_fill 教材", r["category_id"] == "textbook", r)

# 10. Day2 MockAIClient 兼容（recognize 方法 backend）
mock2 = MockAIClient()
mock2.add_success("textbook", 0.96)
r = RecognitionPipeline(backend=mock2).recommend(image_bytes=b"\xff\xd8mock")
check("Day2 MockAIClient 兼容 -> auto_fill 教材",
      r["category_id"] == "textbook" and r["status"] == "auto_fill", r)

print()
print(f"===== 结果汇总：PASS={PASS} FAIL={FAIL} =====")
sys.exit(0 if FAIL == 0 else 1)
