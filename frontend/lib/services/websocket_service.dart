import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:flutter_dotenv/flutter_dotenv.dart';
import 'package:web_socket_channel/web_socket_channel.dart';
import 'package:web_socket_channel/io.dart';

class WebSocketService {
  WebSocketChannel? _channel;
  String? _conversationId;
  Function(Map<String, dynamic>)? onMessage;
  Function(String)? onError;
  Function()? onDisconnect;
  Function(String)? onProcessing;

  bool get isConnected => _channel != null;

  Future<void> connect(String conversationId) async {
    try {
      _conversationId = conversationId;
      
      // 여러 환경 변수를 확인하여 URL 결정
      String? baseUrl = dotenv.env['BASE_URL'];


      
      print('🔍 Environment variables check:');
      print('  FASTAPI_URL: ${dotenv.env['FASTAPI_URL']}');
      print('  BASE_URL: ${dotenv.env['BASE_URL']}');
      print('  AI_API_BASE_URL: ${dotenv.env['AI_API_BASE_URL']}');
      print('  Selected baseUrl: $baseUrl');
      
      if (baseUrl == null) {
        final errorMsg = '서버 URL이 설정되지 않았습니다. .env 파일을 확인해주세요.';
        print('❌ $errorMsg');
        onError?.call(errorMsg);
        return;
      }
      
      final wsUrl = baseUrl.replaceFirst('http', 'ws');
      final fullUrl = '$wsUrl/ws/chat/$conversationId';
      
      print('🌐 WebSocket 연결 시도: $fullUrl');
      print('  Conversation ID: $conversationId');
      
      _channel = IOWebSocketChannel.connect(
        Uri.parse(fullUrl),
        pingInterval: const Duration(seconds: 10), // Keep-alive ping
      );
      
      _channel!.stream.listen(
        (data) {
          try {
            print('📨 WebSocket 메시지 수신: $data');
            final message = jsonDecode(data);
            final messageType = message['type'] as String?;
            
            print('📋 메시지 타입: $messageType');
            
            switch (messageType) {
              case 'processing':
                final processingMsg = message['message'] ?? '처리 중...';
                print('⏳ 처리 중: $processingMsg');
                onProcessing?.call(processingMsg);
                break;
              case 'error':
                final errorMsg = message['message'] ?? '알 수 없는 오류가 발생했습니다.';
                print('❌ 서버 에러: $errorMsg');
                onError?.call(errorMsg);
                break;
              case 'auth_success':
                print('✅ 인증 성공: ${message['message']}');
                print('  세션 ID: ${message['session_id']}');
                print('  사용자 ID: ${message['user_id']}');
                break;
              case 'response':
                print('💬 AI 응답 수신');
                onMessage?.call(message);
                break;
              default:
                print('📤 기본 메시지 처리');
                onMessage?.call(message);
                break;
            }
          } catch (e) {
            final parseError = '메시지 파싱 오류: $e';
            print('❌ $parseError');
            print('📝 원본 데이터: $data');
            onError?.call(parseError);
          }
        },
        onError: (error) {
          final streamError = 'WebSocket 스트림 오류: $error';
          print('❌ $streamError');
          onError?.call(streamError);
        },
        onDone: () {
          print('🔌 WebSocket 연결이 종료되었습니다.');
          onDisconnect?.call();
          _channel = null;
        },
      );
      
      print('✅ WebSocket 연결 설정 완료: $conversationId');
    } catch (e) {
      final connectError = 'WebSocket 연결 실패: $e';
      print('❌ $connectError');
      onError?.call(connectError);
    }
  }

  void sendMessage({
    required String userId,
    required String message,
    Map<String, dynamic>? photoContext,
    String? jwtToken,
  }) {
    if (_channel == null) {
      final errorMsg = 'WebSocket이 연결되지 않았습니다.';
      print('❌ $errorMsg');
      onError?.call(errorMsg);
      return;
    }

    final messageData = {
      'user_id': userId,
      'message': message,
      'photo_context': photoContext ?? {},
    };
    
    // JWT 토큰이 있으면 추가
    if (jwtToken != null) {
      messageData['jwt_token'] = jwtToken;
    }

    final jsonData = jsonEncode(messageData);
    print('📤 WebSocket 메시지 전송:');
    print('  User ID: $userId');
    print('  Message: $message');
    print('  Photo Context: ${photoContext ?? {}}');
    print('  JWT Token: ${jwtToken != null ? 'Present' : 'None'}');
    print('  JSON Data: $jsonData');

    try {
      _channel!.sink.add(jsonData);
      print('✅ 메시지 전송 성공');
    } catch (e) {
      final sendError = '메시지 전송 실패: $e';
      print('❌ $sendError');
      onError?.call(sendError);
    }
  }

  Future<void> disconnect() async {
    await _channel?.sink.close();
    _channel = null;
  }
}