# -*- coding: utf-8 -*-
"""
拾光Agent · 用户提示优化模块 user_prompt.py（成员B Day 12 交付）
================================================================
任务来源：项目计划书「十五、五人团队逐日开发任务表」Day 12 行，成员B 当日任务
「优化AI识别失败和估价异常的用户提示」（当天目标：UI与交互优化）。

本模块把 Day5 recognition_pipeline（AI 识别链路）与 Day7 price_engine_day7
（估价引擎）的机器返回结果，翻译成用户可直接理解、可立刻行动的提示文案，
供成员C/D 在发布页 / 商品详情页直接渲染：

一、AI 识别失败/低置信度提示  build_recognition_tip(result, scene)
    - 输入：RecognitionPipeline.recommend() 的统一返回结构
      （status: auto_fill / manual_confirm / manual_select / fallback，
       含 fallback_reason / raw_label / confidence / available_categories）
    - 输出：{level, title, message, action, raw_label, fallback_reason}
      - auto_fill        -> 静默成功（消息仅作轻提示，不阻断）
      - manual_confirm   -> 请确认类别
      - manual_select    -> 置信度低，请手动选择
      - fallback         -> 识别失败，按原因给可执行动作
        （服务不可用/超时、返回无标签、置信度非法、置信度越界、
          缺少图片输入、图片输入无效）

二、估价异常/区间提示  build_price_tip(result, scene)
    - 输入：price_engine_day7.estimate_price() 返回
      （成功 dict 含 estimated_min / estimated_max / reason_text / price_tip；
       失败 dict 含 error: {error_code, message}）
    - 输出：{level, title, message, action, error_code}
      - 成功 + price_tip（标价低于/高于建议区间）-> 黄色提示，建议参考
      - 成功 + 无 price_tip                      -> 绿色成功提示（区间展示）
      - 失败 -> 按 ERROR_CODE_TIPS 给具体修正动作

与前后模块衔接：
- 上游：Day5 recognition_pipeline（status/fallback_reason 字段）、
        Day7 price_engine_day7（estimate_price 返回结构）
- 下游：成员C（前端首页/详情页）、成员D（前端发布/交换页）直接取
        title/message/action 渲染，无需感知内部状态机
依赖：仅标准库。
"""

# ---------------------------------------------------------------------------
# 一、AI 识别提示
# ---------------------------------------------------------------------------

# 场景名（供调用方传入，默认发布页 publish）
SCENE_PUBLISH = "publish"
SCENE_DETAIL = "detail"
SCENES = (SCENE_PUBLISH, SCENE_DETAIL)

# status -> 提示级别
_LEVEL_GOOD = "good"      # 绿色/静默成功
_LEVEL_WARN = "warn"      # 黄色/需确认
_LEVEL_ERROR = "error"    # 红色/需手动处理


def _scene_label(scene):
    return "发布" if scene == SCENE_PUBLISH else "详情"


def build_recognition_tip(result, scene=SCENE_PUBLISH):
    """
    把 AI 识别链路结果翻译为用户提示。

    参数：
        result : dict，RecognitionPipeline.recommend() 返回结构
                 （status / fallback_reason / raw_label / confidence /
                   available_categories 等字段；result 为 None 时按失败处理）
        scene  : str，publish / detail
    返回：
        dict {level, title, message, action, raw_label, fallback_reason}
    """
    if result is None or not isinstance(result, dict):
        return {
            "level": _LEVEL_ERROR,
            "title": "AI识别失败",
            "message": "系统暂时无法识别图片，请手动选择物品类别。",
            "action": "打开类别下拉框，手动选择物品类别",
            "raw_label": None,
            "fallback_reason": "识别结果缺失",
        }

    status = result.get("status")
    raw_label = result.get("raw_label")
    fallback_reason = result.get("fallback_reason")
    confidence = result.get("confidence")
    category_name = result.get("category_name")
    scene_txt = _scene_label(scene)

    # 1) 自动填入成功
    if status == "auto_fill":
        return {
            "level": _LEVEL_GOOD,
            "title": "已自动识别类别",
            "message": "系统已自动识别物品类别为「%s」（置信度 %d%%）。"
                       % (category_name or "未分类",
                          int(round(float(confidence) * 100))
                          if _is_finite(confidence) else 0),
            "action": None,
            "raw_label": raw_label,
            "fallback_reason": None,
        }

    # 2) 需人工确认（0.60~0.80）
    if status == "manual_confirm":
        return {
            "level": _LEVEL_WARN,
            "title": "请确认物品类别",
            "message": "AI 识别为「%s」（置信度 %d%%），请确认是否正确。"
                       % (category_name or "未分类",
                          int(round(float(confidence) * 100))
                          if _is_finite(confidence) else 0),
            "action": "确认类别「%s」或重新选择" % (category_name or ""),
            "raw_label": raw_label,
            "fallback_reason": None,
        }

    # 3) 置信度低，需手动选择（<0.60 或标准化兜底类别）
    if status == "manual_select":
        return {
            "level": _LEVEL_WARN,
            "title": "识别置信度较低",
            "message": "AI 未能准确识别图片类别，请手动选择最接近的物品类别。",
            "action": "从下拉框中选择物品类别",
            "raw_label": raw_label,
            "fallback_reason": None,
        }

    # 4) 失败兜底：按原因给出可执行动作
    if status == "fallback":
        return _build_fallback_tip(fallback_reason, raw_label, scene_txt)

    # 5) 未知状态（防御）
    return {
        "level": _LEVEL_ERROR,
        "title": "AI识别失败",
        "message": "识别结果异常（未知状态），请手动选择物品类别。",
        "action": "从下拉框中选择物品类别",
        "raw_label": raw_label,
        "fallback_reason": fallback_reason or "未知识别状态",
    }


def _is_finite(value):
    """判断值是否为有限数值。"""
    try:
        num = float(value)
    except (TypeError, ValueError):
        return False
    return num == num and num != float("inf") and num != -float("inf")


def _build_fallback_tip(reason, raw_label, scene_txt):
    """按 fallback_reason 生成失败提示与动作。reason 为 None 时使用兜底文案。"""
    reason = reason or "AI识别服务不可用"

    # 按关键词归类（与 Day5 recognition_pipeline 产出文案对应）
    mapping = [
        ("缺少图片输入", "请先上传要发布的物品图片。"),
        ("图片输入无效", "图片无法读取，请重新上传一张清晰的物品图片。"),
        ("超时", "AI识别服务响应超时，请稍后重试或手动选择类别。"),
        ("服务不可用", "AI识别服务暂时不可用，请稍后重试或手动选择类别。"),
        ("无标签", "AI识别未返回结果，请手动选择物品类别。"),
        ("置信度非法", "AI识别结果异常，请手动选择物品类别。"),
        ("置信度越界", "AI识别结果异常，请手动选择物品类别。"),
        ("数据异常", "AI识别返回数据异常，请手动选择物品类别。"),
    ]
    message = None
    for key, txt in mapping:
        if reason and key in reason:
            message = txt
            break
    if message is None:
        message = "AI识别未能完成，请手动选择物品类别。"

    return {
        "level": _LEVEL_ERROR,
        "title": "AI识别失败",
        "message": message,
        "action": "从下拉框中手动选择物品类别，或稍后重试",
        "raw_label": raw_label,
        "fallback_reason": reason,
    }


# ---------------------------------------------------------------------------
# 二、估价提示
# ---------------------------------------------------------------------------

# 估价错误码 -> 用户提示（与 Day7 price_engine_day7.ERROR_CODES 对应）
ERROR_CODE_TIPS = {
    "PRICE_ORIGINAL_REQUIRED": {
        "title": "请填写参考原价",
        "message": "估价需要物品的参考原价（如购买价格），请填写后重新估价。",
        "action": "填写参考原价",
    },
    "PRICE_INVALID_FORMAT": {
        "title": "原价格式不正确",
        "message": "原价只能填写数字（如 68 或 68.5），请修改后重新估价。",
        "action": "修改原价为数字格式",
    },
    "PRICE_OUT_OF_RANGE": {
        "title": "原价超出合理范围",
        "message": "原价过高或为异常值（超过 100000 元），请核对后重新填写。",
        "action": "核对并修改原价",
    },
    "CONDITION_REQUIRED": {
        "title": "请选择物品品相",
        "message": "估价需要知道物品的品相（全新/良好/一般），请选择后重新估价。",
        "action": "选择物品品相",
    },
    "CONDITION_INVALID": {
        "title": "品相取值非法",
        "message": "品相只能为「全新/良好/一般」三档之一，请重新选择。",
        "action": "重新选择物品品相",
    },
    "CATEGORY_INVALID": {
        "title": "物品类别不在估价范围内",
        "message": "当前类别暂不支持估价，请先选择正确的物品类别。",
        "action": "重新选择物品类别",
    },
}

# 未知错误码兜底
_UNKNOWN_ERROR_TIP = {
    "title": "估价失败",
    "message": "估价暂未完成，请稍后重试或人工估算参考价。",
    "action": "稍后重试或人工填写建议标价",
}


def build_price_tip(result, scene=SCENE_PUBLISH):
    """
    把估价引擎结果翻译为用户提示。

    参数：
        result : dict，price_engine_day7.estimate_price() 返回
                 （成功含 estimated_min / estimated_max / reason_text / price_tip；
                   失败含 error: {error_code, message}）
        scene  : str，publish / detail（仅用于文案措辞）
    返回：
        dict {level, title, message, action, error_code}
        error_code 为 None 表示估价成功。
    """
    scene_txt = _scene_label(scene)
    if result is None or not isinstance(result, dict):
        return {
            "level": _LEVEL_ERROR,
            "title": "估价失败",
            "message": "估价结果缺失，请稍后重试。",
            "action": "稍后重试",
            "error_code": None,
        }

    # 失败分支
    err = result.get("error")
    if err is not None:
        code = err.get("error_code")
        tip = ERROR_CODE_TIPS.get(code, _UNKNOWN_ERROR_TIP)
        return {
            "level": _LEVEL_ERROR,
            "title": tip["title"],
            "message": tip["message"],
            "action": tip["action"],
            "error_code": code,
        }

    # 成功分支：取区间与标价提示
    lo = result.get("estimated_min")
    hi = result.get("estimated_max")
    price_tip = result.get("price_tip")
    reason_text = result.get("reason_text")

    # 免费赠送（区间 0~0）
    if _is_finite(lo) and _is_finite(hi) and lo == 0 and hi == 0:
        return {
            "level": _LEVEL_GOOD,
            "title": "免费赠送估价为 0 元",
            "message": "该物品选择免费赠送，估价为 0 元。",
            "action": None,
            "error_code": None,
        }

    if not (_is_finite(lo) and _is_finite(hi)):
        return {
            "level": _LEVEL_WARN,
            "title": "估价区间异常",
            "message": "估价区间暂未生成，请稍后重试。",
            "action": "稍后重试",
            "error_code": None,
        }

    base_message = "建议估价区间 %s~%s 元。%s" % (lo, hi, reason_text or "")

    if price_tip:
        # 用户手填标价低于/高于建议区间 -> 黄色提示
        level = _LEVEL_WARN
        title = "标价建议"
        action = "参考建议区间调整标价，或保持当前标价继续发布"
    else:
        # 正常成功（标价在建议区间内）-> 绿色提示
        level = _LEVEL_GOOD
        title = "估价完成"
        action = None

    return {
        "level": level,
        "title": title,
        "message": base_message + ("\n" + price_tip if price_tip else ""),
        "action": action,
        "error_code": None,
    }


# ---------------------------------------------------------------------------
# 三、组合入口（发布页一次渲染）
# ---------------------------------------------------------------------------

def build_publish_tips(recognition_result, price_result, scene=SCENE_PUBLISH):
    """
    发布页组合提示：AI 识别提示 + 估价提示。

    返回：
        {"recognition": build_recognition_tip(...),
         "price": build_price_tip(...)}
    """
    return {
        "recognition": build_recognition_tip(recognition_result, scene),
        "price": build_price_tip(price_result, scene),
    }


# ---------------------------------------------------------------------------
# 简易命令行自测入口
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print("user_prompt.py（Day12 用户提示优化）自测：")
    # 识别提示示例
    ok = {"status": "auto_fill", "category_name": "教材", "confidence": 0.95,
          "raw_label": "textbook", "fallback_reason": None}
    print("auto_fill ->", build_recognition_tip(ok)["title"])
    fb = {"status": "fallback", "raw_label": None,
          "fallback_reason": "AI识别服务不可用/超时/失败，请手动选择类别"}
    print("fallback ->", build_recognition_tip(fb)["message"])
    # 估价提示示例
    pr = {"estimated_min": 27, "estimated_max": 41,
          "reason_text": "原价 68 元 × 教材良好折扣 0.4~0.6 = 27~41 元",
          "price_tip": "您的标价低于建议区间（27~41 元），可适当参考建议价"}
    print("price ->", build_price_tip(pr)["message"])
    err = {"error": {"error_code": "PRICE_INVALID_FORMAT",
                     "message": "原价格式不正确，请输入数字"}}
    print("price_error ->", build_price_tip(err)["title"])
    print("user_prompt 自测通过")
