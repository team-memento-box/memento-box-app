import 'package:flutter/material.dart';
import '../services/dementia_analysis_service.dart';

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

// Main Screen
class ConversationHealthAnalysisScreen extends StatelessWidget {
  final HealthAnalysisData data;

  const ConversationHealthAnalysisScreen({
    Key? key,
    HealthAnalysisData? data,
  }) : data = data ?? const HealthAnalysisData(
         totalSegments: 20,
         dementiaSegmentsCount: 8,
         dementiaRatio: 0.4,
         aiVoiceScore: 66,
         speechContentScore: 65,
         userName: "서봉봉",
         ageGroup: "60대",
         ageGroupAverageRatio: 0.3,
       ), super(key: key);

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.background,
      body: SafeArea(
        child: Column(
          children: [
            _Header(data: data),
            Expanded(
              child: SingleChildScrollView(
                child: Column(
                  children: [
                    const SizedBox(height: 20),
                    _SummaryCards(data: data),
                    const SizedBox(height: 20),
                    _AIVoiceAnalysisCard(data: data),
                    const SizedBox(height: 20),
                    _LanguageAnalysisCard(data: data),
                    const SizedBox(height: 20),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
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

  const _AIVoiceAnalysisCard({required this.data});

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
          _AnalysisResultText(data: data),
          const SizedBox(height: 16),
          Text(
            '대화 음성에서 인지 저하 신호가 일부 관찰되었습니다.\n단기적인 현상일 수 있으므로 정기적인 체크를 권장드립니다. 필요 시 정확한 전문가 진단을 받아보세요.',
            textAlign: TextAlign.center,
            style: AppTextStyles.smallText,
          ),
        ],
      ),
    );
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