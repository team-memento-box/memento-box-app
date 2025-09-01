import 'package:flutter/material.dart';
import 'dart:math';
import '../services/dementia_analysis_service.dart';
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
      return '더 좋은 결과';
    } else {
      return '주의가 필요함';
    }
  }

  String get comparisonForAnalysis {
    if (isAboveAverage) {
      return '평균보다 낮은 위험도를 보였습니다';
    } else {
      return '평균보다 높은 위험도를 보였습니다';
    }
  }
}

// Main Screen
class ConversationHealthAnalysisScreen extends StatefulWidget {
  final HealthAnalysisData? initialData;
  final Report? reportData;
  final String? sessionId;

  const ConversationHealthAnalysisScreen({
    super.key,
    this.initialData,
    this.reportData,
    this.sessionId,
  });

  @override
  State<ConversationHealthAnalysisScreen> createState() => _ConversationHealthAnalysisScreenState();
}

class _ConversationHealthAnalysisScreenState extends State<ConversationHealthAnalysisScreen> {
  HealthAnalysisData? data;
  ReportTextAnalysisData? textAnalysisData;
  ReportAudioAnalysisData? audioAnalysisData;
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
    if (widget.sessionId != null || widget.reportData?.sessionId != null) {
      setState(() => isLoading = true);
      try {
        final sessionId = widget.sessionId ?? widget.reportData!.sessionId;
        
        // 병렬로 텍스트 분석과 음성 분석 데이터 로드
        final results = await Future.wait([
          ReportTextAnalysisApi.fetchTextAnalysisData(sessionId),
          ReportAudioAnalysisApi.fetchAudioAnalysisData(sessionId),
        ]);
        
        setState(() {
          textAnalysisData = results[0] as ReportTextAnalysisData?;
          audioAnalysisData = results[1] as ReportAudioAnalysisData?;
          
          // 음성 분석 데이터가 있으면 HealthAnalysisData 업데이트
          if (audioAnalysisData != null) {
            data = HealthAnalysisData(
              totalSegments: audioAnalysisData!.totalSlices,
              dementiaSegmentsCount: audioAnalysisData!.dementiaSlices,
              dementiaRatio: audioAnalysisData!.dementiaRatio,
              aiVoiceScore: data?.aiVoiceScore ?? 66,
              speechContentScore: data?.speechContentScore ?? 65,
              userName: widget.reportData?.userName ?? data?.userName ?? "사용자",
              ageGroup: widget.reportData?.ageGroup ?? data?.ageGroup ?? "60대",
              ageGroupAverageRatio: 0.3, // TODO: 연령대별 평균 데이터 필요
            );
          }
          
          isLoading = false;
        });
      } catch (e) {
        print('❌ Error loading analysis data: $e');
        setState(() => isLoading = false);
      }
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
            // 날짜 정보
            Text(
              widget.reportData?.formattedDate ?? '2025-05-26 13:56',
              style: TextStyle(
                color: const Color(0xFF777777),
                fontSize: screenWidth * 0.032,
                fontFamily: 'Pretendard',
                fontWeight: FontWeight.w600,
              ),
            ),
            SizedBox(height: screenHeight * 0.02),
            
            // 요약 카드들
            _DetailSpeechSummary(screenWidth, data!),
            SizedBox(height: screenHeight * 0.03),
            
            // AI 음성 분석 카드
            _AIVoiceAnalysisCard(
              data: data!,
              audioAnalysisData: audioAnalysisData,
              screenWidth: screenWidth,
              screenHeight: screenHeight,
            ),
            SizedBox(height: screenHeight * 0.03),
            
            // 발화 언어 분석 카드
            _SpeechAnalysisCard(
              screenWidth: screenWidth,
              screenHeight: screenHeight,
              data: data!,
              textAnalysisData: textAnalysisData,
            ),
            
            SizedBox(height: screenHeight * 0.1),
          ],
        ),
      ),
      bottomNavigationBar: const CustomBottomNavBar(currentIndex: 3),
    );
  }
}

// Detail Speech Summary Component
Widget _DetailSpeechSummary(double screenWidth, HealthAnalysisData data) {
  return Container(
    width: 265.83,
    height: 209,
    child: Stack(
      children: [
        // AI 음성 분석 요약 카드
        Positioned(
          left: 0,
          top: 0,
          child: Container(
            width: 127.83,
            height: 179,
            decoration: ShapeDecoration(
              color: const Color(0xFF7CD0A0),
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
              padding: const EdgeInsets.all(14),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.center,
                children: [
                  Text(
                    'AI 음성 분석 요약',
                    textAlign: TextAlign.center,
                    style: TextStyle(
                      color: Colors.white,
                      fontSize: 14,
                      fontFamily: 'Pretendard',
                      fontWeight: FontWeight.w800,
                    ),
                  ),
                  const Spacer(),
                  Container(
                    width: 51,
                    height: 51,
                    decoration: BoxDecoration(
                      image: DecorationImage(
                        image: NetworkImage("https://placehold.co/51x51"),
                        fit: BoxFit.contain,
                      ),
                    ),
                  ),
                  const Spacer(),
                  Text.rich(
                    TextSpan(
                      children: [
                        TextSpan(
                          text: '${data.userName}님, 이번 대화에서\n',
                          style: TextStyle(
                            color: Colors.white,
                            fontSize: 11,
                            fontFamily: 'Pretendard',
                            fontWeight: FontWeight.w700,
                          ),
                        ),
                        TextSpan(
                          text: '${data.ageGroup} 평균보다\n',
                          style: TextStyle(
                            color: const Color(0xFF777777),
                            fontSize: 11,
                            fontFamily: 'Pretendard',
                            fontWeight: FontWeight.w700,
                          ),
                        ),
                        TextSpan(
                          text: data.comparisonText,
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
                ],
              ),
            ),
          ),
        ),
        
        // 발화 언어 분석 요약 카드
        Positioned(
          left: 138,
          top: 0,
          child: Container(
            width: 127.83,
            height: 179,
            decoration: ShapeDecoration(
              color: const Color(0xFF7CD0A0),
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
              padding: const EdgeInsets.all(14),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.center,
                children: [
                  Text(
                    '발화 언어 분석 요약',
                    textAlign: TextAlign.center,
                    style: TextStyle(
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
                      image: DecorationImage(
                        image: NetworkImage("https://placehold.co/56x56"),
                        fit: BoxFit.contain,
                      ),
                      boxShadow: [
                        BoxShadow(
                          color: Color(0x19000000),
                          blurRadius: 4,
                          offset: Offset(0, 2),
                          spreadRadius: 0,
                        ),
                      ],
                    ),
                  ),
                  const Spacer(),
                  Text.rich(
                    TextSpan(
                      children: [
                        TextSpan(
                          text: '${data.userName}님, 이번 대화에서\n',
                          style: TextStyle(
                            color: Colors.white,
                            fontSize: 11,
                            fontFamily: 'Pretendard',
                            fontWeight: FontWeight.w700,
                          ),
                        ),
                        TextSpan(
                          text: '${data.ageGroup} 평균보다\n',
                          style: TextStyle(
                            color: const Color(0xFF777777),
                            fontSize: 11,
                            fontFamily: 'Pretendard',
                            fontWeight: FontWeight.w700,
                          ),
                        ),
                        TextSpan(
                          text: data.comparisonText,
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
  final ReportAudioAnalysisData? audioAnalysisData;
  final double screenWidth;
  final double screenHeight;

  const _AIVoiceAnalysisCard({
    required this.data,
    this.audioAnalysisData,
    required this.screenWidth,
    required this.screenHeight,
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
            'AI 음성 분석',
            style: AppTextStyles.cardTitle,
          ),
          const SizedBox(height: 16),
          Text(
            '대화 음성의 특성을 분석해 인지 저하 징후를 탐지 합니다.\n전체 대화 중 의심 구간이 비율이 높을수록\n인지 저하의 가능성이 높습니다.',
            textAlign: TextAlign.center,
            style: AppTextStyles.smallText,
          ),
          const SizedBox(height: 20),
          Text(
            '이번 대화 분석 결과입니다',
            style: AppTextStyles.bodyText,
          ),
          const SizedBox(height: 16),
          _SegmentsVisualization(data: data),
          const SizedBox(height: 12),
          const _SegmentLegend(),
          const SizedBox(height: 16),
          _AnalysisResultText(data: audioAnalysisData != null ? 
            HealthAnalysisData(
              totalSegments: audioAnalysisData!.totalSlices,
              dementiaSegmentsCount: audioAnalysisData!.dementiaSlices,
              dementiaRatio: audioAnalysisData!.dementiaRatio,
              aiVoiceScore: data.aiVoiceScore,
              speechContentScore: data.speechContentScore,
              userName: data.userName,
              ageGroup: data.ageGroup,
              ageGroupAverageRatio: data.ageGroupAverageRatio,
            ) : data),
          const SizedBox(height: 16),
          Text(
            _getAudioAnalysisRecommendation(),
            textAlign: TextAlign.center,
            style: AppTextStyles.smallText,
          ),
        ],
      ),
    );
  }
  
  String _getAudioAnalysisRecommendation() {
    if (audioAnalysisData == null) {
      return '음성 분석 데이터를 불러오는 중입니다...';
    }
    
    switch (audioAnalysisData!.riskLevel) {
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
        mainAxisAlignment: MainAxisAlignment.spaceEvenly,
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
  const _SegmentLegend();

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceEvenly,
      children: [
        Text(
          '정상',
          style: TextStyle(
            color: AppColors.normalSegment,
            fontSize: 12,
            fontFamily: 'Pretendard',
            fontWeight: FontWeight.w800,
            height: 1.5,
          ),
        ),
        Text(
          '위험',
          style: TextStyle(
            color: AppColors.riskSegment,
            fontSize: 12,
            fontFamily: 'Pretendard',
            fontWeight: FontWeight.w800,
            height: 1.5,
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
          const TextSpan(
            text: '입니다',
            style: TextStyle(
              color: AppColors.textTertiary,
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
    // 간단한 평균 비교 로직 (실제로는 더 복잡한 로직 필요)
    return textAnalysisData!.lexicalDiversity > 0.6 && 
           textAnalysisData!.mlu > 8.0;
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
      width: 240,
      height: 240,
      child: CustomPaint(
        painter: DataRadarChartPainter(
          lexicalDiversity: textAnalysisData.lexicalDiversity,
          mlu: textAnalysisData.mlu,
          demonstrativeRatio: textAnalysisData.demonstrativeRatio,
          speechRate: textAnalysisData.speechRate,
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

  DataRadarChartPainter({
    required this.lexicalDiversity,
    required this.mlu,
    required this.demonstrativeRatio,
    required this.speechRate,
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

    // Normalize values to 0-1 range for visualization
    final normalizedValues = [
      _normalizeValue(lexicalDiversity, 0.0, 1.0),      // Top
      _normalizeValue(mlu, 0.0, 20.0),                  // Right  
      _normalizeValue(demonstrativeRatio, 0.0, 1.0),    // Bottom
      _normalizeValue(speechRate, 0.0, 5.0),            // Left
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

    // Draw average reference (simplified - could be actual age group averages)
    final avgValues = [0.5, 0.5, 0.5, 0.5]; // Placeholder average values
    final avgPath = Path();
    final avgPaint = Paint()
      ..color = const Color(0xFF62BE8A)
      ..style = PaintingStyle.stroke
      ..strokeWidth = 2
      ..strokeCap = StrokeCap.round;

    for (int i = 0; i < avgValues.length; i++) {
      final angle = (i * 90 - 90) * 3.14159 / 180;
      final value = avgValues[i];
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