
import 'package:just_audio/just_audio.dart';
import 'package:http/http.dart' as http;
import 'dart:async';
import 'dart:io';
import 'dart:convert';

class AudioService {
  final AudioPlayer _audioPlayer = AudioPlayer();
  AudioPlayer get player => _audioPlayer;
  String? _currentAsset;

  // 재생 상태 스트림 컨트롤러 추가
  final StreamController<bool> _playingController =
      StreamController<bool>.broadcast();

  // 현재 재생 여부를 확인하는 getter
  bool get isPlaying => _audioPlayer.playerState.playing;

  // 완료 콜백
  void Function()? onCompleted;

  Duration? getDuration() => _audioPlayer.duration;

  AudioService() {
    _audioPlayer.playerStateStream.listen((state) {
      final isPlaying =
          state.playing && state.processingState != ProcessingState.completed;
      _playingController.add(isPlaying);

      // 완료 시 콜백 호출
      if (state.processingState == ProcessingState.completed) {
        onCompleted?.call();
      }
    });
  }

  Future<void> loadAsset(String path) async {
    if (_currentAsset != path || _audioPlayer.audioSource == null) {
      await _audioPlayer.setAsset(path);
      _currentAsset = path;
    }
  }

  Future<void> loadUrl(String url) async {
    if (_currentAsset != url || _audioPlayer.audioSource == null) {
      await _audioPlayer.setUrl(url);
      _currentAsset = url;
    }
  }

  Future<void> loadAudio(String path) async {
    if (path.startsWith('http')) {
      await loadUrl(path);
    } else {
      await loadAsset(path);
    }
  }

  // AudioService() {
  //   _audioPlayer.playerStateStream.listen((state) {
  //     if (state.processingState == ProcessingState.completed) {
  //       onCompleted?.call(); // 콜백 실행
  //     }
  //   });
  // }

  Future<void> play() async {
    final duration = _audioPlayer.duration;
    final position = _audioPlayer.position;

    // 종료된 경우 처음부터 재생
    if (duration != null && position >= duration) {
      await _audioPlayer.seek(Duration.zero);
    }

    await _audioPlayer.play();

    // 강제로 스트림을 통해 재생 상태 업데이트
    // 혹은 setState 대용으로 callback 설정도 가능
    _playingController.add(true);
  }

  Future<void> pause() async {
    await _audioPlayer.pause();
    _playingController.add(false);
  }

  Future<void> seek(Duration position) => _audioPlayer.seek(position);
  Future<void> replay() async => _audioPlayer.seek(Duration.zero);
  Future<void> dispose() => _audioPlayer.dispose();

  Future<void> skipForward(Duration duration) async {
    final current = _audioPlayer.position;
    final total = _audioPlayer.duration ?? Duration.zero;
    final newPosition = current + duration;

    await _audioPlayer.seek(newPosition < total ? newPosition : total);
  }

  Future<void> skipBackward(Duration duration) async {
    final current = _audioPlayer.position;
    final newPosition = current - duration;

    if (newPosition > Duration.zero) {
      await _audioPlayer.seek(newPosition);
    } else {
      await _audioPlayer.seek(Duration.zero);
    }
  }

  Stream<Duration> get positionStream => _audioPlayer.positionStream;
  Stream<Duration?> get durationStream => _audioPlayer.durationStream;
  // Stream<bool> get player => _audioPlayer.playingStream;
  Stream<bool> get playingStream => _playingController.stream;

  // TTS 오디오 재생
  Future<void> playAudio(String audioUrl) async {
    try {
      await loadUrl(audioUrl);
      await play();
    } catch (e) {
      print('오디오 재생 실패: $e');
      rethrow;
    }
  }

  // STT 처리 (여기서는 mock 구현, 실제로는 백엔드 API 호출)
  Future<String?> speechToText(String audioPath) async {
    try {
      // 실제 구현에서는 백엔드 STT API 호출
      // 임시로 mock 구현
      print('STT 처리 중: $audioPath');
      
      // 파일이 존재하는지 확인
      final file = File(audioPath);
      if (!await file.exists()) {
        print('오디오 파일이 존재하지 않습니다: $audioPath');
        return null;
      }
      
      // TODO: 실제 STT API 호출 구현
      // final bytes = await file.readAsBytes();
      // final response = await http.post(
      //   Uri.parse('YOUR_STT_API_ENDPOINT'),
      //   headers: {'Content-Type': 'audio/m4a'},
      //   body: bytes,
      // );
      
      // 임시로 고정된 텍스트 반환 (테스트용)
      await Future.delayed(Duration(seconds: 1)); // STT 처리 시뮬레이션
      return '음성 입력이 성공적으로 변환되었습니다.';
      
    } catch (e) {
      print('STT 처리 실패: $e');
      return null;
    }
  }
}
