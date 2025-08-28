import 'package:flutter/material.dart';
import 'package:uuid/uuid.dart';
import 'package:record/record.dart';
import 'package:speech_to_text/speech_to_text.dart';
import 'package:path_provider/path_provider.dart';
import 'package:permission_handler/permission_handler.dart';
import 'dart:io';
import '../services/websocket_service.dart';
import '../core/supabase_service.dart';
import '../widgets/assistant_bubble.dart';
import '../widgets/user_speech_bubble.dart';
import '../widgets/photo_box.dart';
import '../models/photo.dart';
import '../utils/audio_service.dart';

class PhotoConversationScreen extends StatefulWidget {
  final String photoId;
  final String photoUrl;
  final String jwtToken;

  const PhotoConversationScreen({
    Key? key,
    required this.photoId,
    required this.photoUrl,
    required this.jwtToken,
  }) : super(key: key);

  @override
  State<PhotoConversationScreen> createState() => _PhotoConversationScreenState();
}

class _PhotoConversationScreenState extends State<PhotoConversationScreen> {
  final WebSocketService _webSocketService = WebSocketService();
  final List<Map<String, dynamic>> _messages = [];
  String _conversationId = '';
  String _userId = 'temp_user';
  bool _isConnecting = false;
  bool _isProcessing = false;
  String _processingMessage = '';
  Photo? _currentPhoto;
  
  // TTS/STT 관련 변수
  late AudioService _audioService;
  late AudioRecorder _audioRecorder;
  late SpeechToText _speechToText;
  bool _isRecording = false;
  bool _isListening = false;
  String? _recordingPath;
  bool _isTTSPlaying = false;
  String _currentWords = '';
  final TextEditingController _messageController = TextEditingController();

  @override
  void initState() {
    super.initState();
    _audioService = AudioService();
    _audioRecorder = AudioRecorder();
    _speechToText = SpeechToText();
    _initializeSpeech();
    _initializeConversation();
  }

  @override
  void dispose() {
    _webSocketService.disconnect();
    _audioService.dispose();
    _audioRecorder.dispose();
    _messageController.dispose();
    super.dispose();
  }

  Future<void> _initializeConversation() async {
    setState(() {
      _isConnecting = true;
    });

    try {
      print('🚀 대화 초기화 시작');
      
      // 새 대화 ID 생성
      _conversationId = const Uuid().v4();
      print('🆔 대화 ID 생성: $_conversationId');
      
      // 사진 정보 조회
      print('📷 사진 정보 로드 시작...');
      await _loadPhotoData();
      print('📷 사진 정보 로드 완료');
      
      // WebSocket 연결 설정
      print('🔗 WebSocket 콜백 설정');
      _webSocketService.onMessage = _handleMessage;
      _webSocketService.onError = _handleError;
      _webSocketService.onDisconnect = _handleDisconnect;
      _webSocketService.onProcessing = _handleProcessing;
      
      // WebSocket 연결
      print('🌐 WebSocket 연결 시도');
      await _webSocketService.connect(_conversationId);
      print('✅ WebSocket 연결 완료');
      
      // 잠시 대기 후 초기 메시지 전송
      await Future.delayed(const Duration(milliseconds: 1000));
      print('💬 초기 메시지 전송');
      _sendMessage('안녕하세요! 이 사진에 대해 이야기해보세요.');
      
      // 초기 메시지 전송 후 음성 인식 준비 완료
      await Future.delayed(const Duration(milliseconds: 2000));
      // 자동 시작하지 않고 사용자가 직접 마이크 버튼을 누르도록 변경
      
    } catch (e) {
      print('❌ 대화 초기화 실패: $e');
      _handleError('초기화 실패: $e');
    } finally {
      setState(() {
        _isConnecting = false;
      });
      print('🏁 대화 초기화 완료');
    }
  }

  Future<void> _loadPhotoData() async {
    try {
      final response = await SupabaseService.client
          .from('photos')
          .select('*')
          .eq('id', widget.photoId)
          .single();
      
      setState(() {
        _currentPhoto = Photo.fromSupabase(response);
      });
    } catch (e) {
      print('사진 데이터 로드 실패: $e');
    }
  }

  void _handleMessage(Map<String, dynamic> message) {
    print('🎯 메시지 핸들링 시작');
    print('  전체 메시지: $message');
    print('  메시지 타입: ${message['type']}');
    
    setState(() {
      _isProcessing = false;
      _processingMessage = '';
      
      if (message['type'] == 'response' && message['data'] != null) {
        final responseText = message['data']['response_text'] ?? '응답을 받을 수 없습니다.';
        final audioUrl = message['data']['audio_url'];
        print('💬 AI 응답 텍스트: $responseText');
        print('🔊 AI 응답 오디오: $audioUrl');
        
        _messages.add({
          'type': 'ai',
          'text': responseText,
          'timestamp': DateTime.now(),
        });
        
        // TTS 재생
        if (audioUrl != null && audioUrl.isNotEmpty) {
          _playTTS(audioUrl);
        }
        
        print('✅ AI 메시지 UI에 추가됨: ${_messages.length}개 메시지');
      } else {
        print('⚠️ 예상과 다른 메시지 형식:');
        print('  type: ${message['type']}');
        print('  data: ${message['data']}');
      }
    });
  }

  void _handleProcessing(String message) {
    print('⏳ 처리 중 상태 업데이트: $message');
    setState(() {
      _isProcessing = true;
      _processingMessage = message;
    });
  }

  void _handleError(String error) {
    print('❌ WebSocket 에러 핸들링: $error');
    setState(() {
      _isProcessing = false;
      _processingMessage = '';
    });
    
    if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('연결 오류: $error'),
          backgroundColor: Colors.red,
        ),
      );
      print('🔔 에러 스낵바 표시됨');
    }
  }

  void _handleDisconnect() {
    print('🔌 WebSocket 연결 종료 핸들링');
    if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('연결이 종료되었습니다.'),
          backgroundColor: Colors.orange,
        ),
      );
      print('🔔 연결 종료 스낵바 표시됨');
    }
  }

  void _sendMessage(String message) {
    print('📝 메시지 전송 요청:');
    print('  메시지: "$message"');
    
    if (message.trim().isEmpty) {
      print('❌ 빈 메시지 - 전송 중단');
      return;
    }

    // 사용자 메시지 추가
    setState(() {
      _messages.add({
        'type': 'user',
        'text': message.trim(),
        'timestamp': DateTime.now(),
      });
    });

    print('💬 UI에 사용자 메시지 추가됨: ${_messages.length}개 메시지');

    // WebSocket으로 전송
    final photoContext = {
      'photo_id': widget.photoId,
      'photo_url': widget.photoUrl,
      'description': _currentPhoto?.description ?? '',
    };

    print('🔗 WebSocket 전송 준비:');
    print('  User ID: $_userId');
    print('  Photo Context: $photoContext');
    print('  JWT Token: ${widget.jwtToken.isNotEmpty ? 'Present (${widget.jwtToken.length} chars)' : 'Empty'}');

    _webSocketService.sendMessage(
      userId: _userId,
      message: message.trim(),
      photoContext: photoContext,
      jwtToken: widget.jwtToken,
    );
  }

  Future<void> _playTTS(String audioUrl) async {
    if (_isTTSPlaying) return;
    
    try {
      setState(() {
        _isTTSPlaying = true;
      });
      
      print('🔊 TTS 재생 시작: $audioUrl');
      await _audioService.playAudio(audioUrl);
      print('✅ TTS 재생 완료');
    } catch (e) {
      print('❌ TTS 재생 실패: $e');
    } finally {
      setState(() {
        _isTTSPlaying = false;
      });
    }
  }

  Future<void> _startListening() async {
    if (_isListening) return;
    
    try {
      // 마이크 권한 확인
      final status = await Permission.microphone.request();
      if (!status.isGranted) {
        print('❌ 마이크 권한 거부됨');
        return;
      }
      
      // 녹음 파일 경로 설정
      final directory = await getTemporaryDirectory();
      final filePath = '${directory.path}/recording_${DateTime.now().millisecondsSinceEpoch}.m4a';
      
      setState(() {
        _isListening = true;
        _isRecording = true;
        _currentWords = '';
        _recordingPath = filePath;
      });
      
      print('🎤 실시간 음성 인식 + 녹음 시작');
      
      // STT 시작 (백그라운드)
      _speechToText.listen(
        onResult: (result) {
          setState(() {
            _currentWords = result.recognizedWords;
          });
          print('🗣️ 인식된 텍스트: ${result.recognizedWords}');
          print('🗣️ 최종 결과: ${result.finalResult}');
        },
        listenFor: const Duration(seconds: 30), // 더 길게
        pauseFor: const Duration(seconds: 5),   // 더 길게
        partialResults: true,
        localeId: 'ko-KR', // ko_KR → ko-KR 변경
        cancelOnError: false, // 에러 시 자동 취소 방지
        listenMode: ListenMode.dictation, // dictation 모드
      );
      
      // 녹음 시작
      await _audioRecorder.start(
        const RecordConfig(encoder: AudioEncoder.aacLc),
        path: filePath,
      );
      
    } catch (e) {
      print('❌ 음성 인식/녹음 시작 실패: $e');
      setState(() {
        _isListening = false;
        _isRecording = false;
        _currentWords = '';
        _recordingPath = null;
      });
    }
  }

  Future<void> _stopListening() async {
    if (!_isListening) return;
    
    try {
      print('🛑 음성 인식 + 녹음 중지');
      
      // STT 중지
      await _speechToText.stop();
      
      // 녹음 중지
      final recordingPath = await _audioRecorder.stop();
      
      setState(() {
        _isListening = false;
        _isRecording = false;
      });
      
      // 인식된 텍스트가 있으면 메시지 전송
      if (_currentWords.isNotEmpty) {
        print('✅ 인식 완료된 텍스트: $_currentWords');
        _sendMessage(_currentWords);
        
        // 동시에 녹음 파일을 Supabase에 업로드
        if (recordingPath != null && File(recordingPath).existsSync()) {
          _uploadAudioToSupabase(recordingPath, _currentWords);
        }
        
        _currentWords = '';
      }
    } catch (e) {
      print('❌ 음성 인식/녹음 중지 실패: $e');
      setState(() {
        _isListening = false;
        _isRecording = false;
        _currentWords = '';
      });
    }
  }

  Future<void> _uploadAudioToSupabase(String filePath, String transcriptText) async {
    try {
      final file = File(filePath);
      
      // TODO: 실제 값들로 교체 필요
      const familyId = 'temp_family'; 
      const sessionId = 'temp_session';
      
      // Storage 경로: family_id/user_id/session_id/conversation_id.wav
      final storagePath = '$familyId/$_userId/$sessionId/$_conversationId.wav';
      
      print('📤 음성 파일 업로드 시작: $storagePath');
      
      // Supabase Storage 'voice' 버킷에 업로드
      await SupabaseService.client.storage
          .from('voice')
          .upload(storagePath, file);
      
      // 업로드된 파일의 public URL 생성
      final audioUrl = SupabaseService.client.storage
          .from('voice')
          .getPublicUrl(storagePath);
      
      print('✅ 음성 파일 업로드 완료: $audioUrl');
      
      // DB의 conversations 테이블에 user_response_audio_url 저장
      await _saveAudioUrlToDatabase(audioUrl, transcriptText);
      
      // 임시 파일 삭제
      await file.delete();
      print('🗑️ 임시 파일 삭제됨');
      
    } catch (e) {
      print('❌ 음성 파일 업로드 실패: $e');
      // 업로드 실패해도 임시 파일은 삭제
      try {
        await File(filePath).delete();
      } catch (_) {}
    }
  }

  Future<void> _saveAudioUrlToDatabase(String audioUrl, String transcriptText) async {
    try {
      print('💾 DB에 음성 URL 저장 시작');
      
      await SupabaseService.client
          .from('conversations')
          .insert({
            'conversation_id': _conversationId,
            'user_id': _userId,
            'user_message': transcriptText,
            'user_response_audio_url': audioUrl,
            'timestamp': DateTime.now().toIso8601String(),
          });
      
      print('✅ DB에 음성 URL 저장 완료');
    } catch (e) {
      print('❌ DB 저장 실패: $e');
    }
  }

  void _sendTextMessage([String? text]) {
    final message = text ?? _messageController.text;
    if (message.trim().isEmpty) return;
    
    _messageController.clear();
    _sendMessage(message);
  }

  Future<void> _initializeSpeech() async {
    try {
      bool available = await _speechToText.initialize(
        onStatus: (status) {
          print('🎤 Speech status: $status');
          if (status == 'done' || status == 'notListening') {
            setState(() {
              _isListening = false;
            });
            if (_currentWords.isNotEmpty) {
              _sendMessage(_currentWords);
              _currentWords = '';
            }
          }
        },
        onError: (error) {
          print('❌ Speech error: $error');
          setState(() {
            _isListening = false;
            _currentWords = '';
          });
        },
      );
      
      if (!available) {
        print('❌ Speech recognition not available');
      } else {
        print('✅ Speech recognition initialized');
        
        // 지원되는 언어 목록 출력
        final locales = await _speechToText.locales();
        print('🌍 지원되는 언어 목록:');
        for (var locale in locales) {
          print('  - ${locale.localeId}: ${locale.name}');
        }
        
        // 기본 언어 확인
        final systemLocale = await _speechToText.systemLocale();
        print('📱 시스템 기본 언어: ${systemLocale?.localeId}');
      }
    } catch (e) {
      print('❌ Speech initialization error: $e');
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_isConnecting) {
      return Scaffold(
        body: const Center(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              CircularProgressIndicator(),
              SizedBox(height: 20),
              Text('대화를 준비하고 있습니다...'),
            ],
          ),
        ),
      );
    }

    return Scaffold(
      backgroundColor: const Color(0xFFF7F7F7),
      appBar: AppBar(
        title: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text('실시간 사진 대화'),
            Text(
              'WebSocket: ${_webSocketService.isConnected ? '연결됨' : '연결 안됨'} | 메시지: ${_messages.length}개',
              style: const TextStyle(fontSize: 12),
            ),
          ],
        ),
        backgroundColor: _webSocketService.isConnected ? Colors.blue : Colors.orange,
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: () {
              print('🔄 수동 재연결 요청');
              _initializeConversation();
            },
          ),
          IconButton(
            icon: Icon(_isProcessing ? Icons.hourglass_empty : Icons.chat),
            onPressed: null,
          ),
        ],
      ),
      body: Column(
        children: [
          // 사진 표시 영역
          Container(
            padding: const EdgeInsets.all(20),
            child: PhotoBox(
              photoPath: widget.photoUrl,
              isNetwork: true,
            ),
          ),
          // 메시지 목록
          Expanded(
            child: ListView.builder(
              padding: const EdgeInsets.symmetric(horizontal: 20),
              itemCount: _messages.length + (_isProcessing ? 1 : 0),
              itemBuilder: (context, index) {
                if (index == _messages.length && _isProcessing) {
                  // 처리 중 메시지 표시
                  return Padding(
                    padding: const EdgeInsets.symmetric(vertical: 8),
                    child: AssistantBubble(
                      text: _processingMessage,
                      isActive: true,
                    ),
                  );
                }
                
                final message = _messages[index];
                final isAi = message['type'] == 'ai';
                
                return Padding(
                  padding: const EdgeInsets.symmetric(vertical: 8),
                  child: isAi
                      ? AssistantBubble(
                          text: message['text'],
                          isActive: false,
                        )
                      : UserSpeechBubble(
                          text: message['text'],
                          isActive: false,
                        ),
                );
              },
            ),
          ),
          // 실시간 음성 인식 텍스트 표시
          if (_isListening && _currentWords.isNotEmpty)
            Container(
              padding: const EdgeInsets.all(16),
              color: Colors.blue.withOpacity(0.1),
              child: Row(
                children: [
                  const Icon(Icons.mic, color: Colors.blue, size: 16),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      _currentWords,
                      style: const TextStyle(
                        color: Colors.blue,
                        fontStyle: FontStyle.italic,
                      ),
                    ),
                  ),
                ],
              ),
            ),
          // 메시지 입력 영역
          Container(
            padding: const EdgeInsets.all(20),
            decoration: const BoxDecoration(
              color: Colors.white,
              border: Border(
                top: BorderSide(color: Colors.grey, width: 0.5),
              ),
            ),
            child: Row(
              children: [
                Expanded(
                  child: TextField(
                    controller: _messageController,
                    decoration: const InputDecoration(
                      hintText: '메시지를 입력하세요...',
                      border: OutlineInputBorder(),
                    ),
                    onSubmitted: (_) => _sendTextMessage(),
                  ),
                ),
                const SizedBox(width: 10),
                ElevatedButton(
                  onPressed: _isProcessing ? null : _sendTextMessage,
                  child: _isProcessing 
                      ? const SizedBox(
                          width: 16,
                          height: 16,
                          child: CircularProgressIndicator(strokeWidth: 2),
                        )
                      : const Text('전송'),
                ),
                const SizedBox(width: 10),
                GestureDetector(
                  onTapDown: (_) => _startListening(),
                  onTapUp: (_) => _stopListening(),
                  onTapCancel: () => _stopListening(),
                  child: Container(
                    width: 56,
                    height: 56,
                    decoration: BoxDecoration(
                      color: _isListening ? Colors.red : Colors.blue,
                      borderRadius: BorderRadius.circular(28),
                      boxShadow: _isListening ? [
                        BoxShadow(
                          color: Colors.red.withOpacity(0.3),
                          blurRadius: 8,
                          spreadRadius: 2,
                        ),
                      ] : null,
                    ),
                    child: Icon(
                      _isListening ? Icons.mic : Icons.mic_none,
                      color: Colors.white,
                      size: 28,
                    ),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}