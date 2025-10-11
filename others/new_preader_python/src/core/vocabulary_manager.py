"""
单词本管理器 - 管理用户保存的单词和翻译
"""

import sqlite3
import json
import os
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
from src.config.config_manager import ConfigManager
from src.core.database_manager import DatabaseManager
from src.utils.logger import get_logger

logger = get_logger(__name__)

class VocabularyItem:
    """单词本条目"""
    
    def __init__(self, word: str, translation: str, language: str = "en", 
                 context: str = "", book_id: str = "", position: int = 0,
                 created_at: Optional[datetime] = None, updated_at: Optional[datetime] = None,
                 item_id: Optional[int] = None, review_count: int = 0, 
                 last_reviewed: Optional[datetime] = None, mastery_level: int = 0):
        self.id = item_id
        self.word = word
        self.translation = translation
        self.language = language
        self.context = context
        self.book_id = book_id
        self.position = position
        self.created_at = created_at or datetime.now()
        self.updated_at = updated_at or datetime.now()
        self.review_count = review_count
        self.last_reviewed = last_reviewed
        self.mastery_level = mastery_level  # 0-5, 0表示未掌握，5表示完全掌握
        
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'id': self.id,
            'word': self.word,
            'translation': self.translation,
            'language': self.language,
            'context': self.context,
            'book_id': self.book_id,
            'position': self.position,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'review_count': self.review_count,
            'last_reviewed': self.last_reviewed.isoformat() if self.last_reviewed else None,
            'mastery_level': self.mastery_level
        }
        
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'VocabularyItem':
        """从字典创建实例"""
        item = cls(
            word=data['word'],
            translation=data['translation'],
            language=data.get('language', 'en'),
            context=data.get('context', ''),
            book_id=data.get('book_id', ''),
            position=data.get('position', 0),
            item_id=data.get('id'),
            review_count=data.get('review_count', 0),
            last_reviewed=None,  # 将在后面单独设置
            mastery_level=data.get('mastery_level', 0)
        )
        
        if 'created_at' in data and data['created_at']:
            item.created_at = datetime.fromisoformat(data['created_at'])
        if 'updated_at' in data and data['updated_at']:
            item.updated_at = datetime.fromisoformat(data['updated_at'])
        if 'last_reviewed' in data and data['last_reviewed']:
            item.last_reviewed = datetime.fromisoformat(data['last_reviewed'])
            
        # 设置额外的属性
        if 'review_count' in data:
            item.review_count = data['review_count']
        if 'mastery_level' in data:
            item.mastery_level = data['mastery_level']
        
        return item

class VocabularyManager:
    """单词本管理器"""
    
    def __init__(self, db_path: Optional[str] = None):
        # 使用系统默认数据库
        if db_path is None:
            # 使用配置管理器获取默认数据库路径
            config_manager = ConfigManager()
            config = config_manager.get_config()
            self.db_path = os.path.expanduser(config["paths"]["database"])
        else:
            # 使用指定的数据库路径
            self.db_path = os.path.expanduser(db_path)
        self._init_database()
        
    def _init_database(self) -> None:
        """初始化数据库"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 创建单词表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS vocabulary (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    word TEXT NOT NULL,
                    translation TEXT NOT NULL,
                    language TEXT DEFAULT 'en',
                    context TEXT DEFAULT '',
                    book_id TEXT DEFAULT '',
                    position INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    review_count INTEGER DEFAULT 0,
                    last_reviewed TIMESTAMP,
                    mastery_level INTEGER DEFAULT 0,
                    UNIQUE(word, book_id, position)
                )
            ''')
            
            # 创建索引
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_word ON vocabulary(word)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_book_id ON vocabulary(book_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_language ON vocabulary(language)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_created_at ON vocabulary(created_at)')
            
            conn.commit()
            conn.close()
            logger.info("单词本数据库表初始化成功")
            
        except Exception as e:
            logger.error(f"单词本数据库表初始化失败: {e}")
            raise
    
    def add_word(self, word: str, translation: str, language: str = "en", 
                 context: str = "", book_id: str = "", position: int = 0) -> Optional[VocabularyItem]:
        """添加单词到单词本"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 检查是否已存在
            cursor.execute(
                'SELECT id FROM vocabulary WHERE word = ? AND book_id = ? AND position = ?',
                (word, book_id or "", position or 0)
            )
            existing = cursor.fetchone()
            
            if existing:
                # 更新已存在的记录
                cursor.execute('''
                    UPDATE vocabulary 
                    SET translation = ?, language = ?, context = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (translation, language, context, existing[0]))
                item_id = existing[0]
            else:
                # 插入新记录
                cursor.execute('''
                    INSERT INTO vocabulary 
                    (word, translation, language, context, book_id, position)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (word, translation, language, context, book_id or "", position or 0))
                item_id = cursor.lastrowid
            
            conn.commit()
            conn.close()
            
            if item_id:
                return self.get_word_by_id(item_id)
            return None
            
        except Exception as e:
            logger.error(f"添加单词失败: {e}")
            return None
    
    def get_word_by_id(self, word_id: int) -> Optional[VocabularyItem]:
        """根据ID获取单词"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM vocabulary WHERE id = ?', (word_id,))
            row = cursor.fetchone()
            conn.close()
            
            if row:
                return self._row_to_vocabulary_item(row)
            return None
            
        except Exception as e:
            logger.error(f"获取单词失败: {e}")
            return None
    
    def get_words_by_book(self, book_id: str) -> List[VocabularyItem]:
        """获取指定书籍的所有单词"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM vocabulary WHERE book_id = ? ORDER BY position', (book_id or "",))
            rows = cursor.fetchall()
            conn.close()
            
            return [self._row_to_vocabulary_item(row) for row in rows]
            
        except Exception as e:
            logger.error(f"获取书籍单词失败: {e}")
            return []
    
    def get_all_words(self, language: str = None) -> List[VocabularyItem]:
        """获取所有单词"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            if language:
                cursor.execute('SELECT * FROM vocabulary WHERE language = ? ORDER BY created_at DESC', (language,))
            else:
                cursor.execute('SELECT * FROM vocabulary ORDER BY created_at DESC')
                
            rows = cursor.fetchall()
            conn.close()
            
            return [self._row_to_vocabulary_item(row) for row in rows]
            
        except Exception as e:
            logger.error(f"获取所有单词失败: {e}")
            return []
    
    def search_words(self, keyword: str) -> List[VocabularyItem]:
        """搜索单词"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute(
                'SELECT * FROM vocabulary WHERE word LIKE ? OR translation LIKE ? ORDER BY created_at DESC',
                (f'%{keyword}%', f'%{keyword}%')
            )
            rows = cursor.fetchall()
            conn.close()
            
            return [self._row_to_vocabulary_item(row) for row in rows]
            
        except Exception as e:
            logger.error(f"搜索单词失败: {e}")
            return []
    
    def update_word(self, word_id: int, **kwargs) -> bool:
        """更新单词信息"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 构建更新语句
            set_clause = []
            params = []
            
            for key, value in kwargs.items():
                if key in ['word', 'translation', 'language', 'context', 'review_count', 'mastery_level']:
                    set_clause.append(f"{key} = ?")
                    params.append(value)
            
            if not set_clause:
                return False
                
            set_clause.append("updated_at = CURRENT_TIMESTAMP")
            params.append(word_id)
            
            cursor.execute(
                f'UPDATE vocabulary SET {", ".join(set_clause)} WHERE id = ?',
                params
            )
            
            conn.commit()
            conn.close()
            return cursor.rowcount > 0
            
        except Exception as e:
            logger.error(f"更新单词失败: {e}")
            return False
    
    def delete_word(self, word_id: int) -> bool:
        """删除单词"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('DELETE FROM vocabulary WHERE id = ?', (word_id,))
            conn.commit()
            conn.close()
            
            return cursor.rowcount > 0
            
        except Exception as e:
            logger.error(f"删除单词失败: {e}")
            return False
    
    def record_review(self, word_id: int, mastery_level: int = None) -> bool:
        """记录单词复习"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            update_fields = ['review_count = review_count + 1', 'last_reviewed = CURRENT_TIMESTAMP']
            params = []
            
            if mastery_level is not None:
                update_fields.append('mastery_level = ?')
                params.append(mastery_level)
                
            params.append(word_id)
            
            cursor.execute(
                f'UPDATE vocabulary SET {", ".join(update_fields)} WHERE id = ?',
                params
            )
            
            conn.commit()
            conn.close()
            return cursor.rowcount > 0
            
        except Exception as e:
            logger.error(f"记录复习失败: {e}")
            return False
    
    def get_words_for_review(self, limit: int = 20) -> List[VocabularyItem]:
        """获取需要复习的单词"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM vocabulary 
                WHERE mastery_level < 5 OR mastery_level IS NULL
                ORDER BY last_reviewed ASC NULLS FIRST, created_at ASC
                LIMIT ?
            ''', (limit,))
            
            rows = cursor.fetchall()
            conn.close()
            
            return [self._row_to_vocabulary_item(row) for row in rows]
            
        except Exception as e:
            logger.error(f"获取复习单词失败: {e}")
            return []
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 总单词数
            cursor.execute('SELECT COUNT(*) FROM vocabulary')
            total_words = cursor.fetchone()[0]
            
            # 按掌握程度统计
            cursor.execute('''
                SELECT mastery_level, COUNT(*) 
                FROM vocabulary 
                GROUP BY mastery_level 
                ORDER BY mastery_level
            ''')
            mastery_stats = {row[0]: row[1] for row in cursor.fetchall()}
            
            # 按语言统计
            cursor.execute('''
                SELECT language, COUNT(*) 
                FROM vocabulary 
                GROUP BY language 
                ORDER BY COUNT(*) DESC
            ''')
            language_stats = {row[0]: row[1] for row in cursor.fetchall()}
            
            # 今日新增
            cursor.execute('''
                SELECT COUNT(*) FROM vocabulary 
                WHERE DATE(created_at) = DATE('now')
            ''')
            today_new = cursor.fetchone()[0]
            
            conn.close()
            
            return {
                'total_words': total_words,
                'mastery_stats': mastery_stats,
                'language_stats': language_stats,
                'today_new': today_new
            }
            
        except Exception as e:
            logger.error(f"获取统计信息失败: {e}")
            return {}
    
    def _row_to_vocabulary_item(self, row) -> VocabularyItem:
        """将数据库行转换为VocabularyItem对象"""
        # 先创建基础对象
        item = VocabularyItem(
            item_id=row[0],
            word=row[1],
            translation=row[2],
            language=row[3],
            context=row[4],
            book_id=row[5],
            position=row[6],
            created_at=datetime.fromisoformat(row[7]) if row[7] else None,
            updated_at=datetime.fromisoformat(row[8]) if row[8] else None
        )
        
        # 设置额外的属性
        if row[9] is not None:  # review_count
            item.review_count = row[9]
        if row[10] is not None:  # last_reviewed
            item.last_reviewed = datetime.fromisoformat(row[10]) if row[10] else None
        if row[11] is not None:  # mastery_level
            item.mastery_level = row[11]
            
        return item

# 全局单词本管理器实例
_vocabulary_manager = None

def get_vocabulary_manager() -> VocabularyManager:
    """获取全局单词本管理器实例"""
    global _vocabulary_manager
    if _vocabulary_manager is None:
        _vocabulary_manager = VocabularyManager()
    return _vocabulary_manager

def init_vocabulary_manager(db_path: Optional[str] = None) -> VocabularyManager:
    """初始化全局单词本管理器"""
    global _vocabulary_manager
    _vocabulary_manager = VocabularyManager(db_path)
    return _vocabulary_manager