"""
VoxCPM2 推理服务器 (FastAPI)
运行在 voxcpm2_env 环境中，提供 HTTP API 供 GUI 调用
"""
import os
import sys
import logging
import tempfile
from pathlib import Path
from typing import Optional
import numpy as np
import soundfile as sf
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# 初始化 FastAPI
app = FastAPI(title="VoxCPM2 Inference Server", version="1.0.0")

# 全局模型实例
model = None


class SynthesisRequest(BaseModel):
    """合成请求参数"""
    text: str
    reference_wav_path: Optional[str] = None
    prompt_wav_path: Optional[str] = None
    prompt_text: Optional[str] = None
    cfg_value: float = 2.0
    inference_timesteps: int = 10
    output_dir: str = "./outputs"
    denoise_enabled: bool = False  # 音频降噪开关
    normalize_text: bool = True    # 文本正规范化开关


class SynthesisResponse(BaseModel):
    """合成响应"""
    success: bool
    audio_path: Optional[str] = None
    error: Optional[str] = None
    duration: Optional[float] = None


def load_model():
    """加载 VoxCPM2 模型（单例）"""
    global model
    if model is not None:
        return model
    
    logger.info("Loading VoxCPM2 model...")
    try:
        from voxcpm import VoxCPM
        
        # 使用本地模型路径
        model_path = str(Path(__file__).parent.parent / "model_weights")
        logger.info(f"Using local model path: {model_path}")
        
        model = VoxCPM.from_pretrained(
            model_path,
            load_denoiser=False,
            local_files_only=True  # 强制使用本地文件
        )
        logger.info(f"Model loaded successfully. Sample rate: {model.tts_model.sample_rate}")
        return model
    except Exception as e:
        logger.error(f"Failed to load model: {e}")
        raise


@app.on_event("startup")
def startup_event():
    """启动时预加载模型"""
    try:
        load_model()
        logger.info("VoxCPM2 Inference Server started successfully")
    except Exception as e:
        logger.error(f"Failed to initialize model: {e}")
        # 不退出，允许后续请求触发懒加载


@app.post("/generate", response_model=SynthesisResponse)
def generate_speech(request: SynthesisRequest):
    """
    语音合成接口
    
    支持三种模式：
    1. 基础 TTS: 仅提供 text
    2. 声音克隆: 提供 text + reference_wav_path
    3. 极致克隆: 提供 text + reference_wav_path + prompt_wav_path + prompt_text
    """
    try:
        # 确保模型已加载
        tts_model = load_model()
        
        logger.info(f"Generating speech for text: {request.text[:50]}...")
        
        # 构建生成参数
        generate_kwargs = {
            "text": request.text,
            "cfg_value": request.cfg_value,
            "inference_timesteps": request.inference_timesteps,
            "denoise": request.denoise_enabled,      # 修正为实际支持的参数名
            "normalize": request.normalize_text,     # 修正为实际支持的参数名
        }
        
        # 添加参考音频（声音克隆）
        if request.reference_wav_path:
            generate_kwargs["reference_wav_path"] = request.reference_wav_path
            
            # 极致克隆模式
            if request.prompt_wav_path and request.prompt_text:
                generate_kwargs["prompt_wav_path"] = request.prompt_wav_path
                generate_kwargs["prompt_text"] = request.prompt_text
        
        # 执行推理
        wav = tts_model.generate(**generate_kwargs)
        
        # 保存音频
        output_dir = Path(request.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        temp_file = tempfile.NamedTemporaryFile(
            delete=False,
            suffix=".wav",
            dir=str(output_dir)
        )
        temp_file.close()
        
        sf.write(temp_file.name, wav, tts_model.tts_model.sample_rate)
        
        duration = len(wav) / tts_model.tts_model.sample_rate
        
        logger.info(f"Speech generated successfully. Duration: {duration:.2f}s")
        
        return SynthesisResponse(
            success=True,
            audio_path=temp_file.name,
            duration=duration
        )
    
    except Exception as e:
        logger.error(f"Generation failed: {e}", exc_info=True)
        return SynthesisResponse(
            success=False,
            error=str(e)
        )


@app.get("/health")
def health_check():
    """健康检查接口"""
    return {
        "status": "healthy",
        "model_loaded": model is not None
    }


if __name__ == "__main__":
    # 启动服务器
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=8000,
        log_level="info"
    )