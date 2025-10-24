"""
老板键屏幕 - 模拟终端界面
"""


import os
import subprocess
import threading
from typing import Dict, Any, Optional, List, ClassVar
from datetime import datetime

from textual.app import ComposeResult
from textual.screen import Screen
from textual.containers import Container, Vertical, Horizontal
from textual.widgets import Static, Input, Label
from textual.reactive import reactive
from textual import events, on

from src.themes.theme_manager import ThemeManager
from src.locales.i18n_manager import get_global_i18n
from src.ui.styles.universal_style_isolation import apply_universal_style_isolation, remove_universal_style_isolation
from src.core.database_manager import DatabaseManager

from src.utils.logger import get_logger

logger = get_logger(__name__)

class BossKeyScreen(Screen[None]):

    """老板键屏幕 - 模拟真实终端"""
    
    CSS_PATH = "../styles/boss_key_overrides.tcss"
    
    TITLE: ClassVar[Optional[str]] = "Terminal"
    
    def __init__(self, theme_manager: ThemeManager):
        """
        初始化老板键屏幕
        
        Args:
            theme_manager: 主题管理器
        """
        super().__init__()
        self.theme_manager = theme_manager
        self.db_manager = DatabaseManager()  # 数据库管理器
        
        # 终端状态
        self.command_history: List[str] = []
        self.history_index: int = -1
        self.current_directory = os.getcwd()
        self.output_lines: List[str] = []
        
        # 获取用户名和主机名
        self.username = os.getenv('USER', 'user')
        self.hostname = os.getenv('HOSTNAME', 'localhost')
        
        # 初始化终端输出
        self._add_welcome_message()

    def _has_permission(self, permission_key: str) -> bool:
        """检查权限"""
        try:
            return self.db_manager.has_permission(permission_key)
        except Exception as e:
            logger.error(f"检查权限失败: {e}")
            return True  # 出错时默认允许
    
    def compose(self) -> ComposeResult:
        """组合老板键屏幕界面"""
        yield Container(
            Vertical(
                Static("", id="terminal-output"),
                Horizontal(
                    Label(self._get_prompt(), id="terminal-prompt"),
                    Input(placeholder="", id="terminal-input"),
                    id="terminal-input-container"
                ),
                id="terminal-container"
            )
        )
    
    def on_mount(self) -> None:
        """屏幕挂载时的回调"""
        """组件挂载时应用样式隔离"""
        # 应用通用样式隔离
        apply_universal_style_isolation(self)
        # 设置焦点到输入框
        input_widget = self.query_one("#terminal-input", Input)
        input_widget.focus()
        
        # 更新输出显示
        self._update_output()
        
        # 更新提示符
        self._update_prompt()
    
    def _add_welcome_message(self) -> None:
        """添加欢迎消息"""
        welcome_lines = [
            f"Last login: {datetime.now().strftime('%a %b %d %H:%M:%S')} on ttys000",
            f"{self.username}@{self.hostname}:~$ ",
            "",
            "# Terminal Mode - Type 'exit' or press Ctrl+C to exit",
            "# Type 'help' for available commands",
            ""
        ]
        self.output_lines.extend(welcome_lines)
    
    def _get_prompt(self) -> str:
        """获取命令提示符"""
        # 简化路径显示
        home_dir = os.path.expanduser("~")
        if self.current_directory.startswith(home_dir):
            display_dir = "~" + self.current_directory[len(home_dir):]
        else:
            display_dir = self.current_directory
        
        return f"{self.username}@{self.hostname}:{display_dir}$ "
    
    def _update_prompt(self) -> None:
        """更新命令提示符"""
        try:
            prompt_widget = self.query_one("#terminal-prompt", Label)
            prompt_widget.update(self._get_prompt())
        except Exception:
            pass
    
    def _update_output(self) -> None:
        """更新终端输出"""
        try:
            output_widget = self.query_one("#terminal-output", Static)
            # 只显示最近的输出行，避免内存占用过多
            display_lines = self.output_lines[-100:] if len(self.output_lines) > 100 else self.output_lines
            output_widget.update("\n".join(display_lines))
        except Exception:
            pass
    
    @on(Input.Submitted)
    def on_input_submitted(self, event: Input.Submitted) -> None:
        """处理命令输入"""
        command = event.value.strip()
        
        if command:
            # 添加到历史记录
            self.command_history.append(command)
            self.history_index = len(self.command_history)
            
            # 显示命令
            self.output_lines.append(f"{self._get_prompt()}{command}")
            
            # 执行命令
            self._execute_command(command)
        else:
            # 空命令，只显示提示符
            self.output_lines.append(self._get_prompt())
        
        # 清空输入框
        event.input.value = ""
        
        # 更新显示
        self._update_output()
        self._update_prompt()
    
    def _execute_command(self, command: str) -> None:
        """执行终端命令"""
        try:
            # 处理特殊命令
            if command == "exit" or command == "quit":
                self.app.pop_screen()
                return
            elif command == "clear" or command == "cls":
                self.output_lines = []
                self._add_welcome_message()
                return
            elif command.startswith("cd "):
                self._handle_cd_command(command)
                return
            elif command == "pwd":
                self.output_lines.append(self.current_directory)
                return
            elif command == "whoami":
                self.output_lines.append(self.username)
                return
            elif command == "date":
                self.output_lines.append(datetime.now().strftime('%a %b %d %H:%M:%S %Z %Y'))
                return
            elif command == "help" or command == "?":
                self._show_help()
                return
            
            # 执行真实的系统命令
            self._execute_system_command(command)
            
        except Exception as e:
            self.output_lines.append(f"Error executing command: {e}")
            logger.error(f"{get_global_i18n().t('boss_key.exec_command_failed')}: {e}")
    
    def _handle_cd_command(self, command: str) -> None:
        """处理cd命令"""
        try:
            parts = command.split(None, 1)
            if len(parts) == 1:
                # cd without arguments - go to home directory
                target_dir = os.path.expanduser("~")
            else:
                target_dir = parts[1]
                
                # 处理相对路径和绝对路径
                if not os.path.isabs(target_dir):
                    target_dir = os.path.join(self.current_directory, target_dir)
                
                # 展开用户目录符号
                target_dir = os.path.expanduser(target_dir)
            
            # 规范化路径
            target_dir = os.path.normpath(target_dir)
            
            # 检查目录是否存在
            if os.path.isdir(target_dir):
                self.current_directory = target_dir
                os.chdir(target_dir)  # 同时更改Python的工作目录
            else:
                self.output_lines.append(f"cd: {target_dir}: No such file or directory")
                
        except Exception as e:
            self.output_lines.append(f"cd: {e}")
    
    def _execute_system_command(self, command: str) -> None:
        """执行系统命令"""
        def run_command():
            try:
                # 在当前目录执行命令
                result = subprocess.run(
                    command,
                    shell=True,
                    cwd=self.current_directory,
                    capture_output=True,
                    text=True,
                    timeout=30  # 30秒超时
                )
                
                # 处理输出
                if result.stdout:
                    self.output_lines.extend(result.stdout.strip().split('\n'))
                if result.stderr:
                    self.output_lines.extend(result.stderr.strip().split('\n'))
                
                # 如果命令失败，显示返回码
                if result.returncode != 0:
                    self.output_lines.append(f"Command exited with code {result.returncode}")
                
                # 更新显示（在主线程中）
                self.app.schedule_on_ui(self._update_output)
                
            except subprocess.TimeoutExpired:
                self.output_lines.append("Command timed out after 30 seconds")
                self.app.schedule_on_ui(self._update_output)
            except Exception as e:
                self.output_lines.append(f"Error: {e}")
                self.app.schedule_on_ui(self._update_output)
        
        # 在后台线程执行命令，避免阻塞UI
        thread = threading.Thread(target=run_command, daemon=True)
        thread.start()
    
    def _show_help(self) -> None:
        """显示帮助信息"""
        help_text = [
            "Available commands:",
            "  exit, quit  - Exit Terminal mode",
            "  clear, cls  - Clear screen",
            "  cd <dir>    - Change directory",
            "  pwd         - Print working directory",
            "  whoami      - Print current user",
            "  date        - Print current date and time",
            "  help, ?     - Show this help",
            "",
            "You can also run any system command available in your shell.",
            "Press Ctrl+C or type 'exit' to exit Terminal mode.",
            ""
        ]
        self.output_lines.extend(help_text)
    
    def on_key(self, event: events.Key) -> None:
        """处理键盘事件"""
        if event.key == "ctrl+c":
            # Ctrl+C 退出老板键模式
            self.app.pop_screen()
            event.prevent_default()
        elif event.key == "up":
            # 上箭头 - 历史命令向上
            self._navigate_history(-1)
            event.prevent_default()
        elif event.key == "down":
            # 下箭头 - 历史命令向下
            self._navigate_history(1)
            event.prevent_default()
    
    def _navigate_history(self, direction: int) -> None:
        """导航命令历史"""
        if not self.command_history:
            return
        
        # 更新历史索引
        new_index = self.history_index + direction
        
        if 0 <= new_index < len(self.command_history):
            self.history_index = new_index
            command = self.command_history[self.history_index]
        elif new_index >= len(self.command_history):
            self.history_index = len(self.command_history)
            command = ""
        else:
            return  # 不能再往上了
        
        # 更新输入框
        try:
            input_widget = self.query_one("#terminal-input", Input)
            input_widget.value = command
            input_widget.cursor_position = len(command)
        except Exception:
            pass