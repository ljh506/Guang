# -*- coding: utf-8 -*-
"""
拾光Agent · Day5 自测脚本（成员B 交付）
========================================
覆盖识别链路全流程：Mock 识别 -> normalize 标准化 -> 阈值分流 -> 兜底。

运行方式：python test_day5.py
依赖：仅标准库。
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
# 兼容用例：引用 Day2 交付的 ai_client（backend 注入机制复用验证）
sys.path.insert(0, r"C:\Users\LENOVO\Desktop\拾光Agent\成员B_Day2_交付")
# 依赖模块：Day4 交付的 category_normalizer
sys.path.insert(0, r"C:\Users\LENOVO\Desktop\拾光Agent\成员B_Day4_交付")

from recognition_pipeline import (RecognitionPipeline, MockBackend,
                                 build_available_categories, STATUS_AUTO_FILL,
                                 STATUS_MANUAL_CONFIRM, STATUS_MANUAL_SELECT,
                                 STATUS_FALLBACK)

PASS = 0
FAIL = 0


def check(name, condition, detail=""):
    global PASS, FAIL
    if condition:
        PASS += 1
        print("[PASS]", name)
    else:
        FAIL += 1
        print("[FAIL]", name, "->", detail)


def make_pipeline(results):
    mock = MockBackend(predefined_results=results)
    return RecognitionPipeline(backend=mock), mock


def test_pipeline():
    print("\n===== recognition_pipeline 识别链路测试 =====")

    # 1) 高置信度已知标签 -> auto_fill
    p, _ = make_pipeline([{"type": "success", "label": "textbook", "confidence": 0.95}])
    r = p.recommend(image_path="img_high.jpg")
    check("高置信度已知标签 -> auto_fill 且无需确认",
          r["status"] == STATUS_AUTO_FILL and r["need_confirm"] is False
          and r["category_id"] == "textbook" and r["category_name"] == "教材",
          r)
    check("matched_by=alias（精确同义词命中）",
          r["matched_by"] == "alias", r)
    check("confidence 输出为调整后值（0.95）",
          abs(r["confidence"] - 0.95) < 1e-9, r)

    # 2) 中置信度 -> manual_confirm
    p, _ = make_pipeline([{"type": "success", "label": "t-shirt", "confidence": 0.70}])
    r = p.recommend(image_path="img_mid.jpg")
    check("中置信度(0.70) -> manual_confirm 且需要确认",
          r["status"] == STATUS_MANUAL_CONFIRM and r["need_confirm"] is True
          and r["category_id"] == "clothing", r)

    # 3) 低置信度 -> manual_select
    p, _ = make_pipeline([{"type": "success", "label": "umbrella", "confidence": 0.40}])
    r = p.recommend(image_path="img_low.jpg")
    check("低置信度(0.40) -> manual_select 且需要确认",
          r["status"] == STATUS_MANUAL_SELECT and r["need_confirm"] is True
          and r["category_id"] == "life_goods", r)

    # 4) 未知标签高置信度 -> 标准化兜底 other + 强制 manual_select
    p, _ = make_pipeline([{"type": "success", "label": "weird_label_xyz", "confidence": 0.99}])
    r = p.recommend(image_path="img_unknown.jpg")
    check("未知标签高置信度 -> other 兜底且强制 manual_select",
          r["category_id"] == "other" and r["matched_by"] == "fallback"
          and r["status"] == STATUS_MANUAL_SELECT and r["need_confirm"] is True,
          r)
    check("兜底置信度被负向调整（0.99-0.10=0.89）",
          abs(r["confidence"] - 0.89) < 1e-9, r)

    # 5) 未知标签低置信度 -> other + manual_select
    p, _ = make_pipeline([{"type": "success", "label": "some_mystery_item", "confidence": 0.30}])
    r = p.recommend(image_path="img_unknown2.jpg")
    check("未知标签低置信度 -> other + manual_select",
          r["category_id"] == "other" and r["status"] == STATUS_MANUAL_SELECT,
          r)

    # 6) 服务异常 -> fallback 兜底
    p, _ = make_pipeline([{"type": "failure", "reason": "模拟超时"}])
    r = p.recommend(image_path="img_fail.jpg")
    check("服务异常 -> fallback 且 need_confirm=True",
          r["status"] == STATUS_FALLBACK and r["fallback"] is True
          and r["need_confirm"] is True and r["category_id"] is None,
          r)
    check("fallback_reason 携带原因",
          isinstance(r["fallback_reason"], str) and "超时" in r["fallback_reason"],
          r)

    # 7) 后端返回数据异常（缺 label）-> fallback
    p, _ = make_pipeline([])
    p.backend = lambda img: {"confidence": 0.9}
    r = p.recommend(image_path="img_bad1.jpg")
    check("后端缺 label -> fallback", r["status"] == STATUS_FALLBACK, r)

    # 8) 置信度越界 -> fallback
    p, _ = make_pipeline([])
    p.backend = lambda img: {"label": "textbook", "confidence": 1.5}
    r = p.recommend(image_path="img_bad2.jpg")
    check("置信度越界(1.5) -> fallback", r["status"] == STATUS_FALLBACK, r)

    # 9) 图片路径传入 -> 正常识别（backend 收到路径）
    p, mock = make_pipeline([{"type": "success", "label": "Math Book", "confidence": 0.85}])
    r = p.recommend(image_path="img_path_test.jpg")
    check("图片路径传入 -> 识别成功且 backend 收到路径",
          r["category_id"] == "textbook" and mock.calls == ["img_path_test.jpg"],
          r)

    # 10) image_bytes 传入 -> 落临时文件调用 backend
    p, mock = make_pipeline([{"type": "success", "label": "iPhone", "confidence": 0.92}])
    r = p.recommend(image_bytes=b"\xff\xd8\xff\xe0 fake-jpeg-bytes")
    check("image_bytes 传入 -> 识别成功（复用 Day4 预留字段）",
          r["category_id"] == "electronics" and r["status"] == STATUS_AUTO_FILL,
          r)
    check("image_bytes 临时文件已清理",
          len(mock.calls) == 1 and not os.path.exists(mock.calls[0]),
          mock.calls)

    # 11) 无输入 -> fallback
    p, _ = make_pipeline([])
    r = p.recommend()
    check("无输入 -> fallback 且提示缺少图片",
          r["status"] == STATUS_FALLBACK and "缺少图片输入" in r["fallback_reason"],
          r)

    # 12) backend 抛文件不存在异常 -> fallback
    p, _ = make_pipeline([])
    p.backend = lambda img: (_ for _ in ()).throw(FileNotFoundError("图片路径不存在"))
    r = p.recommend(image_path="C:/no_such_dir/no_such_img.jpg")
    check("backend 文件不存在异常 -> fallback", r["status"] == STATUS_FALLBACK, r)

    # 13) 中文标签高置信度 -> textbook auto_fill
    p, _ = make_pipeline([{"type": "success", "label": "高数教材", "confidence": 0.90}])
    r = p.recommend(image_path="img_cn1.jpg")
    check("中文标签(高数教材) -> textbook auto_fill",
          r["category_id"] == "textbook" and r["status"] == STATUS_AUTO_FILL,
          r)

    # 14) 关键词包含命中 -> matched_by=keyword
    p, _ = make_pipeline([{"type": "success", "label": "高等数学教材第2版", "confidence": 0.85}])
    r = p.recommend(image_path="img_kw.jpg")
    check("关键词包含命中 -> textbook + matched_by=keyword",
          r["category_id"] == "textbook" and r["matched_by"] == "keyword",
          r)

    # 15) available_categories 完整 10 项
    available = build_available_categories()
    check("available_categories 含 10 个一级类别",
          len(available) == 10 and all("category_id" in a and "category_name" in a
                                       for a in available),
          available)

    # 16) fallback 时也返回完整类别列表供手动选择
    p, _ = make_pipeline([{"type": "failure", "reason": "服务错误"}])
    r = p.recommend(image_path="img_fb.jpg")
    check("fallback 携带 available_categories（10 项）",
          r["fallback"] and len(r["available_categories"]) == 10, r)

    # 17) 统一返回结构字段完整性
    p, _ = make_pipeline([{"type": "success", "label": "novel", "confidence": 0.88}])
    r = p.recommend(image_path="img_struct.jpg")
    required_fields = {"category_id", "category_name", "confidence", "need_confirm",
                       "matched_by", "fallback", "available_categories"}
    check("统一返回结构 7 个主字段齐全",
          required_fields.issubset(set(r.keys())), r.keys())

    # 18) 高置信度已知标签 need_confirm=False / 其他情况 True（判定矩阵）
    p, _ = make_pipeline([{"type": "success", "label": "basketball", "confidence": 0.99}])
    r = p.recommend(image_path="img_auto.jpg")
    check("auto_fill 场景 need_confirm=False",
          r["status"] == STATUS_AUTO_FILL and r["need_confirm"] is False, r)

    # 19) 与 Day2 MockAIClient 对象兼容（backend 注入机制复用）
    from ai_client import MockAIClient  # Day2 交付
    day2_mock = MockAIClient()
    day2_mock.add_success("textbook", 0.96)
    p = RecognitionPipeline(backend=day2_mock)  # 对象型 backend（含 recognize 方法）
    r = p.recommend(image_path="img_day2.jpg")
    check("兼容 Day2 MockAIClient（backend 注入机制复用）",
          r["category_id"] == "textbook" and r["status"] == STATUS_AUTO_FILL, r)

    # 20) 空字符串标签 -> other 兜底
    p, _ = make_pipeline([{"type": "success", "label": "", "confidence": 0.80}])
    r = p.recommend(image_path="img_empty.jpg")
    check("空字符串标签 -> other + manual_select",
          r["category_id"] == "other" and r["status"] == STATUS_MANUAL_SELECT, r)


if __name__ == "__main__":
    test_pipeline()
    print("\n===== 结果汇总：PASS=%d FAIL=%d =====" % (PASS, FAIL))
    sys.exit(0 if FAIL == 0 else 1)
