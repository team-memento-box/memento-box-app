import 'photo.dart';

class SessionData {
  final String id;
  final String status;
  final List<String> selectedPhotos;
  final int totalDurationSeconds;
  final int? cistScore;
  final DateTime? startedAt;
  final DateTime? completedAt;
  final String? notes;
  final List<ConversationData>? conversations;

  SessionData({
    required this.id,
    required this.status,
    required this.selectedPhotos,
    required this.totalDurationSeconds,
    this.cistScore,
    this.startedAt,
    this.completedAt,
    this.notes,
    this.conversations,
  });

  factory SessionData.fromJson(Map<String, dynamic> json) {
    return SessionData(
      id: json['id'],
      status: json['status'],
      selectedPhotos: List<String>.from(json['selected_photos'] ?? []),
      totalDurationSeconds: json['total_duration_seconds'] ?? 0,
      cistScore: json['cist_score'],
      startedAt: json['started_at'] != null ? DateTime.parse(json['started_at']) : null,
      completedAt: json['completed_at'] != null ? DateTime.parse(json['completed_at']) : null,
      notes: json['notes'],
      conversations: json['conversations'] != null 
          ? (json['conversations'] as List).map((e) => ConversationData.fromJson(e)).toList()
          : null,
    );
  }
}

class ConversationData {
  final String id;
  final int conversationOrder;
  final String questionText;
  final String questionType;
  final String? userResponseText;
  final String? userResponseAudioUrl;
  final int? responseDurationSeconds;
  final Map<String, dynamic>? aiAnalysis;
  final int? cistScore;
  final bool isCistItem;
  final DateTime createdAt;
  final String? photoId;
  final Photo? photo;

  ConversationData({
    required this.id,
    required this.conversationOrder,
    required this.questionText,
    required this.questionType,
    this.userResponseText,
    this.userResponseAudioUrl,
    this.responseDurationSeconds,
    this.aiAnalysis,
    this.cistScore,
    required this.isCistItem,
    required this.createdAt,
    this.photoId,
    this.photo,
  });

  factory ConversationData.fromJson(Map<String, dynamic> json) {
    return ConversationData(
      id: json['id'],
      conversationOrder: json['conversation_order'],
      questionText: json['question_text'],
      questionType: json['question_type'],
      userResponseText: json['user_response_text'],
      userResponseAudioUrl: json['user_response_audio_url'],
      responseDurationSeconds: json['response_duration_seconds'],
      aiAnalysis: json['ai_analysis'],
      cistScore: json['cist_score'],
      isCistItem: json['is_cist_item'] ?? false,
      createdAt: DateTime.parse(json['created_at']),
      photoId: json['photo_id'],
      photo: json['photos'] != null ? Photo.fromSupabase(json['photos']) : null,
    );
  }
}

class Report {
  final String id;
  final String sessionId;
  final String userId;
  final int totalCistScore;
  final int maxPossibleScore;
  final String? cognitiveStatus;
  final Map<String, dynamic>? categoryScores;
  final List<String> insights;
  final List<String> recommendations;
  final DateTime reportGeneratedAt;
  final bool isShared;
  final DateTime? sharedAt;
  final DateTime createdAt;
  final SessionData? session;
  // 사용자 정보 필드 추가
  final String? userName; // users.full_name
  final DateTime? userBirthDate; // users.birth_date

  Report({
    required this.id,
    required this.sessionId,
    required this.userId,
    required this.totalCistScore,
    required this.maxPossibleScore,
    this.cognitiveStatus,
    this.categoryScores,
    required this.insights,
    required this.recommendations,
    required this.reportGeneratedAt,
    required this.isShared,
    this.sharedAt,
    required this.createdAt,
    this.session,
    this.userName,
    this.userBirthDate,
  });

  factory Report.fromSupabase(Map<String, dynamic> json) {
    return Report(
      id: json['id'],
      sessionId: json['session_id'],
      userId: json['user_id'],
      totalCistScore: json['total_cist_score'] ?? 0,
      maxPossibleScore: json['max_possible_score'] ?? 21,
      cognitiveStatus: json['cognitive_status'],
      categoryScores: json['category_scores'],
      insights: List<String>.from(json['insights'] ?? []),
      recommendations: List<String>.from(json['recommendations'] ?? []),
      reportGeneratedAt: DateTime.parse(json['report_generated_at']),
      isShared: json['is_shared'] ?? false,
      sharedAt: json['shared_at'] != null ? DateTime.parse(json['shared_at']) : null,
      createdAt: DateTime.parse(json['created_at']),
      session: json['sessions'] != null ? SessionData.fromJson(json['sessions']) : null,
      userName: json['users'] != null ? json['users']['full_name'] : null,
      userBirthDate: json['users'] != null && json['users']['birth_date'] != null
          ? DateTime.parse(json['users']['birth_date'])
          : null,
    );
  }

  // 기존 API 호환성을 위한 getter들
  String get reportId => id;
  String get convId => sessionId;
  String? get anomalyReport => _generateAnomalyReport();
  DateTime? get created_at => createdAt;
  String? get imageUrl => session?.conversations?.first?.photo?.url;

  // 인지 상태에 따른 이상 소견 생성
  String? _generateAnomalyReport() {
    switch (cognitiveStatus) {
      case 'high_concern':
        return '인지기능 검사 결과, 주의 깊은 관찰이 필요한 수준의 어려움이 확인되었습니다. 전문의 상담을 권장합니다.';
      case 'moderate_concern':
        return '인지기능 검사에서 일부 영역에 어려움이 관찰되었습니다. 지속적인 모니터링이 필요합니다.';
      case 'mild_concern':
        return '인지기능 검사에서 경미한 변화가 관찰되었습니다. 정기적인 검사를 통한 추적 관찰을 권장합니다.';
      case 'normal':
        return '인지기능 검사 결과가 정상 범위 내에 있습니다.';
      default:
        return null;
    }
  }

  // 점수 백분율 계산
  double get scorePercentage => (totalCistScore / maxPossibleScore) * 100;

  // 포맷된 날짜 반환
  String get formattedDate {
    return '${createdAt.year}년 ${createdAt.month.toString().padLeft(2, '0')}월 ${createdAt.day.toString().padLeft(2, '0')}일';
  }

  // 인지 상태 한글 표시
  String get cognitiveStatusText {
    switch (cognitiveStatus) {
      case 'normal':
        return '정상';
      case 'mild_concern':
        return '경미한 주의';
      case 'moderate_concern':
        return '중등도 주의';
      case 'high_concern':
        return '높은 주의';
      default:
        return '미분류';
    }
  }

  // 연령대 계산 (10의 자리대로 끼어서)
  String get ageGroup {
    if (userBirthDate == null) return '연령 미상';
    
    final now = DateTime.now();
    final age = now.year - userBirthDate!.year;
    
    // 생일이 지나지 않았으면 나이에서 1을 뺀
    final adjustedAge = now.month < userBirthDate!.month ||
            (now.month == userBirthDate!.month && now.day < userBirthDate!.day)
        ? age - 1
        : age;
    
    final ageGroupNumber = (adjustedAge ~/ 10) * 10;
    return '$ageGroupNumber대';
  }

  // 사용자 이름 (님 붙여서)
  String get userDisplayName {
    if (userName == null || userName!.isEmpty) return '사용자';
    return userName!.endsWith('님') ? userName! : '${userName!}님';
  }
}