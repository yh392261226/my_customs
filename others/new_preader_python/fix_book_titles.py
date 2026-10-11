#!/usr/bin/env python3
"""
书籍标题清洗脚本（一次性运行）。

爬取落盘的文件名形如「来源网站_书名.txt」，早期在「导入/扫描」流程中
会把文件名（含网站前缀）当成书名写进数据库，导致：
    - books.title       出现「网站名_书名」前缀（少量）
    - crawl_history.    出现「书名 - 网站名」后缀（较多，爬取管理页读取）
本脚本把数据库里的书名清洗为纯「书名」：
    - 去掉开头的「网站名_」前缀
    - 去掉结尾的「 - 网站名」/「_网站名」后缀
同时同步重建 books.pinyin（用于搜索）。

用法：
    # 先预览将要修改的行（不修改数据库）
    python fix_book_titles.py --dry-run

    # 真正执行
    python fix_book_titles.py

    # 自定义数据库路径
    python fix_book_titles.py --db ~/.config/new_preader/database.sqlite
"""
import argparse
import os
import sqlite3
import sys

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.config.config_manager import ConfigManager
from src.core.database_manager import convert_to_pinyin


def parse_args():
    parser = argparse.ArgumentParser(description="书籍标题清洗脚本（去除网站名前缀/后缀）")
    parser.add_argument("--dry-run", action="store_true", help="仅预览，不修改数据库")
    parser.add_argument("--db", default=None, help="数据库文件路径（默认读取配置）")
    return parser.parse_args()


def get_db_path():
    if args.db:
        return os.path.expanduser(args.db)
    config = ConfigManager.get_instance().get_config()
    db_path = config.get("paths", {}).get("database")
    return os.path.expanduser(db_path) if db_path else None


def load_site_names(con):
    cur = con.cursor()
    try:
        cur.execute("SELECT name FROM novel_sites")
        return [r[0] for r in cur.fetchall() if r[0]]
    except Exception:
        return []


def clean_title(title, site_names):
    """去掉标题中开头的「网站名_」前缀与结尾的「 - 网站名」/「_网站名」后缀。

    返回 (清洗后标题, 是否发生改动)。
    """
    t = title or ""
    original = t
    # 去开头前缀：网站名_
    for s in site_names:
        if t.startswith(s + "_"):
            t = t[len(s) + 1:]
            break
    # 去结尾后缀： - 网站名 或 _网站名
    for s in site_names:
        if not s:
            continue
        for sep in (" - ", "_"):
            suf = sep + s
            if t.endswith(suf):
                t = t[: -len(suf)]
                break
        if t != original:
            break
    if not t:
        return original, (t != original)
    return t, (t != original)


def main():
    db_path = get_db_path()
    if not db_path or not os.path.isfile(db_path):
        print(f"未找到数据库文件: {db_path}")
        return
    print(f"数据库: {db_path}")

    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    site_names = load_site_names(con)
    print(f"已加载网站名 {len(site_names)} 个")

    # ---- books.title / pinyin ----
    cur = con.cursor()
    cur.execute("SELECT path, title, pinyin FROM books")
    rows = cur.fetchall()
    books_changed = 0
    for row in rows:
        path, title, old_pinyin = row["path"], row["title"], row["pinyin"]
        new_title, changed = clean_title(title, site_names)
        if not changed:
            continue
        new_pinyin = convert_to_pinyin(new_title) if old_pinyin is not None else None
        books_changed += 1
        if args.dry_run:
            print(f"[预览 books] {title!r} -> {new_title!r}")
            continue
        cur.execute(
            "UPDATE books SET title = ?, pinyin = ? WHERE path = ?",
            (new_title, new_pinyin, path),
        )

    # ---- crawl_history.novel_title ----
    try:
        cur.execute("SELECT id, novel_title FROM crawl_history")
        ch_rows = cur.fetchall()
    except Exception:
        ch_rows = []
    ch_changed = 0
    for row in ch_rows:
        rid, novel_title = row["id"], row["novel_title"]
        new_title, changed = clean_title(novel_title, site_names)
        if not changed:
            continue
        ch_changed += 1
        if args.dry_run:
            print(f"[预览 crawl_history] {novel_title!r} -> {new_title!r}")
            continue
        cur.execute(
            "UPDATE crawl_history SET novel_title = ? WHERE id = ?",
            (new_title, rid),
        )

    if not args.dry_run:
        con.commit()
    con.close()

    print("-" * 60)
    print(f"结果: books 修改 {books_changed} 条, crawl_history 修改 {ch_changed} 条"
          + (" (dry-run, 未实际修改)" if args.dry_run else " (已提交)"))
    if not args.dry_run and (books_changed or ch_changed):
        print("提示: 修改后建议在应用内「设置 -> 重建全文搜索索引」一次。")


if __name__ == "__main__":
    args = parse_args()
    main()
