"""
书籍回收站服务（统一删除 / 恢复 / 撤销 / 自动清空）。

设计要点
--------
* 所有删除书籍的入口（``Bookshelf.remove_book``、``DatabaseManager.delete_book``、
  去重、合并、批量合并、清理缺失文件等）最终都会走 ``RecycleBin.trash_book``：
  先把书籍行与所有关联数据快照下来，再删除数据库记录，并把物理文件移动到
  应用自己的回收站目录（而不是系统回收站，这样才能一键还原）。
* 一次操作对应一个 ``batch_id``。批量去重 / 合并 / 批量合并误操作后，可用
  ``restore_batch`` 一次撤销整批（并回滚合并生成的新书），单条记录也可用
  ``restore_items`` 单独恢复。
* 恢复时若原路径已被占用（用户重新导入了同名文件），会自动改用带
  ``_restored_N`` 后缀的新路径，并同步改写所有关联数据里的路径，避免覆盖新数据。
* 只有「清空 / 彻底删除 / 到达自动清空周期」才会真正删除物理文件。

关联数据（快照 + 恢复）
----------------------
``user_books`` / ``reading_history`` / ``book_metadata`` / ``bookmarks`` /
``book_tags`` / ``merged_book_sources`` / ``search_indexed_books`` /
``crawl_history``（按 ``file_path`` 关联；删除书籍时一并移入回收站，恢复时还原，
因此回收站里的书不会出现在爬取管理列表中，且恢复后爬取记录随之回来）。
表或列不存在时自动跳过，兼容旧版本数据库。
"""
from __future__ import annotations

import json
import os
import shutil
import sqlite3
import tempfile
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from src.utils.logger import get_logger

logger = get_logger(__name__)

DEFAULT_AUTO_CLEAR_DAYS = 10

# (表名, 指向书籍路径的列名)。merged_book_sources 保存的是「合并产物」的溯源，
# 只有删除产物本身时才需要一并快照；search_indexed_books 用 book_id 存路径；
# crawl_history 用 file_path 关联（爬取管理删除书籍时一并快照，恢复时还原，
# 从而保证「回收站里的书不出现在爬取管理」且「恢复后爬取记录能回来」）。
RELATED_TABLES: Tuple[Tuple[str, str], ...] = (
    ("user_books", "book_path"),
    ("reading_history", "book_path"),
    ("book_metadata", "book_path"),
    ("bookmarks", "book_path"),
    ("book_tags", "book_path"),
    ("merged_book_sources", "merged_file_path"),
    ("search_indexed_books", "book_id"),
    ("crawl_history", "file_path"),
)

# 常用操作标识（仅用于展示，不参与逻辑判断）
OP_DELETE = "delete"
OP_DEDUPLICATE = "deduplicate"
OP_MERGE = "merge"
OP_BATCH_MERGE = "batch_merge"
OP_MISSING = "missing"
OP_UNDO_MERGE = "undo_merge"
OP_IMPORT_DEDUP = "import_dedup"
OP_IMPORT_REPLACE = "import_replace"

OPERATION_LABELS = {
    OP_DELETE: "删除",
    OP_DEDUPLICATE: "批量去重",
    OP_MERGE: "合并",
    OP_BATCH_MERGE: "批量合并",
    OP_MISSING: "清理缺失文件",
    OP_UNDO_MERGE: "撤销合并",
    OP_IMPORT_DEDUP: "导入去重",
    OP_IMPORT_REPLACE: "导入替换",
}


def _table_columns(conn: sqlite3.Connection, table: str) -> List[str]:
    try:
        return [r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()]
    except sqlite3.Error:
        return []


def _quote(name: str) -> str:
    """表名/列名均来自代码内常量或 PRAGMA，仍做一层引号保护。"""
    return '"' + str(name).replace('"', '""') + '"'


class RecycleBin:
    """回收站：数据快照、文件保管、恢复、彻底删除、自动清空。"""

    def __init__(self, db_path: str, files_dir: Optional[str] = None) -> None:
        self.db_path = db_path
        if files_dir:
            self.files_dir = os.path.abspath(os.path.expanduser(files_dir))
        elif db_path == ":memory:":
            self.files_dir = os.path.join(tempfile.gettempdir(), "newreader_recycle_bin")
        else:
            self.files_dir = os.path.join(os.path.dirname(db_path), "recycle_bin", "files")
        os.makedirs(self.files_dir, exist_ok=True)
        self._memory_conn: Optional[sqlite3.Connection] = None
        self._ensure_schema()

    # ------------------------------------------------------------------ 基础

    def _connect(self) -> sqlite3.Connection:
        if self.db_path == ":memory:":
            if self._memory_conn is None:
                self._memory_conn = sqlite3.connect(":memory:", check_same_thread=False)
                self._memory_conn.row_factory = sqlite3.Row
            return self._memory_conn
        conn = sqlite3.connect(self.db_path, timeout=10)
        conn.row_factory = sqlite3.Row
        return conn

    def _ensure_schema(self) -> None:
        with self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS recycle_batches (
                    batch_id TEXT PRIMARY KEY,
                    operation TEXT NOT NULL DEFAULT 'delete',
                    note TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL,
                    item_count INTEGER NOT NULL DEFAULT 0,
                    extra TEXT NOT NULL DEFAULT '{}',
                    undone INTEGER NOT NULL DEFAULT 0
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS recycle_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    batch_id TEXT NOT NULL,
                    book_path TEXT NOT NULL,
                    title TEXT NOT NULL DEFAULT '',
                    author TEXT NOT NULL DEFAULT '',
                    operation TEXT NOT NULL DEFAULT 'delete',
                    reason TEXT NOT NULL DEFAULT '',
                    deleted_at TEXT NOT NULL,
                    book_row TEXT NOT NULL DEFAULT '{}',
                    related_rows TEXT NOT NULL DEFAULT '{}',
                    file_name TEXT NOT NULL DEFAULT '',
                    file_existed INTEGER NOT NULL DEFAULT 0,
                    restored_at TEXT
                )
            """)
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_recycle_items_batch ON recycle_items(batch_id)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_recycle_items_deleted ON recycle_items(deleted_at)"
            )
            conn.commit()

    # ------------------------------------------------------------------ 批次

    def create_batch(self, operation: str = OP_DELETE, note: str = "",
                     extra: Optional[Dict[str, Any]] = None) -> str:
        """创建一次操作批次，返回 batch_id（同一次批量操作共用一个 id）。"""
        batch_id = uuid.uuid4().hex
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO recycle_batches (batch_id, operation, note, created_at, extra) "
                "VALUES (?, ?, ?, ?, ?)",
                (batch_id, operation, note or "", datetime.now().isoformat(),
                 json.dumps(extra or {}, ensure_ascii=False)),
            )
            conn.commit()
        return batch_id

    def add_created_paths(self, batch_id: Optional[str], paths: Iterable[str]) -> None:
        """登记本次操作新建的文件（合并产物），撤销整批时会删除它们。"""
        if not batch_id:
            return
        new_paths = [os.path.abspath(p) for p in paths if p]
        if not new_paths:
            return
        with self._connect() as conn:
            row = conn.execute(
                "SELECT extra FROM recycle_batches WHERE batch_id = ?", (batch_id,)
            ).fetchone()
            if row is None:
                return
            try:
                extra = json.loads(row["extra"] or "{}")
            except Exception:
                extra = {}
            created = list(extra.get("created_paths") or [])
            for path in new_paths:
                if path not in created:
                    created.append(path)
            extra["created_paths"] = created
            conn.execute(
                "UPDATE recycle_batches SET extra = ? WHERE batch_id = ?",
                (json.dumps(extra, ensure_ascii=False), batch_id),
            )
            conn.commit()

    def _ensure_batch(self, conn: sqlite3.Connection, batch_id: Optional[str],
                      operation: str) -> str:
        if batch_id:
            exists = conn.execute(
                "SELECT 1 FROM recycle_batches WHERE batch_id = ?", (batch_id,)
            ).fetchone()
            if exists:
                return batch_id
        new_id = batch_id or uuid.uuid4().hex
        conn.execute(
            "INSERT OR IGNORE INTO recycle_batches (batch_id, operation, created_at) "
            "VALUES (?, ?, ?)",
            (new_id, operation, datetime.now().isoformat()),
        )
        return new_id

    # ------------------------------------------------------------------ 删除

    def _capture_related(self, conn: sqlite3.Connection, path: str) -> Dict[str, List[Dict[str, Any]]]:
        result: Dict[str, List[Dict[str, Any]]] = {}
        for table, column in RELATED_TABLES:
            columns = _table_columns(conn, table)
            if column not in columns:
                continue
            try:
                rows = conn.execute(
                    f"SELECT * FROM {_quote(table)} WHERE {_quote(column)} = ?", (path,)
                ).fetchall()
                if rows:
                    result[table] = [dict(r) for r in rows]
            except sqlite3.Error as e:
                logger.debug(f"回收站快照 {table} 失败: {e}")
        return result

    def _shelve_file_in_place(self, src: str) -> str:
        """在文件原目录内改名（追加 ``.recycled`` 后缀），腾出原路径给覆盖写入。

        与「移入独立回收站目录」相比，文件始终留在原文件夹，既避免改变文件位置带来的
        各种副作用，又能在导入替换等需要复用原路径的场景下保护被替换的旧文件，
        恢复时只需把后缀改回即可。不要求改名时返回空串。
        """
        if not src or not os.path.isfile(src):
            return ""
        shelved = f"{src}.recycled"
        if os.path.exists(shelved):
            shelved = f"{src}.recycled-{uuid.uuid4().hex[:8]}"
        try:
            os.rename(src, shelved)
            return shelved
        except OSError as e:
            logger.error(f"回收站原位置改名失败 {src}: {e}")
            return ""

    def trash_book(self, book_path: str, *, delete_file: bool = True,
                   operation: str = OP_DELETE, reason: str = "",
                   batch_id: Optional[str] = None,
                   cleanup_associated: bool = True,
                   rename_in_place: bool = False) -> bool:
        """把一本书移入回收站（记录快照 + 删除数据库数据 + 保护文件）。

        默认**不改变文件的物理位置**：文件继续留在原路径，直到用户「彻底删除」才真正
        移除。仅在 ``rename_in_place=True`` 时（如导入替换需要复用原路径），会在原目录
        内给文件加 ``.recycled`` 后缀，既腾出原路径又方便恢复。

        Args:
            book_path: 书籍绝对路径。
            delete_file: 回收站是否负责该物理文件（决定「彻底删除」时是否真删文件）。
            operation: 操作类型（delete/deduplicate/merge/...）。
            reason: 附加说明，如「重复组推荐删除」。
            batch_id: 所属操作批次；为空时自动创建单书批次。
            cleanup_associated: 是否清理关联表（快照始终会采集）。
            rename_in_place: 是否在原目录内改名以保护文件（导入替换场景）。

        Returns:
            是否确实删除了书籍记录或文件。
        """
        if not book_path:
            return False
        abs_path = os.path.abspath(os.path.expanduser(book_path))
        with self._connect() as conn:
            cur = conn.cursor()
            row = cur.execute("SELECT * FROM books WHERE path = ?", (abs_path,)).fetchone()
            file_existed = os.path.isfile(abs_path)
            if row is None and not file_existed:
                return False

            book_row = dict(row) if row is not None else {}
            related = self._capture_related(conn, abs_path)

            # 保护文件：默认保持原位（不移动），仅在需要复用原路径（如导入替换）时
            # 在原目录内改名，方便恢复且不改变文件所在位置。
            actual_path = self._shelve_file_in_place(abs_path) if (rename_in_place and file_existed) else ""
            try:
                if cleanup_associated:
                    for table, column in RELATED_TABLES:
                        if column not in _table_columns(conn, table):
                            continue
                        try:
                            cur.execute(
                                f"DELETE FROM {_quote(table)} WHERE {_quote(column)} = ?",
                                (abs_path,),
                            )
                        except sqlite3.Error as e:
                            logger.debug(f"回收站清理 {table} 失败: {e}")
                    # 全文索引：删掉登记与倒排记录，恢复后由后台任务重新补建
                    for sql in (
                        "DELETE FROM search_content WHERE book_id = ?",
                        "DELETE FROM search_indexed_books WHERE book_id = ?",
                    ):
                        try:
                            cur.execute(sql, (abs_path,))
                        except sqlite3.Error:
                            pass

                cur.execute("DELETE FROM books WHERE path = ?", (abs_path,))
                deleted = cur.rowcount > 0

                real_batch = self._ensure_batch(conn, batch_id, operation)
                cur.execute(
                    "INSERT INTO recycle_items "
                    "(batch_id, book_path, title, author, operation, reason, deleted_at, "
                    " book_row, related_rows, file_name, file_existed) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        real_batch,
                        abs_path,
                        str(book_row.get("title") or os.path.basename(abs_path)),
                        str(book_row.get("author") or ""),
                        operation,
                        reason or "",
                        datetime.now().isoformat(),
                        json.dumps(book_row, ensure_ascii=False),
                        json.dumps(related, ensure_ascii=False),
                        actual_path,
                        1 if (file_existed and delete_file) else 0,
                    ),
                )
                conn.execute(
                    "UPDATE recycle_batches SET item_count = item_count + 1 WHERE batch_id = ?",
                    (real_batch,),
                )
                conn.commit()
                logger.info(
                    f"书籍已移入回收站: {abs_path} (操作={operation}, 批次={real_batch})"
                )
                return bool(deleted or file_existed)
            except Exception:
                conn.rollback()
                if actual_path and os.path.exists(actual_path):
                    try:
                        os.rename(actual_path, abs_path)
                    except OSError as restore_err:
                        logger.error(f"回收站事务失败后还原文件名失败: {restore_err}")
                raise

    def trash_file(self, file_path: str, *, operation: str = OP_IMPORT_DEDUP,
                   title: Optional[str] = None, author: Optional[str] = None,
                   reason: str = "", rename_in_place: bool = False) -> bool:
        """把单个【尚未在书架登记】的文件移入回收站。

        用于导入阶段的「去重丢弃较小文件」「同名替换旧文件」等场景：这些文件不一定
        已在 ``books`` 表登记，无法直接走 :meth:`trash_book`，但仍应进回收站以便恢复，
        而不是被真正删除。

        默认不改变文件位置；仅 ``rename_in_place=True`` 时（导入替换）在原目录内改名
        以保护文件，避免被随后写入的新文件覆盖。

        Args:
            file_path: 文件绝对路径。
            operation: 操作类型（``import_dedup`` / ``import_replace``）。
            title/author: 展示用元数据；缺省时从文件名推断。
            reason: 附加说明。
            rename_in_place: 是否在原目录内改名以保护文件（导入替换场景）。

        Returns:
            文件是否成功移入回收站。
        """
        if not file_path:
            return False
        abs_path = os.path.abspath(os.path.expanduser(file_path))
        if not os.path.isfile(abs_path):
            return False
        actual_path = self._shelve_file_in_place(abs_path) if rename_in_place else ""
        stem, _ = os.path.splitext(os.path.basename(abs_path))
        book_row = {
            "path": abs_path,
            "title": title or stem,
            "author": author or "",
        }
        with self._connect() as conn:
            cur = conn.cursor()
            real_batch = self._ensure_batch(conn, None, operation)
            cur.execute(
                "INSERT INTO recycle_items "
                "(batch_id, book_path, title, author, operation, reason, deleted_at, "
                " book_row, related_rows, file_name, file_existed) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    real_batch,
                    abs_path,
                    title or stem,
                    author or "",
                    operation,
                    reason or "",
                    datetime.now().isoformat(),
                    json.dumps(book_row, ensure_ascii=False),
                    json.dumps({}, ensure_ascii=False),
                    actual_path,
                    1,
                ),
            )
            conn.execute(
                "UPDATE recycle_batches SET item_count = item_count + 1 WHERE batch_id = ?",
                (real_batch,),
            )
            conn.commit()
        logger.info(
            f"文件已移入回收站: {abs_path} (操作={operation}, 批次={real_batch})"
        )
        return True

    # ------------------------------------------------------------------ 查询

    def list_items(self, include_restored: bool = False) -> List[Dict[str, Any]]:
        sql = "SELECT * FROM recycle_items"
        if not include_restored:
            sql += " WHERE restored_at IS NULL"
        sql += " ORDER BY deleted_at DESC, id DESC"
        with self._connect() as conn:
            return [dict(r) for r in conn.execute(sql).fetchall()]

    def list_batches(self) -> List[Dict[str, Any]]:
        """按批次聚合（只列出仍有可恢复条目的批次）。"""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT b.*, COUNT(i.id) AS remaining, MIN(i.deleted_at) AS deleted_at "
                "FROM recycle_batches b JOIN recycle_items i ON i.batch_id = b.batch_id "
                "WHERE i.restored_at IS NULL GROUP BY b.batch_id "
                "ORDER BY deleted_at DESC"
            ).fetchall()
            return [dict(r) for r in rows]

    def get_item(self, item_id: int) -> Optional[Dict[str, Any]]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM recycle_items WHERE id = ?", (item_id,)
            ).fetchone()
            return dict(row) if row else None

    def count(self) -> int:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT COUNT(*) AS n FROM recycle_items WHERE restored_at IS NULL"
            ).fetchone()
            return int(row["n"] if row else 0)

    # ------------------------------------------------------------------ 恢复

    def _unique_path(self, conn: sqlite3.Connection, path: str) -> str:
        """目标路径被占用时生成一个不冲突的新路径。"""
        base, ext = os.path.splitext(path)
        for index in range(1, 1000):
            candidate = f"{base}_restored_{index}{ext}"
            occupied = conn.execute(
                "SELECT 1 FROM books WHERE path = ?", (candidate,)
            ).fetchone()
            if not occupied and not os.path.exists(candidate):
                return candidate
        return f"{base}_restored_{uuid.uuid4().hex[:8]}{ext}"

    @staticmethod
    def _insert_row(conn: sqlite3.Connection, table: str, row: Dict[str, Any]) -> None:
        columns = _table_columns(conn, table)
        keys = [k for k in row if k in columns]
        if not keys:
            return
        placeholders = ", ".join("?" for _ in keys)
        sql = (
            f"INSERT OR IGNORE INTO {_quote(table)} "
            f"({', '.join(_quote(k) for k in keys)}) VALUES ({placeholders})"
        )
        conn.execute(sql, [row[k] for k in keys])

    def _restore_one(self, conn: sqlite3.Connection, item: Dict[str, Any]) -> Tuple[bool, str, bool]:
        """恢复单条记录，返回 (是否成功, 实际恢复到的路径, 文件是否还原)。"""
        original = item["book_path"]
        actual = item.get("file_name") or original
        # 仅当文件被原位改名（导入替换等）且原路径已被占用时，才另取不冲突路径；
        # 文件一直留在原位的场景直接沿用原路径，不做任何搬运。
        if actual and actual != original and (
            os.path.exists(original)
            or conn.execute("SELECT 1 FROM books WHERE path = ?", (original,)).fetchone()
        ):
            target = self._unique_path(conn, original)
        else:
            target = original

        try:
            book_row = json.loads(item["book_row"] or "{}")
            related = json.loads(item["related_rows"] or "{}")
        except Exception as e:
            logger.error(f"回收站记录解析失败 id={item['id']}: {e}")
            return False, original, False

        if target != original:
            book_row["path"] = target
            for table, rows in related.items():
                column = dict(RELATED_TABLES).get(table)
                if column:
                    for row in rows:
                        row[column] = target

        file_restored = False
        if actual and os.path.isfile(actual):
            if actual != target:
                # 原位改名（.recycled）或路径冲突：把文件移回目标路径
                try:
                    os.makedirs(os.path.dirname(target) or ".", exist_ok=True)
                    shutil.move(actual, target)
                    file_restored = True
                except Exception as e:
                    logger.error(f"还原回收站文件失败 {actual} -> {target}: {e}")
            else:
                # 文件始终在原位未移动（默认行为），无需搬运
                file_restored = True

        if book_row:
            self._insert_row(conn, "books", book_row)
        else:
            # 极端情况：删除时 books 表已无记录（只有文件）。补一条最小记录，
            # 让恢复出来的文件重新出现在书库里。
            self._insert_row(conn, "books", {
                "path": target,
                "title": item.get("title") or os.path.basename(target),
                "author": item.get("author") or "未知作者",
                "format": os.path.splitext(target)[1].lower() or ".txt",
                "add_date": datetime.now().isoformat(),
                "tags": "",
                "metadata": "",
                "file_size": os.path.getsize(target) if os.path.isfile(target) else 0,
            })

        for table, rows in related.items():
            for row in rows:
                try:
                    self._insert_row(conn, table, row)
                except sqlite3.Error as e:
                    logger.debug(f"恢复关联数据 {table} 失败: {e}")

        # FTS：清掉可能的残留，并移除「已索引」登记，让后台任务用恢复后的文件重建
        for sql in (
            "DELETE FROM search_content WHERE book_id = ?",
            "DELETE FROM search_indexed_books WHERE book_id = ?",
        ):
            try:
                conn.execute(sql, (original,))
                if target != original:
                    conn.execute(sql, (target,))
            except sqlite3.Error:
                pass

        conn.execute(
            "UPDATE recycle_items SET restored_at = ? WHERE id = ?",
            (datetime.now().isoformat(), item["id"]),
        )
        conn.execute(
            "UPDATE recycle_batches SET item_count = MAX(item_count - 1, 0) "
            "WHERE batch_id = ?",
            (item["batch_id"],),
        )
        return True, target, file_restored

    def restore_items(self, item_ids: Sequence[int]) -> Dict[str, Any]:
        """恢复指定的回收站条目（含文件与所有关联数据）。"""
        result: Dict[str, Any] = {"ok": 0, "failed": 0, "paths": [], "files": 0}
        if not item_ids:
            return result
        with self._connect() as conn:
            for item_id in item_ids:
                row = conn.execute(
                    "SELECT * FROM recycle_items WHERE id = ? AND restored_at IS NULL",
                    (item_id,),
                ).fetchone()
                if row is None:
                    continue
                try:
                    ok, path, file_restored = self._restore_one(conn, dict(row))
                    if ok:
                        result["ok"] += 1
                        result["paths"].append(path)
                        result["files"] += 1 if file_restored else 0
                    else:
                        result["failed"] += 1
                except Exception as e:
                    logger.error(f"恢复回收站条目 {item_id} 失败: {e}")
                    result["failed"] += 1
            self._cleanup_empty_batches(conn)
            conn.commit()
        return result

    def restore_batch(self, batch_id: str, remove_created: bool = True) -> Dict[str, Any]:
        """撤销整个操作批次（批量去重 / 合并误操作的统一入口）。

        ``remove_created=True`` 时会同时删除该批次生成的新文件与书籍记录
        （主要是合并产物），从而完整回到操作前的状态。
        """
        with self._connect() as conn:
            ids = [
                r["id"] for r in conn.execute(
                    "SELECT id FROM recycle_items WHERE batch_id = ? AND restored_at IS NULL",
                    (batch_id,),
                ).fetchall()
            ]
            batch = conn.execute(
                "SELECT * FROM recycle_batches WHERE batch_id = ?", (batch_id,)
            ).fetchone()
            try:
                extra = json.loads(batch["extra"] or "{}") if batch else {}
            except Exception:
                extra = {}
            conn.commit()

        result = self.restore_items(ids)

        removed_created = 0
        if remove_created:
            for path in extra.get("created_paths") or []:
                try:
                    with self._connect() as conn:
                        conn.execute("DELETE FROM books WHERE path = ?", (path,))
                        for table, column in RELATED_TABLES:
                            if column in _table_columns(conn, table):
                                try:
                                    conn.execute(
                                        f"DELETE FROM {_quote(table)} WHERE {_quote(column)} = ?",
                                        (path,),
                                    )
                                except sqlite3.Error:
                                    pass
                        try:
                            conn.execute(
                                "DELETE FROM search_content WHERE book_id = ?", (path,)
                            )
                        except sqlite3.Error:
                            pass
                        conn.commit()
                    if os.path.isfile(path):
                        os.remove(path)
                    removed_created += 1
                except Exception as e:
                    logger.error(f"撤销批次时删除合并产物失败 {path}: {e}")

        with self._connect() as conn:
            conn.execute(
                "UPDATE recycle_batches SET undone = 1 WHERE batch_id = ?", (batch_id,)
            )
            self._cleanup_empty_batches(conn)
            conn.commit()

        result["removed_created"] = removed_created
        return result

    def _cleanup_empty_batches(self, conn: sqlite3.Connection) -> None:
        try:
            conn.execute(
                "DELETE FROM recycle_batches WHERE batch_id NOT IN "
                "(SELECT DISTINCT batch_id FROM recycle_items WHERE restored_at IS NULL)"
            )
            conn.execute("DELETE FROM recycle_items WHERE restored_at IS NOT NULL")
        except sqlite3.Error as e:
            logger.debug(f"清理空回收站批次失败: {e}")

    # ------------------------------------------------------------------ 清空

    def purge_items(self, item_ids: Sequence[int]) -> int:
        """彻底删除指定条目（真删除：物理文件 + 回收站记录）。"""
        if not item_ids:
            return 0
        purged = 0
        with self._connect() as conn:
            for item_id in item_ids:
                row = conn.execute(
                    "SELECT file_name, book_path, file_existed FROM recycle_items WHERE id = ?",
                    (item_id,),
                ).fetchone()
                if row is None:
                    continue
                actual = (row["file_name"] or row["book_path"]) or ""
                if row["file_existed"]:
                    self._delete_original_file(conn, actual)
                conn.execute("DELETE FROM recycle_items WHERE id = ?", (item_id,))
                purged += 1
            self._cleanup_empty_batches(conn)
            conn.commit()
        return purged

    def _delete_original_file(self, conn, path: str) -> None:
        """真正删除文件（回收站彻底删除 / 清空 / 过期清理时调用）。

        安全护栏：若路径仍被书库 ``books`` 表引用（例如该书已被重新导入），
        则不删除，避免误删在用书。文件不存在时静默跳过。
        """
        if not path or not os.path.isfile(path):
            return
        try:
            if conn.execute("SELECT 1 FROM books WHERE path = ?", (path,)).fetchone():
                logger.warning(f"回收站彻底删除跳过仍被书库引用的文件: {path}")
                return
        except sqlite3.Error:
            pass
        try:
            os.remove(path)
        except OSError as e:
            logger.error(f"彻底删除回收站文件失败 {path}: {e}")

    def empty(self) -> int:
        """清空回收站（真正删除所有文件与记录）。"""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT file_name, book_path, file_existed FROM recycle_items"
            ).fetchall()
            for row in rows:
                actual = (row["file_name"] or row["book_path"]) or ""
                if row["file_existed"]:
                    self._delete_original_file(conn, actual)
            count = len(rows)
            conn.execute("DELETE FROM recycle_items")
            conn.execute("DELETE FROM recycle_batches")
            conn.commit()
        logger.info(f"回收站已清空，共彻底删除 {count} 条记录")
        return count

    def purge_expired(self, days: int) -> int:
        """按天数自动清空过期条目；days <= 0 表示禁用自动清空。"""
        if days <= 0:
            return 0
        threshold = (datetime.now() - timedelta(days=days)).isoformat()
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT id, file_name, book_path, file_existed FROM recycle_items WHERE deleted_at < ?",
                (threshold,),
            ).fetchall()
            for row in rows:
                actual = (row["file_name"] or row["book_path"]) or ""
                if row["file_existed"]:
                    self._delete_original_file(conn, actual)
            conn.execute("DELETE FROM recycle_items WHERE deleted_at < ?", (threshold,))
            self._cleanup_empty_batches(conn)
            conn.commit()
        if rows:
            logger.info(f"回收站自动清空：已彻底删除 {len(rows)} 条超过 {days} 天的记录")
        return len(rows)

    def auto_purge_from_config(self) -> int:
        """读取 advanced.recycle_bin_auto_clear_days 并执行自动清空（默认 10 天）。"""
        try:
            from src.config.config_manager import ConfigManager
            config = ConfigManager.get_instance().get_config()
            days = config.get("advanced", {}).get(
                "recycle_bin_auto_clear_days", DEFAULT_AUTO_CLEAR_DAYS
            )
            return self.purge_expired(int(days))
        except Exception as e:
            logger.debug(f"读取回收站自动清空配置失败: {e}")
            return 0


_BIN_CACHE: Dict[str, "RecycleBin"] = {}


def get_recycle_bin(db_manager: Any = None) -> RecycleBin:
    """获取与指定 DatabaseManager（或默认数据库）绑定的回收站实例。"""
    if db_manager is not None and getattr(db_manager, "get_db_path", None):
        db_path = db_manager.get_db_path()
    else:
        from src.config.config_manager import ConfigManager
        config = ConfigManager.get_instance().get_config()
        db_path = os.path.expanduser(config["paths"]["database"])
    key = os.path.abspath(db_path) if db_path != ":memory:" else ":memory:"
    if key not in _BIN_CACHE:
        _BIN_CACHE[key] = RecycleBin(db_path)
    return _BIN_CACHE[key]


def recycle_book(db_manager: Any, book_path: str, *, delete_file: bool = True,
                 operation: str = OP_DELETE, reason: str = "",
                 batch_id: Optional[str] = None) -> bool:
    """便捷入口：把一本书（及文件）移入回收站。"""
    return get_recycle_bin(db_manager).trash_book(
        book_path,
        delete_file=delete_file,
        operation=operation,
        reason=reason,
        batch_id=batch_id,
    )


def operation_label(operation: str) -> str:
    return OPERATION_LABELS.get(operation, operation or OPERATION_LABELS[OP_DELETE])
