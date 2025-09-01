import '../core/supabase_service.dart';
import '../models/report.dart';

class ReportApi {
  /// 가족 구성원의 모든 세션 리포트 조회
  static Future<List<Report>> fetchReports(String accessToken) async {
    try {
      // accessToken에서 현재 사용자 정보 추출
      final currentUser = SupabaseService.client.auth.currentUser;
      if (currentUser == null) {
        throw Exception('사용자가 인증되지 않았습니다.');
      }
      final currentUserId = currentUser.id;
      
      print('🔍 Fetching family reports for guardian: $currentUserId');
      
      // 1. 현재 사용자의 가족 ID 조회
      final familyMember = await SupabaseService.client
          .from('family_members')
          .select('family_id')
          .eq('user_id', currentUserId)
          .maybeSingle();
      
      if (familyMember == null) {
        print('❌ Family member info not found for user: $currentUserId');
        return [];
      }
      
      final familyId = familyMember['family_id'];
      print('🔍 Family ID: $familyId');
      
      // 2. 가족 구성원들의 user_id 목록 조회
      final familyMembers = await SupabaseService.client
          .from('family_members')
          .select('user_id')
          .eq('family_id', familyId);
      
      final memberUserIds = familyMembers.map((m) => m['user_id'] as String).toList();
      print('🔍 Family member user IDs: $memberUserIds');
      
      if (memberUserIds.isEmpty) {
        return [];
      }
      
      // 3. 가족 구성원들의 세션 리포트 조회 (사용자 정보 포함)
      final response = await SupabaseService.client
          .from('session_reports')
          .select('''
            id,
            session_id,
            user_id,
            total_cist_score,
            max_possible_score,
            cognitive_status,
            category_scores,
            insights,
            recommendations,
            report_generated_at,
            is_shared,
            shared_at,
            created_at,
            users!inner(
              id,
              full_name,
              birth_date
            ),
            sessions!inner(
              id,
              status,
              selected_photos,
              total_duration_seconds,
              cist_score,
              started_at,
              completed_at,
              notes
            )
          ''')
          .inFilter('user_id', memberUserIds)
          .order('created_at', ascending: false);

      print('✅ Found ${response.length} reports');
      
      return response.map((json) => Report.fromSupabase(json)).toList();
    } catch (e) {
      print('❌ Error fetching reports: $e');
      throw Exception('리포트 목록을 불러오지 못했습니다: $e');
    }
  }

  /// 특정 리포트 상세 조회
  static Future<Report> fetchReportDetail(String userId, String reportId) async {
    try {
      print('🔍 Fetching report detail: $reportId for user: $userId');
      
      final response = await SupabaseService.client
          .from('session_reports')
          .select('''
            id,
            session_id,
            user_id,
            total_cist_score,
            max_possible_score,
            cognitive_status,
            category_scores,
            insights,
            recommendations,
            report_generated_at,
            is_shared,
            shared_at,
            created_at,
            users!inner(
              id,
              full_name,
              birth_date
            ),
            sessions!inner(
              id,
              status,
              selected_photos,
              total_duration_seconds,
              cist_score,
              started_at,
              completed_at,
              notes,
              conversations(
                id,
                conversation_order,
                ai_output,
                question_type,
                user_input,
                user_response_audio_url,
                response_duration_seconds,
                ai_analysis,
                cist_score,
                is_cist_item,
                created_at,
                photo_id,
                photos(
                  id,
                  filename,
                  original_filename,
                  file_path,
                  description,
                  tags
                )
              )
            )
          ''')
          .eq('id', reportId)
          .eq('user_id', userId)
          .single();

      print('✅ Report detail fetched successfully');
      
      return Report.fromSupabase(response);
    } catch (e) {
      print('❌ Error fetching report detail: $e');
      throw Exception('리포트 상세 내용을 불러오지 못했습니다: $e');
    }
  }

  /// 새로운 리포트 생성
  static Future<Report> createReport({
    required String userId,
    required String sessionId,
    required int totalCistScore,
    int maxPossibleScore = 21,
    String? cognitiveStatus,
    Map<String, dynamic>? categoryScores,
    List<String>? insights,
    List<String>? recommendations,
  }) async {
    try {
      print('📝 Creating new report for session: $sessionId');
      
      final reportData = {
        'session_id': sessionId,
        'user_id': userId,
        'total_cist_score': totalCistScore,
        'max_possible_score': maxPossibleScore,
        'cognitive_status': cognitiveStatus ?? _determineCognitiveStatus(totalCistScore),
        'category_scores': categoryScores,
        'insights': insights ?? [],
        'recommendations': recommendations ?? [],
        'report_generated_at': DateTime.now().toIso8601String(),
        'is_shared': false,
      };

      final response = await SupabaseService.client
          .from('session_reports')
          .insert(reportData)
          .select()
          .single();

      print('✅ Report created successfully: ${response['id']}');
      
      return Report.fromSupabase(response);
    } catch (e) {
      print('❌ Error creating report: $e');
      throw Exception('리포트 생성 중 오류가 발생했습니다: $e');
    }
  }

  /// CIST 점수에 따른 인지 상태 판정
  static String _determineCognitiveStatus(int score) {
    if (score >= 18) return 'normal';
    if (score >= 14) return 'mild_concern';
    if (score >= 10) return 'moderate_concern';
    return 'high_concern';
  }

  /// 리포트 공유 상태 업데이트
  static Future<void> shareReport(String reportId, String userId) async {
    try {
      await SupabaseService.client
          .from('session_reports')
          .update({
            'is_shared': true,
            'shared_at': DateTime.now().toIso8601String(),
          })
          .eq('id', reportId)
          .eq('user_id', userId);
      
      print('✅ Report shared successfully: $reportId');
    } catch (e) {
      print('❌ Error sharing report: $e');
      throw Exception('리포트 공유 중 오류가 발생했습니다: $e');
    }
  }
}

class ReportTextAnalysisApi {
  /// 특정 세션의 발화 텍스트 분석 데이터 조회
  static Future<ReportTextAnalysisData?> fetchTextAnalysisData(
    String sessionId,
  ) async {
    try {
      print('🔍 Fetching text analysis data for session: $sessionId');

      final response = await SupabaseService.client
          .from('session_text_analysis')
          .select('''
            id,
            session_id,
            user_id,
            lexical_diversity,
            mlu,
            demonstrative_ratio,
            speech_rate
          ''')
          .eq('session_id', sessionId)
          .maybeSingle();

      if (response == null) {
        print('ℹ️ No text analysis data found for session: $sessionId');
        return null;
      }

      print('✅ Text analysis data fetched successfully');
      return ReportTextAnalysisData.fromJson(response);
    } catch (e) {
      print('❌ Error fetching text analysis data: $e');
      return null; // 에러 시 null 반환
    }
  }
}

class ReportAudioAnalysisApi {
  /// 특정 세션의 음성 분석 데이터 조회
  static Future<ReportAudioAnalysisData?> fetchAudioAnalysisData(
    String sessionId,
  ) async {
    try {
      print('🔍 Fetching audio analysis data for session: $sessionId');

      final response = await SupabaseService.client
          .from('session_audio_analysis')
          .select('''
            id,
            session_id,
            user_id,
            family_id,
            merged_audio_path,
            total_slices,
            dementia_slices,
            risk_level,
            adjusted_mean,
            created_at
          ''')
          .eq('session_id', sessionId)
          .maybeSingle();

      if (response == null) {
        print('ℹ️ No audio analysis data found for session: $sessionId');
        return null;
      }

      print('✅ Audio analysis data fetched successfully');
      return ReportAudioAnalysisData.fromJson(response);
    } catch (e) {
      print('❌ Error fetching audio analysis data: $e');
      return null; // 에러 시 null 반환
    }
  }
} 