# -*- coding: utf-8 -*-
"""
拾光Agent · 类别标准化模块（成员B Day 4 交付）
====================================================
将 AI 识别返回的原始标签 / 关键词标准化到 Day1 类别清单的统一体系。

Day4 统一类别体系（10 个一级类别）：
    textbook / electronics / life_goods / clothing / stationery /
    digital_accessories / sports_equipment / furniture / other_books / other

功能：
    ① 同义词/别名映射表（精确匹配 + 关键词包含匹配）
    ② normalize(raw_label) -> {category_id, category_name, confidence_adjust, matched_by}
    ③ 未知输入兜底 other
    ④ 提供 to_engine_category() 将 Day4 类别映射为 Day2 price_engine 使用的类别ID

与 ai_client 的衔接：
    ai_client.map_label_to_category() 是 Day2 的轻量映射；本模块是其增强版，
    建议 Day5 起统一改用 category_normalizer.normalize() 完成标签标准化。

依赖：仅标准库。
"""

# ---------------------------------------------------------------------------
# 统一类别体系
# ---------------------------------------------------------------------------

CATEGORY_IDS = [
    "textbook", "electronics", "life_goods", "clothing", "stationery",
    "digital_accessories", "sports_equipment", "furniture", "other_books", "other",
]

CATEGORY_NAMES = {
    "textbook": "教材",
    "electronics": "电子产品",
    "life_goods": "生活用品",
    "clothing": "衣物",
    "stationery": "文具用品",
    "digital_accessories": "数码配件",
    "sports_equipment": "运动器材",
    "furniture": "家具与宿舍用品",
    "other_books": "其他书籍/资料",
    "other": "其他",
}

# ---------------------------------------------------------------------------
# ① 同义词 / 别名映射表
# ---------------------------------------------------------------------------

# 精确别名表：规范化后的 key -> category_id
# 键统一为：小写 + 去首尾空格 + 空格转下划线
SYNONYM_MAP = {
    # 教材 textbook
    "textbook": "textbook", "text_book": "textbook", "book": "textbook",
    "math_book": "textbook", "math": "textbook", "calculus": "textbook",
    "linear_algebra": "textbook", "study_book": "textbook",
    "教材": "textbook", "课本": "textbook", "高数教材": "textbook",
    "高等数学": "textbook", "教辅": "textbook", "考研书": "textbook",
    # 电子产品 electronics
    "electronics": "electronics", "electronic": "electronics",
    "laptop": "electronics", "computer": "electronics", "pc": "electronics",
    "phone": "electronics", "smartphone": "electronics", "iphone": "electronics",
    "ipad": "electronics", "tablet": "electronics", "camera": "electronics",
    "kindle": "electronics", "手机": "electronics", "电脑": "electronics",
    "笔记本": "electronics", "相机": "electronics", "平板": "electronics",
    "耳机": "digital_accessories", "earphone": "digital_accessories",
    "headphone": "digital_accessories", "airpods": "digital_accessories",
    "充电宝": "digital_accessories", "power_bank": "digital_accessories",
    "充电器": "digital_accessories", "charger": "digital_accessories",
    "数据线": "digital_accessories", "cable": "digital_accessories",
    "mouse": "digital_accessories", "键盘": "digital_accessories",
    "keyboard": "digital_accessories", "usb": "digital_accessories",
    "手环": "digital_accessories", "bracelet": "digital_accessories",
    # 生活用品 life_goods
    "life_goods": "life_goods", "daily_use": "life_goods",
    "cup": "life_goods", "mug": "life_goods", "lamp": "life_goods",
    "umbrella": "life_goods", "thermos": "life_goods",
    "水杯": "life_goods", "保温杯": "life_goods", "台灯": "life_goods",
    "雨伞": "life_goods", "生活用品": "life_goods", "收纳盒": "life_goods",
    # 衣物 clothing
    "clothing": "clothing", "clothes": "clothing",
    "t_shirt": "clothing", "tshirt": "clothing", "shirt": "clothing",
    "jacket": "clothing", "hoodie": "clothing", "shoes": "clothing",
    "trousers": "clothing", "pants": "clothing",
    "衣服": "clothing", "短袖": "clothing", "卫衣": "clothing",
    "夹克": "clothing", "外套": "clothing", "鞋": "clothing", "裤子": "clothing",
    # 文具用品 stationery
    "stationery": "stationery", "school_supplies": "stationery",
    "pen": "stationery", "pencil": "stationery", "ballpoint": "stationery",
    "notebook": "stationery", "ruler": "stationery", "sticky_note": "stationery",
    "笔": "stationery", "铅笔": "stationery", "中性笔": "stationery",
    "圆珠笔": "stationery", "文具": "stationery", "便利贴": "stationery",
    # 运动器材 sports_equipment
    "sports_equipment": "sports_equipment", "sports": "sports_equipment",
    "basketball": "sports_equipment", "football": "sports_equipment",
    "badminton": "sports_equipment", "yoga_mat": "sports_equipment",
    "dumbbell": "sports_equipment", "jump_rope": "sports_equipment",
    "篮球": "sports_equipment", "足球": "sports_equipment",
    "羽毛球": "sports_equipment", "瑜伽垫": "sports_equipment",
    "哑铃": "sports_equipment", "跳绳": "sports_equipment",
    # 家具与宿舍用品 furniture
    "furniture": "furniture",
    "chair": "furniture", "desk": "furniture", "bookshelf": "furniture",
    "bed_side_table": "furniture", "closet": "furniture",
    "椅子": "furniture", "桌子": "furniture", "书桌": "furniture",
    "书架": "furniture", "床头柜": "furniture", "衣柜": "furniture",
    # 其他书籍/资料 other_books
    "other_books": "other_books", "books_other": "other_books",
    "novel": "other_books", "magazine": "other_books", "comic": "other_books",
    "小说": "other_books", "杂志": "other_books", "漫画": "other_books",
    "课外书": "other_books", "期刊": "other_books",
    # 其他 other
    "other": "other", "misc": "other", "miscellaneous": "other",
}

# 关键词包含匹配表：category_id -> [子串关键词]
# 用于 raw 未精确命中但包含特征词时（如 "高等数学教材第2版" 含 "教材"）
KEYWORD_MAP = {
    "textbook": ["教材", "课本", "高数", "线代", "考研", "textbook", "math"],
    "electronics": ["手机", "电脑", "平板", "相机", "电子", "phone", "laptop", "camera"],
    "digital_accessories": ["耳机", "充电", "数据线", "耳机", "charger", "earphone"],
    "life_goods": ["水杯", "台灯", "雨伞", "收纳", "cup", "lamp", "umbrella"],
    "clothing": ["衣", "短袖", "卫衣", "鞋", "裤", "jacket", "shirt", "cloth"],
    "stationery": ["笔", "文具", "便利贴", "pen", "notebook", "pencil"],
    "sports_equipment": ["篮球", "球拍", "羽毛球", "瑜伽", "哑铃", "跳绳", "basketball", "ball"],
    "furniture": ["椅子", "桌子", "书架", "床头", "衣柜", "chair", "desk", "furniture"],
    "other_books": ["小说", "杂志", "漫画", "课外", "novel", "magazine", "comic"],
}

# ---------------------------------------------------------------------------
# 内部工具
# ---------------------------------------------------------------------------

def _norm_key(raw):
    """规范化别名键：小写、去首尾空格、内部空格转下划线。"""
    return str(raw).strip().lower().replace(" ", "_")


# ---------------------------------------------------------------------------
# ② 核心标准化函数
# ---------------------------------------------------------------------------

def normalize(raw_label):
    """
    将 AI 识别原始标签 / 关键词标准化为统一类别。

    返回：
        {
            "category_id": str,          # 10 个一级类别之一
            "category_name": str,        # 类别中文名
            "confidence_adjust": float,  # 建议置信度调整量（fallback 为负）
            "matched_by": str,           # alias / keyword / fallback
        }
    """
    if raw_label is None or (isinstance(raw_label, str) and raw_label.strip() == ""):
        return _result("other", "fallback", adjust=-0.10)

    key = _norm_key(raw_label)

    # 1) 精确别名匹配
    if key in SYNONYM_MAP:
        cid = SYNONYM_MAP[key]
        return _result(cid, "alias", adjust=0.0)

    # 2) 关键词包含匹配
    for cid, keywords in KEYWORD_MAP.items():
        for kw in keywords:
            if kw in key:
                return _result(cid, "keyword", adjust=0.0)

    # 3) 未知兜底
    return _result("other", "fallback", adjust=-0.10)


def _result(category_id, matched_by, adjust):
    return {
        "category_id": category_id,
        "category_name": CATEGORY_NAMES.get(category_id, category_id),
        "confidence_adjust": adjust,
        "matched_by": matched_by,
    }


# ---------------------------------------------------------------------------
# ④ 与 Day2 price_engine / ai_client 的衔接
# ---------------------------------------------------------------------------

# Day4 统一类别 -> Day2 price_engine 类别ID 映射
DAY4_TO_ENGINE_MAP = {
    "textbook": "textbook",
    "electronics": "electronics",
    "life_goods": "life_goods",
    "clothing": "clothing",
    "stationery": "school_supplies",
    "digital_accessories": "digital_accessory",
    "sports_equipment": "sports",
    "furniture": "furniture",
    "other_books": "books_other",
    "other": "other",
}


def to_engine_category(category_id):
    """
    将 Day4 统一类别ID 映射为 Day2 price_engine 使用的类别ID。
    （Day2 引擎的折扣表使用 textbook/electronics/.../school_supplies/...）
    """
    return DAY4_TO_ENGINE_MAP.get(category_id, "other")


# ---------------------------------------------------------------------------
# 简易命令行自测入口
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    samples = ["Math Book", "高数教材", "iPhone", "耳机", "T-Shirt",
               "basketball", "小说", "unknown_xyz", "  水杯  ", None]
    for s in samples:
        print(repr(s), "->", normalize(s))
