"""
帮助文档自动生成器
通过 importlib 导入所有 Screen/Dialog 模块，读取已翻译的 BINDINGS，生成分类 Markdown
"""

import importlib
import inspect

from src.utils.logger import get_logger

logger = get_logger(__name__)

# 屏幕模块列表
_SCREEN_MODULES = [
    "src.ui.screens.welcome_screen",
    "src.ui.screens.bookshelf_screen",
    "src.ui.screens.reader_screen",
    "src.ui.screens.help_screen",
    "src.ui.screens.settings_screen",
    "src.ui.screens.statistics_screen",
    "src.ui.screens.boss_key_screen",
    "src.ui.screens.file_explorer_screen",
    "src.ui.screens.get_books_screen",
    "src.ui.screens.search_results_screen",
    "src.ui.screens.bookmarks_screen",
    "src.ui.screens.compare_reader_screen",
    "src.ui.screens.crawler_management_screen",
    "src.ui.screens.novel_sites_management_screen",
    "src.ui.screens.proxy_list_screen",
    "src.ui.screens.login_screen",
    "src.ui.screens.lock_screen",
    "src.ui.screens.users_management_screen",
]

# 弹窗模块列表
_DIALOG_MODULES = [
    "src.ui.dialogs.confirm_dialog",
    "src.ui.dialogs.input_dialog",
    "src.ui.dialogs.search_dialog",
    "src.ui.dialogs.sort_dialog",
    "src.ui.dialogs.page_dialog",
    "src.ui.dialogs.chapter_dialog",
    "src.ui.dialogs.directory_dialog",
    "src.ui.dialogs.file_chooser_dialog",
    "src.ui.dialogs.password_dialog",
    "src.ui.dialogs.bookmark_dialog",
    "src.ui.dialogs.bookmark_edit_dialog",
    "src.ui.dialogs.content_search_dialog",
    "src.ui.dialogs.translation_dialog",
    "src.ui.dialogs.vocabulary_dialog",
    "src.ui.dialogs.review_dialog",
    "src.ui.dialogs.batch_ops_dialog",
    "src.ui.dialogs.batch_input_dialog",
    "src.ui.dialogs.rename_book_dialog",
    "src.ui.dialogs.duplicate_books_dialog",
    "src.ui.dialogs.scan_progress_dialog",
    "src.ui.dialogs.novel_site_dialog",
    "src.ui.dialogs.proxy_edit_dialog",
    "src.ui.dialogs.select_books_dialog",
    "src.ui.dialogs.search_results_dialog",
    "src.ui.dialogs.crawler_merge_dialog",
    "src.ui.dialogs.book_comparison_dialog",
    "src.ui.dialogs.note_dialog",
    "src.ui.dialogs.permissions_dialog",
]


class HelpGenerator:
    """自动扫描所有 Screen/Dialog 的 BINDINGS 并生成分类 Markdown"""

    def __init__(self):
        self._app_bindings: list[tuple[str, str, str]] = []
        self._screens: dict[str, dict] = {}
        self._dialogs: dict[str, dict] = {}
        self._scanned = False

    # ------------------------------------------------------------------
    # 公开 API
    # ------------------------------------------------------------------

    def generate_markdown(self) -> str:
        """生成完整的分类 Markdown 帮助文档"""
        self._ensure_scanned()

        # 获取 i18n 翻译函数
        try:
            from src.locales.i18n_manager import get_global_i18n
            t_fn = get_global_i18n().t
        except Exception:
            t_fn = lambda k: k

        lines: list[str] = []
        lines.append(f"# {t_fn('help.sub_title')}\n\n")

        # ---- 快捷键 ----
        lines.append(f"## {t_fn('help.keyboard_shortcuts')}\n\n")

        # 全局
        if self._app_bindings:
            lines.append(f"### {t_fn('help.global')}\n\n")
            for key, _action, desc in self._app_bindings:
                lines.append(f"- **{self._format_key(key)}** : {desc}\n")
            lines.append("\n")

        # 页面分组
        for group_title, screens in self._group_screens():
            group_lines: list[str] = []
            for _name, info in screens:
                bindings = info.get("bindings", [])
                if not bindings:
                    continue
                group_lines.append(f"### {info.get('title', _name)}\n\n")
                for key, _action, desc in bindings:
                    group_lines.append(f"- **{self._format_key(key)}** : {desc}\n")
                group_lines.append("\n")
            if group_lines:
                lines.extend(group_lines)

        # 弹窗分组
        if self._dialogs:
            dialogs_title = t_fn("help.dialogs") if t_fn("help.dialogs") != "help.dialogs" else "弹窗快捷键"
            lines.append(f"## {dialogs_title}\n\n")
            for group_title, dialogs in self._group_dialogs():
                group_lines = []
                for _name, info in dialogs:
                    bindings = info.get("bindings", [])
                    if not bindings:
                        continue
                    group_lines.append(f"### {info.get('title', _name)}\n\n")
                    for key, _action, desc in bindings:
                        group_lines.append(f"- **{self._format_key(key)}** : {desc}\n")
                    group_lines.append("\n")
                if group_lines:
                    lines.extend(group_lines)

        # ---- 关于 ----
        lines.append(f"## {t_fn('help.about')}\n\n")
        lines.append(f"{t_fn('help.about_content')}\n")

        return "".join(lines)

    # ------------------------------------------------------------------
    # 扫描
    # ------------------------------------------------------------------

    def _ensure_scanned(self) -> None:
        if self._scanned:
            return
        self._scan_app_bindings()
        self._scan_modules(_SCREEN_MODULES, is_modal=False)
        self._scan_modules(_DIALOG_MODULES, is_modal=True)
        self._scanned = True
        logger.debug(
            f"帮助扫描完成: {len(self._app_bindings)} 全局 + "
            f"{len(self._screens)} 屏幕 + {len(self._dialogs)} 弹窗"
        )

    def _scan_app_bindings(self) -> None:
        try:
            from src.ui.app import NewReaderApp
            for b in getattr(NewReaderApp, "BINDINGS", []):
                norm = self._normalize_binding(b)
                if norm:
                    self._app_bindings.append(norm)
        except Exception as e:
            logger.warning(f"扫描 app BINDINGS 失败: {e}")

    def _scan_modules(self, module_names: list[str], is_modal: bool) -> None:
        # 延迟导入 textual 类型，避免非 app 环境崩溃
        try:
            from textual.screen import Screen, ModalScreen
        except ImportError:
            logger.warning("无法导入 textual.screen，跳过扫描")
            return

        base = ModalScreen if is_modal else Screen
        target = self._dialogs if is_modal else self._screens

        for mod_name in module_names:
            try:
                module = importlib.import_module(mod_name)
            except Exception as e:
                logger.debug(f"跳过 {mod_name}: {e}")
                continue

            for cls_name, cls in inspect.getmembers(module, inspect.isclass):
                try:
                    if not issubclass(cls, base):
                        continue
                    if cls in (Screen, ModalScreen):
                        continue
                    # Screen 类型的检测：非 is_modal 时排除 ModalScreen
                    if not is_modal and issubclass(cls, ModalScreen):
                        continue
                except TypeError:
                    continue

                bindings_raw = getattr(cls, "BINDINGS", [])
                if not bindings_raw:
                    continue

                doc = inspect.getdoc(cls) or cls_name
                title = doc.split("\n")[0].strip("。，. ")

                bindings: list[tuple[str, str, str]] = []
                for b in bindings_raw:
                    norm = self._normalize_binding(b)
                    if norm:
                        bindings.append(norm)

                if bindings:
                    target[cls_name] = {
                        "title": title,
                        "module": mod_name.rsplit(".", 1)[-1],
                        "bindings": bindings,
                    }
            logger.debug(f"扫描: {mod_name} -> {len(target)} 条目")

    # ------------------------------------------------------------------
    # 工具
    # ------------------------------------------------------------------

    @staticmethod
    def _normalize_binding(b) -> tuple[str, str, str] | None:
        """将 Binding 对象或元组统一转换为 (key, action, description) 元组"""
        # Textual Binding 对象 (key, action, description 属性)
        if hasattr(b, "key") and hasattr(b, "action") and hasattr(b, "description"):
            key = str(getattr(b, "key", ""))
            action = str(getattr(b, "action", ""))
            desc = str(getattr(b, "description", ""))
            if key and action:
                return (key, action, desc)
            return None

        # 传统元组格式 (key, action) 或 (key, action, description)
        try:
            length = len(b)  # type: ignore[arg-type]
            if length >= 3:
                return (str(b[0]), str(b[1]), str(b[2]))
            elif length == 2:
                return (str(b[0]), str(b[1]), str(b[1]))
        except (TypeError, IndexError):
            pass

        return None

    @staticmethod
    def _format_key(key: str) -> str:
        """格式化快捷键显示：特殊键用符号替换，其余保留原始大小写"""
        mapping = {
            "escape": "ESC", "return": "Enter", "space": "Space",
            "slash": "/",
            "left": "←", "right": "→", "up": "↑", "down": "↓",
            "ctrl+c": "Ctrl+C", "ctrl+s": "Ctrl+S",
            "shift+left": "Shift+←", "shift+right": "Shift+→",
            "shift+up": "Shift+↑", "shift+down": "Shift+↓",
        }
        parts = key.split(",")
        out = []
        for p in parts:
            p = p.strip()
            out.append(mapping.get(p.lower(), p))
        return " / ".join(out)

    # ------------------------------------------------------------------
    # 分组
    # ------------------------------------------------------------------

    def _group_screens(self) -> list[tuple[str, list]]:
        order = [
            ("欢迎", ["welcome"]),
            ("书架", ["bookshelf"]),
            ("阅读", ["reader", "bookmark"]),
            ("获取书籍", ["get_books"]),
            ("爬取管理", ["crawler"]),
            ("书籍网站管理", ["novel_site"]),
            ("代理管理", ["proxy"]),
            ("文件管理", ["file_explorer"]),
            ("搜索", ["search"]),
            ("统计", ["statistic"]),
            ("设置", ["setting"]),
            ("用户管理", ["user", "login", "lock"]),
            ("帮助", ["help"]),
            ("其他", ["boss", "compare"]),
        ]
        return self._group(self._screens, order, "其他页面")

    def _group_dialogs(self) -> list[tuple[str, list]]:
        order = [
            ("通用操作", ["confirm", "input", "directory", "file_chooser", "password"]),
            ("书架相关", ["batch", "search_dialog", "sort", "rename", "duplicate", "scan"]),
            ("阅读相关", ["page", "chapter", "content_search", "bookmark", "translation", "vocabulary", "review"]),
            ("爬取相关", ["crawler", "novel_site", "proxy_edit", "select_books"]),
            ("对比与笔记", ["comparison", "note"]),
            ("权限管理", ["permission"]),
        ]
        return self._group(self._dialogs, order, "其他弹窗")

    @staticmethod
    def _group(
        items: dict[str, dict], order: list[tuple[str, list[str]]], fallback_label: str
    ) -> list[tuple[str, list]]:
        grouped: dict[str, list] = {g[0]: [] for g in order}
        ungrouped: list = []

        for name, info in items.items():
            placed = False
            search = f"{name.lower()} {info.get('module', '').lower()}"
            for grp, keywords in order:
                if any(kw in search for kw in keywords):
                    grouped[grp].append((name, info))
                    placed = True
                    break
            if not placed:
                ungrouped.append((name, info))

        result = []
        for grp, _ in order:
            if grouped[grp]:
                result.append((grp, grouped[grp]))
        if ungrouped:
            result.append((fallback_label, ungrouped))
        return result
