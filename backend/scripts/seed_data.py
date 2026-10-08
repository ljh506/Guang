# -*- coding: utf-8 -*-
"""
拾光Agent · 演示数据导入脚本（成员A Day 3 整合）
================================================
读取 backend/data/ 下的 schools.csv / users.csv，写入后端 shiguang.db。

- 表结构遵循后端 SQLAlchemy 模型（schools / users，含 created_at）
- 支持重复运行：先清空再插入，保证幂等
- 依赖：仅 Python 标准库

运行方式（后端工程根目录 backend/）：
    python scripts/seed_data.py
"""
import csv
import os
import sqlite3
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "shiguang.db")
SCHOOLS_CSV = os.path.join(BASE_DIR, "data", "schools.csv")
USERS_CSV = os.path.join(BASE_DIR, "data", "users.csv")


def _parse_dt(s: str) -> str:
    """CSV 中的 created_at 字符串直接使用（ISO 文本）。"""
    return s.strip()


def _load_csv(path: str):
    with open(path, "r", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def main() -> int:
    for p in (SCHOOLS_CSV, USERS_CSV):
        if not os.path.exists(p):
            print("[错误] 缺少数据文件:", p)
            return 1

    schools = _load_csv(SCHOOLS_CSV)
    users = _load_csv(USERS_CSV)

    conn = sqlite3.connect(DB_PATH)
    try:
        # 幂等：先清空再插入（created_at 由 SQLAlchemy 在首次 insert 时生成）
        conn.execute("DELETE FROM users")
        conn.execute("DELETE FROM schools")

        now = datetime.now().isoformat(timespec="seconds")

        for row in schools:
            conn.execute(
                "INSERT INTO schools (id, name, latitude, longitude, created_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (int(row["id"]), row["name"].strip(),
                 float(row["latitude"]), float(row["longitude"]), now),
            )

        for row in users:
            conn.execute(
                "INSERT INTO users (id, nickname, avatar, school_id, created_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (int(row["id"]), row["nickname"].strip(),
                 row["avatar"].strip() or None,
                 int(row["school_id"]), _parse_dt(row["created_at"])),
            )

        conn.commit()

        n_school = conn.execute("SELECT COUNT(*) FROM schools").fetchone()[0]
        n_user = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        print(f"数据库文件: {DB_PATH}")
        print(f"School 导入: {n_school} 条")
        print(f"User 导入:   {n_user} 条")
        print()
        print("--- School 预览 ---")
        for r in conn.execute("SELECT id, name, latitude, longitude FROM schools ORDER BY id"):
            print(" ", r)
        print("--- User 预览 ---")
        for r in conn.execute("SELECT id, nickname, school_id, created_at FROM users ORDER BY id"):
            print(" ", r)
    finally:
        conn.close()

    print()
    print("导入完成。可继续 Day4~Day13 数据扩展。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
