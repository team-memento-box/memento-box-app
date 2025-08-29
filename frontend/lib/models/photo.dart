import '../../core/supabase_service.dart';

class Photo {
  final String id;
  final String userId;
  final String fileName;
  final String filename;
  final String originalFilename;
  final String filePath;
  final int? fileSize;
  final String? mimeType;
  final int? width;
  final int? height;
  final String? description;
  final List<String> tags;
  final String? albumId;
  final DateTime? takenAt;
  final String? locationName;
  final double? latitude;
  final double? longitude;
  final bool isFavorite;
  final bool isDeleted;
  final DateTime createdAt;
  final DateTime updatedAt;
  final Map<String, dynamic>? photoAnalyzeResult;
  final DateTime? analyzedAt;

  Photo({
    required this.id,
    required this.userId,
    required this.fileName,
    required this.filename,
    required this.originalFilename,
    required this.filePath,
    this.fileSize,
    this.mimeType,
    this.width,
    this.height,
    this.description,
    required this.tags,
    this.albumId,
    this.takenAt,
    this.locationName,
    this.latitude,
    this.longitude,
    required this.isFavorite,
    required this.isDeleted,
    required this.createdAt,
    required this.updatedAt,
    this.photoAnalyzeResult,
    this.analyzedAt,
  });

  factory Photo.fromSupabase(Map<String, dynamic> json) {
    return Photo(
      id: json['id'],
      userId: json['user_id'],
      fileName: json['file_name'] ?? json['filename'], // 호환성
      filename: json['filename'],
      originalFilename: json['original_filename'],
      filePath: json['file_path'],
      fileSize: json['file_size'],
      mimeType: json['mime_type'],
      width: json['width'],
      height: json['height'],
      description: json['description'],
      tags: List<String>.from(json['tags'] ?? []),
      albumId: json['album_id'],
      takenAt: json['taken_at'] != null ? DateTime.parse(json['taken_at']) : null,
      locationName: json['location_name'],
      latitude: json['latitude']?.toDouble(),
      longitude: json['longitude']?.toDouble(),
      isFavorite: json['is_favorite'] ?? false,
      isDeleted: json['is_deleted'] ?? false,
      createdAt: DateTime.parse(json['created_at']),
      updatedAt: DateTime.parse(json['updated_at']),
      photoAnalyzeResult: json['photo_analyze_result'] as Map<String, dynamic>?,
      analyzedAt: json['analyzed_at'] != null ? DateTime.parse(json['analyzed_at']) : null,
    );
  }

  // Supabase Storage에서 공개 URL 생성
  String get url {
    return SupabaseService.client.storage
        .from('photos')
        .getPublicUrl(filePath);
  }

  // 기존 API 호환성을 위한 getter들
  String? get name => originalFilename;
  int get year => createdAt.year;
  String get season => _getSeason(createdAt);
  String get familyId => userId; // 임시로 userId 사용
  String get uploadedAt => createdAt.toIso8601String();
  String? get sasUrl => url; // 호환성

  // 계절 결정 로직
  String _getSeason(DateTime date) {
    final month = date.month;
    if (month >= 3 && month <= 5) return 'spring';
    if (month >= 6 && month <= 8) return 'summer';
    if (month >= 9 && month <= 11) return 'autumn';
    return 'winter';
  }

  String get formattedUploadedAt {
    return '${createdAt.year}년 ${createdAt.month.toString().padLeft(2, '0')}월 ${createdAt.day.toString().padLeft(2, '0')}일';
  }

  String get formattedTakenAt {
    if (takenAt == null) return formattedUploadedAt;
    return '${takenAt!.year}년 ${takenAt!.month.toString().padLeft(2, '0')}월 ${takenAt!.day.toString().padLeft(2, '0')}일';
  }

  // 파일 크기를 사람이 읽기 쉬운 형태로 변환
  String get formattedFileSize {
    if (fileSize == null) return '알 수 없음';
    
    const units = ['B', 'KB', 'MB', 'GB'];
    double size = fileSize!.toDouble();
    int unitIndex = 0;
    
    while (size >= 1024 && unitIndex < units.length - 1) {
      size /= 1024;
      unitIndex++;
    }
    
    return '${size.toStringAsFixed(1)} ${units[unitIndex]}';
  }

  // 이미지 해상도 문자열
  String get resolution {
    if (width == null || height == null) return '알 수 없음';
    return '${width}x$height';
  }

  // 분석 결과 관련 편의 메서드들
  bool get hasAnalysis => photoAnalyzeResult != null;
  
  String? get analysisCaption => photoAnalyzeResult?['caption'] as String?;
  
  List<String> get analysisDenseCaptions => 
      (photoAnalyzeResult?['dense_captions'] as List?)?.cast<String>() ?? [];
  
  String? get analysisMood => photoAnalyzeResult?['mood'] as String?;
  
  String? get analysisTimePeriod => photoAnalyzeResult?['time_period'] as String?;
  
  List<String> get analysisKeyObjects => 
      (photoAnalyzeResult?['key_objects'] as List?)?.cast<String>() ?? [];
  
  String? get analysisPeopleDescription => 
      photoAnalyzeResult?['people_description'] as String?;
  
  int get analysisPeopleCount => 
      photoAnalyzeResult?['people_count'] as int? ?? 0;
  
  String? get analysisTimeOfDay => photoAnalyzeResult?['time_of_day'] as String?;
  
  String get formattedAnalyzedAt {
    if (analyzedAt == null) return '분석되지 않음';
    return '${analyzedAt!.year}년 ${analyzedAt!.month.toString().padLeft(2, '0')}월 ${analyzedAt!.day.toString().padLeft(2, '0')}일';
  }
}

