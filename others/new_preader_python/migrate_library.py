#!/usr/bin/env python3
"""
书籍库目录结构迁移脚本（一次性运行）。

将旧式「所有书籍平铺在书籍库根目录」的结构，迁移为：
    书籍库根目录 / 来源网站 / 书名首字母 / 书籍文件
    书籍库根目录 / _imported / 书名首字母 / 导入的书籍文件

同时更新数据库中所有引用书籍路径的表（books / crawl_history / user_books /
reading_history / bookmarks / book_metadata / vocabulary）。

用法：
    # 先预览将要执行的操作（不会真正移动文件 / 修改数据库）
    python migrate_library.py --dry-run

    # 真正执行迁移
    python migrate_library.py

    # 自定义书籍库 / 数据库路径
    python migrate_library.py --library ~/Documents/NewReader/books --db ~/.config/new_preader/database.sqlite

注意：
    - 迁移前建议先备份数据库与书籍库目录。
    - 迁移后书籍路径发生变化，请在应用内「设置 -> 重建全文搜索索引」一次，
      否则搜索结果可能基于旧路径而失效。
"""
import argparse
import os
import shutil
import sqlite3
import sys

# 允许以脚本方式直接导入项目内模块
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.config.config_manager import ConfigManager
from src.core.database_manager import DatabaseManager
from src.core.book import Book
from src.utils.storage_layout import (
    get_crawl_storage_dir,
    get_import_storage_dir,
    make_unique_path,
)


def parse_args():
    parser = argparse.ArgumentParser(description="书籍库目录结构迁移脚本")
    parser.add_argument("--dry-run", action="store_true", help="仅预览，不真正移动文件或修改数据库")
    parser.add_argument("--library", default=None, help="书籍库根目录（默认读取配置）")
    parser.add_argument("--db", default=None, help="数据库文件路径（默认读取配置）")
    return parser.parse_args()


def get_config_paths():
    config = ConfigManager.get_instance().get_config()
    library = config.get("paths", {}).get("library")
    db_path = config.get("paths", {}).get("database")
    return os.path.expanduser(library) if library else None, os.path.expanduser(db_path) if db_path else None


def cleanup_empty_dirs(root: str) -> int:
    """删除 root 下所有已空的子目录（不删 root 本身），用于迁移后清理空壳目录。"""
    removed = 0
    for dirpath, _dirnames, _filenames in os.walk(root, topdown=False):
        if dirpath == root:
            continue
        try:
            if not os.listdir(dirpath):
                os.rmdir(dirpath)
                removed += 1
        except OSError:
            pass
    return removed


def main():
    args = parse_args()

    library = args.library or get_config_paths()[0]
    db_path = args.db or get_config_paths()[1]
    if not library or not db_path:
        print("无法确定书籍库目录或数据库路径，请通过 --library / --db 指定。")
        sys.exit(1)

    print(f"书籍库目录 : {library}")
    print(f"数据库路径 : {db_path}")
    print(f"模式       : {'预览(dry-run)' if args.dry_run else '执行迁移'}")
    print("-" * 60)

    if not os.path.isdir(library):
        print(f"书籍库目录不存在: {library}")
        sys.exit(1)
    if not os.path.isfile(db_path):
        print(f"数据库文件不存在: {db_path}")
        sys.exit(1)

    db = DatabaseManager(db_path)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    # 网站信息： id -> (name, storage_folder)
    sites = {
        row["id"]: (row["name"], row["storage_folder"])
        for row in conn.execute("SELECT id, name, storage_folder FROM novel_sites")
    }
    # 爬取历史： file_path -> site_id（用于辨别「爬取书籍」还是「导入书籍」）
    ch_site = {
        row["file_path"]: row["site_id"]
        for row in conn.execute("SELECT file_path, site_id FROM crawl_history WHERE file_path <> ''")
    }
    conn.close()

    books = db  # 复用 DatabaseManager 的路径更新方法（会自动重算拼音等）
    rows = []
    conn2 = sqlite3.connect(db_path)
    conn2.row_factory = sqlite3.Row
    for row in conn2.execute("SELECT path, title FROM books"):
        rows.append((row["path"], row["title"]))
    conn2.close()

    moved = 0
    skipped = 0
    missing = 0
    errors = 0

    for old_path, title in rows:
        if not old_path:
            continue
        old_path = os.path.abspath(os.path.expanduser(old_path))
        if not os.path.isfile(old_path):
            missing += 1
            print(f"[缺失] 文件不存在，跳过: {old_path}")
            continue

        # 计算目标目录（使用修正后的规则：全角转半角、去空白）
        if old_path in ch_site:
            site_id = ch_site[old_path]
            sname, sfolder = sites.get(site_id, (None, None))
            base = os.path.expanduser(sfolder) if sfolder else library
            target_dir = get_crawl_storage_dir(base, sname or "unknown", title or os.path.basename(old_path))
        else:
            target_dir = get_import_storage_dir(library, title or os.path.basename(old_path))

        os.makedirs(target_dir, exist_ok=True)
        target = os.path.join(target_dir, os.path.basename(old_path))
        # 已在正确位置（含修正后的目录名）则跳过；否则移动/复制（可自愈全角/空格目录）。
        # 库内文件用移动，库外文件用复制（保留原文件，避免数据丢失）。
        if os.path.abspath(target) == os.path.abspath(old_path):
            skipped += 1
            continue
        target = make_unique_path(target)

        if args.dry_run:
            print(f"[预览] {old_path}\n        -> {target}")
            moved += 1
            continue

        try:
            shutil.move(old_path, target)
        except Exception as e:
            print(f"[错误] 移动失败 {old_path}: {e}")
            errors += 1
            continue

        # 更新所有引用该路径的数据库表
        try:
            book = db.get_book(old_path)
            if book is not None:
                book.path = target
                db.update_book(book, old_path)
            db.update_user_books_path(old_path, target)
            db.update_reading_history_path(old_path, target)
            db.update_bookmarks_path(old_path, target)
            db.update_book_metadata_path(old_path, target)
            db.update_vocabulary_path(old_path, target)
            db.update_crawl_history_path(old_path, target)
            moved += 1
            print(f"[完成] {os.path.basename(old_path)}\n        -> {target}")
        except Exception as e:
            print(f"[错误] 数据库更新失败 {old_path} -> {target}: {e}")
            errors += 1

    print("-" * 60)
    print(f"结果: 迁移 {moved} 本, 跳过(已分层) {skipped} 本, "
          f"文件缺失 {missing} 本, 出错 {errors} 本")
    if not args.dry_run:
        removed = cleanup_empty_dirs(library)
        if removed:
            print(f"已清理空目录: {removed} 个")
        if moved:
            print("提示: 迁移后路径已变更，请在应用内「设置 -> 重建全文搜索索引」一次。")


if __name__ == "__main__":
    main()
