import 'package:flutter/material.dart';
import 'dart:math';
import '../models/report.dart';
import '../widgets/tap_widget.dart';
import '../widgets/group_bar_widget.dart';
import '../data/report_api.dart';

// Constants
class AppColors {
  static const Color background = Colors.white;
  static const Color cardBackground = Color(0xFFE2F6EB);
  static const Color summaryCardColor = Color(0xFF7CD0A0);
  static const Color textPrimary = Color(0xFF333333);
  static const Color textSecondary = Color(0xFF777777);
  static const Color textTertiary = Color(0xFF111111);
  static const Color normalSegment = Color(0xFF75B874);
  static const Color riskSegment = Color(0xFFFA7B70);
  static const Color accentRed = Color(0xFFF45C5C);
  static const Color accentGreen = Color(0xFF48AC6E);
}

class AppTextStyles {
  static const TextStyle headerTitle = TextStyle(
    color: AppColors.textPrimary,
    fontSize: 16,
    fontFamily: 'Pretendard',
    fontWeight: FontWeight.w600,
  );

  static const TextStyle headerSubtitle = TextStyle(
    color: AppColors.textSecondary,
    fontSize: 12,
    fontFamily: 'Pretendard',
    fontWeight: FontWeight.w600,
  );

  static const TextStyle cardTitle = TextStyle(
    color: AppColors.textTertiary,
    fontSize: 20,
    fontFamily: 'Pretendard',
    fontWeight: FontWeight.w700,
  );

  static const TextStyle bodyText = TextStyle(
    color: AppColors.textTertiary,
    fontSize: 12,
    fontFamily: 'Pretendard',
    fontWeight: FontWeight.w600,
    height: 1.5,
  );

  static const TextStyle smallText = TextStyle(
    color: AppColors.textSecondary,
    fontSize: 10,
    fontFamily: 'Pretendard',
    fontWeight: FontWeight.w500,
    height: 1.4,
  );
}

// Data Models
class HealthAnalysisData {
  final int totalSegments;
  final int dementiaSegmentsCount;
  final double dementiaRatio;
  final int aiVoiceScore;
  final int speechContentScore;
  final String userName;
  final String ageGroup;
  final double ageGroupAverageRatio;

  const HealthAnalysisData({
    required this.totalSegments,
    required this.dementiaSegmentsCount,
    required this.dementiaRatio,
    required this.aiVoiceScore,
    required this.speechContentScore,
    required this.userName,
    required this.ageGroup,
    required this.ageGroupAverageRatio,
  });

  // Computed properties
  bool get isAboveAverage => dementiaRatio < ageGroupAverageRatio;

  String get comparisonText {
    if (isAboveAverage) {
      return '높게 나왔어요';
    } else {
      return '낮게 나왔어요';
    }
  }

  String get comparisonForAnalysis {
    if (isAboveAverage) {
      return '평균보다 낮은 비율입니다';
    } else {
      return '평균보다 높은 비율입니다';
    }
  }
}

// Main Screen
class ConversationHealthAnalysisScreen extends StatefulWidget {
  final HealthAnalysisData? initialData;
  final Report? reportData;
  final String? sessionId;
  final String? photoId;

  const ConversationHealthAnalysisScreen({
    super.key,
    this.initialData,
    this.reportData,
    this.sessionId,
    this.photoId,
  });

  @override
  State<ConversationHealthAnalysisScreen> createState() => _ConversationHealthAnalysisScreenState();
}

class _ConversationHealthAnalysisScreenState extends State<ConversationHealthAnalysisScreen> {
  HealthAnalysisData? data;
  ReportTextAnalysisData? textAnalysisData;
  List<ReportAudioAnalysisData>? audioAnalysisDataList;
  bool isLoading = false;

  @override
  void initState() {
    super.initState();
    data = widget.initialData ?? const HealthAnalysisData(
      totalSegments: 20,
      dementiaSegmentsCount: 8,
      dementiaRatio: 0.4,
      aiVoiceScore: 66,
      speechContentScore: 65,
      userName: "서봉봉",
      ageGroup: "60대",
      ageGroupAverageRatio: 0.3,
    );
    _loadAnalysisData();
  }

  Future<void> _loadAnalysisData() async {
    setState(() => isLoading = true);
    try {
      List<Future> futures = [];
      
      // 텍스트 분석 데이터 로드 (sessionId 필요)
      final sessionId = widget.sessionId ?? widget.reportData?.sessionId;
      if (sessionId != null) {
        futures.add(ReportTextAnalysisApi.fetchTextAnalysisData(sessionId));
      }
      
      // 음성 분석 데이터 로드 (photo_id와 session_id로 조회)
      if (widget.photoId != null) {
        futures.add(ReportAudioAnalysisApi.fetchAudioAnalysisByPhotoAndSession(
          widget.photoId!,
          widget.sessionId,
        ));
      } else if (sessionId != null) {
        // photoId가 없으면 기존 방식으로 sessionId만 사용
        futures.add(ReportAudioAnalysisApi.fetchAudioAnalysisData(sessionId).then((data) => data != null ? [data] : null));
      }
      
      final results = await Future.wait(futures);
      
      setState(() {
        if (results.isNotEmpty && sessionId != null) {
          textAnalysisData = results[0] as ReportTextAnalysisData?;
        }
        
        // 텍스트 분석 데이터가 없으면 더미 데이터 생성 (테스트용)
        textAnalysisData ??= ReportTextAnalysisData(
          id: "dummy-text-analysis",
          sessionId: sessionId ?? "unknown",
          userId: "dummy-user",
          lexicalDiversity: 0.9413,
          mlu: 3.3,
          demonstrativeRatio: 0.18,
          speechRate: 1.56,
        );
        if (results.length > 1) {
          audioAnalysisDataList = results[1] as List<ReportAudioAnalysisData>?;
        } else if (results.isNotEmpty && widget.photoId == null) {
          audioAnalysisDataList = results[0] as List<ReportAudioAnalysisData>?;
        }
        
        // 첫 번째 음성 분석 데이터로 HealthAnalysisData 업데이트
        if (audioAnalysisDataList != null && audioAnalysisDataList!.isNotEmpty) {
          final firstAudioData = audioAnalysisDataList!.first;
          data = HealthAnalysisData(
            totalSegments: firstAudioData.totalSlices,
            dementiaSegmentsCount: firstAudioData.dementiaSlices,
            dementiaRatio: firstAudioData.calculatedDementiaRatio,
            aiVoiceScore: firstAudioData.healthScore ?? data?.aiVoiceScore ?? 66,
            speechContentScore: data?.speechContentScore ?? 65,
            userName: widget.reportData?.userName ?? data?.userName ?? "사용자",
            ageGroup: widget.reportData?.ageGroup ?? data?.ageGroup ?? "60대",
            ageGroupAverageRatio: firstAudioData.ageGroupAvgRatio ?? 0.25,
          );
        }
        
        isLoading = false;
      });
    } catch (e) {
      print('❌ Error loading analysis data: $e');
      setState(() => isLoading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    if (data == null) return const Scaffold(body: Center(child: CircularProgressIndicator()));
    
    final screenSize = MediaQuery.of(context).size;
    final screenWidth = screenSize.width;
    final screenHeight = screenSize.height;

    return Scaffold(
      backgroundColor: const Color(0xFFF7F7F7),
      appBar: GroupBar(title: '대화 건강 지수 상세 페이지'),
      body: SingleChildScrollView(
        padding: EdgeInsets.symmetric(
          horizontal: screenWidth * 0.05,
          vertical: screenHeight * 0.02,
        ),
        child: Column(
          children: [
            
            // 요약 카드들
            DetailSpeechSummary(screenWidth),
            SizedBox(height: screenHeight * 0.04),
            
            // 회색 삼각형 (더 길고 연한 색상)
            Center(
              child: Container(
                width: 0,
                height: 0,
                decoration: BoxDecoration(
                  border: Border(
                    left: BorderSide(width: 50, color: Colors.transparent),
                    right: BorderSide(width: 50, color: Colors.transparent),
                    bottom: BorderSide(width: 20, color: Color(0xFFD0D0D0)),
                  ),
                ),
              ),
            ),
            SizedBox(height: screenHeight * 0.04),
            
            // AI 음성 분석 카드
            _AIVoiceAnalysisCard(
              data: data!,
              audioAnalysisDataList: audioAnalysisDataList,
              screenWidth: screenWidth,
              screenHeight: screenHeight,
            ),
            SizedBox(height: screenHeight * 0.03),
            
            // 발화 언어 분석 카드
            SpeechAnalysisCard(
              screenWidth: screenWidth,
              screenHeight: screenHeight,
              ageGroup: data?.ageGroup,
              textAnalysisData: textAnalysisData,
              buildRadarChart: _buildRadarChart,
              buildLegend: _buildLegend,
            ),
            
            SizedBox(height: screenHeight * 0.1),
          ],
        ),
      ),
      bottomNavigationBar: const CustomBottomNavBar(currentIndex: 3),
    );
  }

  Widget _buildRadarChart(double screenWidth) {
    final chartSize = screenWidth * 0.9; // 화면 너비의 80%

    return Container(
      width: chartSize,
      height: chartSize * 0.9, // 높이만 80%로 줄임
      child: Stack(
        alignment: Alignment.center,
        children: [
          // 동심원들 (배경)
          ...List.generate(5, (index) {
            final radius = (chartSize * 0.6) / 2 * (1 - index * 0.2);
            return Container(
              width: radius * 2,
              height: radius * 2,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                border: Border.all(color: const Color(0xFFDDDDDD), width: 1),
                color: index == 0 ? Colors.white : Colors.transparent,
              ),
            );
          }),

          // 중심에서 각 축으로 선 그리기
          CustomPaint(
            size: Size(chartSize * 0.6, chartSize * 0.6),
            painter: RadarGridPainter(),
          ),

          // 축 레이블들
          _buildAxisLabels(chartSize, screenWidth),

          // 데이터 표시점들
          _buildDataPoints(chartSize),
        ],
      ),
    );
  }

  Widget _buildAxisLabels(double chartSize, double screenWidth) {
    return Stack(
      alignment: Alignment.center,
      children: [
        // 어휘 다양성 (상단)
        Positioned(
          top: chartSize * 0.06,
          child: Text(
            '어휘 다양성',
            style: TextStyle(
              color: const Color(0xFF777777),
              fontSize: screenWidth * 0.035,
              fontFamily: 'Pretendard',
              fontWeight: FontWeight.w500,
            ),
          ),
        ),

        // 지시어 사용 비율 (우측)
        Positioned(
          right: chartSize * 0.04,
          top: chartSize * 0.45,
          child: Text(
            '지시어\n사용 비율',
            textAlign: TextAlign.center,
            style: TextStyle(
              color: const Color(0xFF777777),
              fontSize: screenWidth * 0.035,
              fontFamily: 'Pretendard',
              fontWeight: FontWeight.w500,
            ),
          ),
        ),

        // 발화 속도 (하단)
        Positioned(
          bottom: chartSize * 0.06,
          child: Text(
            '발화 속도',
            style: TextStyle(
              color: const Color(0xFF777777),
              fontSize: screenWidth * 0.035,
              fontFamily: 'Pretendard',
              fontWeight: FontWeight.w500,
            ),
          ),
        ),

        // 평균 발화 길이 (좌측)
        Positioned(
          left: chartSize * 0.04,
          top: chartSize * 0.45,
          child: Text(
            '평균\n발화 길이',
            textAlign: TextAlign.center,
            style: TextStyle(
              color: const Color(0xFF777777),
              fontSize: screenWidth * 0.035,
              fontFamily: 'Pretendard',
              fontWeight: FontWeight.w500,
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildDataPoints(double chartSize) {
    // 원시 데이터 값
    final rawUserValues = {
      'vocabulary': textAnalysisData?.lexicalDiversity ?? 0.5, // 어휘 다양성 (0-1)
      'pronouns': textAnalysisData?.demonstrativeRatio ?? 0.3, // 지시어 사용 비율 (0-1)
      'length': textAnalysisData?.mlu ?? 8.0, // 평균 발화 길이 (MLU) - 실제 값
      'speed': textAnalysisData?.speechRate ?? 1.8, // 발화 속도 - 1초당 1.8단어 (실제 값)
    };

    final rawAvgValues = {
      'vocabulary': textAnalysisData?.avgLexicalDiversity ?? 0.7, // 어휘 다양성 평균
      'pronouns': textAnalysisData?.avgDemonstrativeRatio ?? 0.2, // 지시어 사용 비율 평균
      'length': textAnalysisData?.avgMlu ?? 10.0, // 평균 발화 길이 평균
      'speed': textAnalysisData?.avgSpeechRate ?? 2.2, // 발화 속도 평균 - 1초당 2.2단어
    };

    // Min-Max 스케일링을 위한 범위 설정
    final scales = {
      'vocabulary': {'min': 0.0, 'max': 1.0}, // 이미 0-1 범위
      'pronouns': {'min': 0.0, 'max': 1.0}, // 이미 0-1 범위
      'length': {'min': 1.0, 'max': 20.0}, // MLU 범위: 1-20
      'speed': {'min': 0.1, 'max': 3.0}, // 발화 속도 범위: 0.1-3.0 (1초당 단어 수)
    };

    // 정규화 함수
    double normalize(double value, String key) {
      final scale = scales[key]!;
      final min = scale['min']!;
      final max = scale['max']!;
      return ((value - min) / (max - min)).clamp(0.0, 1.0);
    }

    // 정규화된 값들
    final userValues = {
      'vocabulary': normalize(rawUserValues['vocabulary']!, 'vocabulary'),
      'pronouns': normalize(rawUserValues['pronouns']!, 'pronouns'),
      'length': normalize(rawUserValues['length']!, 'length'),
      'speed': normalize(rawUserValues['speed']!, 'speed'),
    };

    final avgValues = {
      'vocabulary': normalize(rawAvgValues['vocabulary']!, 'vocabulary'),
      'pronouns': normalize(rawAvgValues['pronouns']!, 'pronouns'),
      'length': normalize(rawAvgValues['length']!, 'length'),
      'speed': normalize(rawAvgValues['speed']!, 'speed'),
    };

    return Stack(
      alignment: Alignment.center,
      children: [
        // 평균 데이터 다이아몬드 (녹색)
        CustomPaint(
          size: Size(chartSize, chartSize),
          painter: DataDiamondPainter(
            values: avgValues,
            color: const Color(0xFF90D7AF),
            isUser: false,
          ),
        ),
        // 사용자 데이터 다이아몬드 (빨간색)
        CustomPaint(
          size: Size(chartSize, chartSize),
          painter: DataDiamondPainter(
            values: userValues,
            color: const Color(0xFFF6A192),
            isUser: true,
          ),
        ),
      ],
    );
  }

  Widget _buildLegend(double screenWidth) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.center,
      children: [
        // 사용자 범례
        Row(
          children: [
            Transform.rotate(
              angle: 0.785398, // 45도 (π/4 라디안)
              child: Container(
                width: 6,
                height: 6,
                decoration: const BoxDecoration(color: Color(0xFFF6A192)),
              ),
            ),
            SizedBox(width: screenWidth * 0.02),
            Text(
              data?.userName ?? '사용자',
              style: TextStyle(
                color: const Color(0xFF777777),
                fontSize: screenWidth * 0.024,
                fontFamily: 'Pretendard',
                fontWeight: FontWeight.w500,
              ),
            ),
          ],
        ),

        SizedBox(width: screenWidth * 0.08),

        // 평균 범례
        Row(
          children: [
            Transform.rotate(
              angle: 0.785398, // 45도 (π/4 라디안)
              child: Container(
                width: 6,
                height: 6,
                decoration: const BoxDecoration(color: Color(0xFF90D7AF)),
              ),
            ),
            SizedBox(width: screenWidth * 0.02),
            Text(
              '동일 연령대 평균',
              style: TextStyle(
                color: const Color(0xFF777777),
                fontSize: screenWidth * 0.024,
                fontFamily: 'Pretendard',
                fontWeight: FontWeight.w500,
              ),
            ),
          ],
        ),
      ],
    );
  }
}

// Detail Speech Summary Component
Widget _DetailSpeechSummary(double screenWidth, HealthAnalysisData data) {
  return Padding(
    padding: const EdgeInsets.symmetric(horizontal: 20),
    child: Row(
      children: [
        // AI 음성 분석 요약 카드
        Expanded(
          child: Container(
            height: 160,
            decoration: ShapeDecoration(
              color: const Color(0xFF9BDDB8),
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(13),
              ),
              shadows: [
                BoxShadow(
                  color: Color(0x19000000),
                  blurRadius: 5,
                  offset: Offset(0, 2),
                  spreadRadius: 0,
                ),
              ],
            ),
            child: Padding(
              padding: const EdgeInsets.all(12),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.center,
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Text(
                    'AI 음성 분석 요약',
                    textAlign: TextAlign.center,
                    style: TextStyle(
                      color: Colors.white,
                      fontSize: 13,
                      fontFamily: 'Pretendard',
                      fontWeight: FontWeight.w800,
                    ),
                  ),
                  Container(
                    width: 40,
                    height: 40,
                    decoration: BoxDecoration(
                      image: DecorationImage(
                        image: AssetImage("assets/icons/Audio_icon.png"),
                        fit: BoxFit.contain,
                      ),
                    ),
                  ),
                  Flexible(
                    child: Text.rich(
                      TextSpan(
                        children: [
                          TextSpan(
                            text: '${data.userName}님, 이번 대화에서\n',
                            style: TextStyle(
                              color: Colors.white,
                              fontSize: 10,
                              fontFamily: 'Pretendard',
                              fontWeight: FontWeight.w700,
                            ),
                          ),
                          TextSpan(
                            text: '${data.ageGroup} 평균보다\n',
                            style: TextStyle(
                              color: const Color(0xFF777777),
                              fontSize: 10,
                              fontFamily: 'Pretendard',
                              fontWeight: FontWeight.w700,
                            ),
                          ),
                          TextSpan(
                            text: data.comparisonText,
                            style: TextStyle(
                              color: const Color(0xFFF45C5C),
                              fontSize: 10,
                              fontFamily: 'Pretendard',
                              fontWeight: FontWeight.w700,
                            ),
                          ),
                        ],
                      ),
                      textAlign: TextAlign.center,
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
        
        SizedBox(width: 16),
        
        // 발화 언어 분석 요약 카드
        Expanded(
          child: Container(
            height: 160,
            decoration: ShapeDecoration(
              color: const Color(0xFF9BDDB8),
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(13),
              ),
              shadows: [
                BoxShadow(
                  color: Color(0x19000000),
                  blurRadius: 5,
                  offset: Offset(0, 2),
                  spreadRadius: 0,
                ),
              ],
            ),
            child: Padding(
              padding: const EdgeInsets.all(12),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.center,
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Text(
                    '발화 언어 분석 요약',
                    textAlign: TextAlign.center,
                    style: TextStyle(
                      color: Colors.white,
                      fontSize: 13,
                      fontFamily: 'Pretendard',
                      fontWeight: FontWeight.w800,
                    ),
                  ),
                  Container(
                    width: 40,
                    height: 40,
                    decoration: BoxDecoration(
                      image: DecorationImage(
                        image: AssetImage("assets/icons/Language_icon.png"),
                        fit: BoxFit.contain,
                      ),
                    ),
                  ),
                  Flexible(
                    child: Text.rich(
                      TextSpan(
                        children: [
                          TextSpan(
                            text: '${data.userName}님, 이번 대화에서\n',
                            style: TextStyle(
                              color: Colors.white,
                              fontSize: 10,
                              fontFamily: 'Pretendard',
                              fontWeight: FontWeight.w700,
                            ),
                          ),
                          TextSpan(
                            text: '${data.ageGroup} 평균보다\n',
                            style: TextStyle(
                              color: const Color(0xFF777777),
                              fontSize: 10,
                              fontFamily: 'Pretendard',
                              fontWeight: FontWeight.w700,
                            ),
                          ),
                          TextSpan(
                            text: data.comparisonText,
                            style: TextStyle(
                              color: const Color(0xFFF45C5C),
                              fontSize: 10,
                              fontFamily: 'Pretendard',
                              fontWeight: FontWeight.w700,
                            ),
                          ),
                        ],
                      ),
                      textAlign: TextAlign.center,
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
      ],
    ),
  );
}

// Header Component
class _Header extends StatelessWidget {
  final HealthAnalysisData data;

  const _Header({required this.data});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 15),
      decoration: const BoxDecoration(
        color: AppColors.background,
        border: Border(
          bottom: BorderSide(color: Color(0x7F999999), width: 0.5),
        ),
      ),
      child: Column(
        children: [
          Text(
            '${data.userName}님 대화 건강 지수 분석 결과',
            style: AppTextStyles.headerTitle,
          ),
          const SizedBox(height: 8),
          Text(
            '2025-05-26 13:56',
            style: AppTextStyles.headerSubtitle,
          ),
        ],
      ),
    );
  }
}

// Summary Cards Component
class _SummaryCards extends StatelessWidget {
  final HealthAnalysisData data;

  const _SummaryCards({required this.data});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 20),
      child: Row(
        children: [
          Expanded(
            child: _SummaryCard(
              title: 'AI 음성 분석 요약',
              iconPath: 'assets/images/audio_icon.png',
              userName: data.userName,
              ageGroup: data.ageGroup,
              comparisonText: data.comparisonText,
              isAboveAverage: data.isAboveAverage,
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: _SummaryCard(
              title: '발화 언어 분석 요약',
              iconPath: 'assets/images/language_icon.png',
              userName: data.userName,
              ageGroup: data.ageGroup,
              comparisonText: data.comparisonText,
              isAboveAverage: data.isAboveAverage,
            ),
          ),
        ],
      ),
    );
  }
}

class _SummaryCard extends StatelessWidget {
  final String title;
  final String iconPath;
  final String userName;
  final String ageGroup;
  final String comparisonText;
  final bool isAboveAverage;

  const _SummaryCard({
    required this.title,
    required this.iconPath,
    required this.userName,
    required this.ageGroup,
    required this.comparisonText,
    required this.isAboveAverage,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      height: 180,
      decoration: BoxDecoration(
        color: AppColors.summaryCardColor,
        borderRadius: BorderRadius.circular(13),
        boxShadow: const [
          BoxShadow(
            color: Color(0x19000000),
            blurRadius: 5,
            offset: Offset(0, 2),
          ),
        ],
      ),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.center,
          children: [
            Text(
              title,
              textAlign: TextAlign.center,
              style: const TextStyle(
                color: Colors.white,
                fontSize: 14,
                fontFamily: 'Pretendard',
                fontWeight: FontWeight.w800,
              ),
            ),
            const Spacer(),
            Container(
              width: 56,
              height: 56,
              decoration: BoxDecoration(
                color: Colors.white.withOpacity(0.2),
                borderRadius: BorderRadius.circular(28),
              ),
              child: Image.asset(
                iconPath,
                width: 32,
                height: 32,
              ),
            ),
            const Spacer(),
            Text.rich(
              TextSpan(
                children: [
                  TextSpan(
                    text: '$userName님, 이번 대화에서\n',
                    style: const TextStyle(
                      color: Colors.white,
                      fontSize: 11,
                      fontFamily: 'Pretendard',
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                  TextSpan(
                    text: '$ageGroup 평균보다\n',
                    style: const TextStyle(
                      color: AppColors.textSecondary,
                      fontSize: 11,
                      fontFamily: 'Pretendard',
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                  TextSpan(
                    text: comparisonText,
                    style: TextStyle(
                      color: isAboveAverage ? AppColors.accentRed : AppColors.accentRed,
                      fontSize: 11,
                      fontFamily: 'Pretendard',
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                ],
              ),
              textAlign: TextAlign.center,
            ),
          ],
        ),
      ),
    );
  }
}

// AI Voice Analysis Card Component
class _AIVoiceAnalysisCard extends StatelessWidget {
  final HealthAnalysisData data;
  final List<ReportAudioAnalysisData>? audioAnalysisDataList;
  final double screenWidth;
  final double screenHeight;

  const _AIVoiceAnalysisCard({
    required this.data,
    this.audioAnalysisDataList,
    required this.screenWidth,
    required this.screenHeight,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: EdgeInsets.symmetric(vertical: screenWidth * 0.07),
      decoration: BoxDecoration(
        color: const Color(0xFFE2F6EB),
        borderRadius: BorderRadius.circular(13),
        boxShadow: [
          BoxShadow(
            color: const Color(0x19000000),
            blurRadius: 5,
            offset: const Offset(0, 2),
          ),
        ],
      ),
      child: Column(
        children: [
          // 제목
          Text(
            'AI 음성 분석',
            textAlign: TextAlign.center,
            style: TextStyle(
              color: const Color(0xFF111111),
              fontSize: screenWidth * 0.052,
              fontFamily: 'Pretendard',
              fontWeight: FontWeight.w700,
            ),
          ),
          
          SizedBox(height: screenHeight * 0.015),

          // 설명 텍스트
          Text(
            '대화 음성의 특성을 분석해 인지 저하 징후를 탐지 합니다.\n전체 대화 중 의심 구간이 비율이 높을수록\n인지 저하의 가능성이 높습니다.',
            textAlign: TextAlign.center,
            style: TextStyle(
              color: const Color(0xFF777777),
              fontSize: screenWidth * 0.026,
              fontFamily: 'Pretendard',
              fontWeight: FontWeight.w500,
              height: 1.4,
            ),
          ),
          
          SizedBox(height: screenHeight * 0.02),
          
          Text(
            '이번 대화 분석 결과입니다',
            style: TextStyle(
              color: const Color(0xFF111111),
              fontSize: screenWidth * 0.032,
              fontFamily: 'Pretendard',
              fontWeight: FontWeight.w600,
              height: 1.5,
            ),
          ),
          
          SizedBox(height: screenHeight * 0.02),
          
          _SegmentsVisualization(data: data),
          
          SizedBox(height: screenHeight * 0.015),
          
          _SegmentLegend(data: data),
          
          SizedBox(height: screenHeight * 0.025),
          
          _AnalysisResultText(data: data),
          
          SizedBox(height: screenHeight * 0.03),
          
          Text(
            _getAudioAnalysisRecommendation(),
            textAlign: TextAlign.center,
            style: TextStyle(
              color: const Color(0xFF777777),
              fontSize: screenWidth * 0.03,
              fontFamily: 'Pretendard',
              fontWeight: FontWeight.w500,
              height: 1.4,
            ),
          ),
        ],
      ),
    );
  }
  
  String _getAudioAnalysisRecommendation() {
    if (audioAnalysisDataList == null || audioAnalysisDataList!.isEmpty) {
      return '음성 분석 데이터를 불러오는 중입니다...';
    }
    
    // 첫 번째 데이터의 위험도를 기준으로 추천사항 제공
    switch (audioAnalysisDataList!.first.riskLevel) {
      case 'risk':
        return '대화 음성에서 인지 저하 신호가 다수 관찰되었습니다.\n전문가의 정확한 진단을 받아보시기를 권장합니다.';
      case 'suspect':
        return '대화 음성에서 인지 저하 신호가 일부 관찰되었습니다.\n단기적인 현상일 수 있으므로 정기적인 체크를 권장드립니다.';
      case 'normal':
      default:
        return '대화 음성이 정상 범위 내에 있습니다.\n현재 상태를 유지하시되, 정기적인 확인을 권장합니다.';
    }
  }
}

// Language Analysis Card Component
class _LanguageAnalysisCard extends StatelessWidget {
  final HealthAnalysisData data;

  const _LanguageAnalysisCard({required this.data});

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      margin: const EdgeInsets.symmetric(horizontal: 20),
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: AppColors.cardBackground,
        borderRadius: BorderRadius.circular(13),
        boxShadow: const [
          BoxShadow(
            color: Color(0x19000000),
            blurRadius: 5,
            offset: Offset(0, 2),
          ),
        ],
      ),
      child: Column(
        children: [
          Text(
            '발화 언어 분석',
            style: AppTextStyles.cardTitle,
          ),
          const SizedBox(height: 16),
          Text(
            '발화의 언어적인 특성을 분석해 연령대별 평균과\n통계적인 사용자의 위치를 나타냅니다.\n연령대별 평균은 절대적인 판정 기준이 아님을 유의해주세요.',
            textAlign: TextAlign.center,
            style: AppTextStyles.smallText,
          ),
          const SizedBox(height: 20),
          Text(
            '이번 대화 분석 결과입니다',
            style: AppTextStyles.bodyText,
          ),
          const SizedBox(height: 20),
          _RadarChart(data: data),
          const SizedBox(height: 16),
          Text.rich(
            TextSpan(
              children: [
                TextSpan(
                  text: '${data.ageGroup} 사용자 평균보다 ',
                  style: const TextStyle(
                    color: AppColors.textTertiary,
                    fontSize: 13,
                    fontFamily: 'Pretendard',
                    fontWeight: FontWeight.w700,
                  ),
                ),
                TextSpan(
                  text: data.isAboveAverage ? '높은 점수' : '낮은 점수',
                  style: TextStyle(
                    color: data.isAboveAverage ? AppColors.accentGreen : AppColors.accentRed,
                    fontSize: 13,
                    fontFamily: 'Pretendard',
                    fontWeight: FontWeight.w700,
                  ),
                ),
                const TextSpan(
                  text: '입니다',
                  style: TextStyle(
                    color: Colors.black,
                    fontSize: 13,
                    fontFamily: 'Pretendard',
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ],
            ),
            textAlign: TextAlign.center,
          ),
          const SizedBox(height: 16),
          Text(
            '언어 분석에서 인지 저하 신호가 일부 관찰되었습니다.\n단기적인 현상일 수 있으므로 정기적인 체크를 권장드립니다. 필요 시 정확한 전문가 진단을 받아보세요.',
            textAlign: TextAlign.center,
            style: AppTextStyles.smallText,
          ),
        ],
      ),
    );
  }
}

// Segments Visualization Component
class _SegmentsVisualization extends StatelessWidget {
  final HealthAnalysisData data;

  const _SegmentsVisualization({required this.data});

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      height: 27,
      child: Row(
        mainAxisAlignment: MainAxisAlignment.center,
        children: List.generate(10, (index) {
          Color segmentColor;
          // 정상 구간과 위험 구간 계산 (10개 시각화 기준)
          final visualSlices = 10;
          final visualDementiaSlices = (data.dementiaRatio * visualSlices).round();
          final normalSlices = visualSlices - visualDementiaSlices;
          
          if (index < normalSlices) {
            segmentColor = AppColors.normalSegment; // 정상 (녹색)
          } else {
            segmentColor = AppColors.riskSegment; // 위험 (빨간색)
          }
          
          return Container(
            width: 18.84,
            height: 26.74,
            margin: EdgeInsets.symmetric(horizontal: 1),
            decoration: BoxDecoration(
              color: segmentColor,
              borderRadius: BorderRadius.circular(3),
              boxShadow: const [
                BoxShadow(
                  color: Color(0x19000000),
                  blurRadius: 5,
                  offset: Offset(0, 2),
                ),
              ],
            ),
          );
        }),
      ),
    );
  }
}

class _SegmentLegend extends StatelessWidget {
  final HealthAnalysisData data;
  
  const _SegmentLegend({required this.data});

  @override
  Widget build(BuildContext context) {
    // 정상 구간과 위험 구간의 비율 계산 (10개 시각화 기준)
    final visualSlices = 10;
    final visualDementiaSlices = (data.dementiaRatio * visualSlices).round();
    final normalSlices = visualSlices - visualDementiaSlices;
    
    return Row(
      mainAxisAlignment: MainAxisAlignment.center,
      children: [
        // 정상 구간의 중앙에 "정상" 레이블 배치
        if (normalSlices > 0)
          Expanded(
            flex: normalSlices,
            child: Center(
              child: Text(
                '정상',
                style: TextStyle(
                  color: AppColors.normalSegment,
                  fontSize: 12,
                  fontFamily: 'Pretendard',
                  fontWeight: FontWeight.w800,
                  height: 1.5,
                ),
              ),
            ),
          ),
        // 위험 구간의 중앙에 "의심" 레이블 배치  
        if (visualDementiaSlices > 0)
          Expanded(
            flex: visualDementiaSlices,
            child: Center(
              child: Text(
                '의심',
                style: TextStyle(
                  color: AppColors.riskSegment,
                  fontSize: 12,
                  fontFamily: 'Pretendard',
                  fontWeight: FontWeight.w800,
                  height: 1.5,
                ),
              ),
            ),
          ),
      ],
    );
  }
}

class _AnalysisResultText extends StatelessWidget {
  final HealthAnalysisData data;

  const _AnalysisResultText({required this.data});

  @override
  Widget build(BuildContext context) {
    return Text.rich(
      TextSpan(
        children: [
          TextSpan(
            text: '총 ${data.totalSegments}개 구간 중 ',
            style: const TextStyle(
              color: AppColors.textTertiary,
              fontSize: 13,
              fontFamily: 'Pretendard',
              fontWeight: FontWeight.w700,
              height: 1.46,
            ),
          ),
          TextSpan(
            text: '${data.dementiaSegmentsCount}개',
            style: const TextStyle(
              color: AppColors.accentRed,
              fontSize: 13,
              fontFamily: 'Pretendard',
              fontWeight: FontWeight.w700,
              height: 1.46,
            ),
          ),
          TextSpan(
            text: ' 구간에서 \n인지장애 징후가 포착되었습니다\n${data.ageGroup} 사용자 ',
            style: const TextStyle(
              color: AppColors.textTertiary,
              fontSize: 13,
              fontFamily: 'Pretendard',
              fontWeight: FontWeight.w700,
              height: 1.46,
            ),
          ),
          TextSpan(
            text: data.comparisonForAnalysis,
            style: TextStyle(
              color: data.isAboveAverage ? AppColors.accentRed : AppColors.accentGreen,
              fontSize: 13,
              fontFamily: 'Pretendard',
              fontWeight: FontWeight.w700,
              height: 1.46,
            ),
          ),
        ],
      ),
      textAlign: TextAlign.center,
    );
  }
}

// Radar Chart Component (Simplified)
class _RadarChart extends StatelessWidget {
  final HealthAnalysisData data;

  const _RadarChart({required this.data});

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: 200,
      height: 200,
      child: Stack(
        alignment: Alignment.center,
        children: [
          // Background circles
          Container(
            width: 180,
            height: 180,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              border: Border.all(color: const Color(0xFFDDDDDD), width: 1),
            ),
          ),
          Container(
            width: 120,
            height: 120,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              border: Border.all(color: const Color(0xFFDDDDDD), width: 1),
            ),
          ),
          Container(
            width: 60,
            height: 60,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              border: Border.all(color: const Color(0xFFDDDDDD), width: 1),
            ),
          ),
          // Axis lines
          Container(
            width: 180,
            height: 1,
            color: const Color(0xFFDDDDDD),
          ),
          Container(
            width: 1,
            height: 180,
            color: const Color(0xFFDDDDDD),
          ),
          // Labels
          Positioned(
            top: 10,
            child: _ChartLabel('평균 발화 길이'),
          ),
          Positioned(
            right: 10,
            child: _ChartLabel('발화 속도'),
          ),
          Positioned(
            bottom: 10,
            child: _ChartLabel('지시어 사용 비율'),
          ),
          Positioned(
            left: 10,
            child: _ChartLabel('어휘 다양성'),
          ),
          // Legend
          Positioned(
            top: 40,
            left: 20,
            child: Row(
              children: [
                Container(
                  width: 12,
                  height: 12,
                  decoration: const BoxDecoration(
                    color: Color(0xFF62BE8A),
                    shape: BoxShape.circle,
                  ),
                ),
                const SizedBox(width: 4),
                Text(
                  '${data.userName}님',
                  style: const TextStyle(
                    color: AppColors.textSecondary,
                    fontSize: 9,
                    fontFamily: 'Pretendard',
                    fontWeight: FontWeight.w500,
                  ),
                ),
              ],
            ),
          ),
          Positioned(
            top: 55,
            left: 20,
            child: Row(
              children: [
                Container(
                  width: 12,
                  height: 12,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    border: Border.all(color: const Color(0xFF62BE8A), width: 2),
                  ),
                ),
                const SizedBox(width: 4),
                Text(
                  '동일 연령대 평균',
                  style: const TextStyle(
                    color: AppColors.textSecondary,
                    fontSize: 9,
                    fontFamily: 'Pretendard',
                    fontWeight: FontWeight.w500,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _ChartLabel extends StatelessWidget {
  final String text;

  const _ChartLabel(this.text);

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: const Color(0xFF62BE8A),
        borderRadius: BorderRadius.circular(16),
      ),
      child: Text(
        text,
        style: const TextStyle(
          color: Colors.white,
          fontSize: 9,
          fontFamily: 'Inter',
          fontWeight: FontWeight.w700,
        ),
      ),
    );
  }
}

// Speech Analysis Card Component with Radar Chart
class _SpeechAnalysisCard extends StatelessWidget {
  final double screenWidth;
  final double screenHeight;
  final HealthAnalysisData data;
  final ReportTextAnalysisData? textAnalysisData;

  const _SpeechAnalysisCard({
    required this.screenWidth,
    required this.screenHeight,
    required this.data,
    this.textAnalysisData,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.symmetric(horizontal: 20),
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: AppColors.cardBackground,
        borderRadius: BorderRadius.circular(13),
        boxShadow: const [
          BoxShadow(
            color: Color(0x19000000),
            blurRadius: 5,
            offset: Offset(0, 2),
          ),
        ],
      ),
      child: Column(
        children: [
          Text(
            '발화 언어 분석',
            style: AppTextStyles.cardTitle,
          ),
          const SizedBox(height: 16),
          Text(
            '발화의 언어적인 특성을 분석해 연령대별 평균과\n통계적인 사용자의 위치를 나타냅니다.\n연령대별 평균은 절대적인 판정 기준이 아님을 유의해주세요.',
            textAlign: TextAlign.center,
            style: AppTextStyles.smallText,
          ),
          const SizedBox(height: 20),
          Text(
            '이번 대화 분석 결과입니다',
            style: AppTextStyles.bodyText,
          ),
          const SizedBox(height: 20),
          if (textAnalysisData != null)
            _DataRadarChart(data: data, textAnalysisData: textAnalysisData!)
          else
            _LoadingOrPlaceholderChart(),
          const SizedBox(height: 16),
          if (textAnalysisData != null)
            Text.rich(
              TextSpan(
                children: [
                  TextSpan(
                    text: '${data.ageGroup} 사용자 평균보다 ',
                    style: const TextStyle(
                      color: AppColors.textTertiary,
                      fontSize: 13,
                      fontFamily: 'Pretendard',
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                  TextSpan(
                    text: _getOverallComparison(),
                    style: TextStyle(
                      color: _isAboveAverage() ? AppColors.accentGreen : AppColors.accentRed,
                      fontSize: 13,
                      fontFamily: 'Pretendard',
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                  const TextSpan(
                    text: '입니다',
                    style: TextStyle(
                      color: Colors.black,
                      fontSize: 13,
                      fontFamily: 'Pretendard',
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                ],
              ),
              textAlign: TextAlign.center,
            )
          else
            Text(
              '텍스트 분석 데이터를 불러오는 중입니다...',
              style: AppTextStyles.smallText,
              textAlign: TextAlign.center,
            ),
          const SizedBox(height: 16),
          Text(
            textAnalysisData != null
              ? '언어 분석에서 인지 저하 신호가 일부 관찰되었습니다.\n단기적인 현상일 수 있으므로 정기적인 체크를 권장드립니다. 필요 시 정확한 전문가 진단을 받아보세요.'
              : '텍스트 분석 결과를 기반으로 상세한 분석을 제공합니다.',
            textAlign: TextAlign.center,
            style: AppTextStyles.smallText,
          ),
        ],
      ),
    );
  }

  bool _isAboveAverage() {
    if (textAnalysisData == null) return false;
    return textAnalysisData!.isAboveAverageForAgeGroup(data.ageGroup);
  }

  String _getOverallComparison() {
    return _isAboveAverage() ? '높은 점수' : '낮은 점수';
  }
}

// Data-driven Radar Chart Component
class _DataRadarChart extends StatelessWidget {
  final HealthAnalysisData data;
  final ReportTextAnalysisData textAnalysisData;

  const _DataRadarChart({
    required this.data,
    required this.textAnalysisData,
  });

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: 300,
      height: 300,
      child: CustomPaint(
        painter: DataRadarChartPainter(
          lexicalDiversity: textAnalysisData.lexicalDiversity,
          mlu: textAnalysisData.mlu,
          demonstrativeRatio: textAnalysisData.demonstrativeRatio,
          speechRate: textAnalysisData.speechRate,
          ageGroup: data.ageGroup,
        ),
        child: Stack(
          alignment: Alignment.center,
          children: [
            // Labels positioned around the chart
            Positioned(
              top: 20,
              child: _ChartLabel('어휘 다양성'),
            ),
            Positioned(
              right: 20,
              child: _ChartLabel('평균 발화 길이'),
            ),
            Positioned(
              bottom: 20,
              child: _ChartLabel('지시어 사용 비율'),
            ),
            Positioned(
              left: 20,
              child: _ChartLabel('발화 속도'),
            ),
            // Legend
            Positioned(
              top: 50,
              left: 30,
              child: Row(
                children: [
                  Container(
                    width: 12,
                    height: 12,
                    decoration: const BoxDecoration(
                      color: Color(0xFF62BE8A),
                      shape: BoxShape.circle,
                    ),
                  ),
                  const SizedBox(width: 4),
                  Text(
                    '${data.userName}님',
                    style: const TextStyle(
                      color: AppColors.textSecondary,
                      fontSize: 9,
                      fontFamily: 'Pretendard',
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                ],
              ),
            ),
            Positioned(
              top: 65,
              left: 30,
              child: Row(
                children: [
                  Container(
                    width: 12,
                    height: 12,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      border: Border.all(color: const Color(0xFF62BE8A), width: 2),
                    ),
                  ),
                  const SizedBox(width: 4),
                  Text(
                    '동일 연령대 평균',
                    style: const TextStyle(
                      color: AppColors.textSecondary,
                      fontSize: 9,
                      fontFamily: 'Pretendard',
                      fontWeight: FontWeight.w500,
                    ),
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

// Loading placeholder for chart
class _LoadingOrPlaceholderChart extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Container(
      width: 240,
      height: 240,
      decoration: BoxDecoration(
        shape: BoxShape.circle,
        border: Border.all(color: const Color(0xFFDDDDDD), width: 2),
      ),
      child: const Center(
        child: CircularProgressIndicator(
          color: Color(0xFF62BE8A),
        ),
      ),
    );
  }
}

// Custom Painter for Data-driven Radar Chart
class DataRadarChartPainter extends CustomPainter {
  final double lexicalDiversity;
  final double mlu;
  final double demonstrativeRatio;
  final double speechRate;
  final String? ageGroup;

  DataRadarChartPainter({
    required this.lexicalDiversity,
    required this.mlu,
    required this.demonstrativeRatio,
    required this.speechRate,
    this.ageGroup,
  });

  @override
  void paint(Canvas canvas, Size size) {
    final center = Offset(size.width / 2, size.height / 2);
    final radius = size.width / 2 - 40;
    
    final paint = Paint()
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1
      ..color = const Color(0xFFDDDDDD);

    // Draw background circles
    for (int i = 1; i <= 3; i++) {
      canvas.drawCircle(center, radius * i / 3, paint);
    }

    // Draw axis lines
    final axisAngles = [0, 90, 180, 270]; // degrees
    for (final angle in axisAngles) {
      final radian = angle * 3.14159 / 180;
      final end = Offset(
        center.dx + radius * cos(radian),
        center.dy + radius * sin(radian),
      );
      canvas.drawLine(center, end, paint);
    }

    // Get age group averages for comparison
    final averages = ReportTextAnalysisData.ageGroupAverages[ageGroup ?? '60대'] ?? ReportTextAnalysisData.ageGroupAverages['60대']!;
    
    // Normalize values to 0-1 range for visualization
    final normalizedValues = [
      _normalizeValue(lexicalDiversity, 0.0, 1.0),      // Top
      _normalizeValue(mlu, 0.0, 20.0),                  // Right  
      _normalizeValue(demonstrativeRatio, 0.0, 1.0),    // Bottom
      _normalizeValue(speechRate, 0.0, 5.0),            // Left
    ];

    // Normalize average values
    final normalizedAverages = [
      _normalizeValue(averages['lexicalDiversity']!, 0.0, 1.0),
      _normalizeValue(averages['mlu']!, 0.0, 20.0),
      _normalizeValue(averages['demonstrativeRatio']!, 0.0, 1.0),
      _normalizeValue(averages['speechRate']!, 0.0, 5.0),
    ];

    // Draw user data polygon
    final userPath = Path();
    final userPaint = Paint()
      ..color = const Color(0xFF62BE8A).withOpacity(0.3)
      ..style = PaintingStyle.fill;

    final userStrokePaint = Paint()
      ..color = const Color(0xFF62BE8A)
      ..style = PaintingStyle.stroke
      ..strokeWidth = 2;

    for (int i = 0; i < normalizedValues.length; i++) {
      final angle = (i * 90 - 90) * 3.14159 / 180; // Start from top, go clockwise
      final value = normalizedValues[i];
      final point = Offset(
        center.dx + radius * value * cos(angle),
        center.dy + radius * value * sin(angle),
      );
      
      if (i == 0) {
        userPath.moveTo(point.dx, point.dy);
      } else {
        userPath.lineTo(point.dx, point.dy);
      }
      
      // Draw data points
      canvas.drawCircle(point, 4, Paint()..color = const Color(0xFF62BE8A));
    }
    userPath.close();

    canvas.drawPath(userPath, userPaint);
    canvas.drawPath(userPath, userStrokePaint);

    // Draw average reference using actual age group averages
    final avgPath = Path();
    final avgPaint = Paint()
      ..color = const Color(0xFF62BE8A)
      ..style = PaintingStyle.stroke
      ..strokeWidth = 2
      ..strokeCap = StrokeCap.round;

    for (int i = 0; i < normalizedAverages.length; i++) {
      final angle = (i * 90 - 90) * 3.14159 / 180;
      final value = normalizedAverages[i];
      final point = Offset(
        center.dx + radius * value * cos(angle),
        center.dy + radius * value * sin(angle),
      );
      
      if (i == 0) {
        avgPath.moveTo(point.dx, point.dy);
      } else {
        avgPath.lineTo(point.dx, point.dy);
      }
      
      // Draw hollow circles for average
      canvas.drawCircle(point, 4, Paint()
        ..color = Colors.white
        ..style = PaintingStyle.fill);
      canvas.drawCircle(point, 4, Paint()
        ..color = const Color(0xFF62BE8A)
        ..style = PaintingStyle.stroke
        ..strokeWidth = 2);
    }
    avgPath.close();
    canvas.drawPath(avgPath, avgPaint);
  }

  double _normalizeValue(double value, double min, double max) {
    return ((value - min) / (max - min)).clamp(0.0, 1.0);
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => true;
}

class RadarGridPainter extends CustomPainter {
  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..color = const Color(0xFFDDDDDD)
      ..strokeWidth = 1
      ..style = PaintingStyle.stroke;

    final center = Offset(size.width / 2, size.height / 2);
    final radius = size.width / 2;

    // 4개 축 그리기 (상, 하, 좌, 우)
    // 세로 축
    canvas.drawLine(
      Offset(center.dx, 0),
      Offset(center.dx, size.height),
      paint,
    );

    // 가로 축
    canvas.drawLine(Offset(0, center.dy), Offset(size.width, center.dy), paint);
  }

  @override
  bool shouldRepaint(CustomPainter oldDelegate) => false;
}

class DataDiamondPainter extends CustomPainter {
  final Map<String, double> values;
  final Color color;
  final bool isUser;

  DataDiamondPainter({
    required this.values,
    required this.color,
    required this.isUser,
  });

  @override
  void paint(Canvas canvas, Size size) {
    final center = Offset(size.width / 2, size.height / 2);
    final maxRadius = size.width / 2 * 0.6; // 가장 바깥 원까지 도달하도록 반지름 조정

    // 4개 축의 좌표 계산
    final topPoint = Offset(
      center.dx,
      center.dy - (values['vocabulary']! * maxRadius),
    );
    final rightPoint = Offset(
      center.dx + (values['pronouns']! * maxRadius),
      center.dy,
    );
    final bottomPoint = Offset(
      center.dx,
      center.dy + (values['speed']! * maxRadius),
    );
    final leftPoint = Offset(
      center.dx - (values['length']! * maxRadius),
      center.dy,
    );

    // 다이아몬드 그리기
    final path = Path()
      ..moveTo(topPoint.dx, topPoint.dy)
      ..lineTo(rightPoint.dx, rightPoint.dy)
      ..lineTo(bottomPoint.dx, bottomPoint.dy)
      ..lineTo(leftPoint.dx, leftPoint.dy)
      ..close();

    // 채워진 다이아몬드 (반투명)
    final fillPaint = Paint()
      ..color = color.withOpacity(0.3)
      ..style = PaintingStyle.fill;
    canvas.drawPath(path, fillPaint);

    // 다이아몬드 테두리
    final strokePaint = Paint()
      ..color = color
      ..strokeWidth = 2
      ..style = PaintingStyle.stroke;
    canvas.drawPath(path, strokePaint);

    // 데이터 포인트 그리기 (마름모꼴)
    final pointPaint = Paint()
      ..color = color
      ..style = PaintingStyle.fill;

    final pointSize = 8.0;
    _drawDiamond(canvas, topPoint, pointSize, pointPaint);
    _drawDiamond(canvas, rightPoint, pointSize, pointPaint);
    _drawDiamond(canvas, bottomPoint, pointSize, pointPaint);
    _drawDiamond(canvas, leftPoint, pointSize, pointPaint);
  }

  void _drawDiamond(Canvas canvas, Offset center, double size, Paint paint) {
    final halfSize = size / 2;
    final path = Path()
      ..moveTo(center.dx, center.dy - halfSize) // 위
      ..lineTo(center.dx + halfSize, center.dy) // 오른쪽
      ..lineTo(center.dx, center.dy + halfSize) // 아래
      ..lineTo(center.dx - halfSize, center.dy) // 왼쪽
      ..close();

    canvas.drawPath(path, paint);
  }

  @override
  bool shouldRepaint(CustomPainter oldDelegate) => false;
}

Widget DetailSpeechSummary(double screenWidth) {
  return Column(
    children: [
      Container(
        width: 220,
        height: 170,
        child: Stack(
          children: [
            Positioned(
              left: 0,
              top: 0,
              child: Container(
                width: 127.83,
                height: 179,
                decoration: ShapeDecoration(
                  color: const Color(0xFF9BDDB8),
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(13),
                  ),
                  shadows: [
                    BoxShadow(
                      color: Color(0x19000000),
                      blurRadius: 5,
                      offset: Offset(0, 2),
                      spreadRadius: 0,
                    ),
                  ],
                ),
              ),
            ),
            Positioned(
              left: 11,
              top: 120,
              child: SizedBox(
                width: 107,
                height: 45,
                child: Text.rich(
                  TextSpan(
                    children: [
                      TextSpan(
                        text: '서봉봉님, 이번 대화에서\n ',
                        style: TextStyle(
                          color: Colors.white,
                          fontSize: 11,
                          fontFamily: 'Pretendard',
                          fontWeight: FontWeight.w700,
                          shadows: [
                            Shadow(
                              offset: Offset(0, 1),
                              blurRadius: 5,
                              color: Color(0xFFCFCFCF).withOpacity(0.30),
                            ),
                          ],
                        ),
                      ),
                      TextSpan(
                        text: '60대 평균보다\n',
                        style: TextStyle(
                          color: const Color(0xFF777777),
                          fontSize: 11,
                          fontFamily: 'Pretendard',
                          fontWeight: FontWeight.w700,
                          shadows: [
                            Shadow(
                              offset: Offset(0, 1),
                              blurRadius: 5,
                              color: Color(0xFFCFCFCF).withOpacity(0.30),
                            ),
                          ],
                        ),
                      ),
                      TextSpan(
                        text: '낮게 나왔어요\n',
                        style: TextStyle(
                          color: const Color(0xFFF45C5C),
                          fontSize: 11,
                          fontFamily: 'Pretendard',
                          fontWeight: FontWeight.w700,
                          shadows: [
                            Shadow(
                              offset: Offset(0, 1),
                              blurRadius: 5,
                              color: Color(0xFFCFCFCF).withOpacity(0.30),
                            ),
                          ],
                        ),
                      ),
                    ],
                  ),
                  textAlign: TextAlign.center,
                ),
              ),
            ),
            Positioned(
              left: 14,
              top: 9,
              child: SizedBox(
                width: 98.08,
                height: 30.32,
                child: Text(
                  'AI 음성 분석 요약',
                  textAlign: TextAlign.center,
                  style: TextStyle(
                    color: Colors.white,
                    fontSize: 14,
                    fontFamily: 'Pretendard',
                    fontWeight: FontWeight.w800,
                  ),
                ),
              ),
            ),
            Positioned(
              left: 138,
              top: 0,
              child: Container(
                width: 127.83,
                height: 179,
                decoration: ShapeDecoration(
                  color: const Color(0xFF9BDDB8),
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(13),
                  ),
                  shadows: [
                    BoxShadow(
                      color: Color(0x19000000),
                      blurRadius: 5,
                      offset: Offset(0, 2),
                      spreadRadius: 0,
                    ),
                  ],
                ),
              ),
            ),
            Positioned(
              left: 148,
              top: 9,
              child: SizedBox(
                width: 109,
                height: 30,
                child: Text(
                  '발화 언어 분석 요약',
                  textAlign: TextAlign.center,
                  style: TextStyle(
                    color: Colors.white,
                    fontSize: 14,
                    fontFamily: 'Pretendard',
                    fontWeight: FontWeight.w800,
                  ),
                ),
              ),
            ),
            Positioned(
              left: 148,
              top: 120,
              child: SizedBox(
                width: 109,
                height: 45,
                child: Text.rich(
                  TextSpan(
                    children: [
                      TextSpan(
                        text: '서봉봉님, 이번 대화에서\n',
                        style: TextStyle(
                          color: Colors.white,
                          fontSize: 11,
                          fontFamily: 'Pretendard',
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                      TextSpan(
                        text: '60대 평균보다\n',
                        style: TextStyle(
                          color: const Color(0xFF777777),
                          fontSize: 11,
                          fontFamily: 'Pretendard',
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                      TextSpan(
                        text: '낮게 나왔어요',
                        style: TextStyle(
                          color: const Color(0xFFF45C5C),
                          fontSize: 11,
                          fontFamily: 'Pretendard',
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                    ],
                  ),
                  textAlign: TextAlign.center,
                ),
              ),
            ),
            Positioned(
              left: 175,
              top: 41,
              child: Container(
                width: 56,
                height: 56,
                decoration: BoxDecoration(
                  color: Colors.white,
                  borderRadius: BorderRadius.circular(8),
                  boxShadow: [
                    BoxShadow(
                      color: Color(0x19000000),
                      blurRadius: 4,
                      offset: Offset(0, 2),
                      spreadRadius: 0,
                    ),
                  ],
                ),
                child: Icon(
                  Icons.record_voice_over,
                  color: Color(0xFF7CD0A0),
                  size: 32,
                ),
              ),
            ),
            Positioned(
              left: 38,
              top: 46,
              child: Container(
                width: 51,
                height: 51,
                decoration: BoxDecoration(
                  color: Colors.white,
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Icon(
                  Icons.mic,
                  color: Color(0xFF7CD0A0),
                  size: 28,
                ),
              ),
            ),
          ],
        ),
      ),
    ],
  );
}

class SpeechAnalysisCard extends StatelessWidget {
  final double screenWidth;
  final double screenHeight;
  final String? ageGroup;
  final ReportTextAnalysisData? textAnalysisData;
  final Widget Function(double) buildRadarChart;
  final Widget Function(double) buildLegend;

  const SpeechAnalysisCard({
    super.key,
    required this.screenWidth,
    required this.screenHeight,
    this.ageGroup,
    this.textAnalysisData,
    required this.buildRadarChart,
    required this.buildLegend,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: EdgeInsets.symmetric(vertical: screenWidth * 0.07),
      decoration: BoxDecoration(
        color: const Color(0xFFE2F6EB),
        borderRadius: BorderRadius.circular(13),
        boxShadow: [
          BoxShadow(
            color: const Color(0x19000000),
            blurRadius: 5,
            offset: const Offset(0, 2),
          ),
        ],
      ),
      child: Column(
        children: [
          // 제목
          Text(
            '발화 언어 분석',
            textAlign: TextAlign.center,
            style: TextStyle(
              color: const Color(0xFF111111),
              fontSize: screenWidth * 0.052,
              fontFamily: 'Pretendard',
              fontWeight: FontWeight.w700,
            ),
          ),

          SizedBox(height: screenHeight * 0.015),

          // 설명 텍스트
          Text(
            '발화의 언어적인 특성을 분석해 연령대별 평균과\n통계적인 사용자의 위치를 나타냅니다.\n연령대별 평균은 절대적인 판정 기준이 아님을 유의해주세요.',
            textAlign: TextAlign.center,
            style: TextStyle(
              color: const Color(0xFF777777),
              fontSize: screenWidth * 0.026,
              fontFamily: 'Pretendard',
              fontWeight: FontWeight.w500,
              height: 1.4,
            ),
          ),

          // 방사형 차트 영역
          buildRadarChart(screenWidth),

          // 범례
          buildLegend(screenWidth),

          SizedBox(height: screenHeight * 0.035),

          // 결과 텍스트
          RichText(
            textAlign: TextAlign.center,
            text: TextSpan(
              children: [
                TextSpan(
                  text: '${ageGroup ?? '연령대'} 사용자 평균보다 ',
                  style: TextStyle(
                    color: const Color(0xFF111111),
                    fontSize: screenWidth * 0.034,
                    fontFamily: 'Pretendard',
                    fontWeight: FontWeight.w600,
                  ),
                ),
                TextSpan(
                  text: '낮은 점수',
                  style: TextStyle(
                    color: const Color(0xFFF45B5B),
                    fontSize: screenWidth * 0.034,
                    fontFamily: 'Pretendard',
                    fontWeight: FontWeight.w800,
                  ),
                ),
                TextSpan(
                  text: '입니다',
                  style: TextStyle(
                    color: Colors.black,
                    fontSize: screenWidth * 0.034,
                    fontFamily: 'Pretendard',
                    fontWeight: FontWeight.w800,
                  ),
                ),
              ],
            ),
          ),
          SizedBox(height: screenHeight * 0.03),
          Text(
            '언어 분석에서 인지 저하 신호가 일부 관찰되었습니다.\n단기적인 현상일 수 있으므로 정기적인 체크를 권장드립니다.\n필요 시 정확한 전문가 진단을 받아보세요.',
            textAlign: TextAlign.center,
            style: TextStyle(
              color: const Color(0xFF777777),
              fontSize: screenWidth * 0.03,
              fontFamily: 'Pretendard',
              fontWeight: FontWeight.w500,
              height: 1.4,
            ),
          ),
        ],
      ),
    );
  }
}