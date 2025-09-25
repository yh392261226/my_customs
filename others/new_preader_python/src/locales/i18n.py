"""
国际化支持模块，负责处理应用程序的多语言支持
"""

import os
import json

from typing import Dict, Any, Optional

from src.utils.logger import get_logger

logger = get_logger(__name__)

class I18n:
    """国际化支持类，负责处理多语言翻译"""
    
    def __init__(self, locale_dir: str, default_locale: str = "zh_CN"):
        """
        初始化国际化支持
        
        Args:
            locale_dir: 语言包目录
            default_locale: 默认语言
        """
        self.locale_dir = locale_dir
        self.default_locale = default_locale
        self.current_locale = default_locale
        self.translations = {}
        
        # 加载所有可用的语言包
        self._load_available_locales()
        
        # 加载默认语言包
        self._load_locale(default_locale)
    
    def _load_available_locales(self) -> None:
        """加载所有可用的语言包"""
        self.available_locales = []
        
        try:
            # 遍历语言包目录
            for item in os.listdir(self.locale_dir):
                locale_path = os.path.join(self.locale_dir, item)
                # 检查是否是目录且包含translation.json文件
                if os.path.isdir(locale_path) and os.path.exists(os.path.join(locale_path, "translation.json")):
                    self.available_locales.append(item)
            
            logger.info(f"找到可用语言包: {', '.join(self.available_locales)}")
        except Exception as e:
            logger.error(f"加载可用语言包时出错: {e}")
    
    def _load_locale(self, locale: str) -> bool:
        """
        加载指定语言包
        
        Args:
            locale: 语言代码
            
        Returns:
            bool: 加载是否成功
        """
        try:
            locale_file = os.path.join(self.locale_dir, locale, "translation.json")
            
            if not os.path.exists(locale_file):
                logger.error(f"语言包文件不存在: {locale_file}")
                return False
            
            with open(locale_file, 'r', encoding='utf-8') as f:
                self.translations[locale] = json.load(f)
            
            logger.info(f"已加载语言包: {locale}")
            return True
        except Exception as e:
            logger.error(f"加载语言包时出错: {e}")
            return False
    
    def set_locale(self, locale: str) -> bool:
        """
        设置当前语言
        
        Args:
            locale: 语言代码
            
        Returns:
            bool: 设置是否成功
        """
        if locale not in self.available_locales:
            logger.error(f"不支持的语言: {locale}")
            return False
        
        if locale not in self.translations:
            if not self._load_locale(locale):
                return False
        
        self.current_locale = locale
        logger.info(f"当前语言已设置为: {locale}")
        return True
    
    def get_available_locales(self) -> list:
        """
        获取所有可用的语言
        
        Returns:
            list: 可用语言列表
        """
        return self.available_locales
    
    def get_current_locale(self) -> str:
        """
        获取当前语言
        
        Returns:
            str: 当前语言代码
        """
        return self.current_locale
    
    def t(self, key: str, **kwargs) -> str:
        """
        翻译指定的键
        
        Args:
            key: 翻译键，使用点号分隔的路径，如"common.ok"
            **kwargs: 用于格式化翻译文本的参数
            
        Returns:
            str: 翻译后的文本，如果找不到翻译则返回键本身
        """
        # 尝试从当前语言包中获取翻译
        translation = self._get_translation(self.current_locale, key)
        
        # 如果找不到翻译且当前语言不是默认语言，则尝试从默认语言包中获取
        if translation is None and self.current_locale != self.default_locale:
            translation = self._get_translation(self.default_locale, key)
        
        # 如果仍然找不到翻译，则返回键本身
        if translation is None:
            return key
        
        # 如果有格式化参数，则应用格式化
        if kwargs:
            try:
                return translation.format(**kwargs)
            except KeyError as e:
                logger.error(f"翻译格式化错误，缺少参数: {e}")
                return translation
            except Exception as e:
                logger.error(f"翻译格式化错误: {e}")
                return translation
        
        return translation
    
    def _get_translation(self, locale: str, key: str) -> Optional[str]:
        """
        从指定语言包中获取翻译
        
        Args:
            locale: 语言代码
            key: 翻译键，使用点号分隔的路径
            
        Returns:
            Optional[str]: 翻译文本，如果找不到则返回None
        """
        if locale not in self.translations:
            return None
        
        # 分割键路径
        parts = key.split('.')
        
        # 从语言包中查找翻译
        current = self.translations[locale]
        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return None
        
        # 确保最终结果是字符串
        if isinstance(current, str):
            return current
        else:
            return None