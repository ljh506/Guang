# -*- coding: utf-8 -*-
"""
拾光Agent · 图片识别链路主模块（成员B Day 5 交付）
====================================================
整合 Day2 ai_client（识别调用封装）+ Day4 category_normalizer（类别标准化）
为完整链路：

    输入图片（image_path / image_bytes，复用 Day4 EstimateParams 预留字段）
      -> AI 识别服务（复用/扩展 Day2 backend 注入机制与 MockAIClient）
      -> category_normalizer.normalize 标准化类别
      -> 阈值分流（>=0.80 auto_fill / 0.60~0.80 manual_confirm / <0.60 manual_select）
      -> 失败兜底（服务异常/超时 -> fallback + 可手动选择的类别列表）

统一返回结构 recommend()：
    {
        "category_id": str|None,
        "category_name": str|None,
        "confidence": float,          # 标准化调整后的置信度 0~1
        "need_confirm": bool,         # 是否需要人工介入（确认/选择）
        "matched_by": str|None,       # alias / keyword / fallback
        "fallback": bool,             # 服务异常/超时兜底
        "available_categories": [{"category_id", "category_name"}, ...],
        # —— 以下为扩展字段，供前端细分渲染 ——
        "status": str,                # auto_fill / manual_confirm / manual_select / fallback
        "fallback_reason": str|None,
        "raw_label": str|None,
    }

依赖：仅标准库。
"""

import inspect
import logging
import os
import sys
import tempfile

# 引用 Day4 交付的 category_normalizer；独立运行失败时回退到 Day4 交付目录
try:
    from category_normalizer import (normalize, CATEGORY_IDS, CATEGORY_NAMES,
                                     to_engine_category)
except ModuleNotFoundError:
    sys.path.insert(0, r"C:\Users\LENOVO\Desktop\拾光Agent\成员B_Day4_交付")
    from category_normalizer import (normalize, CATEGORY_IDS, CATEGORY_NAMES,
                                     to_engine_category)

logger = logging.getLogger("recognition_pipeline")

# 与 Day2 ai_client 阈值一致
THRESHOLD_AUTO_FILL = 0.80
THRESHOLD_MANUAL_CONFIRM = 0.60

STATUS_AUTO_FILL = "auto_fill"
STATUS_MANUAL_CONFIRM = "manual_confirm"
STATUS_MANUAL_SELECT = "manual_select"
STATUS_FALLBACK = "fallback"


# ---------------------------------------------------------------------------
# 类别列表（兜底/手动选择时提供给前端）
# ---------------------------------------------------------------------------

def build_available_categories():
    """返回 10 个一级类别的 [{category_id, category_name}, ...]，供前端下拉渲染。"""
    return [
        {"category_id": cid, "category_name": CATEGORY_NAMES[cid]}
        for cid in CATEGORY_IDS
    ]


# ---------------------------------------------------------------------------
# 阈值分流
# ---------------------------------------------------------------------------

def classify_confidence(confidence):
    """
    按置信度阈值分流（与 Day2 ai_client 完全一致）：
        >= 0.80              -> auto_fill
        0.60 ~ 0.80          -> manual_confirm
        < 0.60               -> manual_select
    """
    if confidence is None:
        return STATUS_MANUAL_SELECT
    if confidence >= THRESHOLD_AUTO_FILL:
        return STATUS_AUTO_FILL
    if confidence >= THRESHOLD_MANUAL_CONFIRM:
        return STATUS_MANUAL_CONFIRM
    return STATUS_MANUAL_SELECT


def _clamp_confidence(value):
    return max(0.0, min(1.0, value))


# ---------------------------------------------------------------------------
# 识别链路主类
# ---------------------------------------------------------------------------

class RecognitionPipeline:
    """
    图片 -> 类别 + 置信度 识别链路。

    用法：
        pipeline = RecognitionPipeline(backend=my_vision_backend)
        result = pipeline.recommend(image_path="path/to/img.jpg")
        result = pipeline.recommend(image_bytes=b"...")     # 字节直传
        result = pipeline.recommend()                       # 无输入 -> fallback

    backend 约定（复用 Day2 ai_client 机制）：
        backend(image_path) -> {"label": str, "confidence": float}
        失败时抛异常（如 TimeoutError / ConnectionError / ValueError）。

    与 Day2 的区别：Day2 AIClient.recognize 使用轻量 map_label_to_category；
    本模块统一使用 Day4 category_normalizer.normalize 完成标准化（增强版映射，
    支持同义词表 + 关键词包含 + 兜底），并输出置信度调整。
    """

    def __init__(self, backend=None, timeout_seconds=5.0):
        self.backend = backend if backend is not None else self._default_backend
        self.timeout_seconds = timeout_seconds

    @staticmethod
    def _default_backend(image_path):
        raise RuntimeError("未配置 AI 识别服务 backend，默认走失败兜底")

    # ------------------------------------------------------------------ 输入
    def _resolve_input(self, image_path, image_bytes):
        """返回 (实际传给 backend 的路径, 是否需要清理临时文件)。
        路径存在性由 backend / 真实服务校验（与 Day2 AIClient 一致，pipeline 只负责透传）。"""
        if image_path:
            return image_path, None
        if image_bytes is not None:
            # image_bytes 直传：落临时文件后调用 backend（兼容 Day2 单参 backend）
            suffix = ".jpg"
            fd, tmp_path = tempfile.mkstemp(suffix=suffix)
            try:
                with os.fdopen(fd, "wb") as f:
                    f.write(image_bytes)
            except Exception:
                os.unlink(tmp_path)
                raise
            return tmp_path, tmp_path
        return None, None

    # --------------------------------------------------------------- 主流程
    def recommend(self, image_path=None, image_bytes=None):
        """
        识别链路入口，返回统一结构（见模块 docstring）。

        - backend 正常返回 label/confidence -> normalize 标准化 + 阈值分流
        - backend 异常（不可用/超时/失败）-> fallback 兜底
        """
        available = build_available_categories()

        try:
            resolved_path, cleanup = self._resolve_input(image_path, image_bytes)
            if resolved_path is None:
                return self._make_fallback(available, "缺少图片输入（image_path 或 image_bytes）")
        except Exception as exc:  # noqa: BLE001 - 兜底要求捕获所有异常
            return self._make_fallback(available, "图片输入无效：%s" % exc)

        try:
            try:
                raw = _call_backend(self.backend, resolved_path)
            finally:
                if cleanup:
                    self._safe_cleanup(cleanup)
        except Exception as exc:  # noqa: BLE001 - 兜底要求捕获所有异常
            logger.warning("AI 识别调用失败：%s", exc)
            return self._make_fallback(available, "AI识别服务不可用/超时/失败，请手动选择类别")

        return self._build_result(raw, available)

    # --------------------------------------------------------------- 结果组装
    def _build_result(self, raw, available):
        """根据 backend 返回组装统一结构。
        兼容两种来源：backend 约定 {"label", "confidence"}（Day2 机制），
        以及 Day2 AIClient 统一结果 {"raw_label", "confidence", ...}。"""
        if isinstance(raw, dict):
            label = raw.get("label")
            if label is None:  # 兼容 Day2 AIClient 统一结果（空字符串须保留交给 normalize）
                label = raw.get("raw_label")
            confidence = raw.get("confidence")
        else:
            label = None
            confidence = None

        # 后端返回异常数据 -> 兜底
        if label is None:
            return self._make_fallback(available, "AI识别返回数据异常（无标签），请手动选择类别")
        try:
            confidence = float(confidence)
        except (TypeError, ValueError):
            return self._make_fallback(available, "AI识别置信度非法，请手动选择类别",
                                       raw_label=label)
        if not (0.0 <= confidence <= 1.0):
            return self._make_fallback(available, "AI识别置信度越界，请手动选择类别",
                                       raw_label=label)

        # 标准化：Day4 category_normalizer（同义词/关键词/兜底）
        norm = normalize(label)
        category_id = norm["category_id"]
        matched_by = norm["matched_by"]
        adjusted_confidence = _clamp_confidence(confidence + norm["confidence_adjust"])

        # 阈值分流（与 Day2 一致）；但标准化兜底(other)时强制人工选择
        if matched_by == "fallback":
            status = STATUS_MANUAL_SELECT
        else:
            status = classify_confidence(adjusted_confidence)

        need_confirm = status in (STATUS_MANUAL_CONFIRM, STATUS_MANUAL_SELECT,
                                  STATUS_FALLBACK)

        return {
            "category_id": category_id,
            "category_name": CATEGORY_NAMES.get(category_id, category_id),
            "confidence": adjusted_confidence,
            "need_confirm": need_confirm,
            "matched_by": matched_by,
            "fallback": False,
            "available_categories": available,
            "status": status,
            "fallback_reason": None,
            "raw_label": label,
        }

    @staticmethod
    def _make_fallback(available, reason, raw_label=None):
        return {
            "category_id": None,
            "category_name": None,
            "confidence": None,
            "need_confirm": True,
            "matched_by": None,
            "fallback": True,
            "available_categories": available,
            "status": STATUS_FALLBACK,
            "fallback_reason": reason,
            "raw_label": raw_label,
        }

    @staticmethod
    def _safe_cleanup(tmp_path):
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


# ---------------------------------------------------------------------------
# Mock backend（测试/演示用，无需真实服务）
# ---------------------------------------------------------------------------

class MockBackend:
    """
    测试专用 backend：按预置结果/异常返回。

    用法：
        mock = MockBackend()
        mock.add_success("textbook", 0.95)
        mock.add_failure("模拟超时")
        result = RecognitionPipeline(backend=mock).recommend("img.jpg")
    """

    def __init__(self, predefined_results=None):
        self._results = list(predefined_results or [])
        self.calls = []

    def add_success(self, label, confidence):
        self._results.append({"type": "success", "label": label,
                              "confidence": confidence})

    def add_failure(self, reason="mock 失败"):
        self._results.append({"type": "failure", "reason": reason})

    def __call__(self, image_path):
        self.calls.append(image_path)
        if not self._results:
            raise RuntimeError("mock 无预置结果")
        item = self._results.pop(0)
        if item["type"] == "failure":
            raise RuntimeError(item["reason"])
        return {"label": item["label"], "confidence": item["confidence"]}


# 兼容入口：支持传入 Day2 MockAIClient 风格的 backend 对象（其 recognize 方法）
def _call_backend(backend, image_path):
    """按 backend 签名调用：优先 backend(image_path)，兼容 backend.recognize(image_path)。"""
    if callable(backend):
        return backend(image_path)
    if hasattr(backend, "recognize"):
        return backend.recognize(image_path)
    raise TypeError("backend 必须是可调用对象或含 recognize 方法的对象")


# ---------------------------------------------------------------------------
# 简易命令行自测入口
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    mock = MockBackend()
    mock.add_success("textbook", 0.95)
    mock.add_success("t-shirt", 0.70)
    mock.add_success("weird_label_xyz", 0.99)
    mock.add_failure("服务超时")

    pipeline = RecognitionPipeline(backend=mock)
    for i in range(4):
        print(i, pipeline.recommend(image_path="img_%d.jpg" % i))
