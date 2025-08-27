import os
import subprocess
from pathlib import Path

def preprocess_wav_directory(input_dir, output_dir, sample_rate=16000):
    input_dir = Path(input_dir)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    for wav_file in input_dir.glob("*.wav"):
        output_file = output_dir / wav_file.name
        command = [
            "ffmpeg",
            "-y",
            "-i", str(wav_file),
            "-ar", str(sample_rate),
            "-ac", "1",
            "-acodec", "pcm_s16le",
            str(output_file)
        ]
        subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    print(f"✅ 전처리 완료: {len(list(output_dir.glob('*.wav')))}개 파일이 {output_dir}에 저장되었습니다.")