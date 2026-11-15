#!/usr/bin/env python3
"""修复书库书名(books.title)与爬取管理书名(crawl_history.novel_title)不一致的历史数据。

默认只预览，不写库。书库中大量书名与爬取管理不同是入库时一方用网页原书名、
另一方用文件名推导名造成的（非法字符替换、站点名/ID 后缀、截断等），并非改名
没同步，因此 --apply 必须显式指定修复范围，避免把干净书名批量覆盖掉。

用法：
    # 查看统计与前 20 条差异
    python scripts/repair_book_titles.py

    # 按爬取历史 ID 精确修复（默认以爬取管理的名称为准）
    python scripts/repair_book_titles.py --ids 133205,133207 --apply --backup

    # 按书名/路径关键词筛选后修复
    python scripts/repair_book_titles.py --match 张汤 --apply --backup

    # 反向：以书库名称为准更新爬取管理
    python scripts/repair_book_titles.py --ids 133205 --direction books --apply

    # 明确要修复全部差异时才用（会包含文件名字符替换类差异）
    python scripts/repair_book_titles.py --all --apply --backup
"""
from __future__ import annotations

import argparse
import os
import re
import sqlite3
import sys
from datetime import datetime
from typing import Any, Dict, List

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from src.core.database_manager import DatabaseManager, convert_to_pinyin  # noqa: E402

FILENAME_ILLEGAL = re.compile(r'[\\/:*?"<>|]')
LABELS = {
    "filename_chars": "文件名非法字符替换",
    "filename_stem": "文件名推导",
    "truncated": "文件名截断",
    "suffix": "站点名/ID 后缀",
    "prefix": "站点名前缀",
    "renamed": "疑似改名未同步",
}


def _is_placeholder(title: str, novel_id: str) -> bool:
    """占位/无效标题不能作为权威书名覆盖书库。"""
    title = (title or "").strip()
    if not title:
        return True
    if title.startswith(("书籍ID:", "书籍ID：")):
        return True
    if title == str(novel_id or "").strip():
        return True
    return False


def _category(path: str, book_title: str, crawl_title: str) -> str:
    """区分「入库时取名来源不同」和「改名没同步」两类差异。"""
    if FILENAME_ILLEGAL.sub("_", book_title) == crawl_title:
        return "filename_chars"
    if crawl_title == os.path.splitext(os.path.basename(path))[0]:
        return "filename_stem"
    if crawl_title.endswith(("...", "…")):
        return "truncated"
    if crawl_title.startswith(book_title) and re.fullmatch(r"_\S+", crawl_title[len(book_title):]):
        return "suffix"
    if crawl_title.endswith(book_title) and re.fullmatch(r"\S+_", crawl_title[:-len(book_title)]):
        return "prefix"
    return "renamed"


def collect_mismatches(db_path: str) -> List[Dict[str, Any]]:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            """
            SELECT b.path AS path,
                   b.title AS book_title,
                   h.novel_title AS crawl_title,
                   h.novel_id AS novel_id,
                   h.id AS history_id
            FROM books AS b
            JOIN crawl_history AS h ON h.file_path = b.path
            WHERE h.status = 'success' AND b.title <> h.novel_title
            ORDER BY b.path, h.id DESC
            """
        ).fetchall()
    finally:
        conn.close()

    mismatches: List[Dict[str, Any]] = []
    seen = set()
    for row in rows:
        path = row["path"]
        if path in seen:
            continue
        seen.add(path)
        if _is_placeholder(row["crawl_title"], row["novel_id"]):
            continue
        mismatches.append({
            "path": path,
            "book_title": row["book_title"],
            "crawl_title": row["crawl_title"],
            "history_id": row["history_id"],
            "category": _category(path, row["book_title"], row["crawl_title"]),
        })
    return mismatches


def apply_fixes(db_path: str, items: List[Dict[str, Any]], direction: str) -> int:
    conn = sqlite3.connect(db_path)
    try:
        with conn:
            for item in items:
                if direction == "crawl":
                    conn.execute(
                        "UPDATE books SET title = ?, pinyin = ? WHERE path = ?",
                        (item["crawl_title"], convert_to_pinyin(item["crawl_title"]), item["path"]),
                    )
                else:
                    conn.execute(
                        "UPDATE crawl_history SET novel_title = ? WHERE file_path = ?",
                        (item["book_title"], item["path"]),
                    )
        return len(items)
    finally:
        conn.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="修复书库与爬取管理书名不一致")
    parser.add_argument("--apply", action="store_true", help="实际写库；默认仅预览")
    parser.add_argument("--backup", action="store_true", help="写库前复制一份数据库备份")
    parser.add_argument("--db", default=None, help="数据库路径，默认使用应用配置中的路径")
    parser.add_argument("--ids", default="", help="逗号分隔的爬取历史 ID，精确指定要修复的书")
    parser.add_argument("--match", action="append", default=[],
                        help="书名/路径关键词，可重复；与 --ids 同时使用时取交集")
    parser.add_argument("--all", action="store_true", help="修复全部差异（慎用，含文件名字符替换类）")
    parser.add_argument("--direction", choices=("crawl", "books"), default="crawl",
                        help="crawl=以爬取管理为准改书库（默认）；books=以书库为准改爬取管理")
    parser.add_argument("--limit", type=int, default=20, help="预览时最多显示的条数，默认 20")
    args = parser.parse_args()

    db = DatabaseManager(args.db) if args.db else DatabaseManager()
    db_path = db.get_db_path()
    items = collect_mismatches(db_path)

    print(f"数据库: {db_path}")
    print(f"书名不一致: {len(items)} 本")
    counts: Dict[str, int] = {}
    for item in items:
        counts[item["category"]] = counts.get(item["category"], 0) + 1
    print("分类: " + ", ".join(f"{LABELS[k]}={counts[k]}" for k in LABELS if k in counts))

    scoped = bool(args.ids or args.match or args.all)
    if args.all:
        selected = items
    else:
        selected = items
        if args.ids:
            ids = {int(part) for part in args.ids.split(",") if part.strip()}
            selected = [i for i in selected if i["history_id"] in ids]
        for keyword in args.match:
            selected = [i for i in selected
                        if keyword in i["book_title"] or keyword in i["crawl_title"] or keyword in i["path"]]

    if args.apply and not scoped:
        parser.error("请先用 --ids 或 --match 指定要修复的书籍，确认无误后也可显式使用 --all")

    print(f"本次范围: {len(selected)} 本，方向: "
          f"{'爬取管理 → 书库' if args.direction == 'crawl' else '书库 → 爬取管理'}")
    for i, item in enumerate(selected[:args.limit], 1):
        print(f"{i:>3}. [id={item['history_id']}][{LABELS[item['category']]}]")
        print(f"     书库: {item['book_title']}")
        print(f"     爬取管理: {item['crawl_title']}")
        print(f"     文件: {item['path']}")
    if len(selected) > args.limit:
        print(f"     ... 另有 {len(selected) - args.limit} 本未显示（用 --limit 调整）")

    if not selected:
        return 0
    if not args.apply:
        print("\n预览模式（未修改数据库）。确认后加 --apply --backup 执行修复。")
        return 0

    if args.backup:
        import shutil
        backup_path = f"{db_path}.bak-{datetime.now():%Y%m%d_%H%M%S}"
        shutil.copy2(db_path, backup_path)
        print(f"已备份数据库: {backup_path}")

    changed = apply_fixes(db_path, selected, args.direction)
    print(f"已修复 {changed} 本；请重启或刷新书库页面查看。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
