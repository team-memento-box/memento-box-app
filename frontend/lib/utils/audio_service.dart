
import 'package:just_audio/just_audio.dart';
import 'package:flutter_tts/flutter_tts.dart';
import 'dart:async';

class AudioService {
  final AudioPlayer _audioPlayer = AudioPlayer();
  final FlutterTts _flutterTts = FlutterTts();
  AudioPlayer get player => _audioPlayer;
  String? _currentAsset;

  // 재생 상태 스트림 컨트롤러 추가
  final StreamController<bool> _playingController =
      StreamController<bool>.broadcast();

  // TTS 상태 관리
  bool _isTtsSpeaking = false;
  bool get isTtsSpeaking => _isTtsSpeaking;

  // 현재 재생 여부를 확인하는 getter
  bool get isPlaying => _audioPlayer.playerState.playing || _isTtsSpeaking;

  // 완료 콜백
  void Function()? onCompleted;

  Duration? getDuration() => _audioPlayer.duration;

  AudioService() {
    _initializeTts();
    
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

  void _initializeTts() async {
    // TTS 설정
    await _flutterTts.setLanguage("ko-KR");
    await _flutterTts.setSpeechRate(0.8); // 말하기 속도
    await _flutterTts.setVolume(1.0);
    await _flutterTts.setPitch(1.0);

    // TTS 콜백 설정
    _flutterTts.setStartHandler(() {
      _isTtsSpeaking = true;
      _playingController.add(true);
    });

    _flutterTts.setCompletionHandler(() {
      _isTtsSpeaking = false;
      _playingController.add(false);
      onCompleted?.call();
    });

    _flutterTts.setErrorHandler((msg) {
      print('TTS Error: $msg');
      _isTtsSpeaking = false;
      _playingController.add(false);
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
  // TTS 메서드들
  Future<void> speak(String text) async {
    if (text.trim().isEmpty) return;
    
    try {
      // 기존 재생 중인 오디오 일시정지
      if (_audioPlayer.playerState.playing) {
        await _audioPlayer.pause();
      }
      
      await _flutterTts.speak(text);
    } catch (e) {
      print('TTS speak error: $e');
      _isTtsSpeaking = false;
      _playingController.add(false);
    }
  }

  Future<void> stopTts() async {
    await _flutterTts.stop();
    _isTtsSpeaking = false;
    _playingController.add(false);
  }

  Future<void> pauseTts() async {
    await _flutterTts.pause();
  }

  Future<void> dispose() async {
    await _flutterTts.stop();
    await _audioPlayer.dispose();
  }

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
}
