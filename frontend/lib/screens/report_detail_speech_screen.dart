import 'package:flutter/material.dart';
import '../models/report.dart';
import '../widgets/tap_widget.dart';
import '../widgets/group_bar_widget.dart';
import '../data/report_api.dart';

class ReportDetailSpeechScreen extends StatefulWidget {
  final Report? report_speech_detail;

  const ReportDetailSpeechScreen({super.key, this.report_speech_detail});

  @override
  State<ReportDetailSpeechScreen> createState() =>
      _ReportDetailSpeechScreenState();
}

class _ReportDetailSpeechScreenState extends State<ReportDetailSpeechScreen> {
  ReportTextAnalysisData? textAnalysisData;
  bool isLoading = true;

  @override
  void initState() {
    super.initState();
    _loadTextAnalysisData();
  }

  Future<void> _loadTextAnalysisData() async {
    if (widget.report_speech_detail?.sessionId != null) {
      try {
        final data = await ReportTextAnalysisApi.fetchTextAnalysisData(
          widget.report_speech_detail!.sessionId,
        );
        setState(() {
          textAnalysisData = data;
          isLoading = false;
        });
      } catch (e) {
        print('❌ Error loading text analysis data: $e');
        setState(() {
          isLoading = false;
        });
      }
    } else {
      setState(() {
        isLoading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final screenSize = MediaQuery.of(context).size;
    final screenWidth = screenSize.width;
    final screenHeight = screenSize.height;

    return Scaffold(
      backgroundColor: const Color(0xFFF7F7F7),
      appBar: GroupBar(title: '대화 건강 지수 상세 페이지'),
      body: SingleChildScrollView(
        padding: EdgeInsets.symmetric(
          horizontal: screenWidth * 0.05, // 5% 좌우 패딩
          vertical: screenHeight * 0.02, // 2% 상하 패딩
        ),
        child: Column(
          children: [
            // 날짜 정보
            Text(
              widget.report_speech_detail?.formattedDate ?? '날짜 정보 없음',
              style: TextStyle(
                color: const Color(0xFF777777),
                fontSize: screenWidth * 0.032,
                fontFamily: 'Pretendard',
                fontWeight: FontWeight.w600,
              ),
            ),

            SizedBox(height: screenHeight * 0.02),

            DetailSpeechSummary(screenWidth),

            // 메인 카드
            SpeechAnalysisCard(
              screenWidth: screenWidth,
              screenHeight: screenHeight,
              ageGroup: widget.report_speech_detail?.ageGroup,
              textAnalysisData: textAnalysisData,
              buildRadarChart: _buildRadarChart,
              buildLegend: _buildLegend,
            ),

            SizedBox(height: screenHeight * 0.1), // 하단 여백
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
    // 데이터베이스에서 가져온 사용자 데이터 값 또는 기본값 사용
    final userValues = {
      'vocabulary': textAnalysisData?.lexicalDiversity ?? 0.0, // 어휘 다양성
      'pronouns': textAnalysisData?.demonstrativeRatio ?? 0.0, // 지시어 사용 비율
      'length': textAnalysisData?.mlu ?? 0.0, // 평균 발화 길이 (MLU)
      'speed': textAnalysisData?.speechRate ?? 0.0, // 발화 속도
    };

    // 연령대별 평균값 (데이터베이스에서 가져온 값 또는 기본값)
    final avgValues = {
      'vocabulary': textAnalysisData?.avgLexicalDiversity ?? 0.9, // 어휘 다양성 평균
      'pronouns':
          textAnalysisData?.avgDemonstrativeRatio ?? 0.2, // 지시어 사용 비율 평균
      'length': textAnalysisData?.avgMlu ?? 0.6, // 평균 발화 길이 평균
      'speed': textAnalysisData?.avgSpeechRate ?? 0.7, // 발화 속도 평균
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
              widget.report_speech_detail?.userDisplayName ?? '사용자',
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

Widget DetailSpeechSummary(double screenWidth) {
  return Column(
    children: [
      Container(
        width: 265.83,
        height: 209,
        child: Stack(
          children: [
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
              ),
            ),
            Positioned(
              left: 11,
              top: 134,
              child: SizedBox(
                width: 107,
                height: 15,
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
                height: 30,
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
            ),
            Positioned(
              left: 38,
              top: 46,
              child: Container(
                width: 51,
                height: 51,
                decoration: BoxDecoration(
                  image: DecorationImage(
                    image: NetworkImage("https://placehold.co/51x51"),
                    fit: BoxFit.contain,
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
    ],
  );
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
