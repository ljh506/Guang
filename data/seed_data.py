# -*- coding: utf-8 -*-
"""
拾光Agent · 演示数据初始化脚本（成员B Day 3 交付）
====================================================
按计划书数据表结构创建 School / User 表，并导入演示数据。

- 数据库：shiguang_demo.db（生成于本脚本所在目录）
- 支持重复运行：每次执行先 DROP 再 CREATE，随后导入，保证幂等
- 运行后打印导入结果

运行方式：
    python seed_data.py

依赖：仅 Python 标准库（sqlite3 / csv）
"""

import csv
import os
import sqlite3

# 脚本所在目录（保证从任意 cwd 运行都能找到数据文件与输出数据库）
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "shiguang_demo.db")
SCHOOLS_CSV = os.path.join(BASE_DIR, "demo_schools.csv")
USERS_CSV = os.path.join(BASE_DIR, "demo_users.csv")


def create_tables(conn):
    """创建 School / User 表（字段与计划书数据表一致）。"""
    conn.executescript("""
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
    """)


def load_csv(path):
    """读取 CSV 为 dict 列表。"""
    with open(path, "r", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def seed_schools(conn, rows):
    conn.executemany(
        "INSERT INTO school (id, name, latitude, longitude) "
        "VALUES (:id, :name, :latitude, :longitude)",
        rows,
    )


def seed_users(conn, rows):
    conn.executemany(
        "INSERT INTO user (id, nickname, avatar, school_id, created_at) "
        "VALUES (:id, :nickname, :avatar, :school_id, :created_at)",
        rows,
    )


def main():
    # 校验数据文件存在
    for p in (SCHOOLS_CSV, USERS_CSV):
        if not os.path.exists(p):
            print("[错误] 缺少数据文件:", p)
            return 1

    schools = load_csv(SCHOOLS_CSV)
    users = load_csv(USERS_CSV)

    conn = sqlite3.connect(DB_PATH)
    try:
        create_tables(conn)
        seed_schools(conn, schools)
        seed_users(conn, users)
        conn.commit()

        # 打印导入结果
        n_schools = conn.execute("SELECT COUNT(*) FROM school").fetchone()[0]
        n_users = conn.execute("SELECT COUNT(*) FROM user").fetchone()[0]
        print("数据库文件:", DB_PATH)
        print("School 导入: {n} 条".format(n=n_schools))
        print("User 导入: {n} 条".format(n=n_users))
        print()
        print("--- School 预览 ---")
        for row in conn.execute("SELECT id, name, latitude, longitude FROM school ORDER BY id"):
            print(row)
        print("--- User 预览 ---")
        for row in conn.execute("SELECT id, nickname, school_id, created_at FROM user ORDER BY id"):
            print(row)
    finally:
        conn.close()

    print()
    print("导入完成，可继续供 Day 13 演示数据（商品/交换/聊天）扩展使用。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
