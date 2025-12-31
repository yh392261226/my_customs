"""
AES解密工具类 - 用于处理加密的小说内容
"""

import base64
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad
from Crypto.Util.Padding import pad
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
    
    def _process_key_iv(self, key: str, iv: str) -> tuple:
        """
        处理密钥和IV，支持多种格式
        
        Args:
            key: 密钥字符串
            iv: IV字符串
            
        Returns:
            处理后的(key_bytes, iv_bytes)
        """
        # 处理密钥
        key_bytes = key.encode('utf-8')
        key_bytes = self._pad_key(key_bytes)
        
        # 处理IV - 支持base64编码的IV
        try:
            # 尝试base64解码
            iv_bytes = base64.b64decode(iv)
            if len(iv_bytes) < 16:
                iv_bytes = self._pad_key(iv_bytes)
            elif len(iv_bytes) > 16:
                iv_bytes = iv_bytes[:16]
        except:
            # 如果base64解码失败，尝试UTF-8编码
            iv_bytes = iv.encode('utf-8')
            iv_bytes = self._pad_key(iv_bytes)
        
        return key_bytes, iv_bytes
    
    def decrypt(self, encrypted_text: str, padding_mode='pkcs7') -> str:
        """
        AES解密方法
        
        Args:
            encrypted_text: 加密的Base64编码文本
            padding_mode: 填充模式，'pkcs7'(默认) 或 'zero'
            
        Returns:
            解密后的文本
        """
        try:
            # Base64解码
            encrypted_bytes = base64.b64decode(encrypted_text)
            
            # 检查数据长度是否是16的倍数（AES块大小）
            if len(encrypted_bytes) % 16 != 0:
                # 尝试填充到16的倍数
                padding_needed = 16 - (len(encrypted_bytes) % 16)
                encrypted_bytes += b'\x00' * padding_needed
                print(f"警告：加密数据长度({len(encrypted_bytes)-padding_needed})不是16的倍数，已填充{padding_needed}字节")
            
            # 创建AES解密器
            cipher = AES.new(self.key, AES.MODE_CBC, self.iv)
            
            # 解密
            decrypted_bytes = cipher.decrypt(encrypted_bytes)
            
            # 根据填充模式去除填充
            if padding_mode == 'zero':
                # ZeroPadding: 移除末尾的零字节，但保留中间的零字节
                # 找到最后一个非零字节的位置
                last_nonzero = len(decrypted_bytes) - 1
                while last_nonzero >= 0 and decrypted_bytes[last_nonzero] == 0:
                    last_nonzero -= 1
                unpadded_bytes = decrypted_bytes[:last_nonzero + 1]
            else:
                # PKCS7: 使用标准unpad
                try:
                    unpadded_bytes = unpad(decrypted_bytes, AES.block_size)
                except Exception as e:
                    print(f"PKCS7 unpad失败: {e}，尝试移除末尾的填充字节")
                    # 手动移除PKCS7填充
                    if len(decrypted_bytes) > 0:
                        padding_length = decrypted_bytes[-1]
                        if 1 <= padding_length <= 16:
                            unpadded_bytes = decrypted_bytes[:-padding_length]
                        else:
                            unpadded_bytes = decrypted_bytes
                    else:
                        unpadded_bytes = decrypted_bytes
            
            # 转换为字符串，使用replace处理无效字符
            try:
                return unpadded_bytes.decode('utf-8')
            except UnicodeDecodeError:
                # 如果UTF-8解码失败，尝试使用replace模式
                return unpadded_bytes.decode('utf-8', errors='replace')
            
        except Exception as e:
            # 如果解密失败，返回原始文本
            print(f"AES解密失败: {e}")
            return encrypted_text
    
    def decrypt_with_fallback(self, encrypted_text: str, key: str = None, iv: str = None, 
                            padding_mode='pkcs7') -> str:
        """
        带备用方案的AES解密方法
        
        Args:
            encrypted_text: 加密的Base64编码文本
            key: 可选的密钥，如果提供则覆盖初始化时的密钥
            iv: 可选的IV，如果提供则覆盖初始化时的IV
            padding_mode: 填充模式，'pkcs7'(默认) 或 'zero'
            
        Returns:
            解密后的文本
        """
        original_key = self.key
        original_iv = self.iv
        
        # 如果提供了备用密钥和IV，使用它们
        if key and iv:
            self.key, self.iv = self._process_key_iv(key, iv)
        
        # 尝试解密
        result = self.decrypt(encrypted_text, padding_mode)
        
        # 恢复原始密钥和IV
        self.key = original_key
        self.iv = original_iv
        
        return result


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