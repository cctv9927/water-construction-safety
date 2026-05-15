"""
FastAPI 主服务 - 语音处理模块
端口：8083
"""
import asyncio
import logging
from pathlib import Path
from typing import Optional
import tempfile

from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import Response, JSONResponse
from pydantic import BaseModel, Field
import uvicorn

from .recognizer import WhisperRecognizer, get_recognizer, recognize_speech
from .intent import detect_intent, IntentResult
from .alert_trigger import create_alert_from_intent, Alert, get_trigger, AlertTrigger
from .tts import text_to_speech, announce_alert, get_tts_engine

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# 创建 FastAPI 应用
app = FastAPI(
    title="AI Voice Service",
    description="水利工地安全监管系统 - 语音处理模块",
    version="1.0.0",
)

# ============== 请求/响应模型 ==============

class RecognizeRequest(BaseModel):
    """语音识别请求"""
    audio_url: Optional[str] = Field(None, description="音频文件 URL")
    enable_tts: bool = Field(False, description="是否启用 TTS 播报")
    trigger_alert: bool = Field(True, description="是否触发告警")


class RecognizeResponse(BaseModel):
    """语音识别响应"""
    code: int
    message: str
    text: Optional[str] = None
    language: Optional[str] = None
    duration: Optional[float] = None
    intent: Optional[dict] = None
    alert: Optional[dict] = None


class TTSRequest(BaseModel):
    """TTS 请求"""
    text: str = Field(..., description="要转换的文本")
    voice: Optional[str] = Field("zh-CN-Xiaoxiao", description="音色名称")


class TTSResponse(BaseModel):
    """TTS 响应"""
    code: int
    message: str
    audio_data: Optional[str] = Field(None, description="Base64 编码的音频数据")


# ============== 全局变量 ==============

# 语音识别器（延迟初始化）
_recognizer: Optional[WhisperRecognizer] = None
# 告警触发器
_alert_trigger: Optional[AlertTrigger] = None


def get_whisper_recognizer() -> WhisperRecognizer:
    """获取 Whisper 识别器"""
    global _recognizer
    if _recognizer is None:
        _recognizer = WhisperRecognizer(model_name="base")
    return _recognizer


def get_alert_trigger() -> AlertTrigger:
    """获取告警触发器"""
    global _alert_trigger
    if _alert_trigger is None:
        _alert_trigger = AlertTrigger(announce=True)
    return _alert_trigger


# ============== API 路由 ==============

@app.get("/")
async def root():
    """服务健康检查"""
    return {"status": "ok", "service": "ai-voice", "port": 8083}


@app.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "recognizer": "ready" if _recognizer else "not_initialized",
    }


@app.post("/recognize", response_model=RecognizeResponse)
async def recognize_speech_endpoint(
    file: UploadFile = File(...),
    trigger_alert: bool = True,
    background_tasks: BackgroundTasks = BackgroundTasks(),
):
    """
    语音识别接口
    
    上传音频文件，进行语音识别和意图检测
    """
    try:
        # 保存上传文件
        suffix = Path(file.filename).suffix if file.filename else ".mp3"
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as f:
            content = await file.read()
            f.write(content)
            temp_path = f.name
        
        try:
            # 语音识别
            recognizer = get_whisper_recognizer()
            result = await recognizer.recognize_file(temp_path)
            
            if not result["text"]:
                return RecognizeResponse(
                    code=1,
                    message="未能识别到语音内容",
                    text="",
                )
            
            # 意图检测
            intent_result = detect_intent(result["text"])
            
            # 告警处理
            alert_data = None
            if trigger_alert and intent_result.confidence >= 0.5:
                alert = create_alert_from_intent(intent_result, source="voice")
                if alert:
                    alert_data = {
                        "level": alert.level.value,
                        "message": alert.message,
                        "timestamp": alert.timestamp,
                        "confidence": alert.confidence,
                    }
                    # 后台播报
                    background_tasks.add_task(
                        get_alert_trigger().process_alert, alert
                    )
            
            return RecognizeResponse(
                code=0,
                message="success",
                text=result["text"],
                language=result.get("language"),
                duration=result.get("duration"),
                intent={
                    "type": intent_result.intent.value,
                    "confidence": intent_result.confidence,
                    "entities": intent_result.entities,
                    "keywords_matched": intent_result.keywords_matched,
                },
                alert=alert_data,
            )
        finally:
            Path(temp_path).unlink(missing_ok=True)
            
    except Exception as e:
        logger.error(f"Recognition error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/recognize/url", response_model=RecognizeResponse)
async def recognize_from_url(
    request: RecognizeRequest,
    trigger_alert: bool = True,
    background_tasks: BackgroundTasks = BackgroundTasks(),
):
    """
    从 URL 识别语音
    
    Args:
        request: 包含音频 URL 的请求
    """
    if not request.audio_url:
        raise HTTPException(status_code=400, detail="audio_url is required")
    
    try:
        recognizer = get_whisper_recognizer()
        result = await recognizer.recognize_url(request.audio_url)
        
        if not result["text"]:
            return RecognizeResponse(
                code=1,
                message="未能识别到语音内容",
                text="",
            )
        
        # 意图检测
        intent_result = detect_intent(result["text"])
        
        # 告警处理
        alert_data = None
        if trigger_alert and intent_result.confidence >= 0.5:
            alert = create_alert_from_intent(intent_result, source="voice")
            if alert:
                alert_data = {
                    "level": alert.level.value,
                    "message": alert.message,
                    "timestamp": alert.timestamp,
                    "confidence": alert.confidence,
                }
                background_tasks.add_task(
                    get_alert_trigger().process_alert, alert
                )
        
        return RecognizeResponse(
            code=0,
            message="success",
            text=result["text"],
            language=result.get("language"),
            duration=result.get("duration"),
            intent={
                "type": intent_result.intent.value,
                "confidence": intent_result.confidence,
                "entities": intent_result.entities,
            },
            alert=alert_data,
        )
        
    except Exception as e:
        logger.error(f"URL recognition error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/tts", response_model=TTSResponse)
async def text_to_speech_endpoint(request: TTSRequest):
    """
    文本转语音
    
    Args:
        request: TTS 请求
    """
    try:
        tts = get_tts_engine()
        
        # 临时修改音色
        original_voice = tts.voice
        if request.voice:
            tts.voice = request.voice
        
        audio_bytes = await tts.speak(request.text)
        
        # 恢复音色
        tts.voice = original_voice
        
        # 转换为 Base64
        import base64
        audio_base64 = base64.b64encode(audio_bytes).decode()
        
        return TTSResponse(
            code=0,
            message="success",
            audio_data=audio_base64,
        )
        
    except Exception as e:
        logger.error(f"TTS error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/tts/save")
async def tts_save(text: str, output_path: str, voice: str = "zh-CN-Xiaoxiao"):
    """
    文本转语音并保存文件
    
    Args:
        text: 要转换的文本
        output_path: 输出文件路径
        voice: 音色名称
    """
    try:
        tts = get_tts_engine()
        tts.voice = voice
        await tts.speak(text, output_path)
        
        return {"code": 0, "message": f"Audio saved to {output_path}"}
    except Exception as e:
        logger.error(f"TTS save error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/alert/announce")
async def announce_alert_endpoint(message: str, level: str = "P1"):
    """
    播报告警
    
    Args:
        message: 告警内容
        level: 告警级别 P0/P1/P2
    """
    try:
        audio_bytes = await announce_alert(message, level)
        
        return Response(
            content=audio_bytes,
            media_type="audio/mpeg",
            headers={"Content-Disposition": "inline"},
        )
    except Exception as e:
        logger.error(f"Announce error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/voices")
async def list_voices():
    """列出可用音色"""
    tts = get_tts_engine()
    return {"voices": tts.list_voices()}


# ============== 启动服务 ==============

def main():
    """启动服务"""
    logger.info("Starting AI Voice Service on port 8083...")
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8083,
        reload=False,
        log_level="info",
    )


if __name__ == "__main__":
    main()
