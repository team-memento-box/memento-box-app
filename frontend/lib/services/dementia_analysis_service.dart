import 'dart:io';
import 'dart:convert';
import 'package:http/http.dart' as http;

class DementiaAnalysisService {
  static const String _baseUrl = 'http://localhost:8000'; // 개발용 URL
  
  /// 오디오 파일을 백엔드로 전송하여 치매 분석 결과를 받아오는 함수
  static Future<DementiaAnalysisResult> analyzeAudioFile({
    required File audioFile,
    String? userId,
    String? familyId,
    String? photoId,
  }) async {
    try {
      // Multipart 요청 생성
      var request = http.MultipartRequest(
        'POST',
        Uri.parse('$_baseUrl/audio-dementia-detection'),
      );
      
      // 오디오 파일 추가
      request.files.add(
        await http.MultipartFile.fromPath(
          'audio_file',
          audioFile.path,
        ),
      );
      
      // 선택적 필드들 추가
      if (userId != null) request.fields['user_id'] = userId;
      if (familyId != null) request.fields['family_id'] = familyId;
      if (photoId != null) request.fields['photo_id'] = photoId;
      
      // 요청 전송
      var response = await request.send();
      var responseBody = await response.stream.bytesToString();
      
      if (response.statusCode == 200) {
        final jsonData = json.decode(responseBody);
        return DementiaAnalysisResult.fromJson(jsonData);
      } else {
        throw Exception('API 호출 실패: ${response.statusCode}');
      }
    } catch (e) {
      throw Exception('치매 분석 요청 중 오류 발생: $e');
    }
  }
}

/// 백엔드 API 응답을 나타내는 클래스
class DementiaAnalysisResult {
  final bool success;
  final String audioFile;
  final int totalSegments;
  final bool dementiaDetected;
  final int dementiaSegmentsCount;
  final int normalSegmentsCount;
  final double dementiaRatio;
  final List<SegmentDetail> segmentDetails;
  final int overallPrediction;
  final String overallPredictionLabel;
  final List<String> classNames;
  final DatabaseInfo? database;

  const DementiaAnalysisResult({
    required this.success,
    required this.audioFile,
    required this.totalSegments,
    required this.dementiaDetected,
    required this.dementiaSegmentsCount,
    required this.normalSegmentsCount,
    required this.dementiaRatio,
    required this.segmentDetails,
    required this.overallPrediction,
    required this.overallPredictionLabel,
    required this.classNames,
    this.database,
  });

  factory DementiaAnalysisResult.fromJson(Map<String, dynamic> json) {
    return DementiaAnalysisResult(
      success: json['success'] ?? false,
      audioFile: json['audio_file'] ?? '',
      totalSegments: json['total_segments'] ?? 0,
      dementiaDetected: json['dementia_detected'] ?? false,
      dementiaSegmentsCount: json['dementia_segments_count'] ?? 0,
      normalSegmentsCount: json['normal_segments_count'] ?? 0,
      dementiaRatio: (json['dementia_ratio'] ?? 0.0).toDouble(),
      segmentDetails: (json['segment_details'] as List? ?? [])
          .map((item) => SegmentDetail.fromJson(item))
          .toList(),
      overallPrediction: json['overall_prediction'] ?? 0,
      overallPredictionLabel: json['overall_prediction_label'] ?? '',
      classNames: List<String>.from(json['class_names'] ?? []),
      database: json['database'] != null 
          ? DatabaseInfo.fromJson(json['database'])
          : null,
    );
  }

  /// UI에서 사용할 HealthAnalysisData로 변환
  HealthAnalysisData toHealthAnalysisData({
    required String userName,
    required String ageGroup,
    double ageGroupAverageRatio = 0.25,
  }) {
    // AI 음성 점수 계산: 100 - (dementiaRatio * 100) 반올림
    int aiVoiceScore = (100 - (dementiaRatio * 100)).round();
    
    // 발화 내용 점수 (임시로 AI 음성 점수와 비슷하게 설정, 약간 다르게)
    int speechContentScore = (aiVoiceScore * 0.98).round();
    
    return HealthAnalysisData(
      totalSegments: totalSegments,
      dementiaSegmentsCount: dementiaSegmentsCount,
      dementiaRatio: dementiaRatio,
      aiVoiceScore: aiVoiceScore,
      speechContentScore: speechContentScore,
      userName: userName,
      ageGroup: ageGroup,
      ageGroupAverageRatio: ageGroupAverageRatio,
    );
  }
}

/// 세그먼트별 상세 분석 결과
class SegmentDetail {
  final String segmentId;
  final int prediction;
  final String predictionLabel;
  final double confidence;
  final Map<String, double> probabilities;

  const SegmentDetail({
    required this.segmentId,
    required this.prediction,
    required this.predictionLabel,
    required this.confidence,
    required this.probabilities,
  });

  factory SegmentDetail.fromJson(Map<String, dynamic> json) {
    return SegmentDetail(
      segmentId: json['segment_id'] ?? '',
      prediction: json['prediction'] ?? 0,
      predictionLabel: json['prediction_label'] ?? '',
      confidence: (json['confidence'] ?? 0.0).toDouble(),
      probabilities: Map<String, double>.from(
        json['probabilities']?.map(
          (key, value) => MapEntry(key, (value as num).toDouble()),
        ) ?? {},
      ),
    );
  }
}

/// 데이터베이스 저장 정보
class DatabaseInfo {
  final bool saved;
  final String? recordId;
  final int? healthScore;
  final String? error;
  final String? note;

  const DatabaseInfo({
    required this.saved,
    this.recordId,
    this.healthScore,
    this.error,
    this.note,
  });

  factory DatabaseInfo.fromJson(Map<String, dynamic> json) {
    return DatabaseInfo(
      saved: json['saved'] ?? false,
      recordId: json['record_id'],
      healthScore: json['health_score'],
      error: json['error'],
      note: json['note'],
    );
  }
}

/// 기존 HealthAnalysisData 클래스 (report_detail_speech.dart에서 import하여 사용)
class HealthAnalysisData {
  final int totalSegments;
  final int dementiaSegmentsCount;
  final double dementiaRatio;
  final int aiVoiceScore;
  final int speechContentScore;
  final String userName;
  final String ageGroup;
  final double ageGroupAverageRatio;
  final Map<String, double> languageAnalysisScores;

  const HealthAnalysisData({
    required this.totalSegments,
    required this.dementiaSegmentsCount,
    required this.dementiaRatio,
    required this.aiVoiceScore,
    required this.speechContentScore,
    required this.userName,
    required this.ageGroup,
    required this.ageGroupAverageRatio,
    this.languageAnalysisScores = const {
      '평균 발화 길이': 0.7,
      '어휘 다양성': 0.5,
      '발화 속도': 0.8,
      '지시어 사용 비율': 0.6,
    },
  });

  bool get isAboveAverage => dementiaRatio > ageGroupAverageRatio;
  
  String get comparisonText => isAboveAverage ? "높게 나왔어요" : "낮게 나왔어요";
  
  String get comparisonForAnalysis => isAboveAverage ? "평균보다 높은 비율" : "평균보다 낮은 비율";
}