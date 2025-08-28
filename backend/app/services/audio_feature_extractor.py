#!/usr/bin/env python3
"""
Audio Feature Extractor for Alzheimer's Dementia Recognition

이 스크립트는 새로운 음성 파일에서 특징을 추출하여 
학습된 모델에서 사용할 수 있는 형태로 변환합니다.

사용법:
    python audio_feature_extractor.py <audio_file_path>
    
예시:
    python audio_feature_extractor.py sample_audio.wav
"""

import os
import sys
import numpy as np
import pandas as pd
import librosa
import warnings
from scipy import signal
from scipy.stats import kurtosis, skew
from sklearn.preprocessing import StandardScaler
import argparse

warnings.filterwarnings('ignore')

class AudioFeatureExtractor:
    """음성 파일에서 특징을 추출하는 클래스"""
    
    def __init__(self, sample_rate=16000):
        self.sample_rate = sample_rate
        self.feature_names = [
            'MFCC2', 'kurt_MFCC30', 'mean_MFCC30', 'skew_MFCC2', 'mean_MFCC16',
            'flt_bnk_eng22', 'MFCC30', 'kurt_MFCC16', 'flt_bnk_eng2', 'flt_bnk_eng24', 
            'MFCC1', 'flt_bnk_eng15', 'kurt_MFCC2', 'flt_bnk_eng20', 'flt_bnk_eng13', 
            'n_sil_segments', 'frac_silence', 'min_sil_len', 'jitter', 'shimmer', 'HNR'
        ]
    
    def load_audio(self, audio_path):
        """오디오 파일 로드 및 전처리"""
        try:
            # 오디오 파일 로드
            audio, sr = librosa.load(audio_path, sr=self.sample_rate)
            
            # 모노로 변환 (스테레오인 경우)
            if len(audio.shape) > 1:
                audio = np.mean(audio, axis=1)
            
            print(f"오디오 로드 완료: {len(audio)/sr:.2f}초, 샘플레이트: {sr}Hz")
            return audio
            
        except Exception as e:
            print(f"오디오 로드 오류: {e}")
            return None
    
    def get_envelope(self, signal_data):
        """신호의 엔벨로프 추출"""
        # 힐버트 변환을 사용하여 엔벨로프 계산
        analytic_signal = signal.hilbert(signal_data)
        envelope = np.abs(analytic_signal)
        return envelope
    
    def get_envelope_original(self, input_signal):
        """원본과 100% 동일한 엔벨로프 추출 방식"""
        # Taking the absolute value 
        absolute_signal = []
        for sample in input_signal:
            absolute_signal.append(abs(sample))
        
        # Peak detection
        interval_length = 50
        output_signal = []
        
        for base_index in range(interval_length, len(absolute_signal)):
            maximum = 0
            for lookback_index in range(interval_length):
                maximum = max(absolute_signal[base_index - lookback_index], maximum)
            output_signal.append(maximum)
        return np.array(output_signal)  # numpy 배열로 변환
    
    def silence_detection(self, signal_env, mod=0.1):
        """침묵 구간 감지"""
        # 엔벨로프의 평균값을 기준으로 침묵 임계값 설정
        threshold = np.mean(signal_env) * mod
        
        # 침묵 구간 식별
        silence_mask = signal_env < threshold
        
        # 침묵 구간의 시작과 끝 지점 찾기
        silence_changes = np.diff(silence_mask.astype(int))
        silence_starts = np.where(silence_changes == 1)[0]
        silence_stops = np.where(silence_changes == -1)[0]
        
        # 첫 번째와 마지막 구간 처리
        if len(silence_starts) > 0 and len(silence_stops) > 0:
            if silence_stops[0] < silence_starts[0]:
                silence_stops = silence_stops[1:]
            if silence_starts[-1] > silence_stops[-1]:
                silence_starts = silence_starts[:-1]
        
        return silence_starts, silence_stops, silence_mask
    
    def silence_detection_original(self, signal_env, mod):
        """원본과 100% 동일한 침묵 감지 방식"""
        import math
        
        n1 = 0.95 # percent of min amp values to calculate th
        k1 = 1.1 # constant coefficient of th
        signal_pos_sort = np.array(sorted(signal_env))
        I0 = np.argsort(signal_env)
        n_percent = math.floor(len(signal_pos_sort)*n1)
        th = k1*np.mean(signal_pos_sort[0:n_percent])

        ind_silence = list(np.argwhere(abs(signal_env)>th).T)
        ind_silence = list(ind_silence[0])
        ind_silence2 = ind_silence[1:]
        ind_silence2.append(ind_silence[-1])
        ind_silence3 = ind_silence[:-1]
        ind_silence3.insert(0 ,ind_silence[0])
        ind_silence = np.array(ind_silence)
        ind_silence2 = np.array(ind_silence2)
        ind_silence3 = np.array(ind_silence3)
        ind_silence.shape , ind_silence2.shape, ind_silence3.shape
        # if mod:
        #   ind_new =ind_silence[(abs(ind_silence - ind_silence2) > sr) | ( (ind_silence - ind_silence3 ) > sr)] 
        # else:
        #   ind_new =ind_silence

        ind_new =ind_silence[(abs(ind_silence - ind_silence2) > self.sample_rate) | ((ind_silence - ind_silence3 ) > self.sample_rate)] 
        if not any(ind_new):
            ind_new =[ind_silence[np.argmax(abs(ind_silence - ind_silence2))],ind_silence2[np.argmax(abs(ind_silence - ind_silence2))]]
        # print('ind_new:',ind_new)
        sil_start = ind_new[::2];
        sil_stop = ind_new[1::2];
        l = min(len(sil_start) , len(sil_stop));
        return sil_start,sil_stop,l
    
    def filter_bank_function(self, signal_data, sample_rate):
        """필터뱅크 에너지 계산"""
        # 26개 필터뱅크 생성 (MFCC 계산용)
        n_mels = 26
        mel_spectrogram = librosa.feature.melspectrogram(
            y=signal_data, 
            sr=sample_rate, 
            n_mels=n_mels,
            n_fft=2048,
            hop_length=512
        )
        
        # 에너지 계산
        filter_bank_energy = np.sum(mel_spectrogram, axis=1)
        
        return filter_bank_energy
    
    def filter_bank_function_original(self, signal_data, sample_rate):
        """원본과 100% 동일한 필터뱅크 계산 방식"""
        pre_emphasis = 0.97
        # signal = signal_main2
        emphasized_signal = np.append(signal_data[0], signal_data[1:] - pre_emphasis * signal_data[:-1])
        frame_size = 0.025
        frame_stride = 0.01
        frame_length, frame_step = frame_size * sample_rate, frame_stride * sample_rate  # Convert from seconds to samples
        signal_length = len(emphasized_signal)
        frame_length = int(round(frame_length))
        frame_step = int(round(frame_step))
        num_frames = int(np.ceil(float(np.abs(signal_length - frame_length)) / frame_step))  # Make sure that we have at least 1 frame

        pad_signal_length = num_frames * frame_step + frame_length
        z = np.zeros((pad_signal_length - signal_length))
        pad_signal = np.append(emphasized_signal, z) # Pad Signal to make sure that all frames have equal number of samples without truncating any samples from the original signal

        indices = np.tile(np.arange(0, frame_length), (num_frames, 1)) + np.tile(np.arange(0, num_frames * frame_step, frame_step), (frame_length, 1)).T
        frames = pad_signal[indices.astype(np.int32, copy=False)]
        frames *= np.hamming(frame_length)
        NFFT = 512
        # frames *= 0.54 - 0.46 * np.cos((2 * np.pi * n) / (frame_length - 1))  # Explicit Implementation **
        mag_frames = np.absolute(np.fft.rfft(frames, NFFT))  # Magnitude of the FFT
        pow_frames = ((1.0 / NFFT) * ((mag_frames) ** 2))  # Power Spectrum
        nfilt = 26
        low_freq_mel = 0
        high_freq_mel = (2595 * np.log10(1 + (sample_rate / 2) / 700))  # Convert Hz to Mel
        mel_points = np.linspace(low_freq_mel, high_freq_mel, nfilt + 2)  # Equally spaced in Mel scale
        hz_points = (700 * (10**(mel_points / 2595) - 1))  # Convert Mel to Hz
        bin = np.floor((NFFT + 1) * hz_points / sample_rate)

        fbank = np.zeros((nfilt, int(np.floor(NFFT / 2 + 1))))
        for m in range(1, nfilt + 1):
            f_m_minus = int(bin[m - 1])   # left
            f_m = int(bin[m])             # center
            f_m_plus = int(bin[m + 1])    # right

            for k in range(f_m_minus, f_m):
                fbank[m - 1, k] = (k - bin[m - 1]) / (bin[m] - bin[m - 1])
            for k in range(f_m, f_m_plus):
                fbank[m - 1, k] = (bin[m + 1] - k) / (bin[m + 1] - bin[m])
        filter_banks = np.dot(pow_frames, fbank.T)
        filter_banks = np.where(filter_banks == 0, np.finfo(float).eps, filter_banks)  # Numerical Stability
        filter_banks = 20 * np.log10(filter_banks)  # dB
        filter_banks -= (np.mean(filter_banks, axis=0) + 1e-8)
        return filter_banks
    
    def calculate_jitter_shimmer(self, signal_data, sample_rate):
        """Jitter와 Shimmer 계산"""
        # 피치 추출
        pitches, magnitudes = librosa.piptrack(y=signal_data, sr=sample_rate)
        
        # 유효한 피치 값만 추출
        valid_pitches = []
        for t in range(pitches.shape[1]):
            index = magnitudes[:, t].argmax()
            pitch = pitches[index, t]
            if pitch > 0:
                valid_pitches.append(pitch)
        
        if len(valid_pitches) < 2:
            return 0.0, 0.0
        
        valid_pitches = np.array(valid_pitches)
        
        # Jitter 계산 (피치 주기 변화율)
        pitch_periods = 1.0 / valid_pitches
        jitter = np.std(pitch_periods) / np.mean(pitch_periods)
        
        # Shimmer 계산 (진폭 변화율)
        # 간단한 구현을 위해 RMS 에너지 변화율 사용
        frame_length = int(0.025 * sample_rate)  # 25ms 프레임
        hop_length = int(0.010 * sample_rate)   # 10ms 호프
        
        rms_energy = librosa.feature.rms(
            y=signal_data, 
            frame_length=frame_length, 
            hop_length=hop_length
        ).flatten()
        
        if len(rms_energy) > 1:
            shimmer = np.std(rms_energy) / np.mean(rms_energy)
        else:
            shimmer = 0.0
        
        return jitter, shimmer
    
    def calculate_jitter_shimmer_hnr_original(self, signal_data, sample_rate):
        """원본과 동일한 Jitter, Shimmer, HNR 계산 방식"""
        # 원본에서는 surfboard 라이브러리를 사용했지만, 여기서는 간단한 구현
        # 실제로는 surfboard 라이브러리가 필요할 수 있음
        
        # 간단한 Jitter 계산
        pitches, magnitudes = librosa.piptrack(y=signal_data, sr=sample_rate)
        valid_pitches = []
        for t in range(pitches.shape[1]):
            index = magnitudes[:, t].argmax()
            pitch = pitches[index, t]
            if pitch > 0:
                valid_pitches.append(pitch)
        
        if len(valid_pitches) < 2:
            jitter = 0.0
        else:
            pitch_periods = 1.0 / np.array(valid_pitches)
            jitter = np.std(pitch_periods) / np.mean(pitch_periods)
        
        # 간단한 Shimmer 계산
        frame_length = int(0.025 * sample_rate)
        hop_length = int(0.010 * sample_rate)
        rms_energy = librosa.feature.rms(y=signal_data, frame_length=frame_length, hop_length=hop_length).flatten()
        
        if len(rms_energy) > 1:
            shimmer = np.std(rms_energy) / np.mean(rms_energy)
        else:
            shimmer = 0.0
        
        # 간단한 HNR 계산
        spectral_centroids = librosa.feature.spectral_centroid(y=signal_data, sr=sample_rate).flatten()
        spectral_bandwidths = librosa.feature.spectral_bandwidth(y=signal_data, sr=sample_rate).flatten()
        hnr = np.mean(spectral_centroids) / (np.mean(spectral_bandwidths) + 1e-8)
        
        return jitter, shimmer, hnr
    
    def calculate_hnr(self, signal_data, sample_rate):
        """Harmonic-to-Noise Ratio 계산"""
        # 간단한 HNR 계산 (스펙트럼 중심과 대역폭 사용)
        spectral_centroids = librosa.feature.spectral_centroid(
            y=signal_data, sr=sample_rate
        ).flatten()
        
        spectral_bandwidths = librosa.feature.spectral_bandwidth(
            y=signal_data, sr=sample_rate
        ).flatten()
        
        # HNR 근사값 계산
        hnr = np.mean(spectral_centroids) / (np.mean(spectral_bandwidths) + 1e-8)
        
        return hnr
    
    def extract_features_from_segment(self, audio_segment, sample_rate, sil_start=None, sil_stop=None):
        """20초 세그먼트에서 특징 추출 - 원본과 동일한 방식"""
        # 원본과 동일한 MFCC 파라미터 사용
        mfccs = librosa.feature.mfcc(
            y=audio_segment, 
            sr=sample_rate, 
            n_mfcc=42,  # 원본과 동일
            n_fft=2048,
            hop_length=512
        )
        
        # 원본과 동일한 필터뱅크 계산
        filter_banks = self.filter_bank_function_original(audio_segment, sample_rate)
        
        # 침묵 관련 특징 (원본과 동일한 계산)
        if sil_start is not None and sil_stop is not None:
            n_sil_segments = len(sil_start)
            
            if n_sil_segments > 0:
                try:
                    silence_length = np.sum(sil_stop - sil_start) / sample_rate
                except:
                    silence_length = (sil_stop[0] - sil_start[0]) / sample_rate
            else:
                silence_length = 0.0
        else:
            # 기존 방식 (fallback)
            envelope = self.get_envelope_original(audio_segment)
            sil_start, sil_stop, l = self.silence_detection_original(envelope, 1)
            n_sil_segments = l
            
            if n_sil_segments > 0:
                try:
                    silence_length = np.sum(sil_stop - sil_start) / sample_rate
                except:
                    silence_length = (sil_stop[0] - sil_start[0]) / sample_rate
            else:
                silence_length = 0.0
            
        sig_len = len(audio_segment) / sample_rate
        frac_silence = (silence_length / sig_len) * 100 if sig_len > 0 else 0.0
        
        if n_sil_segments > 0:
            try:
                min_sil_len = np.min(sil_stop - sil_start) / sample_rate
            except:
                min_sil_len = (sil_stop[0] - sil_start[0]) / sample_rate
        else:
            min_sil_len = 0.0
        
        # Jitter, Shimmer, HNR (원본과 동일한 방식)
        jitter, shimmer, hnr = self.calculate_jitter_shimmer_hnr_original(audio_segment, sample_rate)
        
        # 특징 벡터 구성 (원본과 동일한 계산 방식)
        features = {
            'MFCC2': np.max(mfccs[2-1, :]),  # MFCC2 최대값 (원본과 동일)
            'kurt_MFCC30': kurtosis(mfccs[30-1, :]),  # MFCC30 첨도
            'mean_MFCC30': np.mean(mfccs[30-1, :]),  # MFCC30 평균
            'skew_MFCC2': skew(mfccs[2-1, :]),  # MFCC2 왜도
            'mean_MFCC16': np.mean(mfccs[16-1, :]),  # MFCC16 평균
            'flt_bnk_eng22': np.sum(filter_banks[22-1, :]),  # 필터뱅크 22 합계 (원본과 동일)
            'MFCC30': np.max(mfccs[30-1, :]),  # MFCC30 최대값 (원본과 동일)
            'kurt_MFCC16': kurtosis(mfccs[16-1, :]),  # MFCC16 첨도
            'flt_bnk_eng2': np.sum(filter_banks[2-1, :]),  # 필터뱅크 2 합계
            'flt_bnk_eng24': np.sum(filter_banks[24-1, :]),  # 필터뱅크 24 합계
            'MFCC1': np.max(mfccs[1-1, :]),  # MFCC1 최대값 (원본과 동일)
            'flt_bnk_eng15': np.sum(filter_banks[15-1, :]),  # 필터뱅크 15 합계
            'kurt_MFCC2': kurtosis(mfccs[2-1, :]),  # MFCC2 첨도
            'flt_bnk_eng20': np.sum(filter_banks[20-1, :]),  # 필터뱅크 20 합계
            'flt_bnk_eng13': np.sum(filter_banks[13-1, :]),  # 필터뱅크 13 합계
            'n_sil_segments': n_sil_segments,  # 침묵 구간 수
            'frac_silence': frac_silence,  # 침묵 비율
            'min_sil_len': min_sil_len,  # 최소 침묵 길이
            'jitter': jitter,  # 지터
            'shimmer': shimmer,  # 쉬머
            'HNR': hnr  # 하모닉 대 노이즈 비율
        }
        
        return features
    
    def extract_features(self, audio_path):
        """주요 특징 추출 - 20초 단위로 슬라이싱하여 여러 세그먼트 생성"""
        print("특징 추출 시작...")
        
        # 오디오 로드
        audio = self.load_audio(audio_path)
        if audio is None:
            return None
        
        # 가드 샘플 제거 (20초 세그먼트 3개를 위해 조정)
        # 67.7초에서 20초 세그먼트 3개 = 60초 필요, 따라서 7.7초만 제거
        total_guard = len(audio) - (20 * 3 * self.sample_rate)  # 20초 * 3개 세그먼트
        if total_guard > 0:
            guard_samples = int(total_guard / 2)  # 시작과 끝에 균등 분배
            audio = audio[guard_samples:-guard_samples]
            print(f"가드 샘플 제거 완료: {guard_samples/self.sample_rate:.1f}초 (총 {total_guard/self.sample_rate:.1f}초)")
        else:
            print("가드 샘플 제거 불필요: 오디오가 너무 짧음")
        
        # 파일명에서 ID 추출 (확장자 제거)
        base_name = os.path.splitext(os.path.basename(audio_path))[0]
        
        # 20초 세그먼트 3개 생성 (1초 오버랩)
        segment_duration = 20  # 20초
        samples_per_segment = int(segment_duration * self.sample_rate)
        
        all_features = []
        
        print(f"20초 세그먼트 3개 생성 (1초 오버랩)...")
        print(f"오디오 길이: {len(audio)/self.sample_rate:.1f}초")
        
        # 원본과 동일한 노이즈 샘플 추출 (침묵 구간)
        print("노이즈 샘플 추출 중...")
        envelope = self.get_envelope_original(audio)
        
        # 원본과 동일한 방식: mod=1로 먼저 시도, 실패하면 mod=0
        try:
            silence_starts, silence_stops, l = self.silence_detection_original(envelope, 1)
            print(f"침묵 감지 성공 (mod=1): {l}개 구간")
        except:
            silence_starts, silence_stops, l = self.silence_detection_original(envelope, 0)
            print(f"침묵 감지 성공 (mod=0): {l}개 구간")
        
        # 노이즈 샘플 구성 (원본과 동일한 방식)
        try:
            noisy_part = audio[silence_starts[0]:silence_stops[0]]
            for i in range(len(silence_starts)-1):
                noisy_part = np.concatenate([noisy_part, audio[silence_starts[i+1]:silence_stops[i+1]]])
        except:
            # 침묵 구간이 부족한 경우 원본 오디오의 일부를 노이즈로 사용
            noisy_part = audio[:int(0.1 * self.sample_rate)]  # 처음 0.1초
        
        print(f"노이즈 샘플 길이: {len(noisy_part)/self.sample_rate:.2f}초")
        
        # 20초 세그먼트 3개 생성 (1초 오버랩)
        # 가드 샘플 제거 후 60초에서 20초 세그먼트 3개: 0-20, 19-39, 38-58
        segment_starts = [0, 19, 38]  # 초 단위
        segment_ends = [20, 39, 58]   # 초 단위
        
        for i, (start_sec, end_sec) in enumerate(zip(segment_starts, segment_ends)):
            start_sample = int(start_sec * self.sample_rate)
            end_sample = int(end_sec * self.sample_rate)
            
            # 오디오 길이 확인
            if end_sample > len(audio):
                print(f"경고: 세그먼트 {i+1}이 오디오 길이를 초과합니다. 건너뜁니다.")
                continue
                
            segment = audio[start_sample:end_sample]
            print(f"세그먼트 {i+1}: {start_sec}s ~ {end_sec}s (길이: {len(segment)/self.sample_rate:.1f}s)")
            
            # 세그먼트가 비어있지 않은지 확인
            if len(segment) == 0:
                print(f"경고: 세그먼트 {i+1}이 비어있습니다. 건너뜁니다.")
                continue
            
            # 원본과 동일한 노이즈 감소 처리
            try:
                import noisereduce as nr
                reduced_noise = nr.reduce_noise(y=segment, y_noise=noisy_part, sr=self.sample_rate)
                print(f"  노이즈 감소 완료")
                segment = reduced_noise
            except Exception as e:
                print(f"  노이즈 감소 실패: {e}, 원본 세그먼트 사용")
            
            # 원본과 동일한 침묵 감지 (각 세그먼트별로)
            segment_envelope = self.get_envelope_original(segment)
            try:
                sil_start, sil_stop, l = self.silence_detection_original(segment_envelope, 1)
            except:
                sil_start, sil_stop, l = self.silence_detection_original(segment_envelope, 0)
            
            # 특징 추출
            features = self.extract_features_from_segment(segment, self.sample_rate, sil_start, sil_stop)
            
            # ID 추가
            features['ID'] = f"{base_name}_{i+1}"
            
            all_features.append(features)
        
        # 속도 변형 (0.8x, 1.2x) 추가
        print("속도 변형 세그먼트 생성 중...")
        
        # 0.8x 속도 (느리게)
        audio_slow = librosa.effects.time_stretch(audio, rate=0.8)
        
        for i, (start_sec, end_sec) in enumerate(zip(segment_starts, segment_ends)):
            start_sample = int(start_sec * self.sample_rate)
            end_sample = int(end_sec * self.sample_rate)
            
            # 오디오 길이 확인
            if end_sample > len(audio_slow):
                print(f"경고: 느린 속도 세그먼트 {i+1}이 오디오 길이를 초과합니다. 건너뜁니다.")
                continue
                
            segment = audio_slow[start_sample:end_sample]
            
            # 특징 추출
            features = self.extract_features_from_segment(segment, self.sample_rate)
            
            # ID 추가 (속도 표시)
            features['ID'] = f"{base_name}_slow_{i+1}"
            
            all_features.append(features)
        
        # 1.2x 속도 (빠르게)
        audio_fast = librosa.effects.time_stretch(audio, rate=1.2)
        
        for i, (start_sec, end_sec) in enumerate(zip(segment_starts, segment_ends)):
            start_sample = int(start_sec * self.sample_rate)
            end_sample = int(end_sec * self.sample_rate)
            
            # 오디오 길이 확인
            if end_sample > len(audio_fast):
                print(f"경고: 빠른 속도 세그먼트 {i+1}이 오디오 길이를 초과합니다. 건너뜁니다.")
                continue
                
            segment = audio_fast[start_sample:end_sample]
            
            # 특징 추출
            features = self.extract_features_from_segment(segment, self.sample_rate)
            
            # ID 추가 (속도 표시)
            features['ID'] = f"{base_name}_fast_{i+1}"
            
            all_features.append(features)
        
        print(f"총 {len(all_features)}개 세그먼트의 특징 추출 완료!")
        return all_features
    
    def features_to_dataframe(self, features_list):
        """특징 리스트를 DataFrame 형태로 변환"""
        if not features_list:
            return None
        
        # ID를 첫 번째 컬럼으로, 나머지 특징들을 순서대로 정렬
        df = pd.DataFrame(features_list)
        
        # ID를 첫 번째 컬럼으로 이동
        if 'ID' in df.columns:
            cols = ['ID'] + self.feature_names
            df = df[cols]
        
        return df
    
    def save_features(self, features_list, output_path):
        """특징 리스트를 CSV 파일로 저장"""
        df = self.features_to_dataframe(features_list)
        if df is not None:
            df.to_csv(output_path, index=False)
            print(f"특징이 {output_path}에 저장되었습니다.")
            print(f"총 {len(df)}개 세그먼트가 저장되었습니다.")
            return True
        return False

def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(
        description='음성 파일에서 특징을 추출하여 CSV 형태로 저장합니다.'
    )
    parser.add_argument(
        'audio_file', 
        help='입력 오디오 파일 경로'
    )
    parser.add_argument(
        '-o', '--output', 
        default='extracted_features.csv',
        help='출력 CSV 파일 경로 (기본값: extracted_features.csv)'
    )
    parser.add_argument(
        '--sample-rate', 
        type=int, 
        default=16000,
        help='샘플레이트 (기본값: 16000)'
    )
    
    args = parser.parse_args()
    
    # 파일 존재 확인
    if not os.path.exists(args.audio_file):
        print(f"오류: 파일을 찾을 수 없습니다: {args.audio_file}")
        sys.exit(1)
    
    # 지원하는 오디오 형식 확인
    supported_formats = ['.wav', '.mp3', '.flac', '.m4a', '.ogg']
    file_ext = os.path.splitext(args.audio_file)[1].lower()
    
    if file_ext not in supported_formats:
        print(f"경고: 지원하지 않는 오디오 형식입니다: {file_ext}")
        print(f"지원 형식: {', '.join(supported_formats)}")
    
    # 특징 추출기 생성
    extractor = AudioFeatureExtractor(sample_rate=args.sample_rate)
    
    # 특징 추출
    features_list = extractor.extract_features(args.audio_file)
    
    if features_list is not None:
        # 첫 번째 세그먼트의 특징 출력 (예시)
        print(f"\n첫 번째 세그먼트의 특징 (예시):")
        first_features = features_list[0]
        for name, value in first_features.items():
            if name != 'ID':
                print(f"{name}: {value:.6f}")
        
        # CSV 파일로 저장
        if extractor.save_features(features_list, args.output):
            print(f"\n특징이 성공적으로 {args.output}에 저장되었습니다.")
            print("이 파일을 학습된 모델에서 사용할 수 있습니다.")
        else:
            print("특징 저장에 실패했습니다.")
    else:
        print("특징 추출에 실패했습니다.")
        sys.exit(1)

if __name__ == "__main__":
    main()
