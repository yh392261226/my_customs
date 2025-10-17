import os
import time
from lang import get_text

# 动态导入处理，避免模块不存在时的导入错误
try:
    from db import DBManager
    DB_AVAILABLE = True
except ImportError:
    DB_AVAILABLE = False
    print("警告: db模块不可用，数据库功能将受限")

try:
    from utils import build_pages_from_file
    UTILS_AVAILABLE = True
except ImportError:
    UTILS_AVAILABLE = False

try:
    from epub_utils import parse_epub, get_epub_metadata
    EPUB_AVAILABLE = True
except ImportError:
    EPUB_AVAILABLE = False

try:
    from pdf_utils import parse_pdf, get_pdf_metadata
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False

try:
    from mobi_utils import parse_mobi, get_mobi_metadata
    MOBI_AVAILABLE = True
except ImportError:
    MOBI_AVAILABLE = False

try:
    from azw_utils import parse_azw, get_azw_metadata
    AZW_AVAILABLE = True
except ImportError:
    AZW_AVAILABLE = False

class Bookshelf:
    def __init__(self, lang="zh"):
        self.lang = lang
        if DB_AVAILABLE:
            self.db = DBManager()
            self.books = self.load_books()
        else:
            self.db = None
            self.books = []
            print("警告: 数据库不可用，书架功能受限")

    def load_books(self):
        books = self.db.get_books()
        result = []
        for id_, path, title, author, book_type, old_tags in books:  # 注意这里改为old_tags
            exists = os.path.exists(path)
            # 获取书籍的标签列表 - 从数据库实时获取
            book_tags = self.db.get_book_tags(id_)
            tag_names = [tag[1] for tag in book_tags]  # 获取标签名称列表
            
            result.append({
                "id": id_,
                "path": path,
                "title": title,
                "author": author,
                "type": book_type,
                "tags": tag_names,  # 使用实时获取的标签列表
                "exists": exists
            })
        # 按照标题升序排序
        result.sort(key=lambda x: x["title"].lower())
        return result

    # 添加标签相关方法
    def get_all_tags(self):
        """获取所有标签"""
        tags = self.db.get_all_tags()
        return [tag[1] for tag in tags]

    def filter_books_by_tag(self, tag_name):
        """按标签过滤书籍 - 修复筛选逻辑"""
        if not tag_name:  # 如果标签为空，返回所有书籍
            return self.books
            
        return [book for book in self.books if tag_name in book["tags"]]

    def update_book_metadata(self, book_id, title, author, tags):
        """更新书籍元数据（标题、作者、标签）"""
        # 使用 self.db.conn 而不是 self.conn
        c = self.db.conn.cursor()
        
        # 使用事务确保所有操作要么全部成功，要么全部失败
        try:
            # 更新标题和作者
            c.execute("UPDATE books SET title=?, author=? WHERE id=?", (title, author, book_id))
            
            # 清空现有标签
            c.execute("DELETE FROM book_tags WHERE book_id=?", (book_id,))
            
            # 添加新标签
            if tags:
                tag_list = [tag.strip() for tag in tags.split(',') if tag.strip()]
                for tag_name in tag_list:
                    # 确保标签存在
                    tag_id = self.db.add_tag(tag_name)
                    # 关联标签和书籍
                    c.execute("INSERT OR IGNORE INTO book_tags (book_id, tag_id) VALUES (?, ?)", (book_id, tag_id))
            
            # 提交事务
            self.db.conn.commit()
            return True
            
        except Exception as e:
            # 发生错误时回滚
            self.db.conn.rollback()
            print(f"{get_text('update_books_source_failed', self.lang)}: {str(e)}")
            return False

    def batch_update_tags(self, book_ids, action, tag_name):
        """批量更新标签 - 修复已存在标签无法添加的问题"""
        success_count = 0
        
        # 首先处理标签
        if action == "add":
            # 确保标签存在并获取标签ID
            tag_id = self.db.add_tag(tag_name)
            if tag_id is None:
                print(f"{get_text('cannot_create_tag', self.lang).format(tag=tag_name)}")
                return 0
        elif action == "remove":
            # 获取标签ID
            all_tags = self.db.get_all_tags()
            tag_id = None
            for tag in all_tags:
                if tag[1] == tag_name:
                    tag_id = tag[0]
                    break
            if not tag_id:
                # 标签不存在，无需继续
                print(f"{get_text('tag', self.lang)} '{tag_name}' {get_text('not_exists', self,lang)}")
                return 0
        
        # 使用事务处理批量操作
        conn = self.db.conn
        c = conn.cursor()
        
        try:
            for book_id in book_ids:
                try:
                    if action == "add":
                        # 检查是否已经存在该标签关联
                        c.execute("SELECT COUNT(*) FROM book_tags WHERE book_id=? AND tag_id=?", (book_id, tag_id))
                        exists = c.fetchone()[0] > 0
                        
                        if not exists:
                            c.execute("INSERT INTO book_tags (book_id, tag_id) VALUES (?, ?)", (book_id, tag_id))
                            # print(f"添加标签成功: 书籍ID={book_id}, 标签ID={tag_id}")
                            success_count += 1
                        else:
                            # print(f"标签已存在: 书籍ID={book_id}, 标签ID={tag_id}")
                            # 即使标签已存在，我们也认为操作成功
                            success_count += 1
                    elif action == "remove":
                        c.execute("DELETE FROM book_tags WHERE book_id=? AND tag_id=?", (book_id, tag_id))
                        if c.rowcount > 0:
                            # print(f"移除标签成功: 书籍ID={book_id}, 标签ID={tag_id}")
                            success_count += 1
                        # else:
                            # print(f"标签不存在: 书籍ID={book_id}, 标签ID={tag_id}")
                except Exception as e:
                    print(f"{get_text('deal_book_id_error', self.lang).format(id=book_id)}: {str(e)}")
            
            # 提交事务
            conn.commit()
            print(f"{get_text('multype_update_success', self.lang)}: {get_text('update_success_books', self.lang).format(count=success_count)}")
            
        except Exception as e:
            # 发生错误时回滚
            conn.rollback()
            print(f"{get_text('multype_update_failed', self.lang)}: {str(e)}")
        
        # 重新加载书籍列表
        self.books = self.load_books()
        return success_count

    def check_books_existence(self):
        """检查所有书籍文件是否存在"""
        for book in self.books:
            book["exists"] = os.path.exists(book["path"])
        return self.books

    def update_book_path(self, book_id, new_path):
        """更新书籍路径"""
        if not os.path.exists(new_path):
            return False
            
        # 更新数据库
        self.db.update_book_path(book_id, new_path)
        
        # 更新内存中的书籍列表
        for book in self.books:
            if book["id"] == book_id:
                book["path"] = new_path
                book["exists"] = True
                break
                
        return True

    def delete_book(self, book_id):
        """从书架删除书籍"""
        # 从数据库删除
        self.db.delete_book(book_id)
        
        # 从内存中的书籍列表删除
        self.books = [book for book in self.books if book["id"] != book_id]
        
    def delete_books(self, book_ids):
        """批量删除书籍"""
        for book_id in book_ids:
            self.db.delete_book(book_id)
        
        # 从内存中的书籍列表删除
        self.books = [book for book in self.books if book["id"] not in book_ids]

    def add_book(self, file_path, tags="", width=80, height=25, line_spacing=1):
        ext = os.path.splitext(file_path)[-1].lower()
        if not os.path.exists(file_path):
            print(f"错误: 文件不存在: {file_path}")
            return None
            
        # 检查数据库是否可用
        if not DB_AVAILABLE or self.db is None:
            print("错误: 数据库不可用，无法添加书籍")
            return None
            
        # 简单的加载提示
        print(f"{get_text('loading_books', self.lang)}...")
        
        try:
            # 根据文件类型处理
            if ext == ".epub":
                if not EPUB_AVAILABLE:
                    print("警告: epub解析模块不可用，使用基础信息")
                    title = os.path.basename(file_path)
                    author = "未知作者"
                else:
                    print(f"{get_text('parsing_epub_data', self.lang)}...")
                    try:
                        title, author = get_epub_metadata(file_path)
                    except Exception as e:
                        print(f"EPUB解析错误: {str(e)}")
                        title = os.path.basename(file_path)
                        author = f"EPUB解析错误: {str(e)[:30]}..."
                print(f"{get_text('save_to_db', self.lang)}...")
                self.db.add_book(file_path, title or os.path.basename(file_path), author, "epub", tags)
                
            elif ext == ".pdf":
                if not PDF_AVAILABLE:
                    print("警告: PDF解析模块不可用，使用基础信息")
                    title = os.path.basename(file_path)
                    author = "未知作者"
                else:
                    print(f"{get_text('parsing_pdf_data', self.lang)}...")
                    try:
                        title, author = get_pdf_metadata(file_path)
                        
                        # 如果PDF加密，设置一个标志
                        if title is None and author is None:
                            title = os.path.basename(file_path)
                            author = "加密PDF - 需要密码"
                    except Exception as e:
                        print(f"PDF解析错误: {str(e)}")
                        title = os.path.basename(file_path)
                        author = f"PDF解析错误: {str(e)[:30]}..."
                print(f"{get_text('save_to_db', self.lang)}...")
                self.db.add_book(file_path, title or os.path.basename(file_path), author, "pdf", tags)
                
            elif ext == ".mobi":
                if not MOBI_AVAILABLE:
                    print("警告: MOBI解析模块不可用，使用基础信息")
                    title = os.path.basename(file_path)
                    author = "未知作者"
                else:
                    print(f"{get_text('parsing_epub_data', self.lang)}...")
                    try:
                        title, author = get_mobi_metadata(file_path)
                    except Exception as e:
                        print(f"MOBI解析错误: {str(e)}")
                        title = os.path.basename(file_path)
                        author = f"MOBI解析错误: {str(e)[:30]}..."
                print(f"{get_text('save_to_db', self.lang)}...")
                self.db.add_book(file_path, title or os.path.basename(file_path), author, "mobi", tags)
                
            elif ext in [".azw", ".azw3"]:
                if not AZW_AVAILABLE:
                    print("警告: AZW解析模块不可用，使用基础信息")
                    title = os.path.basename(file_path)
                    author = "未知作者"
                else:
                    print(f"{get_text('parsing_azw_data', self.lang)}...")
                    try:
                        title, author = get_azw_metadata(file_path)
                    except Exception as e:
                        print(f"AZW解析错误: {str(e)}")
                        title = os.path.basename(file_path)
                        author = f"AZW解析错误: {str(e)[:30]}..."
                print(f"{get_text('save_to_db', self.lang)}...")
                self.db.add_book(file_path, title or os.path.basename(file_path), author, "azw", tags)
                
            else:
                # 对于txt、md等文本文件，直接使用文件名
                print(f"{get_text('save_to_db', self.lang)}...")
                self.db.add_book(file_path, os.path.basename(file_path), "", "txt", tags)
                
            self.books = self.load_books()
            return True
            
        except Exception as e:
            print(f"添加书籍时发生错误: {str(e)}")
            # 尝试使用基础信息添加书籍
            try:
                self.db.add_book(file_path, os.path.basename(file_path), "解析错误", "txt", tags)
                self.books = self.load_books()
                return True
            except:
                print("无法添加书籍到数据库")
                return False

    def add_dir(self, dir_path, tags="", width=80, height=25, line_spacing=1):
        if not os.path.isdir(dir_path):
            print(f"错误: 目录不存在: {dir_path}")
            return
            
        # 检查数据库是否可用
        if not DB_AVAILABLE or self.db is None:
            print("错误: 数据库不可用，无法添加目录")
            return
            
        # 获取目录中所有支持的书籍文件
        files = []
        for fname in os.listdir(dir_path):
            fpath = os.path.join(dir_path, fname)
            if os.path.isfile(fpath) and fname.lower().endswith(('.txt', '.epub', '.pdf', '.mobi', '.azw', '.azw3', '.md')):
                # 检查文件大小，避免处理空文件或损坏文件
                try:
                    file_size = os.path.getsize(fpath)
                    if file_size > 0:  # 只处理非空文件
                        files.append(fpath)
                    else:
                        print(f"跳过空文件: {fname}")
                except OSError:
                    print(f"无法访问文件: {fname}")
                
        if not files:
            print("未找到有效的书籍文件")
            return
            
        # 简单的加载提示
        print(f"{get_text('total_add_books', self.lang).format(books=len(files))}...")
        
        success_count = 0
        error_count = 0
        
        for i, fpath in enumerate(files):
            print(f"{get_text('parsing_books', self.lang).format(books=f'{i+1}/{len(files)}')}: {os.path.basename(fpath)}")
            
            try:
                result = self.add_book(fpath, tags=tags, width=width, height=height, line_spacing=line_spacing)
                if result:
                    success_count += 1
                else:
                    error_count += 1
                    print(f"添加书籍失败: {os.path.basename(fpath)}")
            except Exception as e:
                error_count += 1
                print(f"处理文件时发生错误 {os.path.basename(fpath)}: {str(e)}")
                # 继续处理下一个文件，不中断整个扫描过程
        
        print(f"目录扫描完成: 成功 {success_count} 个文件, 失败 {error_count} 个文件")
        
        # 显示更新后的书架
        if success_count > 0:
            print("\n📊 更新后的书架:")
            self.display_bookshelf()

    def get_book_by_id(self, book_id):
        for b in self.books:
            if b["id"] == book_id:
                return b
        return None

    def search_books(self, keyword):
        keyword = keyword.strip().lower()
        result = [book for book in self.books if keyword in book["title"].lower()]
        # 搜索结果也按照标题升序排序
        result.sort(key=lambda x: x["title"].lower())
        return result
    
    def delete_book(self, book_id):
        self.db.delete_book(book_id)
        self.books = self.load_books()

    def get_books_by_ids(self, book_ids):
        """根据ID列表获取书籍信息"""
        return [book for book in self.books if book["id"] in book_ids]
    
    def get_all_books(self):
        """获取所有书籍"""
        return self.books
    
    def display_bookshelf(self, books=None):
        """显示书架列表，包含统计信息"""
        if books is None:
            books = self.books
        
        if not books:
            print("📚 书架为空")
            return
        
        # 显示统计信息
        stats = self.get_book_statistics()
        if stats["total"] == 0:
            print("📚 书架为空")
            return
        
        print(f"📚 书架统计 - 共 {stats['total']} 本书")
        
        # 按类型显示统计
        type_stats = []
        for book_type, count in stats["by_type"].items():
            type_name = self._get_type_display_name(book_type)
            type_stats.append(f"{type_name}({count})")
        
        if type_stats:
            print("📖 类型分布: " + " | ".join(type_stats))
        
        print("-" * 60)  # 分隔线
        
        # 显示书籍列表
        print("📖 书籍列表:")
        for i, book in enumerate(books, 1):
            status = "✅" if book.get("exists", True) else "❌"
            tags_text = ", ".join(book.get("tags", [])) if book.get("tags") else "无标签"
            print(f"  {i}. {status} {book['title']} - {book['author']} [{book.get('type', 'unknown')}]")
            if tags_text:
                print(f"     标签: {tags_text}")
            print()
    
    def get_book_statistics(self):
        """获取书籍统计信息"""
        if not self.books:
            return {"total": 0, "by_type": {}}
        
        stats = {
            "total": len(self.books),
            "by_type": {}
        }
        
        # 统计每种类型的书籍数量
        for book in self.books:
            book_type = book.get("type", "unknown")
            if book_type not in stats["by_type"]:
                stats["by_type"][book_type] = 0
            stats["by_type"][book_type] += 1
        
        return stats
    
    def display_statistics(self):
        """显示书籍统计信息"""
        stats = self.get_book_statistics()
        
        if stats["total"] == 0:
            print("📚 书架为空")
            return
        
        # 显示统计信息
        print(f"📚 书架统计 - 共 {stats['total']} 本书")
        
        # 按类型显示统计
        type_stats = []
        for book_type, count in stats["by_type"].items():
            type_name = self._get_type_display_name(book_type)
            type_stats.append(f"{type_name}({count})")
        
        if type_stats:
            print("📖 类型分布: " + " | ".join(type_stats))
    
    def _get_type_display_name(self, book_type):
        """获取书籍类型的显示名称"""
        type_names = {
            "epub": "EPUB",
            "pdf": "PDF", 
            "mobi": "MOBI",
            "azw": "AZW",
            "txt": "TXT",
            "md": "Markdown",
            "unknown": "Unknown"
        }
        return type_names.get(book_type, book_type)
    
    def get_statistics_text(self):
        """获取统计信息的格式化文本，用于UI显示"""
        stats = self.get_book_statistics()
        
        if stats["total"] == 0:
            return "书架为空"
        
        # 格式化统计信息
        lines = []
        lines.append(f"总书籍: {stats['total']} 本")
        
        # 按类型显示统计
        type_stats = []
        for book_type, count in stats["by_type"].items():
            type_name = self._get_type_display_name(book_type)
            type_stats.append(f"{type_name}:{count}")
        
        if type_stats:
            lines.append("类型分布: " + " ".join(type_stats))
        
        return " | ".join(lines)
    
    def delete_tag(self, tag_name):
        """删除标签"""
        # 获取标签ID
        tag_id = self.db.get_tag_id(tag_name)
        if tag_id:
            return self.db.delete_tag(tag_id)
        return False

    def get_recent_books(self, limit=3):
        """获取最近阅读的书籍"""
        c = self.db.conn.cursor()
        c.execute("SELECT id, path, title, author, type, tags FROM books WHERE last_read_time IS NOT NULL ORDER BY last_read_time DESC LIMIT ?", (limit,))
        books = c.fetchall()
        
        result = []
        for id_, path, title, author, book_type, tags in books:
            exists = os.path.exists(path)
            # 获取书籍的标签列表
            book_tags = self.db.get_book_tags(id_)
            tag_names = [tag[1] for tag in book_tags]
            
            result.append({
                "id": id_,
                "path": path,
                "title": title,
                "author": author,
                "type": book_type,
                "tags": tag_names,
                "exists": exists,
                "recent": True  # 标记为最近阅读的书籍
            })
        return result

    def clear_recent_reading(self, book_ids):
        """清除指定书籍的最近阅读记录"""
        return self.db.clear_last_read_time(book_ids)