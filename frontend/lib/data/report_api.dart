import '../core/supabase_service.dart';
import '../models/report.dart';

class ReportApi {
  /// 사용자의 모든 세션 리포트 조회
  static Future<List<Report>> fetchReports(String userId) async {
    try {
      print('🔍 Fetching reports for user: $userId');
      
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
          .eq('user_id', userId)
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
                question_text,
                question_type,
                user_response_text,
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