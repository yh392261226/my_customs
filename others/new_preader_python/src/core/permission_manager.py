"""
权限控制系统
用于管理用户权限和访问控制
"""

import json
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set
from enum import Enum

from src.utils.logger import get_logger
from src.core.database_manager import DatabaseManager

logger = get_logger(__name__)

class Permission(Enum):
    """权限枚举"""
    # 书籍相关权限
    BOOK_READ = "book.read"
    BOOK_WRITE = "book.write"
    BOOK_DELETE = "book.delete"
    BOOK_ADD = "book.add"
    
    # 书签相关权限
    BOOKMARK_READ = "bookmark.read"
    BOOKMARK_WRITE = "bookmark.write"
    BOOKMARK_DELETE = "bookmark.delete"
    
    # 搜索相关权限
    SEARCH_READ = "search.read"
    
    # 设置相关权限
    SETTINGS_READ = "settings.read"
    SETTINGS_WRITE = "settings.write"
    
    # 统计相关权限
    STATS_READ = "stats.read"
    STATS_WRITE = "stats.write"
    
    # 用户管理权限
    USER_MANAGE = "user.manage"
    PERMISSION_MANAGE = "permission.manage"
    
    # 系统管理权限
    SYSTEM_ADMIN = "system.admin"


class Role(Enum):
    """角色枚举"""
    ANONYMOUS = "anonymous"      # 匿名用户
    READER = "reader"            # 普通读者
    CONTRIBUTOR = "contributor"  # 贡献者
    MODERATOR = "moderator"      # 版主
    ADMIN = "admin"              # 管理员
    SUPER_ADMIN = "super_admin"  # 超级管理员


class User:
    """用户模型"""
    
    def __init__(self, user_id: int, username: str, role: Role, permissions: List[Permission] = None):
        self.id = user_id
        self.username = username
        self.role = role
        self.permissions = set(permissions) if permissions else set()
        self.created_at = datetime.now()
        self.last_login = None
        self.is_active = True
        self.failed_login_attempts = 0
        self.locked_until = None
    
    def has_permission(self, permission: Permission) -> bool:
        """检查用户是否有特定权限"""
        # 超级管理员拥有所有权限
        if self.role == Role.SUPER_ADMIN:
            return True
        
        # 检查直接权限
        if permission in self.permissions:
            return True
        
        # 根据角色赋予默认权限
        role_permissions = self._get_role_permissions(self.role)
        return permission in role_permissions
    
    def add_permission(self, permission: Permission):
        """添加权限"""
        self.permissions.add(permission)
    
    def remove_permission(self, permission: Permission):
        """移除权限"""
        self.permissions.discard(permission)
    
    def is_locked(self) -> bool:
        """检查用户是否被锁定"""
        if self.locked_until and datetime.now() < self.locked_until:
            return True
        return False
    
    def lock_account(self, duration_minutes: int = 30):
        """锁定账户"""
        self.locked_until = datetime.now() + timedelta(minutes=duration_minutes)
        self.failed_login_attempts = 0
    
    def unlock_account(self):
        """解锁账户"""
        self.locked_until = None
        self.failed_login_attempts = 0
    
    def increment_failed_login(self):
        """增加失败登录次数"""
        self.failed_login_attempts += 1
        # 如果失败次数过多，锁定账户
        if self.failed_login_attempts >= 5:
            self.lock_account()
    
    @staticmethod
    def _get_role_permissions(role: Role) -> Set[Permission]:
        """获取角色默认权限"""
        role_permissions = {
            Role.ANONYMOUS: {
                Permission.BOOK_READ,
                Permission.SEARCH_READ
            },
            Role.READER: {
                Permission.BOOK_READ,
                Permission.BOOKMARK_READ,
                Permission.BOOKMARK_WRITE,
                Permission.SEARCH_READ,
                Permission.STATS_READ
            },
            Role.CONTRIBUTOR: {
                Permission.BOOK_READ,
                Permission.BOOK_WRITE,
                Permission.BOOKMARK_READ,
                Permission.BOOKMARK_WRITE,
                Permission.BOOKMARK_DELETE,
                Permission.SEARCH_READ,
                Permission.STATS_READ
            },
            Role.MODERATOR: {
                Permission.BOOK_READ,
                Permission.BOOK_WRITE,
                Permission.BOOK_DELETE,
                Permission.BOOK_ADD,
                Permission.BOOKMARK_READ,
                Permission.BOOKMARK_WRITE,
                Permission.BOOKMARK_DELETE,
                Permission.SEARCH_READ,
                Permission.SETTINGS_READ,
                Permission.STATS_READ
            },
            Role.ADMIN: {
                Permission.BOOK_READ,
                Permission.BOOK_WRITE,
                Permission.BOOK_DELETE,
                Permission.BOOK_ADD,
                Permission.BOOKMARK_READ,
                Permission.BOOKMARK_WRITE,
                Permission.BOOKMARK_DELETE,
                Permission.SEARCH_READ,
                Permission.SETTINGS_READ,
                Permission.SETTINGS_WRITE,
                Permission.STATS_READ,
                Permission.STATS_WRITE,
                Permission.USER_MANAGE
            },
            Role.SUPER_ADMIN: set(Permission)  # 拥有所有权限
        }
        return role_permissions.get(role, set())


class PermissionManager:
    """权限管理器"""

    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        """
        初始化权限管理器

        Args:
            db_manager: 数据库管理器实例，如果为None则创建默认实例
        """
        if db_manager is None:
            from src.core.database_manager import DatabaseManager
            db_manager = DatabaseManager()
        self.db_manager = db_manager
        self._init_permissions_table()

    def _init_permissions_table(self):
        """初始化权限相关数据库表"""
        # 创建权限表
        create_permissions_sql = """
        CREATE TABLE IF NOT EXISTS permissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            description TEXT,
            category TEXT DEFAULT 'general',
            created_at TEXT NOT NULL
        )
        """

        # 创建角色表
        create_roles_sql = """
        CREATE TABLE IF NOT EXISTS roles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            description TEXT,
            permissions TEXT,  -- JSON格式存储权限列表
            created_at TEXT NOT NULL
        )
        """

        # 创建用户角色关联表
        create_user_roles_sql = """
        CREATE TABLE IF NOT EXISTS user_roles (
            user_id INTEGER NOT NULL,
            role_id INTEGER NOT NULL,
            assigned_at TEXT NOT NULL,
            assigned_by INTEGER,
            PRIMARY KEY (user_id, role_id)
        )
        """

        # 创建用户权限表
        create_user_permissions_sql = """
        CREATE TABLE IF NOT EXISTS user_permissions (
            user_id INTEGER NOT NULL,
            permission_name TEXT NOT NULL,
            granted_at TEXT NOT NULL,
            granted_by INTEGER,
            is_granted BOOLEAN DEFAULT 1,
            PRIMARY KEY (user_id, permission_name)
        )
        """

        try:
            # 使用数据库管理器执行创建表的SQL
            self.db_manager.execute_query(create_permissions_sql)
            self.db_manager.execute_query(create_roles_sql)
            self.db_manager.execute_query(create_user_roles_sql)
            self.db_manager.execute_query(create_user_permissions_sql)

            # 插入默认权限
            default_permissions = [
                ('book.read', '阅读书籍', 'general'),
                ('book.write', '编辑书籍', 'general'),
                ('book.delete', '删除书籍', 'general'),
                ('bookmark.read', '查看书签', 'general'),
                ('bookmark.write', '添加/编辑书签', 'general'),
                ('bookmark.delete', '删除书签', 'general'),
                ('search.use', '使用搜索', 'general'),
                ('settings.read', '查看设置', 'general'),
                ('settings.write', '修改设置', 'general'),
                ('stats.read', '查看统计', 'general'),
            ]

            for perm_name, desc, category in default_permissions:
                insert_perm_sql = """
                INSERT OR IGNORE INTO permissions (name, description, category, created_at)
                VALUES (?, ?, ?, ?)
                """
                self.db_manager.execute_query(insert_perm_sql,
                                            (perm_name, desc, category, datetime.now().isoformat()))

            # 插入默认角色
            default_roles = [
                ('reader', '读者', '["book.read", "bookmark.write", "search.use"]'),
                ('editor', '编辑', '["book.read", "book.write", "bookmark.write", "search.use", "stats.read"]'),
                ('admin', '管理员', '["book.read", "book.write", "book.delete", "bookmark.write", "bookmark.delete", "search.use", "settings.read", "settings.write", "stats.read"]')
            ]

            for role_name, desc, perms in default_roles:
                insert_role_sql = """
                INSERT OR IGNORE INTO roles (name, description, permissions, created_at)
                VALUES (?, ?, ?, ?)
                """
                self.db_manager.execute_query(insert_role_sql,
                                            (role_name, desc, perms, datetime.now().isoformat()))

        except Exception as e:
            logger.error(f"初始化权限表失败: {e}")
    
    def _init_permissions_table(self):
        """初始化权限相关数据库表"""
        with self.db_manager._get_connection() as conn:
            cursor = conn.cursor()
            
            # 创建权限表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS permissions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    description TEXT,
                    category TEXT DEFAULT 'general',
                    created_at TEXT NOT NULL
                )
            """)
            
            # 创建角色表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS roles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    description TEXT,
                    default_permissions TEXT,  -- JSON格式存储默认权限
                    created_at TEXT NOT NULL
                )
            """)
            
            # 创建用户角色关联表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_roles (
                    user_id INTEGER NOT NULL,
                    role_id INTEGER NOT NULL,
                    assigned_at TEXT NOT NULL,
                    assigned_by INTEGER,
                    PRIMARY KEY (user_id, role_id),
                    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
                    FOREIGN KEY (role_id) REFERENCES roles (id) ON DELETE CASCADE
                )
            """)
            
            # 创建用户权限关联表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_permissions (
                    user_id INTEGER NOT NULL,
                    permission_name TEXT NOT NULL,
                    granted_at TEXT NOT NULL,
                    granted_by INTEGER,
                    is_granted BOOLEAN DEFAULT 1,
                    PRIMARY KEY (user_id, permission_name),
                    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
                )
            """)
            
            # 创建角色权限关联表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS role_permissions (
                    role_id INTEGER NOT NULL,
                    permission_name TEXT NOT NULL,
                    assigned_at TEXT NOT NULL,
                    assigned_by INTEGER,
                    PRIMARY KEY (role_id, permission_name),
                    FOREIGN KEY (role_id) REFERENCES roles (id) ON DELETE CASCADE
                )
            """)
            
            # 创建会话表（用于权限验证）
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    session_token TEXT UNIQUE NOT NULL,
                    created_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    ip_address TEXT,
                    user_agent TEXT,
                    is_active BOOLEAN DEFAULT 1,
                    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
                )
            """)
            
            # 创建索引
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_sessions_token ON user_sessions(session_token)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_sessions_user ON user_sessions(user_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_sessions_expires ON user_sessions(expires_at)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_permissions_user ON user_permissions(user_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_permissions_perm ON user_permissions(permission_name)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_roles_user ON user_roles(user_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_roles_role ON user_roles(role_id)")
            
            conn.commit()
            
            # 初始化默认权限
            self._init_default_permissions(cursor)
            
            # 初始化默认角色
            self._init_default_roles(cursor)
    
    def _init_default_permissions(self, cursor):
        """初始化默认权限"""
        created_at = datetime.now().isoformat()
        
        for perm in Permission:
            cursor.execute("""
                INSERT OR IGNORE INTO permissions (name, description, category, created_at)
                VALUES (?, ?, ?, ?)
            """, (perm.value, f"权限: {perm.name}", "general", created_at))
    
    def _init_default_roles(self, cursor):
        """初始化默认角色"""
        created_at = datetime.now().isoformat()
        
        for role in Role:
            # 获取角色默认权限
            default_perms = User._get_role_permissions(role)
            perms_json = json.dumps([perm.value for perm in default_perms])
            
            cursor.execute("""
                INSERT OR IGNORE INTO roles (name, description, default_permissions, created_at)
                VALUES (?, ?, ?, ?)
            """, (role.value, f"角色: {role.name}", perms_json, created_at))
    
    def check_permission(self, user_id: int, permission: str) -> bool:
        """
        检查用户是否有特定权限
        
        Args:
            user_id: 用户ID
            permission: 权限名称
            
        Returns:
            是否有权限
        """
        try:
            with self.db_manager._get_connection() as conn:
                cursor = conn.cursor()
                
                # 检查用户是否为超级管理员
                cursor.execute("""
                    SELECT role.name FROM users u
                    JOIN roles role ON u.role = role.name
                    WHERE u.id = ? AND role.name = ?
                """, (user_id, Role.SUPER_ADMIN.value))
                
                if cursor.fetchone():
                    return True  # 超级管理员拥有所有权限
                
                # 检查用户直接权限
                cursor.execute("""
                    SELECT is_granted FROM user_permissions
                    WHERE user_id = ? AND permission_name = ?
                """, (user_id, permission))
                
                user_perm = cursor.fetchone()
                if user_perm and user_perm[0]:
                    return True
                
                # 检查用户角色权限
                cursor.execute("""
                    SELECT rp.permission_name FROM role_permissions rp
                    JOIN user_roles ur ON rp.role_id = ur.role_id
                    WHERE ur.user_id = ? AND rp.permission_name = ?
                """, (user_id, permission))
                
                return cursor.fetchone() is not None
                
        except Exception as e:
            logger.error(f"检查权限失败: {e}")
            return False
    
    def grant_permission(self, user_id: int, permission: str, granted_by: int = None) -> bool:
        """
        授予用户权限
        
        Args:
            user_id: 用户ID
            permission: 权限名称
            granted_by: 授予权限的用户ID
            
        Returns:
            是否成功
        """
        try:
            with self.db_manager._get_connection() as conn:
                cursor = conn.cursor()
                
                # 检查权限是否存在
                cursor.execute("SELECT id FROM permissions WHERE name = ?", (permission,))
                if not cursor.fetchone():
                    logger.error(f"权限不存在: {permission}")
                    return False
                
                granted_at = datetime.now().isoformat()
                
                # 插入或更新用户权限
                cursor.execute("""
                    INSERT OR REPLACE INTO user_permissions 
                    (user_id, permission_name, granted_at, granted_by, is_granted)
                    VALUES (?, ?, ?, ?, 1)
                """, (user_id, permission, granted_at, granted_by))
                
                conn.commit()
                logger.info(f"权限 {permission} 已授予用户 {user_id}")
                return True
                
        except Exception as e:
            logger.error(f"授予权限失败: {e}")
            return False
    
    def revoke_permission(self, user_id: int, permission: str) -> bool:
        """
        撤销用户权限
        
        Args:
            user_id: 用户ID
            permission: 权限名称
            
        Returns:
            是否成功
        """
        try:
            with self.db_manager._get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    UPDATE user_permissions 
                    SET is_granted = 0
                    WHERE user_id = ? AND permission_name = ?
                """, (user_id, permission))
                
                conn.commit()
                logger.info(f"权限 {permission} 已从用户 {user_id} 撤销")
                return cursor.rowcount > 0
                
        except Exception as e:
            logger.error(f"撤销权限失败: {e}")
            return False
    
    def assign_role(self, user_id: int, role_name: str, assigned_by: int = None) -> bool:
        """
        为用户分配角色
        
        Args:
            user_id: 用户ID
            role_name: 角色名称
            assigned_by: 分配角色的用户ID
            
        Returns:
            是否成功
        """
        try:
            with self.db_manager._get_connection() as conn:
                cursor = conn.cursor()
                
                # 检查角色是否存在
                cursor.execute("SELECT id FROM roles WHERE name = ?", (role_name,))
                role_result = cursor.fetchone()
                if not role_result:
                    logger.error(f"角色不存在: {role_name}")
                    return False
                
                role_id = role_result[0]
                assigned_at = datetime.now().isoformat()
                
                # 分配角色
                cursor.execute("""
                    INSERT OR REPLACE INTO user_roles (user_id, role_id, assigned_at, assigned_by)
                    VALUES (?, ?, ?, ?)
                """, (user_id, role_id, assigned_at, assigned_by))
                
                conn.commit()
                logger.info(f"角色 {role_name} 已分配给用户 {user_id}")
                return True
                
        except Exception as e:
            logger.error(f"分配角色失败: {e}")
            return False
    
    def remove_role(self, user_id: int, role_name: str) -> bool:
        """
        移除用户角色
        
        Args:
            user_id: 用户ID
            role_name: 角色名称
            
        Returns:
            是否成功
        """
        try:
            with self.db_manager._get_connection() as conn:
                cursor = conn.cursor()
                
                # 检查角色是否存在
                cursor.execute("SELECT id FROM roles WHERE name = ?", (role_name,))
                role_result = cursor.fetchone()
                if not role_result:
                    logger.error(f"角色不存在: {role_name}")
                    return False
                
                role_id = role_result[0]
                
                cursor.execute("""
                    DELETE FROM user_roles
                    WHERE user_id = ? AND role_id = ?
                """, (user_id, role_id))
                
                conn.commit()
                logger.info(f"角色 {role_name} 已从用户 {user_id} 移除")
                return cursor.rowcount > 0
                
        except Exception as e:
            logger.error(f"移除角色失败: {e}")
            return False
    
    def get_user_permissions(self, user_id: int) -> List[str]:
        """
        获取用户的所有权限
        
        Args:
            user_id: 用户ID
            
        Returns:
            权限列表
        """
        try:
            with self.db_manager._get_connection() as conn:
                cursor = conn.cursor()
                
                permissions = set()
                
                # 获取用户直接权限
                cursor.execute("""
                    SELECT permission_name FROM user_permissions
                    WHERE user_id = ? AND is_granted = 1
                """, (user_id,))
                
                for row in cursor.fetchall():
                    permissions.add(row[0])
                
                # 获取用户角色权限
                cursor.execute("""
                    SELECT rp.permission_name FROM role_permissions rp
                    JOIN user_roles ur ON rp.role_id = ur.role_id
                    WHERE ur.user_id = ?
                """, (user_id,))
                
                for row in cursor.fetchall():
                    permissions.add(row[0])
                
                # 如果是超级管理员，添加所有权限
                cursor.execute("""
                    SELECT role.name FROM users u
                    JOIN roles role ON u.role = role.name
                    WHERE u.id = ? AND role.name = ?
                """, (user_id, Role.SUPER_ADMIN.value))
                
                if cursor.fetchone():
                    cursor.execute("SELECT name FROM permissions")
                    all_perms = [row[0] for row in cursor.fetchall()]
                    permissions.update(all_perms)
                
                return list(permissions)
                
        except Exception as e:
            logger.error(f"获取用户权限失败: {e}")
            return []
    
    def get_user_roles(self, user_id: int) -> List[str]:
        """
        获取用户的所有角色
        
        Args:
            user_id: 用户ID
            
        Returns:
            角色列表
        """
        try:
            with self.db_manager._get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT r.name FROM roles r
                    JOIN user_roles ur ON r.id = ur.role_id
                    WHERE ur.user_id = ?
                """, (user_id,))
                
                return [row[0] for row in cursor.fetchall()]
                
        except Exception as e:
            logger.error(f"获取用户角色失败: {e}")
            return []
    
    def create_session(self, user_id: int, ip_address: str = None, user_agent: str = None) -> Optional[str]:
        """
        创建用户会话
        
        Args:
            user_id: 用户ID
            ip_address: IP地址
            user_agent: 用户代理
            
        Returns:
            会话令牌，如果失败则返回None
        """
        try:
            session_token = secrets.token_urlsafe(32)
            created_at = datetime.now()
            expires_at = created_at + timedelta(hours=24)  # 24小时有效期
            
            with self.db_manager._get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT INTO user_sessions 
                    (user_id, session_token, created_at, expires_at, ip_address, user_agent)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (user_id, session_token, created_at.isoformat(), 
                      expires_at.isoformat(), ip_address, user_agent))
                
                conn.commit()
                return session_token
                
        except Exception as e:
            logger.error(f"创建会话失败: {e}")
            return None
    
    def validate_session(self, session_token: str) -> Optional[int]:
        """
        验证会话令牌
        
        Args:
            session_token: 会话令牌
            
        Returns:
            用户ID，如果无效则返回None
        """
        try:
            with self.db_manager._get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT user_id FROM user_sessions
                    WHERE session_token = ? AND is_active = 1
                    AND expires_at > ?
                """, (session_token, datetime.now().isoformat()))
                
                result = cursor.fetchone()
                return result[0] if result else None
                
        except Exception as e:
            logger.error(f"验证会话失败: {e}")
            return None
    
    def invalidate_session(self, session_token: str) -> bool:
        """
        使会话失效
        
        Args:
            session_token: 会话令牌
            
        Returns:
            是否成功
        """
        try:
            with self.db_manager._get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    UPDATE user_sessions
                    SET is_active = 0
                    WHERE session_token = ?
                """, (session_token,))
                
                conn.commit()
                return cursor.rowcount > 0
                
        except Exception as e:
            logger.error(f"使会话失效失败: {e}")
            return False
    
    def hash_password(self, password: str) -> str:
        """
        哈希密码
        
        Args:
            password: 明文密码
            
        Returns:
            哈希后的密码
        """
        salt = secrets.token_hex(16)
        pwdhash = hashlib.pbkdf2_hmac('sha256', 
                                      password.encode('utf-8'), 
                                      salt.encode('utf-8'), 
                                      100000)
        return salt + pwdhash.hex()
    
    def verify_password(self, password: str, hashed_pwd: str) -> bool:
        """
        验证密码
        
        Args:
            password: 明文密码
            hashed_pwd: 哈希密码
            
        Returns:
            密码是否正确
        """
        if len(hashed_pwd) < 32:  # 长度不够，不是有效的哈希
            return False
        
        salt = hashed_pwd[:32]
        stored_pwd = hashed_pwd[32:]
        pwdhash = hashlib.pbkdf2_hmac('sha256',
                                      password.encode('utf-8'),
                                      salt.encode('utf-8'),
                                      100000)
        return pwdhash.hex() == stored_pwd