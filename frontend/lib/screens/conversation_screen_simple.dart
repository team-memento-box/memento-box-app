import 'package:flutter/material.dart';
import 'package:uuid/uuid.dart';
import '../services/websocket_service.dart';
import '../core/supabase_service.dart';
import '../widgets/assistant_bubble.dart';
import '../widgets/user_speech_bubble.dart';
import '../widgets/photo_box.dart';
import '../models/photo.dart';

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
  String _conversationId = '';
  String _userId = 'temp_user';
  bool _isConnecting = false;
  bool _isProcessing = false;
  String _processingMessage = '';
  Photo? _currentPhoto;

  @override
  void initState() {
    super.initState();
    _initializeConversation();
  }

  @override
  void dispose() {
    _webSocketService.disconnect();
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
        print('💬 AI 응답 텍스트: $responseText');
        
        _messages.add({
          'type': 'ai',
          'text': responseText,
          'timestamp': DateTime.now(),
        });
        
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
    );
  }
}