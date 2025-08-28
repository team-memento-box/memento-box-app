#!/usr/bin/env python3

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fish_module import init_engine, run_tts
import numpy as np
import base64
from io import BytesIO
from scipy.io.wavfile import write as write_wav
import logging
import requests
import tempfile
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Fish-Speech TTS GPU Server")

# Global engine variable
engine = None

class TTSRequest(BaseModel):
    text: str
    reference_audio: str = "test.wav"
    reference_text: str = ""
    output_format: str = "base64"  # "base64" or "file"

class TTSResponse(BaseModel):
    sample_rate: int
    audio_base64: str = None
    file_path: str = None
    duration: float
    status: str

def download_audio_from_url(url: str) -> str:
    """Download audio file from URL and save to temporary file"""
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as tmp_file:
            for chunk in response.iter_content(chunk_size=8192):
                tmp_file.write(chunk)
            return tmp_file.name
    except Exception as e:
        logger.error(f"Failed to download audio from {url}: {e}")
        raise HTTPException(status_code=400, detail=f"Failed to download audio: {str(e)}")

@app.on_event("startup")
async def startup_event():
    global engine
    logger.info("Loading Fish-Speech models...")
    try:
        engine = init_engine(
            llama_checkpoint_path="checkpoints/fish-speech-1.5-yth-lora-8000",
            decoder_checkpoint_path="checkpoints/fish-speech-1.5/firefly-gan-vq-fsq-8x1024-21hz-generator.pth",
            device="cuda",
            half=False,
            compile=False
        )
        logger.info("Models loaded successfully!")
    except Exception as e:
        logger.error(f"Failed to load models: {e}")
        raise e

@app.post("/tts", response_model=TTSResponse)
async def text_to_speech(request: TTSRequest):
    temp_audio_path = None
    try:
        logger.info(f"TTS request: {request.text[:50]}...")
        
        # Handle reference audio
        if request.reference_audio.startswith("http"):
            # Download from URL (Supabase storage)
            temp_audio_path = download_audio_from_url(request.reference_audio)
            prompt_audio_path = temp_audio_path
        else:
            # Use local file
            prompt_audio_path = request.reference_audio if request.reference_audio != "test.wav" else "test.wav"
        
        # Run inference
        sample_rate, waveform = run_tts(
            engine=engine,
            input_text=request.text,
            prompt_audio_path=prompt_audio_path,
            prompt_text=request.reference_text
        )
        
        duration = len(waveform) / sample_rate
        
        if request.output_format == "base64":
            # Convert to base64
            buffer = BytesIO()
            waveform_int16 = (waveform * 32767).astype(np.int16)
            write_wav(buffer, sample_rate, waveform_int16)
            buffer.seek(0)
            audio_data = base64.b64encode(buffer.getvalue()).decode()
            
            return TTSResponse(
                sample_rate=sample_rate,
                audio_base64=audio_data,
                duration=duration,
                status="success"
            )
        else:
            # Save to file
            import time
            timestamp = int(time.time())
            output_path = f"outputs/output_{timestamp}.wav"
            
            # Create output directory
            from pathlib import Path
            Path("outputs").mkdir(exist_ok=True)
            
            # Save file
            waveform_int16 = (waveform * 32767).astype(np.int16)
            write_wav(output_path, sample_rate, waveform_int16)
            
            return TTSResponse(
                sample_rate=sample_rate,
                file_path=output_path,
                duration=duration,
                status="success"
            )
            
    except Exception as e:
        logger.error(f"TTS inference failed: {e}")
        raise HTTPException(status_code=500, detail=f"TTS inference failed: {str(e)}")
    finally:
        # Clean up temporary file
        if temp_audio_path and os.path.exists(temp_audio_path):
            try:
                os.unlink(temp_audio_path)
                logger.info(f"Cleaned up temporary file: {temp_audio_path}")
            except Exception as e:
                logger.warning(f"Failed to clean up temporary file {temp_audio_path}: {e}")

@app.get("/health")
async def health_check():
    return {"status": "healthy", "model_loaded": engine is not None}

@app.get("/")
async def root():
    return {"message": "Fish-Speech TTS GPU Server", "docs": "/docs"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")