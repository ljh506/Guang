# -*- coding: utf-8 -*-
"""
拾光Agent · 演示数据生成脚本 demo_data.py（成员B Day 13 交付）
================================================================
任务来源：项目计划书「十五、五人团队逐日开发任务表」Day 13 行，成员B 当日任务
「准备AI识别和估价演示案例」（当天目标：比赛Demo数据与演示）。

本脚本生成比赛演示所需的完整数据（衔接 Day3 已完成的学校/用户数据）：

- school   : 7 所学校（读取 Day3 demo_schools.csv；文件缺失时内置回退）
- user     : 5 个演示用户（读取 Day3 demo_users.csv；文件缺失时内置回退）
- goods    : 20 个演示商品（覆盖教材/电子产品/生活用品/衣物/文具/数码配件/
             运动器材/家具/其他书籍等类别）
- user_wish: 各用户想要的物品类别（衔接 Day9 match_engine 的 wish 意愿）
- exchange : 3 组交换关系（negotiating / confirmed 状态，双方确认标记）
- chat     : 3 组交换对应的聊天记录（文案风格衔接 Day8 快捷消息模板）

生成数据库：shiguang_demo_full.db（本脚本所在目录，幂等重建）。
与 Day3 数据库的衔接：优先读取 Day3 交付目录的 CSV/DB 保持一致的用户与学校；
若 Day3 数据不可用则使用内置同等数据回退，保证演示可独立运行。

依赖：仅标准库（sqlite3 / csv / os / sys）。
"""

import csv
import os
import sqlite3
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(HERE, "shiguang_demo_full.db")

# Day3 交付目录（学校/用户 CSV 来源）
DAY3_DIR = r"C:\Users\LENOVO\Desktop\拾光Agent\成员B_Day3_交付"
SCHOOLS_CSV = os.path.join(DAY3_DIR, "demo_schools.csv")
USERS_CSV = os.path.join(DAY3_DIR, "demo_users.csv")

# ---------------------------------------------------------------------------
# 内置回退数据（Day3 CSV 缺失时使用，与 Day3 保持一致）
# ---------------------------------------------------------------------------
FALLBACK_SCHOOLS = [
    {"id": 1, "name": "清华大学", "latitude": 39.9993, "longitude": 116.3261},
    {"id": 2, "name": "北京大学", "latitude": 39.9890, "longitude": 116.3062},
    {"id": 3, "name": "浙江大学", "latitude": 30.2634, "longitude": 120.1193},
    {"id": 4, "name": "复旦大学", "latitude": 31.2974, "longitude": 121.5033},
    {"id": 5, "name": "武汉大学", "latitude": 30.5360, "longitude": 114.3600},
    {"id": 6, "name": "中山大学", "latitude": 23.0970, "longitude": 113.2920},
    {"id": 7, "name": "四川大学", "latitude": 30.6301, "longitude": 104.0910},
]

FALLBACK_USERS = [
    {"id": 1, "nickname": "拾光少女小鹿", "avatar": "static/avatars/u1.png", "school_id": 1,
     "created_at": "2026-09-01 09:30:00"},
    {"id": 2, "nickname": "二手书生阿泽", "avatar": "static/avatars/u2.png", "school_id": 2,
     "created_at": "2026-09-01 10:15:00"},
    {"id": 3, "nickname": "橙子不吃皮", "avatar": "static/avatars/u3.png", "school_id": 3,
     "created_at": "2026-09-02 14:40:00"},
    {"id": 4, "nickname": "学霸笔记侠", "avatar": "static/avatars/u4.png", "school_id": 4,
     "created_at": "2026-09-03 08:20:00"},
    {"id": 5, "nickname": "操场边的猫", "avatar": "static/avatars/u5.png", "school_id": 5,
     "created_at": "2026-09-04 16:05:00"},
]

# ---------------------------------------------------------------------------
# 演示商品（20 个，覆盖主要类别；asking_price 为用户手填真实标价，
# 与 Day9 匹配算法「价格维度唯一依据」约定一致）
# ---------------------------------------------------------------------------
DEMO_GOODS = [
    # id, user_id, name, category_id, condition, original_price, months_used, is_free, asking_price, status, publish_time, description
    (1, 1, "高等数学（上）教材", "textbook", "good", 68, None, 0, 30, "on_sale", 10, "同济版，笔记齐全，无破损"),
    (2, 1, "保温杯 500ml", "life_goods", "new_like", 89, None, 0, 45, "on_sale", 12, "膳魔师同款，九成新"),
    (3, 1, "羽毛球拍", "sports_equipment", "good", 120, None, 0, 60, "on_sale", 15, "碳素拍，含拍线"),
    (4, 1, "线性代数教材", "textbook", "fair", 45, None, 0, 18, "on_sale", 18, "有少量笔记"),
    (5, 1, "便携小风扇", "electronics", "good", 35, 8, 0, 20, "on_sale", 20, "USB充电，风量三档"),

    (6, 2, "大学物理教材", "textbook", "good", 72, None, 0, 32, "on_sale", 22, "第7版，几乎全新"),
    (7, 2, "折叠自行车", "life_goods", "good", 499, None, 0, 280, "on_sale", 25, "20寸，骑行半年"),
    (8, 2, "LED 台灯", "electronics", "new_like", 129, 4, 0, 60, "on_sale", 28, "三档调光，护眼"),
    (9, 5, "考研政治复习资料", "other_books", "good", 49, None, 0, 22, "on_sale", 30, "肖秀荣1000题，笔记少"),
    (10, 2, "机械键盘", "digital_accessories", "good", 199, 10, 0, 110, "on_sale", 32, "青轴，87键"),

    (11, 3, "数位板 Wacom", "digital_accessories", "good", 399, 14, 0, 220, "on_sale", 35, "CTL-672，压感灵敏"),
    (12, 3, "帆布鞋 38码", "clothing", "new_like", 149, None, 0, 70, "on_sale", 38, "匡威经典款"),
    (13, 3, "高数习题集", "other_books", "good", 35, None, 0, 15, "on_sale", 40, "同济版配套"),
    (14, 3, "榨汁杯", "life_goods", "good", 99, 6, 0, 40, "on_sale", 42, "充电便携款"),

    (15, 4, "24寸显示器", "electronics", "good", 799, 18, 0, 450, "on_sale", 45, "IPS 1080P，无坏点"),
    (16, 4, "四级真题试卷", "textbook", "new_like", 39, None, 0, 20, "on_sale", 48, "2026版，含听力"),
    (17, 4, "收纳盒三件套", "furniture", "new_like", 49, None, 0, 25, "on_sale", 50, "宿舍桌面整理"),
    (18, 4, "蓝牙耳机", "digital_accessories", "fair", 99, 20, 0, 50, "on_sale", 52, "续航正常"),

    (19, 5, "运动跑鞋 42码", "clothing", "good", 299, None, 0, 150, "on_sale", 55, "亚瑟士入门款"),
    (20, 5, "木吉他 41寸", "other", "good", 699, None, 0, 380, "on_sale", 58, "云杉面板，含琴包"),
]

# 用户意愿（wish_category_id：用户想换到的物品类别；衔接 Day9 匹配算法）
DEMO_WISHES = {
    1: ["textbook", "sports_equipment", "clothing"],  # 小鹿：想收教材、运动器材、衣物
    2: ["textbook", "digital_accessories"],  # 阿泽：想收教材、数码配件
    3: ["digital_accessories", "electronics"],  # 橙子：想收数码、电子
    4: ["textbook", "electronics", "digital_accessories"],  # 笔记侠：想收教材、电子、数码
    5: ["clothing", "sports_equipment"],   # 操场猫：想收衣物、运动器材
}

# 3 组交换关系（goods_a / goods_b 对应 goods.id）
# EX1：小鹿高数教材 ↔ 阿泽大学物理（双向意愿、价格接近）
# EX2：橙子数位板 ↔ 笔记侠显示器（双向意愿、价格有差距但类别命中）
# EX3：操场猫运动跑鞋 ↔ 小鹿羽毛球拍（单向意愿、运动/衣物互需）
DEMO_EXCHANGES = [
    {"id": 1, "user_a_id": 1, "user_b_id": 2, "goods_a_id": 1, "goods_b_id": 6,
     "state": "negotiating", "confirm_a": 1, "confirm_b": 1,
     "created_at": "2026-10-15 10:00:00"},
    {"id": 2, "user_a_id": 3, "user_b_id": 4, "goods_a_id": 11, "goods_b_id": 15,
     "state": "negotiating", "confirm_a": 1, "confirm_b": 0,
     "created_at": "2026-10-15 14:20:00"},
    {"id": 3, "user_a_id": 5, "user_b_id": 1, "goods_a_id": 19, "goods_b_id": 3,
     "state": "confirmed", "confirm_a": 1, "confirm_b": 1,
     "created_at": "2026-10-16 09:30:00"},
]

# 聊天记录（exchange_id, sender_id, receiver_id, msg_key, text, created_at）
DEMO_CHATS = [
    (1, 2, 1, "want", "你好，我想要这个，还在吗？", "2026-10-15 10:02:00"),
    (1, 1, 2, "want_available", "还在的，可以拍给你看～", "2026-10-15 10:03:00"),
    (1, 2, 1, "swap_suggest", "我有一件物品想和你交换，可以看看吗？", "2026-10-15 10:05:00"),
    (1, 1, 2, "swap_confirm", "可以，交换吧～", "2026-10-15 10:08:00"),
    (1, 2, 1, "meet_place", "校内哪里见面交易？", "2026-10-15 10:10:00"),

    (2, 3, 4, "want", "你好，我想要这个，还在吗？", "2026-10-15 14:25:00"),
    (2, 4, 3, "want_available", "还在的，可以拍给你看～", "2026-10-15 14:26:00"),
    (2, 4, 3, "price_negotiate", "价格可以再商量一下吗？", "2026-10-15 14:30:00"),
    (2, 3, 4, "price_offer", "我出 420 元，你看可以吗？", "2026-10-15 14:32:00"),

    (3, 5, 1, "swap_suggest", "我有一件物品想和你交换，可以看看吗？", "2026-10-16 09:35:00"),
    (3, 1, 5, "swap_show", "可以，我把我的物品发给你看看～", "2026-10-16 09:38:00"),
    (3, 5, 1, "swap_confirm", "可以，交换吧～", "2026-10-16 09:40:00"),
    (3, 1, 5, "confirm_deal", "确认交易，谢谢！", "2026-10-16 09:42:00"),
    (3, 5, 1, "complete_feedback", "交易完成，祝你使用愉快！", "2026-10-16 09:45:00"),
]


def _load_csv_or_fallback(csv_path, fallback):
    """读取 CSV（utf-8-sig）；文件缺失/为空时回退内置数据。"""
    if os.path.exists(csv_path):
        try:
            with open(csv_path, "r", encoding="utf-8-sig") as f:
                rows = list(csv.DictReader(f))
            if rows:
                return rows
        except (OSError, csv.Error):
            pass
    return [dict(r) for r in fallback]


def _schools_rows():
    raw = _load_csv_or_fallback(SCHOOLS_CSV, FALLBACK_SCHOOLS)
    rows = []
    for r in raw:
        rows.append({
            "id": int(r["id"]), "name": r["name"],
            "latitude": float(r["latitude"]), "longitude": float(r["longitude"]),
        })
    return rows


def _users_rows():
    raw = _load_csv_or_fallback(USERS_CSV, FALLBACK_USERS)
    rows = []
    for r in raw:
        rows.append({
            "id": int(r["id"]), "nickname": r["nickname"], "avatar": r["avatar"],
            "school_id": int(r["school_id"]), "created_at": r["created_at"],
        })
    return rows


def create_tables(conn):
    conn.executescript("""
    DROP TABLE IF EXISTS chat;
    DROP TABLE IF EXISTS exchange;
    DROP TABLE IF EXISTS user_wish;
    DROP TABLE IF EXISTS goods;
    DROP TABLE IF EXISTS user;
    DROP TABLE IF EXISTS school;

    CREATE TABLE school (
        id         INTEGER PRIMARY KEY,
        name       TEXT    NOT NULL,
        latitude   REAL    NOT NULL,
        longitude  REAL    NOT NULL
    );

    CREATE TABLE user (
        id         INTEGER PRIMARY KEY,
        nickname   TEXT    NOT NULL,
        avatar     TEXT,
        school_id  INTEGER NOT NULL,
        created_at TEXT    NOT NULL,
        FOREIGN KEY (school_id) REFERENCES school (id)
    );

    CREATE TABLE goods (
        id             INTEGER PRIMARY KEY,
        user_id        INTEGER NOT NULL,
        name           TEXT    NOT NULL,
        category_id    TEXT    NOT NULL,
        condition      TEXT    NOT NULL,
        original_price REAL    NOT NULL,
        months_used    INTEGER,
        is_free        INTEGER NOT NULL DEFAULT 0,
        asking_price   REAL    NOT NULL,
        status         TEXT    NOT NULL DEFAULT 'on_sale',
        publish_time   INTEGER,
        description    TEXT,
        FOREIGN KEY (user_id) REFERENCES user (id)
    );

    CREATE TABLE user_wish (
        user_id         INTEGER NOT NULL,
        wish_category_id TEXT   NOT NULL,
        FOREIGN KEY (user_id) REFERENCES user (id)
    );

    CREATE TABLE exchange (
        id          INTEGER PRIMARY KEY,
        user_a_id   INTEGER NOT NULL,
        user_b_id   INTEGER NOT NULL,
        goods_a_id  INTEGER NOT NULL,
        goods_b_id  INTEGER NOT NULL,
        state       TEXT    NOT NULL DEFAULT 'negotiating',
        confirm_a   INTEGER NOT NULL DEFAULT 0,
        confirm_b   INTEGER NOT NULL DEFAULT 0,
        created_at  TEXT    NOT NULL,
        FOREIGN KEY (user_a_id) REFERENCES user (id),
        FOREIGN KEY (user_b_id) REFERENCES user (id),
        FOREIGN KEY (goods_a_id) REFERENCES goods (id),
        FOREIGN KEY (goods_b_id) REFERENCES goods (id)
    );

    CREATE TABLE chat (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        exchange_id INTEGER NOT NULL,
        sender_id   INTEGER NOT NULL,
        receiver_id INTEGER NOT NULL,
        msg_key     TEXT,
        text        TEXT    NOT NULL,
        created_at  TEXT    NOT NULL,
        FOREIGN KEY (exchange_id) REFERENCES exchange (id)
    );
    """)


def seed_all(conn):
    schools = _schools_rows()
    users = _users_rows()

    conn.executemany(
        "INSERT INTO school (id, name, latitude, longitude) "
        "VALUES (:id, :name, :latitude, :longitude)", schools)
    conn.executemany(
        "INSERT INTO user (id, nickname, avatar, school_id, created_at) "
        "VALUES (:id, :nickname, :avatar, :school_id, :created_at)", users)

    conn.executemany(
        "INSERT INTO goods (id, user_id, name, category_id, condition, "
        "original_price, months_used, is_free, asking_price, status, "
        "publish_time, description) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", DEMO_GOODS)

    wish_rows = []
    for uid, cats in DEMO_WISHES.items():
        for c in cats:
            wish_rows.append((uid, c))
    conn.executemany(
        "INSERT INTO user_wish (user_id, wish_category_id) VALUES (?, ?)",
        wish_rows)

    conn.executemany(
        "INSERT INTO exchange (id, user_a_id, user_b_id, goods_a_id, "
        "goods_b_id, state, confirm_a, confirm_b, created_at) "
        "VALUES (:id, :user_a_id, :user_b_id, :goods_a_id, :goods_b_id, "
        ":state, :confirm_a, :confirm_b, :created_at)", DEMO_EXCHANGES)

    conn.executemany(
        "INSERT INTO chat (exchange_id, sender_id, receiver_id, msg_key, "
        "text, created_at) VALUES (?, ?, ?, ?, ?, ?)", DEMO_CHATS)

    return {"schools": len(schools), "users": len(users),
            "goods": len(DEMO_GOODS), "wishes": len(wish_rows),
            "exchanges": len(DEMO_EXCHANGES), "chats": len(DEMO_CHATS)}


def build_demo_db(db_path=None):
    """
    生成完整演示数据库，返回 {counts, db_path}。

    参数：db_path 可指定输出路径，默认本模块同目录 shiguang_demo_full.db。
    幂等：每次重建全部表。
    """
    target = db_path or DB_PATH
    conn = sqlite3.connect(target)
    try:
        create_tables(conn)
        counts = seed_all(conn)
        conn.commit()
    finally:
        conn.close()
    counts["db_path"] = target
    return counts


def main():
    print("拾光Agent · 演示数据生成（Day13）")
    counts = build_demo_db()
    print("数据库：%s" % counts["db_path"])
    for key in ("schools", "users", "goods", "wishes", "exchanges", "chats"):
        print("  %-10s: %d" % (key, counts[key]))
    if counts["schools"] < 7 or counts["users"] != 5 or counts["goods"] != 20 \
            or counts["exchanges"] != 3 or counts["chats"] < 9:
        print("[错误] 演示数据数量不符合验收要求（7校/5用户/20商品/3交换/聊天记录）")
        return 1
    print("演示数据满足验收要求：7所学校 / 5个用户 / 20个商品 / 3组交换 / %d 条聊天记录" % counts["chats"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
