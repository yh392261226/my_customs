"""
用户与权限管理（仅超级管理员）
"""
from typing import Optional, Dict, Any, List, ClassVar, Set
from textual.screen import Screen
from textual.containers import Container, Vertical, Horizontal
from textual.widgets import Label, Input, Button, DataTable
from textual.app import ComposeResult
from src.core.database_manager import DatabaseManager
from src.themes.theme_manager import ThemeManager
from src.locales.i18n_manager import get_global_i18n
from src.utils.logger import get_logger
from src.ui.dialogs.confirm_dialog import ConfirmDialog
from src.ui.dialogs.permissions_dialog import PermissionsDialog
from src.ui.styles.universal_style_isolation import apply_universal_style_isolation
from src.utils.multi_user_manager import multi_user_manager

logger = get_logger(__name__)

class UsersManagementScreen(Screen[None]):
    CSS_PATH = "../styles/users_management_overrides.tcss"

    BINDINGS: ClassVar[list[tuple[str, str, str]]] = [
        ("q", "press('#back-btn')", "返回"),
    ]

    def __init__(self, theme_manager: ThemeManager, db_manager: DatabaseManager):
        super().__init__()
        self.theme_manager = theme_manager
        self.db_manager = db_manager
        self._editing_user_id: Optional[int] = None
        self._new_username = ""
        self._new_password = ""
        self._perm_input = ""

    def compose(self) -> ComposeResult:
        t = get_global_i18n()
        yield Container(
            Vertical(
                Label(t.t('users_management.title'), id="um-title"),
                Horizontal(
                    Input(placeholder=t.t('users_management.new_username'), id="new-username"),
                    Input(placeholder=t.t('users_management.new_password'), password=True, id="new-password"),
                    Button(t.t('users_management.add_new_user'), id="add-user"),
                    id="um-new-user",
                ),
                Horizontal(
                    Input(placeholder=t.t('users_management.username'), id="edit-username"),
                    Input(placeholder=t.t('users_management.password'), password=True, id="edit-password"),
                    Button(t.t("common.edit"), id="edit-user"),
                    Button(t.t("common.cancel"), id="cancel-edit-user"),
                    id="um-edit-user",
                ),
                # Horizontal(
                #     Input(placeholder="用户ID", id="perm-user-id"),
                #     Input(placeholder="权限键（逗号分隔）", id="perm-keys"),
                #     Button("设置权限", id="set-perms"),
                #     id="um-set-perms",
                # ),
                DataTable(id="users-table"),
                Horizontal(
                    Button(t.t('common.back'), id="back-btn"),
                    id="um-back",
                ),
                id="um-container"
            )
        )

    def _has_permission(self, permission_key: str) -> bool:
        """检查权限"""
        try:
            from src.core.database_manager import DatabaseManager
            db_manager = DatabaseManager()
            return db_manager.has_permission(permission_key)
        except Exception as e:
            logger.error(f"检查权限失败: {e}")
            return True  # 出错时默认允许
    
    def _check_button_permissions(self) -> None:
        """检查按钮权限并禁用/启用按钮"""
        try:
            add_user_btn = self.query_one("#add-user", Button)
            
            # 检查权限并设置按钮状态
            if not self._has_permission("users.add"):
                add_user_btn.disabled = True
                add_user_btn.tooltip = get_global_i18n().t('users_management.no_permission')
            else:
                add_user_btn.disabled = False
                add_user_btn.tooltip = None
                
        except Exception as e:
            logger.error(f"检查按钮权限失败: {e}")
    
    def on_mount(self) -> None:
        # 应用通用样式隔离，避免外层样式干扰
        try:
            apply_universal_style_isolation(self)
        except Exception:
            pass
        try:
            self.theme_manager.apply_theme_to_screen(self)
        except Exception:
            pass
        # 默认隐藏编辑区域
        try:
            self.query_one("#um-edit-user").styles.display = "none"
        except Exception:
            pass

        # 检查按钮权限并禁用/启用按钮
        self._check_button_permissions()

        # 初始化用户表
        table = self.query_one("#users-table", DataTable)
        table.add_column("ID", key="id")
        table.add_column(get_global_i18n().t('users_management.username'), key="username")
        table.add_column(get_global_i18n().t('users_management.role'), key="role")
        table.add_column(get_global_i18n().t('users_management.perms'), key="perms")
        table.add_column(get_global_i18n().t('users_management.view_perms'), key="view_perms")
        table.add_column(get_global_i18n().t('common.edit'), key="edit")
        table.add_column(get_global_i18n().t('common.delete'), key="delete")
        
        # 启用隔行变色效果
        table.zebra_stripes = True
        
        self._reload_users_table()

    def _reload_users_table(self) -> None:
        """重新加载用户列表"""
        import sqlite3
        conn = None
        try:
            table = self.query_one("#users-table", DataTable)
            table.clear()
            conn = sqlite3.connect(self.db_manager.db_path)
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute("SELECT id, username, role FROM users ORDER BY id ASC")
            rows = cur.fetchall()
            for row in rows:
                uid = str(row["id"])
                uname = row["username"]
                role = row["role"]
                try:
                    table.add_row(uid, uname, role, f"[{get_global_i18n().t('users_management.role')}]", f"[{get_global_i18n().t('users_management.view_perms')}]", f"[{get_global_i18n().t('common.edit')}]", f"[{get_global_i18n().t('common.delete')}]", key=uid)
                except Exception as re:
                    logger.error(f"添加行失败: {re} (uid={uid})")
        except Exception as e:
            logger.error(f"{get_global_i18n().t('users_management.load_user_failed')}: {e}")
            try:
                self.notify(f"{get_global_i18n().t('users_management.load_user_failed')}：{e}", severity="error")
            except Exception:
                pass
        finally:
            try:
                if conn:
                    conn.close()
            except Exception:
                pass

    def _open_permissions_dialog(self, uid: int) -> None:
        """打开权限管理对话框"""
        try:
            # 收集所有权限和用户当前权限
            all_perms = self._collect_all_permissions()
            user_perms = self._get_user_permissions_safe(uid)
            
            if not all_perms:
                self.notify(get_global_i18n().t('users_management.no_perms'), severity="warning")
                return
            
            # 获取用户名用于显示
            username = self._get_username_by_id(uid)
            
            def handle_permissions_result(result: Optional[Set[str]]) -> None:
                """处理权限设置结果"""
                if result is not None:
                    # 用户确认了权限设置
                    try:
                        # 将权限集合转换为列表
                        permissions_list = list(result)
                        success = self._set_user_permissions_safe(uid, permissions_list)
                        
                        if success:
                            self.notify(get_global_i18n().t('users_management.set_perms_success'), severity="information")
                            self._reload_users_table()  # 刷新用户列表
                        else:
                            self.notify(get_global_i18n().t('users_management.set_perms_failed'), severity="error")
                    except Exception as e:
                        logger.error(f"保存权限失败: {e}")
                        self.notify(get_global_i18n().t('users_management.save_perms_failed'), severity="error")
            
            # 打开新的权限管理对话框
            self.app.push_screen(
                PermissionsDialog(
                    theme_manager=self.theme_manager,
                    user_id=uid,
                    username=username or f"{get_global_i18n().t('users_management.user')}{uid}",
                    all_permissions=all_perms,
                    user_permissions=user_perms
                ),
                callback=handle_permissions_result
            )
            
        except Exception as e:
            logger.error(f"打开权限对话框失败: {e}")
            self.notify(get_global_i18n().t('users_management.cannot_open_perms_dialog'), severity="error")



    # --- 权限适配与扫描工具 ---
    def _collect_all_permissions(self) -> List[str]:
        """收集系统中的所有权限键（优先数据库 permissions 表，其次 db_manager，最后代码扫描）"""
        dm = self.db_manager
        # 0) 直接从数据库 permissions 表读取
        try:
            import sqlite3
            conn = sqlite3.connect(dm.db_path)  # type: ignore[attr-defined]
            cur = conn.cursor()
            # 兼容不同列名：优先读取 key；若无则尝试 name
            keys: list[str] = []
            try:
                cur.execute("SELECT key FROM permissions")
                keys = [str(r[0]) for r in cur.fetchall() if r and r[0] is not None]
            except Exception:
                try:
                    cur.execute("SELECT name FROM permissions")
                    keys = [str(r[0]) for r in cur.fetchall() if r and r[0] is not None]
                except Exception:
                    keys = []
            conn.close()
            if keys:
                # 去重、排序
                return sorted(set(keys))
        except Exception as e:
            logger.debug(f"从 permissions 表读取失败: {e}")
        # 1) 从 db_manager 方法/属性获取
        try:
            for name in ("get_all_permissions", "list_permissions"):
                if hasattr(dm, name):
                    res = getattr(dm, name)()
                    if isinstance(res, (list, tuple, set)):
                        return [str(x) for x in res]
        except Exception as e:
            logger.debug(f"从 db_manager 获取所有权限失败: {e}")
        try:
            for attr in ("permissions", "all_permission_keys", "permission_keys", "ALL_PERMISSIONS", "PERMISSIONS"):
                if hasattr(dm, attr):
                    res = getattr(dm, attr)
                    if isinstance(res, (list, tuple, set)):
                        return [str(x) for x in res]
                    if isinstance(res, dict):
                        return [str(k) for k in res.keys()]
        except Exception as e:
            logger.debug(f"从 db_manager 属性读取权限失败: {e}")
        # 2) 代码扫描兜底
        try:
            import re
            from pathlib import Path
            root = Path(__file__).resolve().parents[3]  # .../newreader
            src_dir = root / "src"
            patterns = [
                r'REQUIRES?_PERMISSION\s*\(\s*[\'"]([^\'"]+)[\'"]\s*\)',
                r'@requires_permission\(\s*[\'"]([^\'"]+)[\'"]\s*\)',
                r'@permission\(\s*[\'"]([^\'"]+)[\'"]\s*\)',
                r'["\']([a-zA-Z0-9_\.\-:]+)["\']\s*[,)]\s*#\s*perm',
                r'ALL_PERMISSIONS\s*=\s*\[([^\]]+)\]',
                r'PERMISSIONS\s*=\s*\[([^\]]+)\]',
                r'ROLE_PERMISSIONS\s*=\s*\{([^\}]+)\}',
            ]
            keys: set[str] = set()
            if src_dir.exists():
                for py in src_dir.rglob("*.py"):
                    if any(seg.startswith(".") for seg in py.parts):
                        continue
                    try:
                        text = py.read_text(encoding="utf-8", errors="ignore")
                    except Exception:
                        continue
                    for pat in patterns:
                        for m in re.finditer(pat, text):
                            grp = m.group(1) if m.groups() else ""
                            if grp:
                                if "[" in grp or "," in grp:
                                    for s in re.findall(r'[\'"]([^\'"]+)[\'"]', grp):
                                        if s:
                                            keys.add(s)
                                else:
                                    keys.add(grp)
            if keys:
                return sorted(keys)
        except Exception as e:
            logger.debug(f"扫描代码提取权限失败: {e}")
        return []

    def _get_user_permissions_safe(self, uid: int) -> set[str]:
        """兼容多命名的获取用户权限接口，不存在则返回空集合"""
        dm = self.db_manager
        candidates = ("get_user_permissions", "list_user_permissions", "fetch_user_permissions")
        for name in candidates:
            try:
                if hasattr(dm, name):
                    res = getattr(dm, name)(int(uid))
                    if isinstance(res, (list, tuple, set)):
                        return set(str(x) for x in res)
                    if isinstance(res, dict):
                        return set(str(k) for k, v in res.items() if v)
            except Exception as e:
                logger.debug(f"{name} 获取用户权限失败: {e}")
        # 属性兜底
        for attr in ("user_permissions",):
            try:
                if hasattr(dm, attr):
                    up = getattr(dm, attr)
                    if isinstance(up, dict):
                        res = up.get(int(uid)) or up.get(str(uid))
                        if isinstance(res, (list, tuple, set)):
                            return set(str(x) for x in res)
            except Exception as e:
                logger.debug(f"通过属性获取用户权限失败: {e}")
        return set()

    def _get_username_by_id(self, uid: int) -> Optional[str]:
        """根据用户ID获取用户名"""
        try:
            import sqlite3
            conn = sqlite3.connect(self.db_manager.db_path)
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute("SELECT username FROM users WHERE id=?", (uid,))
            row = cur.fetchone()
            conn.close()
            return row["username"] if row else None
        except Exception as e:
            logger.error(f"获取用户名失败: {e}")
            return None

    def _view_user_permissions(self, uid: int) -> None:
        """查看用户已有权限（使用对话框显示）"""
        try:
            # 获取用户权限
            user_perms = self._get_user_permissions_safe(uid)
            
            # 获取权限描述信息
            permissions_data = self._get_permissions_data()
            
            # 获取用户名
            username = self._get_username_by_id(uid) or f"{get_global_i18n().t('users_management.user')}{uid}"
            
            # 显示权限列表
            if not user_perms:
                self.notify(f"{username} {get_global_i18n().t('users_management.no_perms')}", severity="information")
                return
            
            # 使用权限对话框显示权限列表（只读模式）
            def handle_view_result(result: Optional[Set[str]]) -> None:
                """处理查看权限结果（只读模式，不需要处理）"""
                # 查看权限对话框是只读的，不需要处理结果
                pass
            
            # 打开权限对话框（只读模式）
            self.app.push_screen(
                PermissionsDialog(
                    theme_manager=self.theme_manager,
                    user_id=uid,
                    username=username,
                    all_permissions=list(permissions_data.keys()),
                    user_permissions=user_perms,
                    read_only=True  # 设置为只读模式
                ),
                callback=handle_view_result
            )
            
        except Exception as e:
            logger.error(f"查看用户权限失败: {e}")
            self.notify(get_global_i18n().t('users_management.open_user_perms_failed'), severity="error")

    def _get_permissions_data(self) -> Dict[str, str]:
        """获取权限的完整信息（key -> description）"""
        try:
            permissions = self.db_manager.get_all_permissions()
            return {perm['key']: perm['description'] for perm in permissions}
        except Exception as e:
            logger.error(f"获取权限数据失败: {e}")
            return {}

    def _set_user_permissions_safe(self, uid: int, keys: list[str]) -> bool:
        """兼容多命名的设置用户权限接口，返回是否成功"""
        dm = self.db_manager
        candidates = ("set_user_permissions", "update_user_permissions")
        for name in candidates:
            try:
                if hasattr(dm, name):
                    ok = getattr(dm, name)(int(uid), keys)
                    return bool(ok)
            except Exception as e:
                logger.debug(f"{name} 设置权限失败: {e}")
        return False

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "new-username":
            self._new_username = event.value or ""
        elif event.input.id == "new-password":
            self._new_password = event.value or ""
        elif event.input.id == "perm-keys":
            self._perm_input = event.value or ""

    def _has_table_action_permission(self, action: str, user_id: int) -> bool:
        """检查表格操作的权限"""
        permission_map = {
            "perms": "users.set_permissions",
            "view_perms": "users.view_permissions",
            "edit": "users.edit",
            "delete": "users.delete"
        }
        
        if action in permission_map:
            return self._has_permission(permission_map[action])
        
        return True  # 默认允许未知操作
    
    def on_data_table_cell_selected(self, event: DataTable.CellSelected) -> None:
        """点击表格的权限/编辑/删除列"""
        try:
            cell_key = event.cell_key
            column = cell_key.column_key.value or ""
            row_key = cell_key.row_key.value or ""
            
            # 检查权限
            if not self._has_table_action_permission(column, int(row_key) if row_key else 0):
                self.notify(get_global_i18n().t('users_management.np_action'), severity="warning")
                return
                
            if column == "perms":
                # 检查多用户设置是否启用
                # if not multi_user_manager.should_show_permissions():
                #     self.notify(get_global_i18n().t('users_management.multi_user_disabled_super'), severity="information")
                #     return
                
                # 检查权限
                if not self._has_permission("users.set_permissions"):
                    self.notify(get_global_i18n().t('users_management.np_set_user_perms'), severity="warning")
                    return
                
                # 打开权限对话框
                try:
                    uid = int(row_key) if row_key else 0
                    if uid <= 0:
                        self.notify(get_global_i18n().t('users_management.unknown_userid'), severity="error")
                        return
                    self._open_permissions_dialog(uid)
                except Exception:
                    self.notify(get_global_i18n().t('users_management.unknown_userid'), severity="error")
                    return

            elif column == "view_perms":
                # 查看用户已有权限
                try:
                    uid = int(row_key) if row_key else 0
                    if uid <= 0:
                        self.notify(get_global_i18n().t('users_management.unknown_userid'), severity="error")
                        return
                    self._view_user_permissions(uid)
                except Exception:
                    self.notify(get_global_i18n().t('users_management.unknown_userid'), severity="error")
                    return

            elif column == "edit":
                # 显示编辑区域并填充
                try:
                    box = self.query_one("#um-edit-user")
                    box.styles.display = "block"
                except Exception:
                    pass
                try:
                    table = self.query_one("#users-table", DataTable)
                    row = table.get_row(row_key) if row_key else []
                    username_val = row[1] if isinstance(row, (list, tuple)) and len(row) > 1 else ""
                    self.query_one("#edit-username", Input).value = str(username_val)
                except Exception:
                    pass
                # 记住当前编辑的用户ID
                self._editing_user_id = int(row_key) if row_key else None
            elif column == "delete":
                # 删除用户
                def on_confirm(confirmed: Optional[bool]) -> None:
                    """处理确认结果"""
                    if not confirmed:
                        return
                    
                    import sqlite3
                    try:
                        conn = sqlite3.connect(self.db_manager.db_path)
                        cur = conn.cursor()
                        cur.execute("DELETE FROM users WHERE id=?", (int(row_key) if row_key else 0,))
                        if cur.rowcount == 0:
                            conn.close()
                            self.notify(get_global_i18n().t('users_management.delete_user_failed_info'), severity="warning")
                            return
                        conn.commit()
                        conn.close()
                        self._reload_users_table()
                    except Exception as e:
                        logger.error(f"删除用户失败: {e}")
                        self.notify(get_global_i18n().t('users_management.delete_user_failed'), severity="error")
                        return

                # 弹出确认对话框
                self.app.push_screen(
                    ConfirmDialog(
                        self.theme_manager,
                        get_global_i18n().t('users_management.confirm_delete'),
                        get_global_i18n().t('users_management.confirm_delete_user')
                    ),
                    callback=on_confirm
                )
        except Exception as e:
            logger.error(f"处理表格点击失败: {e}")

    def _has_button_permission(self, button_id: str) -> bool:
        """检查按钮权限"""
        permission_map = {
            "add-user": "users.add",
            "edit-user": "users.edit",
            "set-perms": "users.set_permissions"
        }
        
        if button_id in permission_map:
            return self._has_permission(permission_map[button_id])
        
        return True  # 默认允许未知按钮
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        # 检查权限
        button_id = event.button.id or ""
        if not self._has_button_permission(button_id):
            self.notify(get_global_i18n().t('users_management.np_action'), severity="warning")
            return
            
        if event.button.id == "add-user":
            # 检查多用户设置是否启用
            if not multi_user_manager.should_show_user_management():
                self.notify(get_global_i18n().t('users_management.multi_user_disabled_super'), severity="information")
                return
                
            # 检查权限
            if not self._has_permission("users.add"):
                self.notify(get_global_i18n().t('users_management.np_add_user'), severity="warning")
                return
                
            try:
                uid = self.db_manager.create_user(self._new_username.strip(), self._new_password)
                if uid:
                    self.notify(f"{get_global_i18n().t('users_management.add_user_success')}：ID {uid}", severity="information")
                    self._reload_users_table()
                else:
                    self.notify(get_global_i18n().t('users_management.add_user_failed'), severity="error")
            except Exception as e:
                logger.error(f"添加用户失败: {e}")
                self.notify(get_global_i18n().t('users_management.add_user_failed'), severity="error")

        elif event.button.id == "set-perms":
            try:
                uid_text = self.query_one("#perm-user-id", Input).value
                uid = int(uid_text) if uid_text else 0
                keys = [k.strip() for k in (self._perm_input or "").split(",") if k.strip()]
                ok = self.db_manager.set_user_permissions(uid, keys)
                if ok:
                    self.notify(get_global_i18n().t('users_management.set_perms_success'), severity="information")
                else:
                    self.notify(get_global_i18n().t('users_management.set_perms_failed'), severity="error")
            except Exception as e:
                logger.error(f"权限设置失败: {e}")
                self.notify(get_global_i18n().t('users_management.set_perms_failed'), severity="error")
        elif event.button.id == "edit-user":
            # 保存编辑：密码可为空
            try:
                uid = getattr(self, "_editing_user_id", None)
                if not uid:
                    self.notify(get_global_i18n().t('users_management.no_user_selected'), severity="warning")
                    return
                new_name = (self.query_one("#edit-username", Input).value or "").strip()
                new_pwd = self.query_one("#edit-password", Input).value or ""
                if not new_name:
                    self.notify(get_global_i18n().t('users_management.empty_username'), severity="warning")
                    return
                import sqlite3, hashlib
                conn = sqlite3.connect(self.db_manager.db_path)
                cur = conn.cursor()
                # 先改用户名
                cur.execute("UPDATE users SET username=? WHERE id=?", (new_name, int(uid)))
                pwd_updated = False
                # 再改密码（如提供）
                if new_pwd:
                    try:
                        if hasattr(self.db_manager, "set_user_password"):
                            # 优先走统一入口，要求返回 True 才视为成功
                            try:
                                ok = bool(self.db_manager.set_user_password(int(uid), new_pwd))  # type: ignore[attr-defined]
                            except Exception as pe:
                                logger.debug(f"调用 set_user_password 异常: {pe}")
                                ok = False
                            if ok:
                                pwd_updated = True
                            else:
                                # 失败则回退至直接更新
                                ph = hashlib.sha256(new_pwd.encode("utf-8")).hexdigest()
                                updated_cols = 0
                                try:
                                    cur.execute("UPDATE users SET password_hash=? WHERE id=?", (ph, int(uid)))
                                    updated_cols += cur.rowcount or 0
                                except Exception:
                                    pass
                                if updated_cols == 0:
                                    try:
                                        cur.execute("UPDATE users SET password=? WHERE id=?", (ph, int(uid)))
                                        updated_cols += cur.rowcount or 0
                                    except Exception:
                                        pass
                                pwd_updated = updated_cols > 0
                        else:
                            ph = hashlib.sha256(new_pwd.encode("utf-8")).hexdigest()
                            updated_cols = 0
                            try:
                                cur.execute("UPDATE users SET password_hash=? WHERE id=?", (ph, int(uid)))
                                updated_cols += cur.rowcount or 0
                            except Exception:
                                pass
                            if updated_cols == 0:
                                try:
                                    cur.execute("UPDATE users SET password=? WHERE id=?", (ph, int(uid)))
                                    updated_cols += cur.rowcount or 0
                                except Exception:
                                    pass
                            pwd_updated = updated_cols > 0
                    except Exception as pe:
                        logger.debug(f"设置新密码失败（已尝试兜底）: {pe}")
                        pwd_updated = False
                conn.commit()
                conn.close()
                # 刷新并隐藏编辑区
                self._reload_users_table()
                try:
                    box = self.query_one("#um-edit-user")
                    box.styles.display = "none"
                except Exception:
                    pass
                # 根据是否有提供新密码以及是否更新成功给出不同提示
                if new_pwd and not pwd_updated:
                    self.notify(get_global_i18n().t('users_management.username_ok_password_failed'), severity="warning")
                else:
                    self.notify(get_global_i18n().t('users_management.edit_success'), severity="information")
            except Exception as e:
                logger.error(f"修改失败: {e}")
                self.notify(get_global_i18n().t('users_management.edit_failed'), severity="error")

        elif event.button.id == "back-btn":
            try:
                self.app.pop_screen()
            except Exception:
                pass
        elif event.button.id == "cancel-edit-user":
            # 直接清空修改的inupt和隐藏修改的区域
            self.query_one("#edit-username", Input).value = ""
            self.query_one("#um-edit-user").styles.display = "none"        
