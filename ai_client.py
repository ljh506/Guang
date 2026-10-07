# -*- coding: utf-8 -*-
"""
拾光Agent · AI 识别服务客户端初版（成员B Day 2 交付）
====================================================
基于 Day 1《1_AI识别类别清单.md》落地。

职责：
- 封装外部视觉识别服务（图片 -> 类别 + 置信度）
- 统一返回结构：category_id / category_name / confidence
- 置信度阈值分流：
      confidence >= 0.80        -> auto_fill      （自动填充类别，前端高亮）
      0.60 <= confidence < 0.80 -> manual_confirm （自动填充但提示人工确认）
      confidence < 0.60         -> manual_select  （不自动填充，进入手动选择）
- 失败兜底：服务不可用 / 超时 / 识别失败 -> fallback（返回兜底标记，发布流程可继续）

设计说明：
- 不绑定具体第三方服务：通过注入 backend 函数解耦，可 mock 测试。
- backend 约定：backend(image_path) -> {"label": str, "confidence": float}，
  或抛出异常（超时/网络/服务错误）。
- 标签 -> 类别ID 映射表维护在 CATEGORY_ALIASES（后续可扩展/配置化）。
"""

import datetime
import logging

logger = logging.getLogger("ai_client")

# 置信度阈值（Day1 文档 §3）
THRESHOLD_AUTO_FILL = 0.80
THRESHOLD_MANUAL_CONFIRM = 0.60

# 类别ID -> 类别名（与《1_AI识别类别清单.md》对齐）
CATEGORY_NAMES = {
    "textbook": "教材",
    "electronics": "电子产品",
    "life_goods": "生活用品",
    "clothing": "衣物",
    "school_supplies": "文具用品",
    "digital_accessory": "数码配件",
    "sports": "运动器材",
    "furniture": "家具与宿舍用品",
    "books_other": "其他书籍/资料",
    "other": "其他",
}

# 第三方服务原始标签 -> 类别ID 映射（Day1 文档 §4；随服务方补充）
CATEGORY_ALIASES = {
    "book": "textbook", "textbook": "textbook", "math book": "textbook",
    "study book": "textbook", "text_book": "textbook",
    "laptop": "electronics", "notebook computer": "electronics",
    "phone": "electronics", "smartphone": "electronics",
    "keyboard": "electronics", "earphone": "electronics",
    "electronic": "electronics", "electronics": "electronics",
    "t-shirt": "clothing", "t_shirt": "clothing", "jacket": "clothing",
    "shoes": "clothing", "clothes": "clothing", "clothing": "clothing",
    "cup": "life_goods", "lamp": "life_goods", "umbrella": "life_goods",
    "daily_use": "life_goods", "life_goods": "life_goods",
    "pen": "school_supplies", "notebook": "school_supplies",
    "stationery": "school_supplies", "school_supplies": "school_supplies",
    "cable": "digital_accessory", "usb": "digital_accessory",
    "mouse": "digital_accessory", "digital_accessory": "digital_accessory",
    "sports_ball": "sports", "basketball": "sports", "yoga_mat": "sports",
    "sports": "sports",
    "furniture": "furniture", "chair": "furniture", "desk": "furniture",
    "novel": "books_other", "magazine": "books_other",
    "books_other": "books_other",
}

# 兜底类别ID：无法映射时归入 other（Day1 文档 §5）
FALLBACK_CATEGORY_ID = "other"
# 兜底标记字段：供前端识别"需要手动选择类别"的场景
FALLBACK_FLAG = "fallback"


# ---------------------------------------------------------------------------
# 识别结果结构
# ---------------------------------------------------------------------------

def make_result(status, category_id=None, confidence=None,
                fallback_reason=None, raw_label=None):
    """
    构造统一返回结构。

    返回字段：
        status            : auto_fill / manual_confirm / manual_select / fallback
        category_id       : 类别ID（None 表示无）
        category_name     : 类别中文名（None 表示无）
        confidence        : 置信度 0~1（None 表示无）
        fallback          : bool，是否需要手动选择兜底
        fallback_reason   : str/None，兜底原因说明
        raw_label         : 原始标签（便于复盘）
    """
    category_name = CATEGORY_NAMES.get(category_id) if category_id else None
    return {
        "status": status,
        "category_id": category_id,
        "category_name": category_name,
        "confidence": confidence,
        "fallback": (status == "fallback" or status == "manual_select"),
        "fallback_reason": fallback_reason,
        "raw_label": raw_label,
    }


def classify_confidence(confidence):
    """
    按置信度阈值分流（Day1 文档 §3）。

    - >= 0.80 : auto_fill
    - 0.60~0.80 : manual_confirm
    - < 0.60 : manual_select
    """
    if confidence is None:
        return "manual_select"
    if confidence >= THRESHOLD_AUTO_FILL:
        return "auto_fill"
    if confidence >= THRESHOLD_MANUAL_CONFIRM:
        return "manual_confirm"
    return "manual_select"


# ---------------------------------------------------------------------------
# 标签映射
# ---------------------------------------------------------------------------

def map_label_to_category(raw_label):
    """将第三方服务返回的原始标签映射到类别ID；无法映射返回 FALLBACK_CATEGORY_ID。"""
    if not raw_label:
        return FALLBACK_CATEGORY_ID
    lowered = str(raw_label).strip().lower()
    # 同时支持带空格与下划线两种标签形式（如 "math book" / "math_book"）
    for key in (lowered, lowered.replace(" ", "_")):
        if key in CATEGORY_ALIASES:
            return CATEGORY_ALIASES[key]
    return FALLBACK_CATEGORY_ID


# ---------------------------------------------------------------------------
# 客户端主类（可注入 backend 以 mock / 接入真实服务）
# ---------------------------------------------------------------------------

class AIClient:
    """
    图片 -> 类别 + 置信度 识别客户端。

    用法：
        client = AIClient(backend=my_vision_backend, timeout_seconds=5)
        result = client.recognize("path/to/image.jpg")

    backend 约定（由接入方实现 / mock）：
        backend(image_path) -> {"label": str, "confidence": float}
        失败时抛异常（如 TimeoutError / ConnectionError / ValueError）。
    """

    def __init__(self, backend=None, timeout_seconds=5.0):
        # 默认 backend：抛异常，表示"未接入真实服务时默认失败兜底"
        self.backend = backend if backend is not None else self._default_backend
        self.timeout_seconds = timeout_seconds

    @staticmethod
    def _default_backend(image_path):
        raise RuntimeError("未配置 AI 识别服务 backend，默认走失败兜底")

    def recognize(self, image_path):
        """
        识别图片并返回统一结构。

        - backend 正常返回 label/confidence -> 映射类别 + 阈值分流
        - backend 异常（不可用/超时/识别失败）-> fallback 兜底
        """
        try:
            raw = self.backend(image_path)
        except Exception as exc:  # noqa: BLE001 - 兜底要求捕获所有异常
            logger.warning("AI 识别调用失败：%s", exc)
            return make_result(
                status="fallback",
                fallback_reason="AI识别服务不可用/超时/失败，请手动选择类别",
            )

        label = raw.get("label")
        confidence = raw.get("confidence")

        # 后端返回异常数据（无 label / confidence 非法）也走兜底
        if label is None or confidence is None:
            return make_result(
                status="fallback",
                fallback_reason="AI识别返回数据异常，请手动选择类别",
                raw_label=label,
            )

        try:
            confidence = float(confidence)
        except (TypeError, ValueError):
            return make_result(
                status="fallback",
                fallback_reason="AI识别置信度非法，请手动选择类别",
                raw_label=label,
            )
        # 置信度越界（<0 或 >1）视为异常，走兜底
        if not (0.0 <= confidence <= 1.0):
            return make_result(
                status="fallback",
                fallback_reason="AI识别置信度越界，请手动选择类别",
                raw_label=label,
            )

        category_id = map_label_to_category(label)
        status = classify_confidence(confidence)
        return make_result(
            status=status,
            category_id=category_id,
            confidence=confidence,
            raw_label=label,
        )


# ---------------------------------------------------------------------------
# Mock 客户端（测试用，无需真实服务）
# ---------------------------------------------------------------------------

class MockAIClient(AIClient):
    """
    测试专用：按预置结果/异常返回，验证阈值分流与兜底逻辑。

    用法：
        mock = MockAIClient(predefined_results=[...])
        mock.add_success("t-shirt", 0.90)
        mock.add_failure("模拟超时")
    """

    def __init__(self, predefined_results=None):
        super().__init__(backend=None)  # 不使用 backend，直接覆写 recognize
        self._results = list(predefined_results or [])
        self.calls = []

    def add_success(self, label, confidence):
        self._results.append({"type": "success", "label": label, "confidence": confidence})

    def add_failure(self, reason="mock 失败"):
        self._results.append({"type": "failure", "reason": reason})

    def recognize(self, image_path):
        self.calls.append(image_path)
        if not self._results:
            return make_result(status="fallback",
                               fallback_reason="mock 无预置结果，走兜底")
        item = self._results.pop(0)
        if item["type"] == "failure":
            return make_result(status="fallback",
                               fallback_reason=item["reason"])
        return super().recognize_from_parsed(item["label"], item["confidence"])


# 说明：AIClient.recognize_from_parsed 用于从已解析 label/confidence 走映射+分流，
# 在下方定义以复用同一套分流逻辑（避免 mock 与真实路径不一致）。
AIClient.recognize_from_parsed = lambda self, label, confidence: (
    lambda cid: make_result(
        status=classify_confidence(confidence),
        category_id=cid,
        confidence=confidence,
        raw_label=label,
    )
)(map_label_to_category(label))


# ---------------------------------------------------------------------------
# 简易命令行自测入口
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    mock = MockAIClient()
    mock.add_success("textbook", 0.96)
    mock.add_success("t-shirt", 0.70)
    mock.add_success("umbrella", 0.40)
    mock.add_failure("服务超时")
    mock.add_success("weird_label_xyz", 0.99)

    print("ai_client.py 自测：")
    for i in range(5):
        r = mock.recognize(f"img_{i}.jpg")
        print(i, r)
