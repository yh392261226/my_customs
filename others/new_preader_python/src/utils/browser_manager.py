"""
浏览器工具类
用于根据设置打开相应的浏览器
"""

import os
import subprocess
import platform
from typing import Optional
from src.utils.logger import get_logger
from src.config.config_manager import ConfigManager

logger = get_logger(__name__)

class BrowserManager:
    """浏览器管理器"""
    
    # 支持的浏览器列表
    SUPPORTED_BROWSERS = ["chrome", "safari", "brave"]
    
    # 默认浏览器路径
    DEFAULT_BROWSER_PATHS = {
        "chrome": {
            "Darwin": "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            "Windows": "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
            "Linux": "google-chrome"
        },
        "safari": {
            "Darwin": "/Applications/Safari.app/Contents/MacOS/Safari",
            "Windows": None,  # Safari 不支持 Windows
            "Linux": None
        },
        "brave": {
            "Darwin": "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
            "Windows": "C:\\Program Files\\BraveSoftware\\Brave-Browser\\Application\\brave.exe",
            "Linux": "brave-browser"
        }
    }
    
    @classmethod
    def get_default_browser(cls) -> str:
        """
        获取默认浏览器
        
        Returns:
            str: 默认浏览器名称
        """
        # 使用ConfigManager获取最新的设置
        try:
            # 创建新的ConfigManager实例以强制重新加载配置
            config_manager = ConfigManager()
            config = config_manager.get_config()
            return config.get("browser", {}).get("default_browser", "chrome")
        except Exception as e:
            logger.warning(f"读取配置失败，使用默认值: {e}")
            return "chrome"
    
    @classmethod
    def get_browser_path(cls, browser_name: Optional[str] = None) -> Optional[str]:
        """
        获取指定浏览器的路径
        
        Args:
            browser_name: 浏览器名称，如果为None则使用默认浏览器
            
        Returns:
            Optional[str]: 浏览器路径，如果浏览器不存在则返回None
        """
        if browser_name is None:
            browser_name = cls.get_default_browser()
        
        if browser_name not in cls.SUPPORTED_BROWSERS:
            logger.error(f"不支持的浏览器: {browser_name}")
            return None
        
        # 首先尝试从配置中获取路径
        try:
            # 创建新的ConfigManager实例以强制重新加载配置
            config_manager = ConfigManager()
            config = config_manager.get_config()
            config_path = config.get("browser", {}).get(f"{browser_name}_path")
            if config_path and os.path.exists(config_path):
                return config_path
        except Exception as e:
            logger.warning(f"读取浏览器路径配置失败: {e}")
        
        # 如果配置路径不存在，使用默认路径
        system = platform.system()
        default_path = cls.DEFAULT_BROWSER_PATHS.get(browser_name, {}).get(system)
        
        if default_path and os.path.exists(default_path):
            return default_path
        
        logger.warning(f"浏览器 {browser_name} 路径不存在: {default_path}")
        return None
    
    @classmethod
    def open_url(cls, url: str, browser_name: Optional[str] = None) -> bool:
        """
        使用指定浏览器打开URL
        
        Args:
            url: 要打开的URL
            browser_name: 浏览器名称，如果为None则使用默认浏览器
            
        Returns:
            bool: 是否成功打开
        """
        if not url:
            logger.error("URL不能为空")
            return False
        
        # 获取浏览器名称（不使用路径）
        if browser_name is None:
            browser_name = cls.get_default_browser()
        
        if not browser_name:
            logger.error("浏览器名称为空")
            return False
        
        try:
            # 根据操作系统和浏览器类型选择打开方式
            system = platform.system()
            
            if system == "Darwin":  # macOS
                if browser_name == "safari":
                    # Safari 使用应用程序名称
                    logger.info(f"使用Safari打开URL: {url}")
                    subprocess.run(["open", "-a", "Safari", url], check=True)
                elif browser_name == "chrome":
                    # Chrome 使用应用程序名称
                    subprocess.run(["open", "-a", "Google Chrome", url], check=True)
                elif browser_name == "brave":
                    # Brave 使用应用程序名称
                    subprocess.run(["open", "-a", "Brave Browser", url], check=True)
                else:
                    # 其他浏览器使用路径
                    subprocess.run(["open", "-a", browser_path, url], check=True)
            elif system == "Windows":  # Windows
                subprocess.run([browser_path, url], check=True)
            else:  # Linux
                subprocess.run([browser_path, url], check=True)
            
            logger.info(f"成功使用 {browser_name} 打开URL: {url}")
            return True
            
        except subprocess.CalledProcessError as e:
            logger.error(f"打开URL失败: {e}")
            return False
        except Exception as e:
            logger.error(f"打开URL时发生错误: {e}")
            return False
    
    @classmethod
    def open_file(cls, file_path: str, browser_name: Optional[str] = None) -> bool:
        """
        使用指定浏览器打开文件
        
        Args:
            file_path: 要打开的文件路径
            browser_name: 浏览器名称，如果为None则使用默认浏览器
            
        Returns:
            bool: 是否成功打开
        """
        if not file_path:
            logger.error("文件路径不能为空")
            return False
        
        if not os.path.exists(file_path):
            logger.error(f"文件不存在: {file_path}")
            return False
        
        # 将文件路径转换为file:// URL
        file_url = f"file://{os.path.abspath(file_path)}"
        return cls.open_url(file_url, browser_name)
    
    @classmethod
    def is_browser_available(cls, browser_name: str) -> bool:
        """
        检查指定浏览器是否可用
        
        Args:
            browser_name: 浏览器名称
            
        Returns:
            bool: 浏览器是否可用
        """
        return cls.get_browser_path(browser_name) is not None
    
    @classmethod
    def get_available_browsers(cls) -> list:
        """
        获取所有可用的浏览器列表
        
        Returns:
            list: 可用浏览器名称列表
        """
        available = []
        for browser in cls.SUPPORTED_BROWSERS:
            if cls.is_browser_available(browser):
                available.append(browser)
        return available