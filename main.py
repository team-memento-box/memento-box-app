#!/usr/bin/env python3

import argparse
import numpy as np
from pathlib import Path
from scipy.io.wavfile import write as write_wav
from fish_module import init_engine, run_tts
from preprocessing import preprocess_wav_directory


def main():
    parser = argparse.ArgumentParser(description="Fish-Speech TTS Inference")
    parser.add_argument("--text", type=str, default="안녕하세요", required=True, help="Text to synthesize")
    parser.add_argument("--output", type=str, default="output.wav", help="Output audio file path")
    parser.add_argument("--reference-audio", type=str, default="test.wav", help="Reference audio file path")
    parser.add_argument("--reference-text", type=str, default="", help="Reference audio transcription")
    parser.add_argument("--llama-checkpoint", type=str, default="checkpoints/fish-speech-1.5", 
                       help="LLaMA model checkpoint path")
    parser.add_argument("--decoder-checkpoint", type=str, 
                       default="checkpoints/fish-speech-1.5/firefly-gan-vq-fsq-8x1024-21hz-generator.pth",
                       help="Decoder model checkpoint path")
    parser.add_argument("--device", type=str, default="cuda", help="Device to use (cuda/cpu)")
    parser.add_argument("--half", action="store_true", help="Use half precision")
    parser.add_argument("--compile", action="store_true", help="Compile models for faster inference")
    parser.add_argument("--preprocess", action="store_true", help="Preprocess reference audio before use")
    parser.add_argument("--input-dir", type=str, default="input_wav", help="Input directory for preprocessing")
    parser.add_argument("--processed-dir", type=str, default="processed_wav", help="Output directory for preprocessing")
    
    args = parser.parse_args()
    
    print("Fish-Speech TTS inference starting...")
    print(f"Text: {args.text}")
    print(f"Output file: {args.output}")
    
    # Preprocess reference audio if requested
    if args.preprocess:
        print("Preprocessing audio files...")
        preprocess_wav_directory(args.input_dir, args.processed_dir, sample_rate=16000)
        # Update reference audio path to use processed version
        if args.reference_audio and Path(args.input_dir).exists():
            processed_ref = Path(args.processed_dir) / Path(args.reference_audio).name
            if processed_ref.exists():
                args.reference_audio = str(processed_ref)
                print(f"Using preprocessed reference audio: {args.reference_audio}")
    
    # Initialize the TTS engine
    print("Loading models...")
    engine = init_engine(
        llama_checkpoint_path=args.llama_checkpoint,
        decoder_checkpoint_path=args.decoder_checkpoint,
        device=args.device,
        half=args.half,
        compile=args.compile
    )
    print("Models loaded successfully!")
    
    # Run TTS inference
    print("Running TTS inference...")
    sample_rate, waveform = run_tts(
        engine=engine,
        input_text=args.text,
        prompt_audio_path=args.reference_audio,
        prompt_text=args.reference_text
    )
    
    # Save audio file
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Convert float32 to int16 for saving
    waveform_int16 = (waveform * 32767).astype(np.int16)
    write_wav(str(output_path), sample_rate, waveform_int16)
    
    print(f"TTS inference completed! Audio saved to: {output_path}")
    print(f"Sample rate: {sample_rate} Hz")
    print(f"Duration: {len(waveform) / sample_rate:.2f} seconds")


if __name__ == "__main__":
    main()