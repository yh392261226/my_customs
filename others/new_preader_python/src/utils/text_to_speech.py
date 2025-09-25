"""
文本朗读模块，提供文本转语音功能
"""

import os

import threading
import subprocess
import platform
from typing import Optional, Callable

from src.utils.logger import get_logger

logger = get_logger(__name__)

class TextToSpeech:
    """文本朗读类"""
    
    def __init__(self):
        """初始化文本朗读类"""
        self._is_speaking = False
        self._stop_requested = False
        self._current_process = None
        self._speech_thread = None
        self._system = platform.system().lower()
    
    def speak(self, text: str, language: str = "zh-CN", rate: int = 1, 
              on_complete: Optional[Callable[[], None]] = None) -> bool:
        """
        朗读文本
        
        Args:
            text: 要朗读的文本
            language: 语言代码
            rate: 语速 (0.5-2.0)
            on_complete: 朗读完成后的回调函数
            
        Returns:
            bool: 是否成功开始朗读
        """
        # 先停止所有正在进行的朗读
        self.stop()
        
        # 等待一小段时间确保进程完全终止
        import time
        time.sleep(0.1)
        
        self._is_speaking = True
        self._stop_requested = False
        
        # 在新线程中执行朗读，避免阻塞主线程
        self._speech_thread = threading.Thread(
            target=self._speak_thread,
            args=(text, language, rate, on_complete)
        )
        self._speech_thread.daemon = True
        self._speech_thread.start()
        
        return True
    
    def _speak_thread(self, text: str, language: str, rate: int, 
                     on_complete: Optional[Callable[[], None]]):
        """
        朗读线程
        
        Args:
            text: 要朗读的文本
            language: 语言代码
            rate: 语速
            on_complete: 朗读完成后的回调函数
        """
        try:
            # 根据不同操作系统选择不同的朗读方式
            if self._system == "darwin":  # macOS
                self._speak_macos(text, language, rate)
            elif self._system == "windows":  # Windows
                self._speak_windows(text, language, rate)
            elif self._system == "linux":  # Linux
                self._speak_linux(text, language, rate)
            else:
                logger.warning(f"不支持的操作系统: {self._system}")
                self._is_speaking = False
                return
            
            # 如果没有被中断且回调函数存在，调用回调函数
            if not self._stop_requested and on_complete:
                on_complete()
                
        except Exception as e:
            logger.error(f"朗读文本时出错: {e}")
        finally:
            self._is_speaking = False
            self._current_process = None
    
    def _speak_macos(self, text: str, language: str, rate: int):
        """
        在macOS上使用say命令朗读文本
        
        Args:
            text: 要朗读的文本
            language: 语言代码
            rate: 语速
        """
        # 将语言代码转换为macOS的语音名称
        voice = self._get_macos_voice(language)
        
        # 创建临时文件存储文本
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', delete=False, encoding='utf-8') as temp:
            temp.write(text)
            temp_path = temp.name
        
        try:
            # 使用say命令朗读文本
            cmd = ["say", "-f", temp_path, "-r", str(int(rate * 180))]
            if voice:
                cmd.extend(["-v", voice])
            
            self._current_process = subprocess.Popen(cmd)
            self._current_process.wait()
        finally:
            # 删除临时文件
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    def _speak_windows(self, text: str, language: str, rate: int):
        """
        在Windows上使用PowerShell朗读文本
        
        Args:
            text: 要朗读的文本
            language: 语言代码
            rate: 语速
        """
        # 创建PowerShell脚本
        ps_script = f"""
        Add-Type -AssemblyName System.Speech
        $synth = New-Object System.Speech.Synthesis.SpeechSynthesizer
        $synth.Rate = {int((rate - 1) * 10)}
        
        # 尝试设置语言
        try {{
            $culture = New-Object System.Globalization.CultureInfo("{language}")
            $synth.SelectVoiceByHints([System.Speech.Synthesis.VoiceGender]::NotSet, [System.Speech.Synthesis.VoiceAge]::NotSet, 0, $culture)
        }} catch {{
            # 如果设置语言失败，使用默认语音
        }}
        
        $synth.Speak("{text.replace('"', '\\"')}")
        """
        
        # 创建临时文件存储脚本
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.ps1', encoding='utf-8') as temp:
            temp.write(ps_script)
            temp_path = temp.name
        
        try:
            # 执行PowerShell脚本
            cmd = ["powershell", "-ExecutionPolicy", "Bypass", "-File", temp_path]
            self._current_process = subprocess.Popen(cmd)
            self._current_process.wait()
        finally:
            # 删除临时文件
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    def _speak_linux(self, text: str, language: str, rate: int):
        """
        在Linux上使用espeak朗读文本
        
        Args:
            text: 要朗读的文本
            language: 语言代码
            rate: 语速
        """
        # 创建临时文件存储文本
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', delete=False, encoding='utf-8') as temp:
            temp.write(text)
            temp_path = temp.name
        
        try:
            # 尝试使用espeak朗读
            lang_code = language.split('-')[0]  # 提取主要语言代码
            cmd = ["espeak", "-f", temp_path, "-v", lang_code, "-s", str(int(rate * 150))]
            
            self._current_process = subprocess.Popen(cmd)
            self._current_process.wait()
        finally:
            # 删除临时文件
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    def _get_macos_voice(self, language: str) -> Optional[str]:
        """
        根据语言代码获取macOS的语音名称
        
        Args:
            language: 语言代码
            
        Returns:
            Optional[str]: 语音名称
        """
        # 语言代码到macOS语音的映射
        voice_map = {
            "zh-CN": "Ting-Ting",
            "zh-TW": "Sin-ji",
            "en-US": "Samantha",
            "en-GB": "Daniel",
            "ja-JP": "Kyoko",
            "ko-KR": "Yuna",
            "fr-FR": "Thomas",
            "de-DE": "Anna",
            "it-IT": "Alice",
            "es-ES": "Jorge",
            "ru-RU": "Milena"
        }
        
        return voice_map.get(language)
    
    def stop(self):
        """停止朗读"""
        self._stop_requested = True
        
        # 终止当前进程
        if self._current_process:
            try:
                self._current_process.terminate()
                self._current_process = None
            except Exception as e:
                logger.error(f"停止当前朗读进程时出错: {e}")
        
        # 根据操作系统终止所有相关的朗读进程
        try:
            if self._system == "darwin":  # macOS
                self._kill_all_say_processes()
            elif self._system == "windows":  # Windows
                self._kill_all_powershell_speech_processes()
            elif self._system == "linux":  # Linux
                self._kill_all_espeak_processes()
        except Exception as e:
            logger.error(f"终止所有朗读进程时出错: {e}")
        
        self._is_speaking = False
    
    def _kill_all_say_processes(self):
        """终止所有say进程 (macOS)"""
        try:
            # 使用pkill命令终止所有say进程
            subprocess.run(["pkill", "-f", "say"], check=False)
            logger.debug("已终止所有say进程")
        except Exception as e:
            logger.error(f"终止say进程时出错: {e}")
    
    def _kill_all_powershell_speech_processes(self):
        """终止所有PowerShell语音进程 (Windows)"""
        try:
            # 终止所有PowerShell进程（这可能会影响其他PowerShell进程，需要更精确的方法）
            subprocess.run(["taskkill", "/f", "/im", "powershell.exe"], check=False)
            logger.debug("已终止所有PowerShell进程")
        except Exception as e:
            logger.error(f"终止PowerShell进程时出错: {e}")
    
    def _kill_all_espeak_processes(self):
        """终止所有espeak进程 (Linux)"""
        try:
            # 使用pkill命令终止所有espeak进程
            subprocess.run(["pkill", "-f", "espeak"], check=False)
            logger.debug("已终止所有espeak进程")
        except Exception as e:
            logger.error(f"终止espeak进程时出错: {e}")
    
    def is_speaking(self) -> bool:
        """
        检查是否正在朗读
        
        Returns:
            bool: 是否正在朗读
        """
        return self._is_speaking