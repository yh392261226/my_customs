"""
AES解密工具类 - 用于处理加密的小说内容
"""

import base64
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad
import re

class AESCipher:
    """AES解密工具类"""
    
    def __init__(self, key: str, iv: str):
        """
        初始化AES解密器
        
        Args:
            key: 解密密钥
            iv: 初始化向量
        """
        # 确保key和iv都是16字节（128位）
        self.key = self._pad_key(key.encode('utf-8'))
        self.iv = self._pad_key(iv.encode('utf-8'))
    
    def _pad_key(self, key: bytes) -> bytes:
        """
        将密钥填充到16字节
        
        Args:
            key: 原始密钥
            
        Returns:
            填充后的16字节密钥
        """
        if len(key) < 16:
            # 如果密钥长度不足16字节，用0填充
            return key + b'\x00' * (16 - len(key))
        elif len(key) > 16:
            # 如果密钥长度超过16字节，截取前16字节
            return key[:16]
        else:
            return key
    
    def decrypt(self, encrypted_text: str) -> str:
        """
        AES解密方法
        
        Args:
            encrypted_text: 加密的Base64编码文本
            
        Returns:
            解密后的文本
        """
        try:
            # Base64解码
            encrypted_bytes = base64.b64decode(encrypted_text)
            
            # 创建AES解密器
            cipher = AES.new(self.key, AES.MODE_CBC, self.iv)
            
            # 解密
            decrypted_bytes = cipher.decrypt(encrypted_bytes)
            
            # 去除填充
            unpadded_bytes = unpad(decrypted_bytes, AES.block_size)
            
            # 转换为字符串
            return unpadded_bytes.decode('utf-8', errors='ignore')
            
        except Exception as e:
            # 如果解密失败，返回原始文本
            print(f"AES解密失败: {e}")
            return encrypted_text


def extract_encryption_keys(html_content: str) -> tuple:
    """
    从HTML内容中提取加密密钥
    
    Args:
        html_content: HTML页面内容
        
    Returns:
        tuple: (aei, aek) 加密密钥
    """
    # 从script标签中提取加密密钥
    patterns = [
        r"var aei = '([^']+)'",
        r"var aek = '([^']+)'",
        r"var aei = \"([^\"]+)\"",
        r"var aek = \"([^\"]+)\""
    ]
    
    aei = None
    aek = None
    
    for i, pattern in enumerate(patterns):
        matches = re.findall(pattern, html_content)
        if matches:
            if i % 2 == 0:  # aei模式
                aei = matches[0] if not aei else aei
            else:  # aek模式
                aek = matches[0] if not aek else aek
    
    # 默认值（如果无法从页面提取）
    if not aei:
        aei = "mAf6AupVNiH5u4vS"
    if not aek:
        aek = "BaL94DxIbGhdAJ80"
    
    return aei, aek


def is_encrypted_content(content: str) -> bool:
    """
    判断内容是否为加密内容
    
    Args:
        content: 要判断的内容
        
    Returns:
        bool: 是否为加密内容
    """
    # 检查是否包含Base64编码的特征
    if len(content) > 20 and re.match(r'^[A-Za-z0-9+/=]+$', content.strip()):
        # 尝试Base64解码看是否成功
        try:
            base64.b64decode(content)
            return True
        except:
            pass
    
    return False


def decrypt_html_content(html_content: str, aei: str = None, aek: str = None) -> str:
    """
    解密HTML页面中的加密内容
    
    Args:
        html_content: HTML页面内容
        aei: 加密密钥（可选，如果不提供则从页面提取）
        aek: 加密密钥（可选，如果不提供则从页面提取）
        
    Returns:
        解密后的HTML内容
    """
    if not aei or not aek:
        aei, aek = extract_encryption_keys(html_content)
    
    # 创建AES解密器
    cipher = AESCipher(aek, aei)
    
    # 查找并解密所有class="d"的标签内容
    def decrypt_match(match):
        encrypted_text = match.group(1)
        if is_encrypted_content(encrypted_text):
            decrypted = cipher.decrypt(encrypted_text)
            return decrypted
        else:
            return encrypted_text
    
    # 解密所有class="d"的标签内容
    decrypted_content = re.sub(
        r'<[^>]*class="d"[^>]*>([^<]+)</[^>]*>',
        decrypt_match,
        html_content
    )
    
    # 解密其他可能的加密标签
    decrypted_content = re.sub(
        r'<[^>]*class=\"d\"[^>]*>([^<]+)</[^>]*>',
        decrypt_match,
        decrypted_content
    )
    
    return decrypted_content