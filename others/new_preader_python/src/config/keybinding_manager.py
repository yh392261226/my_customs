"""
快捷键配置管理器
用于管理用户自定义快捷键
"""

import json
import os
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

from src.config.default_config import DEFAULT_CONFIG
from src.utils.logger import get_logger

logger = get_logger(__name__)

@dataclass
class KeyBinding:
    """快捷键绑定数据类"""
    action: str
    keys: List[str]
    category: str = "general"
    description: str = ""


class KeyBindingManager:
    """快捷键配置管理器"""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        初始化快捷键管理器
        
        Args:
            config_path: 配置文件路径，如果为None则使用默认路径
        """
        self.config_path = config_path or self._get_default_config_path()
        self.default_bindings = self._load_default_bindings()
        self.current_bindings = self.default_bindings.copy()
        self._load_user_config()
    
    def _get_default_config_path(self) -> str:
        """获取默认配置文件路径"""
        config_dir = os.path.expanduser(DEFAULT_CONFIG["paths"]["config_dir"])
        os.makedirs(config_dir, exist_ok=True)
        return os.path.join(config_dir, "keybindings.json")
    
    def _load_default_bindings(self) -> Dict[str, KeyBinding]:
        """从默认配置加载快捷键绑定"""
        bindings = {}
        keybindings_config = DEFAULT_CONFIG.get("keybindings", {})
        
        for action, keys in keybindings_config.items():
            if isinstance(keys, str):
                keys = [keys]
            elif not isinstance(keys, list):
                keys = []
            
            # 根据动作名称确定类别和描述
            category = self._get_category_for_action(action)
            description = self._get_description_for_action(action)
            
            bindings[action] = KeyBinding(
                action=action,
                keys=keys,
                category=category,
                description=description
            )
        
        return bindings
    
    def _get_category_for_action(self, action: str) -> str:
        """根据动作名称确定类别"""
        if action in ["prev_page", "next_page", "scroll_up", "scroll_down", 
                      "goto_page", "toggle_auto_page", "bookmark", "bookmark_list", 
                      "search", "toggle_tts"]:
            return "reading"
        elif action in ["toggle_theme", "change_language", "open_settings", 
                        "toggle_fullscreen", "show_help", "quit"]:
            return "interface"
        elif action in ["open_bookshelf", "add_book", "add_book_directory", 
                        "batch_operations", "export_data", "view_statistics", 
                        "view_global_statistics"]:
            return "bookshelf"
        elif action in ["boss_key", "reset_progress", "adjust_font_size", 
                        "adjust_line_spacing", "adjust_paragraph_spacing"]:
            return "advanced"
        else:
            return "general"
    
    def _get_description_for_action(self, action: str) -> str:
        """根据动作名称获取描述"""
        descriptions = {
            "prev_page": "上一页",
            "next_page": "下一页",
            "scroll_up": "向上滚动",
            "scroll_down": "向下滚动",
            "goto_page": "跳转到指定页",
            "toggle_auto_page": "切换自动翻页",
            "bookmark": "添加书签",
            "bookmark_list": "书签列表",
            "search": "搜索",
            "toggle_tts": "切换文本朗读",
            "toggle_theme": "切换主题",
            "change_language": "切换语言",
            "open_settings": "打开设置",
            "toggle_fullscreen": "切换全屏",
            "show_help": "显示帮助",
            "quit": "退出",
            "open_bookshelf": "打开书架",
            "add_book": "添加书籍",
            "add_book_directory": "添加书籍目录",
            "batch_operations": "批量操作",
            "export_data": "导出数据",
            "view_statistics": "查看统计",
            "view_global_statistics": "查看全局统计",
            "boss_key": "老板键",
            "reset_progress": "重置进度",
            "adjust_font_size": "调整字体大小",
            "adjust_line_spacing": "调整行间距",
            "adjust_paragraph_spacing": "调整段落间距"
        }
        return descriptions.get(action, action.replace("_", " ").title())
    
    def _load_user_config(self):
        """加载用户自定义配置"""
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    user_config = json.load(f)
                
                # 更新当前绑定
                for action, keys in user_config.items():
                    if action in self.current_bindings:
                        if isinstance(keys, str):
                            keys = [keys]
                        elif not isinstance(keys, list):
                            continue
                        self.current_bindings[action].keys = keys
                    else:
                        # 添加用户自定义的快捷键
                        category = self._get_category_for_action(action)
                        description = self._get_description_for_action(action)
                        self.current_bindings[action] = KeyBinding(
                            action=action,
                            keys=keys if isinstance(keys, list) else [keys],
                            category=category,
                            description=description
                        )
                        
                logger.info(f"已加载用户快捷键配置: {self.config_path}")
            except Exception as e:
                logger.error(f"加载用户快捷键配置失败: {e}")
    
    def save_config(self):
        """保存当前配置到文件"""
        try:
            config_dir = os.path.dirname(self.config_path)
            os.makedirs(config_dir, exist_ok=True)
            
            # 创建简单的配置字典（只保存动作和键的映射）
            config_dict = {}
            for action, binding in self.current_bindings.items():
                if binding.keys != self.default_bindings.get(action, KeyBinding("", [])).keys:
                    # 只有当用户自定义了快捷键时才保存
                    config_dict[action] = binding.keys
            
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(config_dict, f, ensure_ascii=False, indent=2)
            
            logger.info(f"已保存快捷键配置: {self.config_path}")
        except Exception as e:
            logger.error(f"保存快捷键配置失败: {e}")
    
    def get_binding(self, action: str) -> Optional[KeyBinding]:
        """获取指定动作的快捷键绑定"""
        return self.current_bindings.get(action)
    
    def get_all_bindings(self) -> Dict[str, KeyBinding]:
        """获取所有快捷键绑定"""
        return self.current_bindings.copy()
    
    def get_bindings_by_category(self, category: str) -> Dict[str, KeyBinding]:
        """按类别获取快捷键绑定"""
        return {k: v for k, v in self.current_bindings.items() if v.category == category}
    
    def set_binding(self, action: str, keys: List[str]) -> bool:
        """设置指定动作的快捷键绑定"""
        if action in self.current_bindings:
            self.current_bindings[action].keys = keys
            return True
        else:
            # 添加新的快捷键绑定
            category = self._get_category_for_action(action)
            description = self._get_description_for_action(action)
            self.current_bindings[action] = KeyBinding(
                action=action,
                keys=keys,
                category=category,
                description=description
            )
            return True
    
    def reset_to_default(self, action: str = None):
        """重置为默认设置"""
        if action:
            # 重置特定动作
            if action in self.default_bindings:
                self.current_bindings[action] = self.default_bindings[action]
        else:
            # 重置所有
            self.current_bindings = self.default_bindings.copy()
    
    def validate_key_conflicts(self, new_bindings: Dict[str, List[str]]) -> List[str]:
        """验证快捷键冲突"""
        conflicts = []
        all_keys = {}
        
        # 检查新绑定之间的冲突
        for action, keys in new_bindings.items():
            for key in keys:
                if key in all_keys:
                    conflicts.append(f"快捷键 '{key}' 冲突: {all_keys[key]} 和 {action}")
                else:
                    all_keys[key] = action
        
        # 检查与现有绑定的冲突
        for action, binding in self.current_bindings.items():
            if action not in new_bindings:  # 只有当这个动作不在新绑定中时才检查
                for key in binding.keys:
                    if key in all_keys:
                        conflicts.append(f"快捷键 '{key}' 冲突: {all_keys[key]} 和 {action}")
        
        return conflicts
    
    def get_available_categories(self) -> List[str]:
        """获取所有可用的类别"""
        categories = set()
        for binding in self.current_bindings.values():
            categories.add(binding.category)
        return sorted(list(categories))