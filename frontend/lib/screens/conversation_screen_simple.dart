import 'package:flutter/material.dart';
import 'package:uuid/uuid.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';
import 'dart:typed_data';
import 'dart:io';
import 'package:record/record.dart';
import 'package:permission_handler/permission_handler.dart';
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
  final TextEditingController _messageController = TextEditingController();
  final List<Map<String, dynamic>> _messages = [];
  final AudioService _audioService = AudioService();
  final AudioRecorder _audioRecorder = AudioRecorder();
  
  String _conversationId = '';
  String _sessionId = '';
  String _userId = 'temp_user';
  bool _isConnecting = false;
  bool _isProcessing = false;
  String _processingMessage = '';
  Photo? _currentPhoto;
  final ScrollController _scrollController = ScrollController();
  
  // 음성 녹음 관련 상태
  bool _isRecording = false;
  bool _hasRecordPermission = false;

  @override
  void initState() {
    super.initState();
    _checkRecordPermission();
    _initializeConversation();
  }

  @override
  void dispose() {
    _webSocketService.disconnect();
    _messageController.dispose();
    _scrollController.dispose();
    _audioService.dispose();
    _audioRecorder.dispose();
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
      
      // 기존 활성 세션 조회
      print('🔍 기존 세션 조회 시작...');
      await _findActiveSession();
      print('🔍 세션 조회 완료: $_sessionId');
      
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
      
      // 자동 메시지 전송 제거 - 사용자가 직접 대화를 시작하도록 함
      print('✅ WebSocket 연결 완료, 사용자 입력 대기 중');
      
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
      
      // 사진의 user_id 가져와서 설정
      if (response['user_id'] != null) {
        _userId = response['user_id'];
        print('🔑 사용자 ID 설정: $_userId');
      }
    } catch (e) {
      print('사진 데이터 로드 실패: $e');
    }
  }
  
  Future<void> _findActiveSession() async {
    try {
      // 현재 사진과 사용자에 해당하는 활성 세션 조회
      final response = await SupabaseService.client
          .from('sessions')
          .select('id')
          .eq('user_id', _userId)
          .contains('selected_photos', [widget.photoId])
          .eq('status', 'active')
          .order('created_at', ascending: false)
          .limit(1)
          .maybeSingle();
      
      if (response != null) {
        _sessionId = response['id'];
        print('✅ 기존 활성 세션 발견: $_sessionId');
      } else {
        print('❌ 기존 활성 세션 없음, 새 세션 생성 필요');
        // 여기서는 일단 기존 로직 유지 (백엔드에서 세션 생성한다고 가정)
        _sessionId = 'backend-generated-session-id';
      }
    } catch (e) {
      print('❌ 세션 조회 실패: $e');
      _sessionId = 'fallback-session-id';
    }
  }

  Future<void> _checkRecordPermission() async {
    final status = await Permission.microphone.status;
    if (status != PermissionStatus.granted) {
      final result = await Permission.microphone.request();
      setState(() {
        _hasRecordPermission = result == PermissionStatus.granted;
      });
    } else {
      setState(() {
        _hasRecordPermission = true;
      });
    }
  }

  Future<void> _startRecording() async {
    if (!_hasRecordPermission) {
      await _checkRecordPermission();
      if (!_hasRecordPermission) return;
    }

    try {
      await _audioRecorder.start(const RecordConfig(
        encoder: AudioEncoder.wav,
        bitRate: 16000,
        sampleRate: 16000,
      ));

      setState(() {
        _isRecording = true;
      });

      print('🎤 녹음 시작됨');
    } catch (e) {
      print('❌ 녹음 시작 실패: $e');
    }
  }

  Future<void> _stopRecording() async {
    try {
      final audioPath = await _audioRecorder.stop();
      setState(() {
        _isRecording = false;
      });

      if (audioPath != null) {
        print('🎤 녹음 완료: $audioPath');
        await _sendAudioMessage(audioPath);
      }
    } catch (e) {
      print('❌ 녹음 중지 실패: $e');
      setState(() {
        _isRecording = false;
      });
    }
  }

  Future<void> _sendAudioMessage(String audioPath) async {
    try {
      // 오디오 파일을 base64로 변환
      final file = File(audioPath);
      final bytes = await file.readAsBytes();
      final base64Audio = base64Encode(bytes);
      
      // 사용자 메시지에 "음성 메시지" 표시 추가
      setState(() {
        _messages.add({
          'type': 'user',
          'text': '🎤 음성 메시지',
          'timestamp': DateTime.now(),
        });
      });

      _scrollToBottom();

      // WebSocket으로 오디오 데이터 전송
      final photoContext = {
        'photo_id': widget.photoId,
        'photo_url': widget.photoUrl,
        'description': _currentPhoto?.description ?? '',
      };

      _webSocketService.sendAudioMessage(
        userId: _userId,
        audioBase64: base64Audio,
        photoContext: photoContext,
        jwtToken: widget.jwtToken,
      );

      print('🎵 오디오 메시지 전송 완료');
      
      // 임시 파일 삭제
      try {
        await file.delete();
      } catch (e) {
        print('임시 파일 삭제 실패: $e');
      }
    } catch (e) {
      print('❌ 오디오 메시지 전송 실패: $e');
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
        print('💬 AI 응답 텍스트: $responseText');
        
        _messages.add({
          'type': 'ai',
          'text': responseText,
          'timestamp': DateTime.now(),
        });
        
        print('✅ AI 메시지 UI에 추가됨: ${_messages.length}개 메시지');
        
        // AI 응답이 들어올 때 자동 스크롤
        _scrollToBottom();
        
        // AI 응답을 TTS로 자동 재생
        _audioService.speak(responseText);
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

  void _sendMessage([String? predefinedMessage]) {
    final message = predefinedMessage ?? _messageController.text.trim();
    
    print('📝 메시지 전송 요청:');
    print('  메시지: "$message"');
    print('  미리 정의된 메시지: ${predefinedMessage != null}');
    
    if (message.isEmpty) {
      print('❌ 빈 메시지 - 전송 중단');
      return;
    }

    // 사용자 메시지 추가
    setState(() {
      _messages.add({
        'type': 'user',
        'text': message,
        'timestamp': DateTime.now(),
      });
    });

    print('💬 UI에 사용자 메시지 추가됨: ${_messages.length}개 메시지');
    
    // 사용자 메시지가 들어올 때 자동 스크롤
    _scrollToBottom();

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
      message: message,
      photoContext: photoContext,
      jwtToken: widget.jwtToken,
    );

    if (predefinedMessage == null) {
      _messageController.clear();
      print('✅ 입력 필드 클리어됨');
    }
  }
  
  Future<void> _handleBackPressed() async {
    try {
      print('🔙 뒤로가기 처리 시작');
      
      // 백그라운드 작업 시작 
      // TODO: BASE_URL 환경변수 사용하도록 개선 필요
      final response = await http.post(
        Uri.parse('http://3.38.196.22:8000/api/openai/story/process-background'), // EC2 서버 IP
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer ${widget.jwtToken}',
        },
        body: jsonEncode({
          'session_id': _sessionId,
          'fish_speech_endpoint': 'http://gpu-server:8000/tts/generate',
        }),
      );
      
      if (response.statusCode == 200) {
        final result = jsonDecode(response.body);
        print('✅ 백그라운드 작업 시작됨: ${result['job_id']}');
        
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text('스토리 생성이 백그라운드에서 시작되었습니다. 작업 ID: ${result['job_id']}'),
              backgroundColor: Colors.green,
            ),
          );
        }
      } else {
        print('❌ 백그라운드 작업 시작 실패: ${response.statusCode}');
        print('응답: ${response.body}');
      }
    } catch (e) {
      print('❌ 뒤로가기 처리 실패: $e');
    }
    
    // WebSocket 연결 종료
    _webSocketService.disconnect();
    
    // 화면 종료
    if (mounted) {
      Navigator.of(context).pop();
    }
  }
  
  /// 자동 스크롤 함수
  void _scrollToBottom() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_scrollController.hasClients && mounted) {
        _scrollController.animateTo(
          _scrollController.position.maxScrollExtent,
          duration: const Duration(milliseconds: 300),
          curve: Curves.easeOut,
        );
      }
    });
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

    return WillPopScope(
      onWillPop: () async {
        await _handleBackPressed();
        return false; // Navigator.pop()을 _handleBackPressed에서 처리
      },
      child: Scaffold(
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
          IconButton(
            icon: const Icon(Icons.close),
            onPressed: _handleBackPressed,
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
            child: _messages.isEmpty && !_isProcessing
                ? Container(
                    width: double.infinity,
                    padding: const EdgeInsets.all(20),
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Icon(
                          Icons.chat_bubble_outline,
                          size: 64,
                          color: Colors.grey[400],
                        ),
                        const SizedBox(height: 24),
                        const Text(
                          '메시지를 입력하여\n대화를 시작해보세요.',
                          textAlign: TextAlign.center,
                          style: TextStyle(
                            fontSize: 18,
                            color: Color(0xFF666666),
                            fontFamily: 'Pretendard',
                            fontWeight: FontWeight.w600,
                            height: 1.5,
                          ),
                        ),
                      ],
                    ),
                  )
                : ListView.builder(
                    controller: _scrollController,
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
                    onSubmitted: (_) => _sendMessage(),
                  ),
                ),
                const SizedBox(width: 10),
                // 마이크 버튼
                GestureDetector(
                  onTapDown: (_) => _startRecording(),
                  onTapUp: (_) => _stopRecording(),
                  onTapCancel: () => _stopRecording(),
                  child: Container(
                    width: 48,
                    height: 48,
                    decoration: BoxDecoration(
                      color: _isRecording ? Colors.red : Colors.blue,
                      borderRadius: BorderRadius.circular(24),
                    ),
                    child: Icon(
                      _isRecording ? Icons.stop : Icons.mic,
                      color: Colors.white,
                      size: 24,
                    ),
                  ),
                ),
                const SizedBox(width: 10),
                ElevatedButton(
                  onPressed: _isProcessing ? null : _sendMessage,
                  child: _isProcessing 
                      ? const SizedBox(
                          width: 16,
                          height: 16,
                          child: CircularProgressIndicator(strokeWidth: 2),
                        )
                      : const Text('전송'),
                ),
              ],
            ),
          ),
        ],
      ),
    ),
    );
  }
}