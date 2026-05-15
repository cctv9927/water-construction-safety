"""
TTS 语音播报模块
- 使用 edge-tts（微软语音，免费，无需 API key）
- 支持多种中文音色
"""
import asyncio
import logging
from pathlib import Path
from typing import Optional

import edge_tts
from edge_tts import Communicate

logger = logging.getLogger(__name__)


class TTSEngine:
    """Edge-TTS 语音合成引擎"""

    # 常用中文音色
    VOICES = {
        "zh-CN-Xiaoxiao": "晓晓（女声，青年）",
        "zh-CN-Yunxi": "云希（男声，青年）",
        "zh-CN-Yunyang": "云扬（男声，新闻）",
        "zh-CN-Xiaoyi": "小艺（女声）",
        "zh-CN-Zhiyu": "智娃（女声，客服）",
        "zh-CN-Xiaoqiu": "晓秋（女声）",
        "zh-CN-Xiaochen": "晓辰（男声）",
    }

    def __init__(
        self,
        voice: str = "zh-CN-Xiaoxiao",
        rate: str = "+0%",
        volume: str = "+0%",
        pitch: str = "+0Hz",
    ):
        """
        初始化 TTS 引擎
        
        Args:
            voice: 音色名称
            rate: 语速调整（-50% 到 +100%）
            volume: 音量调整（-50% 到 +50%）
            pitch: 音调调整（-50Hz 到 +50Hz）
        """
        self.voice = voice
        self.rate = rate
        self.volume = volume
        self.pitch = pitch

    async def speak(self, text: str, output_path: Optional[str] = None) -> bytes:
        """
        将文本转换为语音并保存
        
        Args:
            text: 要转换的文本
            output_path: 输出文件路径（MP3），为 None 则只返回字节
            
        Returns:
            音频数据（字节）
        """
        communicate = Communicate(
            text=text,
            voice=self.voice,
            rate=self.rate,
            volume=self.volume,
            pitch=self.pitch,
        )
        
        if output_path:
            # 保存到文件
            await communicate.save(output_path)
            logger.info(f"TTS saved to {output_path}")
            return b""
        else:
            # 返回字节数据
            audio_data = b""
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    audio_data += chunk["data"]
            return audio_data

    async def speak_stream(self, text: str):
        """
        流式生成语音（用于实时播报）
        
        Args:
            text: 要转换的文本
            
        Yields:
            音频数据块
        """
        communicate = Communicate(
            text=text,
            voice=self.voice,
            rate=self.rate,
            volume=self.volume,
            pitch=self.pitch,
        )
        
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                yield chunk["data"]

    def list_voices(self) -> dict:
        """列出可用音色"""
        return self.VOICES.copy()


class AlertTTS(TTSEngine):
    """告警专用 TTS（语速稍快，音量稍大）"""

    def __init__(self):
        super().__init__(
            voice="zh-CN-Yunxi",
            rate="+10%",     # 语速稍快
            volume="+10%",    # 音量稍大
            pitch="+0Hz",
        )

    async def announce_alert(self, message: str, severity: str = "P1") -> bytes:
        """
        播报告警消息
        
        Args:
            message: 告警内容
            severity: 告警级别
            
        Returns:
            音频数据
        """
        # 构建播报文本
        prefix = self._get_prefix(severity)
        full_text = f"{prefix}，{message}"
        return await self.speak(full_text)

    def _get_prefix(self, severity: str) -> str:
        """获取告警前缀"""
        prefixes = {
            "P0": "紧急告警",
            "P1": "重要告警",
            "P2": "一般提示",
        }
        return prefixes.get(severity, "提示")


# 全局 TTS 实例
_tts_engine: Optional[AlertTTS] = None


def get_tts_engine() -> AlertTTS:
    """获取全局 TTS 引擎"""
    global _tts_engine
    if _tts_engine is None:
        _tts_engine = AlertTTS()
    return _tts_engine


async def text_to_speech(text: str, output_path: Optional[str] = None) -> bytes:
    """便捷函数：文本转语音"""
    return await get_tts_engine().speak(text, output_path)


async def announce_alert(message: str, severity: str = "P1") -> bytes:
    """便捷函数：播报告警"""
    return await get_tts_engine().announce_alert(message, severity)
