"""
VoxCPM2 推理服务器 (FastAPI)
运行在 voxcpm2_env 环境中，提供 HTTP API 供 GUI 调用
"""
import os
import sys
import logging
import torch
import json
import hashlib
import datetime
from pathlib import Path
from typing import Optional
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

# 路径配置
BASE_DIR = Path(__file__).resolve().parent.parent
VOICE_CACHE_DIR = BASE_DIR / "voice_cache"
HISTORY_DIR = BASE_DIR / "outputs" / "generation_history"
VOICE_DB_PATH = VOICE_CACHE_DIR / "voices_db.json"

# 初始化目录
for d in [VOICE_CACHE_DIR, HISTORY_DIR]:
    d.mkdir(parents=True, exist_ok=True)
if not VOICE_DB_PATH.exists():
    with open(VOICE_DB_PATH, 'w', encoding='utf-8') as f:
        json.dump({}, f)


class SynthesisRequest(BaseModel):
    """合成请求参数"""
    text: str
    reference_wav_path: Optional[str] = None
    prompt_wav_path: Optional[str] = None
    prompt_text: Optional[str] = None
    cfg_value: float = 2.0
    inference_timesteps: int = 10
    output_dir: str = "./outputs"
    denoise_enabled: bool = False
    normalize_text: bool = True
    voice_id: Optional[str] = None


class SynthesisResponse(BaseModel):
    """合成响应"""
    success: bool
    audio_path: Optional[str] = None
    error: Optional[str] = None
    duration: Optional[float] = None
    history_id: Optional[str] = None


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
    try:
        tts_model = load_model()
        
        # 1. 执行推理 (利用 VoxCPM 新增的 voice_id 支持)
        logger.info(f"[Inference] Generating for: {request.text[:30]}...")
        wav, audio_feat = tts_model.generate(
            text=request.text,
            voice_id=request.voice_id,
            voice_cache_dir=str(VOICE_CACHE_DIR),
            reference_wav_path=request.reference_wav_path,
            return_audio_feat=True
        )

        # 2. 构建历史记录文件夹
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        history_id = f"{timestamp}_{hashlib.md5(request.text[:20].encode()).hexdigest()[:6]}"
        history_folder = HISTORY_DIR / history_id
        history_folder.mkdir(parents=True, exist_ok=True)

        # 3. 保存音频
        audio_path = history_folder / "audio.wav"
        sf.write(str(audio_path), wav, tts_model.tts_model.sample_rate)

        # 4. 构建并保存完整缓存 (关键：保留 ref_audio_feat)
        new_cache = {"audio_feat": audio_feat, "prompt_text": request.text, "mode": "continuation"}
        if request.voice_id:
            old_cache_path = VOICE_CACHE_DIR / request.voice_id / "cache.pt"
            if old_cache_path.exists():
                old_cache = torch.load(str(old_cache_path), map_location="cpu")
                if "ref_audio_feat" in old_cache:
                    new_cache["ref_audio_feat"] = old_cache["ref_audio_feat"]
                    new_cache["mode"] = "ref_continuation"
        torch.save(new_cache, str(history_folder / "cache.pt"))

        # 5. 保存元数据
        duration = len(wav) / tts_model.tts_model.sample_rate
        meta_data = {
            "id": history_id, 
            "text": request.text, 
            "duration": duration,
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        }
        with open(history_folder / "meta.json", 'w', encoding='utf-8') as f:
            json.dump(meta_data, f, ensure_ascii=False, indent=2)

        logger.info(f"[History] Saved to {history_folder}")
        return SynthesisResponse(success=True, audio_path=str(audio_path), duration=duration, history_id=history_id)
    
    except Exception as e:
        logger.error(f"Generation failed: {e}", exc_info=True)
        return SynthesisResponse(success=False, error=str(e))


@app.get("/list_voices")
def list_voices():
    """获取已注册的音色列表"""
    if not VOICE_DB_PATH.exists():
        return []
    with open(VOICE_DB_PATH, 'r', encoding='utf-8') as f:
        db = json.load(f)
    return [{"id": vid, **info} for vid, info in db.items()]

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