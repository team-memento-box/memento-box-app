import 'package:flutter/material.dart';
import 'package:just_audio/just_audio.dart';
import '../utils/audio_service.dart'; // 분리된 서비스 import

class AudioPlayerWidget extends StatefulWidget {
  final String audioPath;
  final AudioService audioService;

  const AudioPlayerWidget({
    Key? key,
    required this.audioPath,
    required this.audioService,
  }) : super(key: key);

  @override
  State<AudioPlayerWidget> createState() => _AudioPlayerWidgetState();
}

class _AudioPlayerWidgetState extends State<AudioPlayerWidget> {
  // final AudioService widget.audioService = AudioService();
  Duration _position = Duration.zero;
  Duration _duration = Duration.zero;
  bool _isPlaying = false;
  bool _isPressed = false;

  @override
  void initState() {
    super.initState();

    // 현재 상태 가져와 초기 UI 동기화
    _isPlaying = widget.audioService.player.playing;
    _isPressed = widget.audioService.player.playing;

    widget.audioService.onCompleted = () {
      setState(() {
        _isPlaying = false;
        _isPressed = false; // 아이콘을 play로 바꿈
        _position = Duration.zero;
      });
    };

    widget.audioService.positionStream.listen((pos) {
      setState(() => _position = pos);
    });
    widget.audioService.durationStream.listen((dur) {
      if (dur != null) setState(() => _duration = dur);
    });
    // widget.audioService.playingStream.listen((playing) {
    //   setState(() => _isPlaying = playing);
    // });
    // 강제로 초기 duration 설정
    final dur = widget.audioService.getDuration(); // <- 새 메서드 필요
    if (dur != null) {
      setState(() => _duration = dur);
    }
  }

  // @override
  // void dispose() {
  //   widget.audioService.dispose();
  //   super.dispose();
  // }

  @override
  Widget build(BuildContext context) {
    final double progress = _duration.inMilliseconds > 0
        ? _position.inMilliseconds / _duration.inMilliseconds
        : 0.0;

    return GestureDetector(
      onTapDown: (_) => setState(() => _isPressed = true),
      onTapUp: (_) => setState(() => _isPressed = false),
      onTapCancel: () => setState(() => _isPressed = false),
      // onTap: _togglePlay,
      child: Column(
        children: [
          SliderTheme(
            data: SliderTheme.of(context).copyWith(
              activeTrackColor: const Color(0xFF00C8B8),
              inactiveTrackColor: Color(0xFF999999),
              overlayColor: const Color.fromARGB(60, 0, 200, 183),
              thumbColor: Color(0xFF00C8B8),
            ),
            child: Slider(
              value: progress.clamp(0.0, 1.0),
              onChanged: (value) {
                setState(() {
                  // 슬라이드만 따라감 (사용자 조작 도중)
                  _position = Duration(
                    milliseconds: (_duration.inMilliseconds * value).toInt(),
                  );
                });
              },
              onChangeEnd: (value) async {
                // 슬라이더 조작 완료 후 실제 오디오 위치 변경
                final newPosition = Duration(
                  milliseconds: (_duration.inMilliseconds * value).toInt(),
                );
                await widget.audioService.seek(newPosition);

                // // 재생이 끝났던 상태일 경우 재시작
                // if (!_isPlaying || _position >= _duration) {
                //   await widget.audioService.play();
                // }
              },
            ),
          ),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(_format(_position), style: TextStyle(fontSize: 12)),
              Text(_format(_duration), style: TextStyle(fontSize: 12)),
            ],
          ),
          // const SizedBox(height: 8),
          Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              IconButton(
                icon: Image.asset(
                  'assets/icons/Rewind.png',
                  color: Color(0xFF333333),
                ),
                color: _isPressed ? Color(0xFF333333) : Color(0xFF00C8B8),
                onPressed: () =>
                    widget.audioService.skipBackward(Duration(seconds: 10)),
              ),
              const SizedBox(width: 10),
              IconButton(
                icon: Image.asset(
                  _isPlaying
                      ? 'assets/icons/Pause.png'
                      : 'assets/icons/Play.png',
                  color: Color(0xFF333333),
                ),
                color: _isPressed ? Color(0xFF333333) : Color(0xFF00C8B8),
                // onPressed: () {
                //   _isPlaying
                //       ? widget.audioService.pause()
                //       : widget.audioService.play();
                // },
                onPressed: () async {
                  if (!_isPlaying) {
                    try {
                      await widget.audioService.loadAudio(widget.audioPath);
                      widget.audioService.play();
                      setState(() => _isPlaying = true);
                    } catch (e) {
                      print('오디오 로드 실패: $e');
                      ScaffoldMessenger.of(context).showSnackBar(
                        const SnackBar(
                          content: Text('오디오 파일을 불러올 수 없습니다'),
                          backgroundColor: Colors.red,
                        ),
                      );
                    }
                  } else {
                    widget.audioService.pause();
                    setState(() => _isPlaying = false);
                  }
                },
              ),
              const SizedBox(width: 10),
              IconButton(
                icon: Image.asset(
                  'assets/icons/Unwind.png',
                  color: Color(0xFF333333),
                ),
                color: _isPressed ? Color(0xFF333333) : Color(0xFF00C8B8),
                onPressed: () =>
                    widget.audioService.skipForward(Duration(seconds: 10)),
              ),
            ],
          ),
        ],
      ),
    );
    // Column(
    //   children: [
    //     LinearProgressIndicator(value: progress),
    //     Row(
    //       mainAxisAlignment: MainAxisAlignment.spaceBetween,
    //       children: [
    //         Text(_format(_position)),
    //         IconButton(
    //           icon: Icon(_isPlaying ? Icons.pause : Icons.play_arrow),
    //           onPressed: () {
    //             _isPlaying ? widget.audioService.pause() : widget.audioService.play();
    //           },
    //         ),
    //         Text(_format(_duration)),
    //       ],
    //     ),
    //   ],
    // );
  }

  String _format(Duration d) {
    final m = d.inMinutes.remainder(60).toString().padLeft(2, '0');
    final s = d.inSeconds.remainder(60).toString().padLeft(2, '0');
    return '$m:$s';
  }
}



  // Future<void> _togglePlay() async {
  //   if (!isAudioLoaded) {
  //     ScaffoldMessenger.of(
  //       context,
  //     ).showSnackBar(SnackBar(content: Text('오디오 파일이 준비되지 않았습니다')));
  //     return;
  //   }

  //   try {
  //     if (isPlaying) {
  //       await audioPlayer.pause();
  //     } else {
  //       await audioPlayer.play();
  //     }
  //   } catch (e) {
  //     if (mounted) {
  //       ScaffoldMessenger.of(context).showSnackBar(
  //         SnackBar(
  //           content: Text('재생 실패: 파일 형식을 확인해주세요'),
  //           backgroundColor: Colors.red,
  //         ),
  //       );
  //     }
  //     setState(() {
  //       isPlaying = false;
  //       isAudioLoaded = false;
  //     });
  //   }
  // }

// Widget _AudioProgress() {
//     return Column(
//       children: [
//         GestureDetector(
//           onTapDown: isAudioLoaded
//               ? (details) async {
//                   final box = context.findRenderObject() as RenderBox;
//                   final pos = box.globalToLocal(details.globalPosition);
//                   final newProgress = (pos.dx / box.size.width).clamp(0.0, 1.0);
//                   await _seekTo(newProgress);
//                 }
//               : null,
//           child: Container(
//             width: double.infinity,
//             height: 6,
//             decoration: BoxDecoration(
//               color: AppColors.progressBg,
//               borderRadius: BorderRadius.circular(3),
//             ),
//             child: FractionallySizedBox(
//               widthFactor: progress,
//               alignment: Alignment.centerLeft,
//               child: Container(
//                 decoration: BoxDecoration(
//                   color: isAudioLoaded
//                       ? AppColors.primary
//                       : AppColors.progressBg.withOpacity(0.5),
//                   borderRadius: BorderRadius.circular(3),
//                 ),
//               ),
//             ),
//           ),
//         ),
//         SizedBox(height: 8),
//         Text(
//           isAudioLoaded
//               ? '${_formatTime(currentPosition)} / ${_formatTime(totalDuration)}'
//               : '오디오 파일을 찾을 수 없습니다',
//           style: TextStyle(
//             color: isAudioLoaded
//                 ? AppColors.timeText
//                 : AppColors.timeText.withOpacity(0.5),
//             fontSize: 12,
//             fontFamily: 'Pretendard',
//             fontWeight: FontWeight.w500,
//           ),
//         ),
//       ],
//     );
//   }

//   Widget _PlayButton() {
//     return GestureDetector(
//       onTap: isAudioLoaded ? _togglePlay : null,
//       child: Container(
//         width: 50,
//         height: 50,
//         decoration: BoxDecoration(
//           color: isAudioLoaded
//               ? AppColors.primary
//               : AppColors.primary.withOpacity(0.3),
//           shape: BoxShape.circle,
//           boxShadow: isAudioLoaded
//               ? [
//                   BoxShadow(
//                     color: Color(0x33555555),
//                     blurRadius: 5,
//                     offset: Offset(0, 2),
//                   ),
//                 ]
//               : [],
//         ),
//         child: Icon(
//           isAudioLoaded
//               ? (isPlaying ? Icons.pause : Icons.play_arrow)
//               : Icons.music_off,
//           color: Colors.white,
//           size: 28,
//         ),
//       ),
//     );
//   }