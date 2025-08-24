import '../core/supabase_service.dart';
import '../models/report.dart';
import '../models/question.dart';
import '../models/photo.dart';

class SessionApi {
  /// 새로운 대화 세션 시작
  static Future<SessionData> startSession({
    required String userId,
    required List<String> selectedPhotoIds,
    String sessionType = 'reminiscence',
  }) async {
    try {
      print('🎯 Starting new session for user: $userId');
      print('📸 Selected photos: ${selectedPhotoIds.length} photos');
      
      final sessionData = {
        'user_id': userId,
        'session_type': sessionType,
        'status': 'active',
        'selected_photos': selectedPhotoIds,
        'total_duration_seconds': 0,
        'cist_score': null,
        'cist_completed_items': 0,
        'started_at': DateTime.now().toIso8601String(),
        'notes': null,
      };

      final response = await SupabaseService.client
          .from('sessions')
          .insert(sessionData)
          .select()
          .single();

      print('✅ Session created: ${response['id']}');
      
      return SessionData.fromJson(response);
    } catch (e) {
      print('❌ Error starting session: $e');
      throw Exception('세션 시작에 실패했습니다: $e');
    }
  }

  /// 대화 추가
  static Future<ConversationData> addConversation({
    required String sessionId,
    required String userId,
    required String questionText,
    required String questionType,
    String? photoId,
    String? cistCategory,
    bool isCistItem = false,
  }) async {
    try {
      print('💬 Adding conversation to session: $sessionId');
      
      // 현재 대화 순서 조회
      final existingCount = await SupabaseService.client
          .from('conversations')
          .select('id')
          .eq('session_id', sessionId)
          .count();

      final conversationData = {
        'session_id': sessionId,
        'user_id': userId,
        'photo_id': photoId,
        'conversation_order': existingCount,
        'question_text': questionText,
        'question_type': questionType,
        'cist_category': cistCategory,
        'user_response_text': null,
        'user_response_audio_url': null,
        'response_duration_seconds': null,
        'ai_analysis': null,
        'cist_score': null,
        'is_cist_item': isCistItem,
      };

      final response = await SupabaseService.client
          .from('conversations')
          .insert(conversationData)
          .select('''
            *,
            photos(*)
          ''')
          .single();

      print('✅ Conversation added: ${response['id']}');
      
      return ConversationData.fromJson(response);
    } catch (e) {
      print('❌ Error adding conversation: $e');
      throw Exception('대화 추가에 실패했습니다: $e');
    }
  }

  /// 사용자 응답 업데이트
  static Future<ConversationData> updateUserResponse({
    required String conversationId,
    required String userId,
    String? responseText,
    String? audioUrl,
    int? durationSeconds,
    Map<String, dynamic>? aiAnalysis,
    int? cistScore,
  }) async {
    try {
      print('📝 Updating user response for conversation: $conversationId');
      
      final updateData = <String, dynamic>{
        'updated_at': DateTime.now().toIso8601String(),
      };

      if (responseText != null) updateData['user_response_text'] = responseText;
      if (audioUrl != null) updateData['user_response_audio_url'] = audioUrl;
      if (durationSeconds != null) updateData['response_duration_seconds'] = durationSeconds;
      if (aiAnalysis != null) updateData['ai_analysis'] = aiAnalysis;
      if (cistScore != null) updateData['cist_score'] = cistScore;

      final response = await SupabaseService.client
          .from('conversations')
          .update(updateData)
          .eq('id', conversationId)
          .eq('user_id', userId)
          .select('''
            *,
            photos(*)
          ''')
          .single();

      print('✅ User response updated');
      
      return ConversationData.fromJson(response);
    } catch (e) {
      print('❌ Error updating user response: $e');
      throw Exception('사용자 응답 업데이트에 실패했습니다: $e');
    }
  }

  /// 세션 완료
  static Future<SessionData> completeSession({
    required String sessionId,
    required String userId,
    int? totalCistScore,
    String? notes,
  }) async {
    try {
      print('✅ Completing session: $sessionId');
      
      // 총 대화 시간 계산
      final conversations = await SupabaseService.client
          .from('conversations')
          .select('response_duration_seconds')
          .eq('session_id', sessionId);

      int totalDuration = 0;
      for (final conv in conversations) {
        totalDuration += (conv['response_duration_seconds'] as int?) ?? 0;
      }

      // CIST 완료 항목 수 계산
      final cistCount = await SupabaseService.client
          .from('conversations')
          .select('id')
          .eq('session_id', sessionId)
          .eq('is_cist_item', true)
          .count();

      final updateData = {
        'status': 'completed',
        'total_duration_seconds': totalDuration,
        'cist_score': totalCistScore,
        'cist_completed_items': cistCount,
        'completed_at': DateTime.now().toIso8601String(),
        'notes': notes,
        'updated_at': DateTime.now().toIso8601String(),
      };

      final response = await SupabaseService.client
          .from('sessions')
          .update(updateData)
          .eq('id', sessionId)
          .eq('user_id', userId)
          .select()
          .single();

      print('✅ Session completed successfully');
      
      return SessionData.fromJson(response);
    } catch (e) {
      print('❌ Error completing session: $e');
      throw Exception('세션 완료 처리에 실패했습니다: $e');
    }
  }

  /// 세션 조회
  static Future<SessionData?> getSession(String sessionId, String userId) async {
    try {
      final response = await SupabaseService.client
          .from('sessions')
          .select('''
            *,
            conversations(
              *,
              photos(*)
            )
          ''')
          .eq('id', sessionId)
          .eq('user_id', userId)
          .maybeSingle();

      if (response == null) return null;
      
      return SessionData.fromJson(response);
    } catch (e) {
      print('❌ Error getting session: $e');
      throw Exception('세션 조회에 실패했습니다: $e');
    }
  }

  /// 사용자의 모든 세션 조회
  static Future<List<SessionData>> getUserSessions(
    String userId, {
    String? status,
    int? limit,
    int? offset,
  }) async {
    try {
      print('📋 Fetching sessions for user: $userId');
      
      var query = SupabaseService.client
          .from('sessions')
          .select('''
            *,
            conversations(count)
          ''')
          .eq('user_id', userId);

      if (status != null) {
        query = query.eq('status', status);
      }

      if (limit != null) {
        query = query.limit(limit);
      }

      if (offset != null) {
        query = query.range(offset, offset + (limit ?? 20) - 1);
      }

      query = query.order('started_at', ascending: false);

      final response = await query;
      
      print('✅ Found ${response.length} sessions');
      
      return response.map((json) => SessionData.fromJson(json)).toList();
    } catch (e) {
      print('❌ Error fetching sessions: $e');
      throw Exception('세션 목록 조회에 실패했습니다: $e');
    }
  }

  /// CIST 응답 기록
  static Future<void> recordCistResponse({
    required String sessionId,
    required String userId,
    required String conversationId,
    required String cistCategory,
    required String questionText,
    required String expectedResponse,
    String? userResponse,
    bool? isCorrect,
    double? partialScore,
    int? responseTimeSeconds,
    int difficultyLevel = 1,
    String? notes,
  }) async {
    try {
      print('📊 Recording CIST response for session: $sessionId');
      
      final cistData = {
        'session_id': sessionId,
        'user_id': userId,
        'conversation_id': conversationId,
        'cist_category': cistCategory,
        'question_text': questionText,
        'expected_response': expectedResponse,
        'user_response': userResponse,
        'is_correct': isCorrect,
        'partial_score': partialScore,
        'response_time_seconds': responseTimeSeconds,
        'difficulty_level': difficultyLevel,
        'notes': notes,
      };

      await SupabaseService.client
          .from('cist_responses')
          .insert(cistData);

      print('✅ CIST response recorded');
    } catch (e) {
      print('❌ Error recording CIST response: $e');
      throw Exception('CIST 응답 기록에 실패했습니다: $e');
    }
  }

  /// 세션의 CIST 점수 계산
  static Future<int> calculateCistScore(String sessionId) async {
    try {
      final responses = await SupabaseService.client
          .from('cist_responses')
          .select('partial_score, is_correct')
          .eq('session_id', sessionId);

      double totalScore = 0;
      for (final response in responses) {
        if (response['is_correct'] == true) {
          totalScore += 1.0;
        } else if (response['partial_score'] != null) {
          totalScore += (response['partial_score'] as double);
        }
      }

      return totalScore.round();
    } catch (e) {
      print('❌ Error calculating CIST score: $e');
      return 0;
    }
  }
}