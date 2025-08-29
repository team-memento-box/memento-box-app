
import 'package:just_audio/just_audio.dart';
import 'dart:async';

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
}
