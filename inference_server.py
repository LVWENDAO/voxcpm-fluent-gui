"""
VoxCPM2 推理服务器 (FastAPI)
运行在 voxcpm2_env 环境中，提供 HTTP API 供 GUI 调用
"""
import os
import sys
import logging
import tempfile
import torch
import random
import numpy as np
import json
import hashlib
import datetime
import threading
from pathlib import Path
from typing import Optional
import numpy as np
import soundfile as sf
from fastapi import FastAPI, HTTPException, File, UploadFile
from fastapi.responses import JSONResponse
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
# 路径配置：基于根目录 (VoxCPM2.exe 所在目录)
BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR / "outputs"
VOICE_CACHE_DIR = BASE_DIR / "voice_cache"  # 独立于 outputs，防止被误删
HISTORY_DIR = OUTPUT_DIR / "generation_history"
VOICE_DB_PATH = VOICE_CACHE_DIR / "voices_db.json"

# 确保目录存在
VOICE_CACHE_DIR.mkdir(parents=True, exist_ok=True)
HISTORY_DIR.mkdir(parents=True, exist_ok=True)
if not VOICE_DB_PATH.exists():
    with open(VOICE_DB_PATH, 'w', encoding='utf-8') as f:
        json.dump({}, f)

# 暂存最近一次推理的上下文（用于“先听后存”）
last_generation_context = {}


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
    seed: Optional[int] = None     # 随机种子：用于复现生成结果
    voice_id: Optional[str] = None # 音色ID：用于调用已注册的缓存


class SynthesisResponse(BaseModel):
    """合成响应"""
    success: bool
    audio_path: Optional[str] = None
    error: Optional[str] = None
    duration: Optional[float] = None
    history_id: Optional[str] = None  # 新增：返回历史记录ID


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


class VoiceRegisterRequest(BaseModel):
    """音色注册请求（保存上次推理结果）"""
    name: str

@app.post("/save_last_voice")
def save_last_voice(request: VoiceRegisterRequest):
    """
    保存最近一次推理成功的音色配置与缓存
    """
    if not last_generation_context:
        raise HTTPException(status_code=400, detail="没有可用的推理记录，请先生成一次音频。")
    
    try:
        ctx = last_generation_context
        voice_id = hashlib.md5(f"{request.name}{time.time()}".encode()).hexdigest()[:8]
        cache_path = VOICE_CACHE_DIR / f"{voice_id}.pt"
        
        # 保存 Prompt Cache
        torch.save(ctx['prompt_cache'], str(cache_path))
        
        # 更新数据库索引
        db = {}
        if VOICE_DB_PATH.exists():
            with open(VOICE_DB_PATH, 'r', encoding='utf-8') as f:
                db = json.load(f)
        
        db[voice_id] = {
            "name": request.name,
            "path": str(cache_path),
            "ref_audio": ctx.get('ref_audio_path'),
            "config": ctx.get('config', {})
        }
        
        with open(VOICE_DB_PATH, 'w', encoding='utf-8') as f:
            json.dump(db, f, ensure_ascii=False, indent=4)
            
        return {"status": "success", "voice_id": voice_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/list_voices")
def list_voices():
    """获取已注册的音色列表"""
    if not VOICE_DB_PATH.exists():
        logger.info("[Voice List] No voices database found.")
        return []
    with open(VOICE_DB_PATH, 'r', encoding='utf-8') as f:
        db = json.load(f)
    result = [{"id": vid, **info} for vid, info in db.items()]
    logger.info(f"[Voice List] Loaded {len(result)} voices: {[v['name'] for v in result]}")
    return result

@app.post("/generate", response_model=SynthesisResponse)
def generate_speech(request: SynthesisRequest):
    """
    语音合成接口
    
    支持三种模式：
    1. 基础 TTS: 仅提供 text
    2. 声音克隆: 提供 text + reference_wav_path
    3. 极致克隆: 提供 text + reference_wav_path + prompt_wav_path + prompt_text
    """
    # 1. 设置随机种子（仅接受前端传来的值，不自行产生）
    if request.seed is not None:
        current_seed = request.seed
        random.seed(current_seed)
        np.random.seed(current_seed)
        torch.manual_seed(current_seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(current_seed)
            torch.backends.cudnn.deterministic = True
            torch.backends.cudnn.benchmark = False
        logger.info(f"[Seed] Using request seed: {current_seed}")
    else:
        logger.warning("[Seed] No seed provided by frontend, using default system randomness")

    try:
        tts_model = load_model()
        prompt_cache = None

        # 检查是否使用已注册的音色缓存
        if request.voice_id:
            logger.info(f"[Inference] Using registered voice_id: {request.voice_id}")
            
            cache_path = VOICE_CACHE_DIR / request.voice_id / "cache.pt"
            
            if not cache_path.exists():
                logger.error(f"[Inference] Voice cache file not found for: {request.voice_id}")
                raise HTTPException(status_code=404, detail=f"Voice ID not found: {request.voice_id}")
            
            logger.info(f"[Inference] Loading voice cache from: {cache_path}")
            prompt_cache = torch.load(str(cache_path), map_location="cpu")
            
            cache_mode = prompt_cache.get('mode', 'unknown')
            has_audio_feat = 'audio_feat' in prompt_cache
            audio_shape = prompt_cache.get('audio_feat', torch.tensor([])).shape if has_audio_feat else 'N/A'
            
            logger.info(f"[Cache Loaded] Mode: {cache_mode}")
            logger.info(f"[Cache Loaded] Has audio_feat: {has_audio_feat}, Shape: {audio_shape}")
        elif request.reference_wav_path:
            # 没有 voice_id 但有参考音频 -> 手动构建缓存（绕过 librosa）
            logger.info(f"[Inference] Building prompt cache from reference audio: {request.reference_wav_path}")
            ref_path = Path(request.reference_wav_path)
            if not ref_path.exists():
                raise HTTPException(status_code=400, detail=f"Reference audio file not found: {request.reference_wav_path}")
            
            try:
                # 1. 使用 soundfile 加载音频（替代 librosa）
                audio_data, sample_rate = sf.read(str(ref_path.resolve()))
                if len(audio_data.shape) > 1:
                    audio_data = audio_data.mean(axis=1)  # 转单声道
                
                # 2. 转换为 torch tensor
                audio_tensor = torch.from_numpy(audio_data).float().unsqueeze(0)
                logger.info(f"[Audio] Loaded with soundfile: shape={audio_tensor.shape}, sr={sample_rate}")
                
                # 3. 重采样到模型需要的采样率
                target_sr = tts_model.tts_model._encode_sample_rate
                if sample_rate != target_sr:
                    import torchaudio.transforms as T
                    resampler = T.Resample(sample_rate, target_sr)
                    audio_tensor = resampler(audio_tensor)
                    logger.info(f"[Audio] Resampled from {sample_rate} to {target_sr}")
                
                # 4. 填充对齐（padding_mode="right"）
                patch_size = tts_model.tts_model.patch_size
                chunk_size = tts_model.tts_model.chunk_size
                patch_len = patch_size * chunk_size
                
                if audio_tensor.size(1) % patch_len != 0:
                    padding_size = patch_len - audio_tensor.size(1) % patch_len
                    audio_tensor = torch.nn.functional.pad(audio_tensor, (0, padding_size))
                    logger.info(f"[Audio] Padded {padding_size} samples (right)")
                
                # 5. VAE 编码
                with torch.inference_mode():
                    audio_tensor = audio_tensor.to(tts_model.tts_model.device)
                    feat = tts_model.tts_model.audio_vae.encode(audio_tensor, target_sr).cpu()
                    
                    # reshape 为 (T, P, D)
                    latent_dim = tts_model.tts_model.audio_vae.latent_dim
                    audio_feat = feat.view(latent_dim, -1, patch_size).permute(1, 2, 0)
                
                # 6. 构建缓存
                prompt_cache = {
                    "ref_audio_feat": audio_feat,
                    "mode": "reference"
                }
                logger.info(f"[Cache Built] Mode: reference, audio_feat shape: {audio_feat.shape}")
                
            except Exception as e:
                logger.error(f"[Audio] Failed to build cache: {e}", exc_info=True)
                raise HTTPException(status_code=500, detail=f"Failed to process reference audio: {str(e)}")
        else:
            logger.info("[Inference] Pure TTS mode, no voice cache")


        # 2. 设置随机种子
        if current_seed is not None:
            random.seed(current_seed)
            np.random.seed(current_seed)
            torch.manual_seed(current_seed)
            if torch.cuda.is_available():
                torch.cuda.manual_seed_all(current_seed)
                torch.backends.cudnn.deterministic = True
                torch.backends.cudnn.benchmark = False
            logger.info(f"[Seed] Random seed set to: {current_seed}")
        else:
            logger.info("[Seed] No seed provided, using random generation.")

        # 3. 文本预处理：正规范化
        processed_text = request.text
        if request.normalize_text:
            logger.info("[Preprocess] Text normalization enabled")
            try:
                from voxcpm.utils.text_normalize import TextNormalizer
                normalizer = TextNormalizer()
                processed_text = normalizer.normalize(request.text)
                logger.info(f"[Preprocess] Original: {request.text}")
                logger.info(f"[Preprocess] Normalized: {processed_text}")
            except Exception as e:
                logger.warning(f"[Preprocess] Text normalization failed: {e}, using original text")
                processed_text = request.text
        else:
            logger.info("[Preprocess] Text normalization disabled")

        # 4. 执行带缓存的推理
        logger.info(f"[Inference] Generating speech for text: {processed_text[:50]}...")
        logger.info(f"[Inference] Parameters - CFG: {request.cfg_value}, Steps: {request.inference_timesteps}")
        
        # 打印模型设备信息
        model_device = next(tts_model.tts_model.parameters()).device
        logger.info(f"[Inference] Model is running on device: {model_device}")

        wav_generator = tts_model.tts_model._generate_with_prompt_cache(
            target_text=processed_text,
            prompt_cache=prompt_cache,
            inference_timesteps=request.inference_timesteps,
            cfg_value=request.cfg_value,
            min_len=2,
            max_len=4096
        )
        
        # 收集生成器结果
        wav_chunks = []
        generated_audio_feat = None
        for wav_chunk, _, audio_feat in wav_generator:
            wav_chunks.append(wav_chunk)
            generated_audio_feat = audio_feat  # 保存生成的音频特征
        wav = torch.cat(wav_chunks, dim=-1) if wav_chunks else torch.tensor([])

        # 构建新的缓存（仅保留生成的 audio_feat，移除 ref_audio_feat）
        new_cache = {
            "audio_feat": generated_audio_feat.cpu() if generated_audio_feat is not None else None,
            "prompt_text": request.text,
            "mode": "continuation"
        }

        # 暂存上下文供"先听后存"使用
        global last_generation_context
        # 确保 seed 始终为整数，便于复现
        final_seed = current_seed if current_seed is not None else random.randint(0, 2**31 - 1)
        
        last_generation_context = {
            'prompt_cache': new_cache,
            'ref_audio_path': request.reference_wav_path,
            'config': {
                'seed': final_seed,
                'cfg_value': request.cfg_value,
                'inference_timesteps': request.inference_timesteps
            }
        }
        logger.info(f"[Context] Generation context saved with audio_feat shape: {generated_audio_feat.shape if generated_audio_feat is not None else 'None'}")
        

        # 4. 保存音频与历史记录（后端负责归档素材，前端负责管理索引）
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 生成历史 ID
        history_id = f"{timestamp}_{hashlib.md5(request.text[:20].encode()).hexdigest()[:6]}"
        history_folder = HISTORY_DIR / history_id
        history_folder.mkdir(parents=True, exist_ok=True)
        
        # 保存音频到历史文件夹
        audio_filename = "audio.wav"
        audio_path = history_folder / audio_filename
        
        wav_data = wav.squeeze(0).cpu().numpy()
        sf.write(str(audio_path), wav_data, tts_model.tts_model.sample_rate)
        
        # 保存缓存文件 (供前端直接复制注册)
        torch.save(new_cache, str(history_folder / "cache.pt"))
        
        # 保存元数据
        duration = len(wav_data) / tts_model.tts_model.sample_rate
        meta_data = {
            "id": history_id,
            "timestamp": datetime.datetime.now().isoformat(),
            "text": request.text,
            "processed_text": processed_text if processed_text != request.text else None,
            "seed": final_seed,
            "cfg_value": request.cfg_value,
            "inference_timesteps": request.inference_timesteps,
            "normalize_text": request.normalize_text,
            "duration": duration,
            "registered": False
        }
        with open(history_folder / "meta.json", 'w', encoding='utf-8') as f:
            json.dump(meta_data, f, ensure_ascii=False, indent=2)
            
        logger.info(f"[History] Saved to {history_folder}")
        
        return SynthesisResponse(success=True, audio_path=str(audio_path), duration=duration, history_id=history_id)
    
    except Exception as e:
        logger.error(f"Generation failed: {e}", exc_info=True)
        return SynthesisResponse(success=False, error=str(e))

@app.get("/get_last_cache")
def get_last_cache():
    """获取最近一次生成的缓存文件（用于首页一键注册）"""
    if not last_generation_context:
        raise HTTPException(status_code=404, detail="No recent generation context found")
    
    try:
        # 将内存中的缓存临时保存为文件流返回
        cache_data = last_generation_context.get('prompt_cache')
        if not cache_data:
            raise HTTPException(status_code=404, detail="Cache data is empty")
            
        import io
        buffer = io.BytesIO()
        torch.save(cache_data, buffer)
        buffer.seek(0)
        
        from fastapi.responses import StreamingResponse
        return StreamingResponse(buffer, media_type="application/octet-stream", headers={
            "Content-Disposition": "attachment; filename=last_cache.pt"
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
def health_check():
    """健康检查接口"""
    return {
        "status": "healthy",
        "model_loaded": model is not None
    }


if __name__ == "__main__":
    # 启动前端监听守护线程（工业标准方案）
    def _monitor_frontend():
        """监听前端进程状态：前端退出时 stdin 管道会自动关闭（EOF），后端随之退出"""
        try:
            sys.stdin.read()  # 阻塞读取，前端退出时自动收到 EOF
        except Exception:
            pass
        logger.info("[后端] 检测到前端退出，自动关闭服务")
        sys.exit(0)

    threading.Thread(target=_monitor_frontend, daemon=True).start()
    
    # 启动服务器
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=8000,
        log_level="info"
    )