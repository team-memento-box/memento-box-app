from fastapi import FastAPI, File, Form, UploadFile
from fastapi.responses import StreamingResponse
from fish_module import init_engine, run_tts
from preprocessing import preprocess_wav_directory
from pathlib import Path
import io
import os
from scipy.io.wavfile import write as write_wav

app = FastAPI()
engine = init_engine()

@app.post("/infer")
async def infer(
    reference_wav: UploadFile = File(...),
    text: str = Form(...),
    prompt_text: str = Form("")
):
    before_dir = Path("beforepreprocessing")
    after_dir = Path("afterpreprocessing")

    before_dir.mkdir(parents=True, exist_ok=True)
    after_dir.mkdir(parents=True, exist_ok=True)

    input_path = before_dir / reference_wav.filename
    with open(input_path, "wb") as f:
        f.write(await reference_wav.read())

    try:
        preprocess_wav_directory(str(before_dir), str(after_dir))
        processed_path = next(after_dir.glob("*.wav"), None)
        if not processed_path or not processed_path.exists():
            raise FileNotFoundError("전처리된 .wav 파일을 찾을 수 없습니다.")

        sample_rate, waveform = run_tts(engine, text, str(processed_path), prompt_text)

        buffer = io.BytesIO()
        write_wav(buffer, sample_rate, waveform)
        buffer.seek(0)

        return StreamingResponse(buffer, media_type="audio/wav")

    except Exception as e:
        return {"status": "error", "message": str(e)}

    finally:
        try:
            if input_path.exists():
                input_path.unlink()
        except:
            pass

        for f in after_dir.glob("*.wav"):
            try:
                f.unlink()
            except:
                pass