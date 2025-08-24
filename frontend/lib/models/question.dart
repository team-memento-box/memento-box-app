import 'photo.dart';

// CIST 질문 템플릿
class CistQuestion {
  final String id;
  final String category;
  final String templateText;
  final String contextType;
  final int difficultyLevel;
  final DateTime createdAt;

  CistQuestion({
    required this.id,
    required this.category,
    required this.templateText,
    required this.contextType,
    required this.difficultyLevel,
    required this.createdAt,
  });

  factory CistQuestion.fromSupabase(Map<String, dynamic> json) {
    return CistQuestion(
      id: json['id'],
      category: json['category'],
      templateText: json['template_text'],
      contextType: json['context_type'] ?? 'general',
      difficultyLevel: json['difficulty_level'] ?? 1,
      createdAt: DateTime.parse(json['created_at']),
    );
  }
}

// 대화 시작 문구
class ConversationStarter {
  final String id;
  final String starterText;
  final String contextType;
  final String emotionTone;
  final DateTime createdAt;

  ConversationStarter({
    required this.id,
    required this.starterText,
    required this.contextType,
    required this.emotionTone,
    required this.createdAt,
  });

  factory ConversationStarter.fromSupabase(Map<String, dynamic> json) {
    return ConversationStarter(
      id: json['id'],
      starterText: json['starter_text'],
      contextType: json['context_type'] ?? 'general',
      emotionTone: json['emotion_tone'] ?? 'positive',
      createdAt: DateTime.parse(json['created_at']),
    );
  }
}

// 대화 질문 (동적 생성용)
class ConversationQuestion {
  final String id;
  final String text;
  final String type;
  final String? category;
  final int difficultyLevel;
  final String? photoId;
  final Map<String, dynamic>? context;

  ConversationQuestion({
    required this.id,
    required this.text,
    required this.type,
    this.category,
    required this.difficultyLevel,
    this.photoId,
    this.context,
  });

  factory ConversationQuestion.fromTemplate(
    CistQuestion template, {
    String? photoContext,
    Map<String, dynamic>? additionalContext,
  }) {
    return ConversationQuestion(
      id: template.id,
      text: _interpolateTemplate(template.templateText, photoContext, additionalContext),
      type: 'cist_${template.category}',
      category: template.category,
      difficultyLevel: template.difficultyLevel,
      context: additionalContext,
    );
  }

  factory ConversationQuestion.fromStarter(
    ConversationStarter starter, {
    String? photoId,
    String? photoContext,
  }) {
    return ConversationQuestion(
      id: starter.id,
      text: starter.starterText,
      type: 'open_ended',
      difficultyLevel: 1,
      photoId: photoId,
      context: {'emotion_tone': starter.emotionTone, 'photo_context': photoContext},
    );
  }

  // 템플릿 문자열 보간
  static String _interpolateTemplate(
    String template,
    String? photoContext,
    Map<String, dynamic>? context,
  ) {
    String result = template;
    
    if (photoContext != null) {
      result = result.replaceAll('{photo_context}', photoContext);
    }
    
    if (context != null) {
      context.forEach((key, value) {
        result = result.replaceAll('{$key}', value.toString());
      });
    }
    
    return result;
  }
}

// 사용자 응답
class UserResponse {
  final String id;
  final String conversationId;
  final String? textResponse;
  final String? audioUrl;
  final int? durationSeconds;
  final DateTime createdAt;
  final Map<String, dynamic>? analysis;

  UserResponse({
    required this.id,
    required this.conversationId,
    this.textResponse,
    this.audioUrl,
    this.durationSeconds,
    required this.createdAt,
    this.analysis,
  });

  factory UserResponse.fromSupabase(Map<String, dynamic> json) {
    return UserResponse(
      id: json['id'],
      conversationId: json['conversation_id'],
      textResponse: json['user_response_text'],
      audioUrl: json['user_response_audio_url'],
      durationSeconds: json['response_duration_seconds'],
      createdAt: DateTime.parse(json['created_at']),
      analysis: json['ai_analysis'],
    );
  }
}

// 기존 호환성을 위한 클래스들 (photo.dart에서 이동)
class PhotoInfo {
  final String id;
  final String name;
  final String url;

  PhotoInfo({required this.id, required this.name, required this.url});

  factory PhotoInfo.fromJson(Map<String, dynamic> json) {
    return PhotoInfo(id: json['id'], name: json['name'], url: json['url']);
  }

  factory PhotoInfo.fromPhoto(Photo photo) {
    return PhotoInfo(
      id: photo.id,
      name: photo.originalFilename,
      url: photo.url,
    );
  }
}

class ConversationResponse {
  final String status;
  final String conversationId;
  final String question;
  final String audioUrl;
  final PhotoInfo photoInfo;
  final bool isContinuation;

  ConversationResponse({
    required this.status,
    required this.conversationId,
    required this.question,
    required this.audioUrl,
    required this.photoInfo,
    required this.isContinuation,
  });

  factory ConversationResponse.fromJson(Map<String, dynamic> json) {
    return ConversationResponse(
      status: json['status'],
      conversationId: json['conversation_id'],
      question: json['question'],
      audioUrl: json['audio_url'],
      photoInfo: PhotoInfo.fromJson(json['photo_info']),
      isContinuation: json['is_continuation'],
    );
  }
}