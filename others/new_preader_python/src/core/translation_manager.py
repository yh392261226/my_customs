"""
翻译服务管理器 - 支持多种第三方翻译API
"""

import requests
import json
from typing import Dict, Any, Optional, List
from abc import ABC, abstractmethod
from src.utils.logger import get_logger
from src.config.translation_config import get_translation_config

logger = get_logger(__name__)

class TranslationService(ABC):
    """翻译服务抽象基类"""
    
    @abstractmethod
    def translate(self, text: str, target_lang: str, source_lang: str = "auto") -> Dict[str, Any]:
        """翻译文本"""
        pass
    
    @abstractmethod
    def get_supported_languages(self) -> List[str]:
        """获取支持的语言列表"""
        pass

class BaiduTranslationService(TranslationService):
    """百度翻译API服务"""
    
    def __init__(self, app_id: str, secret_key: str):
        self.app_id = app_id
        self.secret_key = secret_key
        self.base_url = "https://fanyi-api.baidu.com/api/trans/vip/translate"
        
    def translate(self, text: str, target_lang: str, source_lang: str = "auto") -> Dict[str, Any]:
        """使用百度翻译API翻译文本"""
        try:
            import hashlib
            import random
            
            salt = str(random.randint(32768, 65536))
            sign = hashlib.md5((self.app_id + text + salt + self.secret_key).encode()).hexdigest()
            
            params = {
                'q': text,
                'from': source_lang,
                'to': target_lang,
                'appid': self.app_id,
                'salt': salt,
                'sign': sign
            }
            
            response = requests.get(self.base_url, params=params, timeout=10)
            response.raise_for_status()
            
            result = response.json()
            
            if 'error_code' in result:
                return {
                    'success': False,
                    'error': f"百度翻译错误: {result.get('error_msg', '未知错误')}",
                    'error_code': result['error_code']
                }
            
            translations = result.get('trans_result', [])
            if translations:
                return {
                    'success': True,
                    'original_text': text,
                    'translated_text': translations[0].get('dst', ''),
                    'source_lang': result.get('from', source_lang),
                    'target_lang': target_lang,
                    'service': 'baidu'
                }
            else:
                return {
                    'success': False,
                    'error': '翻译结果为空'
                }
                
        except Exception as e:
            logger.error(f"百度翻译失败: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_supported_languages(self) -> List[str]:
        """百度翻译支持的语言列表"""
        return ['zh', 'en', 'jp', 'kor', 'fra', 'spa', 'th', 'ara', 'ru', 'pt', 'de', 'it', 'el', 'nl', 'pl', 'bul', 'est', 'dan', 'fin', 'cs', 'rom', 'slo', 'swe', 'hu', 'vie']

class GoogleTranslationService(TranslationService):
    """Google翻译API服务（需要API密钥）"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://translation.googleapis.com/language/translate/v2"
        
    def translate(self, text: str, target_lang: str, source_lang: str = "auto") -> Dict[str, Any]:
        """使用Google翻译API翻译文本"""
        try:
            params = {
                'q': text,
                'target': target_lang,
                'key': self.api_key
            }
            
            if source_lang != "auto":
                params['source'] = source_lang
                
            response = requests.post(self.base_url, data=params, timeout=10)
            response.raise_for_status()
            
            result = response.json()
            translation_data = result.get('data', {})
            translations = translation_data.get('translations', [])
            
            if translations:
                return {
                    'success': True,
                    'original_text': text,
                    'translated_text': translations[0].get('translatedText', ''),
                    'source_lang': translations[0].get('detectedSourceLanguage', source_lang),
                    'target_lang': target_lang,
                    'service': 'google'
                }
            else:
                return {
                    'success': False,
                    'error': '翻译结果为空'
                }
                
        except Exception as e:
            logger.error(f"Google翻译失败: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_supported_languages(self) -> List[str]:
        """Google翻译支持的语言列表"""
        return ['zh', 'en', 'ja', 'ko', 'fr', 'es', 'de', 'it', 'ru', 'pt', 'ar', 'th', 'vi']

class YoudaoTranslationService(TranslationService):
    """有道翻译API服务"""
    
    def __init__(self, app_key: str, app_secret: str):
        self.app_key = app_key
        self.app_secret = app_secret
        self.base_url = "https://openapi.youdao.com/api"
        
    def translate(self, text: str, target_lang: str, source_lang: str = "auto") -> Dict[str, Any]:
        """使用有道翻译API翻译文本"""
        try:
            import hashlib
            import uuid
            
            salt = str(uuid.uuid1())
            sign_text = self.app_key + text + salt + self.app_secret
            sign = hashlib.md5(sign_text.encode()).hexdigest()
            
            data = {
                'q': text,
                'from': source_lang,
                'to': target_lang,
                'appKey': self.app_key,
                'salt': salt,
                'sign': sign
            }
            
            response = requests.post(self.base_url, data=data, timeout=10)
            response.raise_for_status()
            
            result = response.json()
            error_code = result.get('errorCode', '0')
            
            if error_code != '0':
                return {
                    'success': False,
                    'error': f"有道翻译错误: {error_code}",
                    'error_code': error_code
                }
            
            translations = result.get('translation', [])
            if translations:
                return {
                    'success': True,
                    'original_text': text,
                    'translated_text': translations[0],
                    'source_lang': source_lang,
                    'target_lang': target_lang,
                    'service': 'youdao'
                }
            else:
                return {
                    'success': False,
                    'error': '翻译结果为空'
                }
                
        except Exception as e:
            logger.error(f"有道翻译失败: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_supported_languages(self) -> List[str]:
        """有道翻译支持的语言列表"""
        return ['zh-CHS', 'en', 'ja', 'ko', 'fr', 'es', 'pt', 'it', 'de', 'ru', 'ar', 'th', 'vi']

class TranslationManager:
    """翻译管理器 - 统一管理多种翻译服务"""
    
    def __init__(self):
        self.services: Dict[str, TranslationService] = {}
        self.default_service = None
        self.config = {}
        
    def register_service(self, name: str, service: TranslationService) -> None:
        """注册翻译服务"""
        self.services[name] = service
        if not self.default_service:
            self.default_service = name
            
    def set_default_service(self, service_name: str) -> bool:
        """设置默认翻译服务"""
        if service_name in self.services:
            self.default_service = service_name
            return True
        return False
        
    def translate(self, text: str, target_lang: str = "zh", source_lang: str = "auto", service_name: str = None) -> Dict[str, Any]:
        """翻译文本"""
        if not text.strip():
            return {
                'success': False,
                'error': '文本为空'
            }
            
        service_name = service_name or self.default_service
        if not service_name or service_name not in self.services:
            return {
                'success': False,
                'error': f'翻译服务未配置: {service_name}'
            }
            
        service = self.services[service_name]
        return service.translate(text, target_lang, source_lang)
        
    def get_available_services(self) -> List[str]:
        """获取可用的翻译服务列表"""
        return list(self.services.keys())
        
    def get_supported_languages(self, service_name: str = None) -> List[str]:
        """获取支持的语言列表"""
        service_name = service_name or self.default_service
        if service_name and service_name in self.services:
            return self.services[service_name].get_supported_languages()
        return []
        
    def configure_from_dict(self, config: Dict[str, Any]) -> None:
        """从配置字典配置翻译服务"""
        self.config = config
        
        # 检查配置结构：可能是直接的服务配置，也可能是translation_services结构
        if 'translation_services' in config:
            # 使用translation_services结构
            translation_services = config.get('translation_services', {})
            for service_name, service_config in translation_services.items():
                if service_config.get('enabled', False):
                    if service_name == 'baidu':
                        app_id = service_config.get('app_id')
                        secret_key = service_config.get('app_key')  # 注意：配置中是app_key，但API需要secret_key
                        if app_id and secret_key:
                            self.register_service('baidu', BaiduTranslationService(app_id, secret_key))
                    elif service_name == 'google':
                        api_key = service_config.get('api_key')
                        if api_key:
                            self.register_service('google', GoogleTranslationService(api_key))
                    elif service_name == 'youdao':
                        app_key = service_config.get('app_key')
                        app_secret = service_config.get('app_secret')
                        if app_key and app_secret:
                            self.register_service('youdao', YoudaoTranslationService(app_key, app_secret))
        else:
            # 使用直接的服务配置结构
            # 配置百度翻译
            baidu_config = config.get('baidu', {})
            if baidu_config.get('app_id') and baidu_config.get('secret_key'):
                self.register_service('baidu', BaiduTranslationService(
                    baidu_config['app_id'], baidu_config['secret_key']
                ))
                
            # 配置Google翻译
            google_config = config.get('google', {})
            if google_config.get('api_key'):
                self.register_service('google', GoogleTranslationService(
                    google_config['api_key']
                ))
                
            # 配置有道翻译
            youdao_config = config.get('youdao', {})
            if youdao_config.get('app_key') and youdao_config.get('app_secret'):
                self.register_service('youdao', YoudaoTranslationService(
                    youdao_config['app_key'], youdao_config['app_secret']
                ))
            
        # 设置默认服务
        default_service = config.get('default_service')
        if default_service and default_service in self.services:
            self.set_default_service(default_service)
    
    def configure_from_config_manager(self) -> None:
        """从配置管理器配置翻译服务"""
        config_manager = get_translation_config()
        
        # 获取翻译配置
        translation_config = config_manager.config
        
        # 直接使用configure_from_dict方法进行配置
        # configure_from_dict现在能够处理translation_services结构
        self.configure_from_dict(translation_config)

# 全局翻译管理器实例
_translation_manager = None

def get_translation_manager() -> TranslationManager:
    """获取全局翻译管理器实例"""
    global _translation_manager
    if _translation_manager is None:
        _translation_manager = TranslationManager()
    return _translation_manager

def init_translation_manager(config: Dict[str, Any]) -> TranslationManager:
    """初始化全局翻译管理器"""
    global _translation_manager
    _translation_manager = TranslationManager()
    _translation_manager.configure_from_dict(config)
    return _translation_manager

def init_translation_manager_from_config() -> TranslationManager:
    """从配置管理器初始化全局翻译管理器"""
    global _translation_manager
    _translation_manager = TranslationManager()
    _translation_manager.configure_from_config_manager()
    return _translation_manager