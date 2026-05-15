"""
Whisper 语音识别封装
- 使用 openai-whisper 库
- 支持中文普通话识别
- 支持音频文件上传和 URL 拉取
"""
import asyncio
import tempfile
import logging
from pathlib import Path
from typing import Optional, Union

import whisper
import httpx

logger = logging.getLogger(__name__)


class WhisperRecognizer:
    """Whisper 语音识别器封装"""

    def __init__(
        self,
        model_name: str = "base",
        device: str = "cpu",
        download_root: Optional[str] = None,
    ):
        """
        初始化 Whisper 识别器
        
        Args:
            model_name: 模型名称，可选 tiny/base/small/medium/large
            device: 设备类型，cpu/cuda
            download_root: 模型缓存目录
        """
        self.model_name = model_name
        self.device = device
        
        # 设置模型下载路径
        if download_root:
            whisper._download = whisper.utils.get_writer
        
        logger.info(f"Loading Whisper model: {model_name} on {device}")
        self.model = whisper.load_model(model_name, device=device)

    async def recognize_file(self, audio_path: str) -> dict:
        """
        识别本地音频文件
        
        Args:
            audio_path: 音频文件路径
            
        Returns:
            {
                "text": str,          # 识别文本
                "language": str,      # 检测到的语言
                "segments": list,     # 分段信息
                "duration": float     # 音频时长（秒）
            }
        """
        loop = asyncio.get_event_loop()
        
        def _recognize():
            result = self.model.transcribe(
                audio_path,
                language="zh",           # 中文普通话
                task="transcribe",
                verbose=False,
            )
            return result
        
        result = await loop.run_in_executor(None, _recognize)
        
        return {
            "text": result["text"].strip(),
            "language": result.get("language", "zh"),
            "segments": result.get("segments", []),
            "duration": result.get("duration", 0.0),
        }

    async def recognize_bytes(self, audio_bytes: bytes, format: str = "mp3") -> dict:
        """
        识别字节数据
        
        Args:
            audio_bytes: 音频数据
            format: 音频格式
            
        Returns:
            识别结果字典
        """
        with tempfile.NamedTemporaryFile(suffix=f".{format}", delete=False) as f:
            f.write(audio_bytes)
            temp_path = f.name
        
        try:
            return await self.recognize_file(temp_path)
        finally:
            Path(temp_path).unlink(missing_ok=True)

    async def recognize_url(self, url: str, timeout: int = 60) -> dict:
        """
        从 URL 下载并识别音频
        
        Args:
            url: 音频文件 URL
            timeout: 下载超时（秒）
            
        Returns:
            识别结果字典
        """
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(url)
            response.raise_for_status()
            
            # 推断文件格式
            content_type = response.headers.get("content-type", "audio/mpeg")
            ext = self._get_extension(content_type)
            
            return await self.recognize_bytes(response.content, ext)

    def _get_extension(self, content_type: str) -> str:
        """从 content-type 推断文件扩展名"""
        mapping = {
            "audio/mpeg": "mp3",
            "audio/wav": "wav",
            "audio/ogg": "ogg",
            "audio/mp4": "mp4",
            "audio/x-m4a": "m4a",
            "audio/flac": "flac",
        }
        return mapping.get(content_type, "mp3")


# 全局识别器实例（延迟初始化）
_recognizer: Optional[WhisperRecognizer] = None


def get_recognizer() -> WhisperRecognizer:
    """获取全局识别器实例"""
    global _recognizer
    if _recognizer is None:
        _recognizer = WhisperRecognizer(model_name="base")
    return _recognizer


async def recognize_speech(audio_path: str) -> dict:
    """便捷函数：识别语音"""
    return await get_recognizer().recognize_file(audio_path)
