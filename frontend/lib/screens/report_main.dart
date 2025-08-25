import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../user_provider.dart';
import '../models/report.dart';
import '../data/report_api.dart';
import '../widgets/tap_widget.dart';
import '../widgets/group_bar_widget.dart';
import '../widgets/info_dialog.dart';

class ReportMainScreen extends StatefulWidget {
  final Report? report;

  const ReportMainScreen({super.key, this.report});

  @override
  State<ReportMainScreen> createState() => _ReportMainScreenState();
}

class _ReportMainScreenState extends State<ReportMainScreen>
    with TickerProviderStateMixin {
  List<Report> reports = [];
  bool isLoading = true;
  
  // 애니메이션 컨트롤러들
  late AnimationController _cognitiveAnimationController;
  late AnimationController _conversationAnimationController;
  late Animation<double> _cognitiveAnimation;
  late Animation<double> _conversationAnimation;

  @override
  void initState() {
    super.initState();
    
    // 애니메이션 컨트롤러 초기화
    _cognitiveAnimationController = AnimationController(
      duration: const Duration(milliseconds: 2000),
      vsync: this,
    );
    
    _conversationAnimationController = AnimationController(
      duration: const Duration(milliseconds: 2000),
      vsync: this,
    );
    
    // 애니메이션 설정 (Ease 곡선 사용)
    _cognitiveAnimation = Tween<double>(
      begin: 0.0,
      end: 1.0,
    ).animate(CurvedAnimation(
      parent: _cognitiveAnimationController,
      curve: Curves.easeOutCubic,
    ));
    
    _conversationAnimation = Tween<double>(
      begin: 0.0,
      end: 1.0,
    ).animate(CurvedAnimation(
      parent: _conversationAnimationController,
      curve: Curves.easeOutCubic,
    ));
    
    _loadReports();
    
    // 화면 로드 후 약간의 딜레이를 두고 애니메이션 시작
    Future.delayed(const Duration(milliseconds: 500), () {
      _startAnimations();
    });
  }

  Future<void> _loadReports() async {
    // 개별 리포트만 처리하므로 API 호출 불필요
    setState(() {
      reports = [];
      isLoading = false;
    });
  }
  
  void _startAnimations() {
    // 인지 건강 지수 애니메이션 시작
    _cognitiveAnimationController.forward();
    
    // 대화 건강 지수는 조금 늦게 시작
    Future.delayed(const Duration(milliseconds: 300), () {
      _conversationAnimationController.forward();
    });
  }
  
  @override
  void dispose() {
    _cognitiveAnimationController.dispose();
    _conversationAnimationController.dispose();
    super.dispose();
  }

  // 개별 리포트의 CIST 점수
  double get cistScore {
    if (widget.report != null) {
      print('🔍 [DEBUG] 개별 리포트 점수: ${widget.report!.totalCistScore}점');
      print('🔍 [DEBUG] 사용자 이름: ${widget.report!.userName}');
      print('🔍 [DEBUG] 사용자 생년월일: ${widget.report!.userBirthDate}');
      print('🔍 [DEBUG] 연령대: ${widget.report!.ageGroup}');
      print('🔍 [DEBUG] 표시 이름: ${widget.report!.userDisplayName}');
      return widget.report!.totalCistScore.toDouble();
    }
    return 0;
  }

  // 인지 건강 지수 백분율 계산
  double get cognitivePercentage {
    double percentage = (cistScore / 21) * 100; // 21점 만점
    print('🔍 [DEBUG] 인지 건강 지수 백분율: $percentage%');
    return percentage;
  }
  
  // 애니메이션된 인지 건강 지수 백분율
  double get animatedCognitivePercentage {
    return cognitivePercentage * _cognitiveAnimation.value;
  }

  // 대화 건강 지수 계산 (임시로 인지 점수 * 1.2)
  double get conversationScore {
    double score = cistScore * 1.2;
    print('🔍 [DEBUG] 대화 건강 지수 계산:');
    print('  - 인지 점수: $cistScore');
    print('  - 대화 점수 (인지 × 1.2): $score');
    return score;
  }

  // 대화 건강 지수 백분율
  double get conversationPercentage {
    double percentage = (conversationScore / 21) * 100;
    print('🔍 [DEBUG] 대화 건강 지수 백분율: $percentage%');
    return percentage.clamp(0, 100);
  }
  
  // 애니메이션된 대화 건강 지수 백분율
  double get animatedConversationPercentage {
    return conversationPercentage * _conversationAnimation.value;
  }

  @override
  Widget build(BuildContext context) {
    final familyName = Provider.of<UserProvider>(context).familyName ?? '우리 가족';

    return Scaffold(
      backgroundColor: const Color(0xFFF7F7F7),
      appBar: GroupBar(title: familyName),
      body: isLoading
          ? const Center(child: CircularProgressIndicator())
          : SingleChildScrollView(
              padding: const EdgeInsets.all(30),
              child: Column(
                children: [
                  // 인지 건강 지수 카드
                  _buildCognitiveHealthCard(),

                  const SizedBox(height: 8),

                  // 대화 건강 지수 카드
                  _buildConversationHealthCard(),

                  const SizedBox(height: 8),

                  // 목록 보기 버튼
                  SizedBox(
                    width: double.infinity,
                    child: ElevatedButton(
                      onPressed: () {
                        Navigator.pop(context);
                      },
                      style: ElevatedButton.styleFrom(
                        backgroundColor: const Color(0xFF62BE8A),
                        padding: const EdgeInsets.symmetric(vertical: 16),
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(16),
                        ),
                      ),
                      child: const Text(
                        '목록 보기',
                        style: TextStyle(
                          color: Colors.white,
                          fontSize: 18,
                          fontWeight: FontWeight.w800,
                          fontFamily: 'Pretendard',
                        ),
                      ),
                    ),
                  ),
                ],
              ),
            ),
      bottomNavigationBar: const CustomBottomNavBar(currentIndex: 3),
    );
  }

  /// 공용 헤더: 텍스트와 info 아이콘이 중앙, 화살표는 오른쪽
  Widget _buildHeader({
    required String title,
    required TextStyle titleStyle,
    required List<Widget> trailing,
    bool showInfoIcon = false,
    Color? infoIconColor,
    VoidCallback? onInfoTap,
    double height = 28,
  }) {
    return SizedBox(
      height: height,
      child: Stack(
        alignment: Alignment.center,
        children: [
          Center(
            child: Row(
              mainAxisSize: MainAxisSize.min,
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Text(title, style: titleStyle),
                if (showInfoIcon) ...[
                  const SizedBox(width: 8),
                  GestureDetector(
                    onTap: onInfoTap,
                    child: Icon(
                      Icons.info_outline,
                      color: infoIconColor ?? titleStyle.color,
                      size: 16,
                    ),
                  ),
                ],
              ],
            ),
          ),
          Align(
            alignment: Alignment.centerRight,
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: trailing,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildCognitiveHealthCard() {
    // 60대 평균을 14점으로 가정 (21점 만점 기준 약 67%)
    const double ageAverage = 10.0;
    final bool isAboveAverage = cistScore > ageAverage;

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.only(top: 10, left: 20, right: 20, bottom: 20),
      decoration: BoxDecoration(
        color: const Color(0xFF7CD0A0),
        borderRadius: BorderRadius.circular(13),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.1),
            blurRadius: 5,
            offset: const Offset(0, 2),
          ),
        ],
      ),
      child: Column(
        children: [
          _buildHeader(
            title: '인지 건강 지수',
            titleStyle: const TextStyle(
              color: Colors.white,
              fontSize: 20,
              fontWeight: FontWeight.w700,
              fontFamily: 'Pretendard',
            ),
            trailing: [
              const Icon(
                Icons.arrow_forward_ios,
                color: Colors.white,
                size: 16,
              ),
            ],
            showInfoIcon: true,
            infoIconColor: Colors.white,
            onInfoTap: () => InfoDialog.showCognitiveInfo(context),
          ),

          const SizedBox(height: 20),

          // 뇌 이미지
          Container(
            width: 66,
            height: 66,
            decoration: const BoxDecoration(
              image: DecorationImage(
                image: AssetImage('assets/images/brain.png'),
                fit: BoxFit.contain,
              ),
            ),
          ),

          const SizedBox(height: 20),

          // 진행 바 (애니메이션)
          AnimatedBuilder(
            animation: _cognitiveAnimation,
            builder: (context, child) {
              return _buildProgressBar(
                animatedCognitivePercentage, 
                ageAverage / 21 * 100,
              );
            },
          ),

          const SizedBox(height: 12),

          // 상태 텍스트
          RichText(
            textAlign: TextAlign.center,
            text: TextSpan(
              children: [
                TextSpan(
                  text: '${widget.report?.userDisplayName ?? '사용자'}은 ',
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 13,
                    fontWeight: FontWeight.w600,
                    fontFamily: 'Pretendard',
                    shadows: [Shadow(offset: Offset(0, 0), blurRadius: 3, color: Color(0x4DD0D0D0))],
                  ),
                ),
                TextSpan(
                  text: '${widget.report?.ageGroup ?? '연령대'} 평균 ',
                  style: const TextStyle(
                    color: Color(0xFF434343),
                    fontSize: 13,
                    fontWeight: FontWeight.w600,
                    fontFamily: 'Pretendard',
                    shadows: [Shadow(offset: Offset(0, 0), blurRadius: 3, color: Color(0x4DD0D0D0))],
                  ),
                ),
                const TextSpan(
                  text: '보다 ',
                  style: TextStyle(
                    color: Colors.white,
                    fontSize: 13,
                    fontWeight: FontWeight.w600,
                    fontFamily: 'Pretendard',
                    shadows: [Shadow(offset: Offset(0, 0), blurRadius: 3, color: Color(0x4DD0D0D0))],
                  ),
                ),
                TextSpan(
                  text: isAboveAverage ? '높게 나왔어요' : '낮게 나왔어요',
                  style: TextStyle(
                    color: isAboveAverage ? const Color(0xFF4CAF50) : const Color(0xFFFF4848),
                    fontSize: 14,
                    fontWeight: FontWeight.w800,
                    fontFamily: 'Pretendard',
                    shadows: [const Shadow(offset: Offset(0, 0), blurRadius: 3, color: Color(0x4DD0D0D0))],
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildConversationHealthCard() {
    // 대화 건강 지수 계산
    const double ageAverage = 16.0; // 60대 대화 평균 가정
    final bool isAboveAverage = conversationScore > ageAverage;

    print('🔍 [DEBUG] 대화 건강 카드:');
    print('  - 현재 대화 점수: $conversationScore');
    print('  - 60대 평균: $ageAverage');
    print('  - 평균보다 높음: $isAboveAverage');

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: const Color(0xFFE2F6EB),
        borderRadius: BorderRadius.circular(13),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.1),
            blurRadius: 5,
            offset: const Offset(0, 2),
          ),
        ],
      ),
      child: Column(
        children: [
          _buildHeader(
            title: '대화 건강 지수',
            titleStyle: const TextStyle(
              color: Color.fromARGB(255, 0, 0, 0),
              fontSize: 20,
              fontWeight: FontWeight.w700,
              fontFamily: 'Pretendard',
            ),
            trailing: [
              const Icon(
                Icons.arrow_forward_ios,
                color: Color(0xFF7CD0A0),
                size: 16,
              ),
            ],
            showInfoIcon: true,
            infoIconColor: const Color.fromARGB(255, 0, 0, 0),
            onInfoTap: () => InfoDialog.showConversationInfo(context),
          ),

          const SizedBox(height: 20),

          // 채팅 이미지
          Container(
            width: 74,
            height: 74,
            decoration: const BoxDecoration(
              image: DecorationImage(
                image: AssetImage('assets/images/chat.png'),
                fit: BoxFit.contain,
              ),
            ),
          ),

          const SizedBox(height: 20),

          // 진행 바 (애니메이션)
          AnimatedBuilder(
            animation: _conversationAnimation,
            builder: (context, child) {
              return _buildProgressBar(
                animatedConversationPercentage,
                ageAverage / 21 * 100,
                cardColor: const Color(0xFFE2F6EB),
              );
            },
          ),

          const SizedBox(height: 12),

          // 상태 텍스트
          RichText(
            textAlign: TextAlign.center,
            text: TextSpan(
              children: [
                TextSpan(
                  text: '${widget.report?.userDisplayName ?? '사용자'}은 ',
                  style: const TextStyle(
                    color: Color(0xFF111111),
                    fontSize: 13,
                    fontWeight: FontWeight.w600,
                    fontFamily: 'Pretendard',
                    shadows: [Shadow(offset: Offset(0, 1), blurRadius: 5, color: Color(0x4DCFCFCF))],
                  ),
                ),
                TextSpan(
                  text: '${widget.report?.ageGroup ?? '연령대'} 평균',
                  style: const TextStyle(
                    color: Color(0xFF777777),
                    fontSize: 13,
                    fontWeight: FontWeight.w700,
                    fontFamily: 'Pretendard',
                    shadows: [Shadow(offset: Offset(0, 1), blurRadius: 5, color: Color(0x4DCFCFCF))],
                  ),
                ),
                const TextSpan(
                  text: ' 보다 ',
                  style: TextStyle(
                    color: Color(0xFF111111),
                    fontSize: 13,
                    fontWeight: FontWeight.w600,
                    fontFamily: 'Pretendard',
                    shadows: [Shadow(offset: Offset(0, 1), blurRadius: 5, color: Color(0x4DCFCFCF))],
                  ),
                ),
                TextSpan(
                  text: isAboveAverage ? '높게 나왔어요' : '낮게 나왔어요',
                  style: TextStyle(
                    color: isAboveAverage ? const Color(0xFF4CAF50) : const Color(0xFFF45B5B),
                    fontSize: 14,
                    fontWeight: FontWeight.w800,
                    fontFamily: 'Pretendard',
                    shadows: [const Shadow(offset: Offset(0, 1), blurRadius: 5, color: Color(0x4DCFCFCF))],
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildProgressBar(double currentPercentage, double averagePercentage, {Color? cardColor}) {
    return LayoutBuilder(
      builder: (context, constraints) {
        final w = constraints.maxWidth; // 실제 바 너비
        final curX = (currentPercentage.clamp(0, 100) / 100.0) * w;
        final avgX = (averagePercentage.clamp(0, 100) / 100.0) * w;

        print('🔍 [DEBUG] Progress Bar:');
        print('  - 현재 백분율: $currentPercentage%');
        print('  - 평균 백분율: $averagePercentage%');
        print('  - 실제 바 너비: $w');
        print('  - 화살표 위치: $curX');
        print('  - 평균선 위치: $avgX');

        return Column(
          children: [
            // 화살표
            SizedBox(
              height: 16,
              child: Stack(
                clipBehavior: Clip.none,
                children: [
                  Positioned(
                    left: (curX - 8).clamp(0, w - 16), // ← 이미지 폭이 16이므로 /2 해서 8 보정
                    child: Image.asset(
                      'assets/images/triangle.png',
                      width: 16,
                      height: 10,
                      fit: BoxFit.contain,
                      // color: Colors.black, // PNG를 단색으로 덮고 싶으면 사용
                      // colorBlendMode: BlendMode.srcIn,
                    ),
                  ),
                ],
              ),
            ),
            // 진행 바
            Stack(
              children: [
                // 둥근 모서리로 잘라서 안쪽 레이어들 깔끔히 맞춤
                ClipRRect(
                  borderRadius: BorderRadius.circular(6),
                  child: SizedBox(
                    width: double.infinity,
                    height: 12,
                    child: Stack(
                      children: [
                        // 0~100% 전체 그라데이션 (항상 전체 폭)
                        Container(
                          decoration: const BoxDecoration(
                            gradient: LinearGradient(
                              colors: [
                                Color(0xFF48AC6F), // 초록
                                Color(0xFFFDDC83), // 노랑
                                Color(0xFFEF5131), // 빨강
                              ],
                              stops: [
                                0.0,   // 0%
                                0.59,  // 59%
                                1.0,   // 100%
                              ],
                            ),
                          ),
                        ),

                        // 현재 퍼센트 이후를 회색으로 덮기 (끝까지)
                        Positioned(
                          left: curX.clamp(0, w),
                          right: 0,
                          top: 0,
                          bottom: 0,
                          child: Container(color: const Color(0xFFD9D9D9)),
                        ),
                      ],
                    ),
                  ),
                ),
                // 평균 표시 라인
                Positioned(
                  left: (avgX - 1.5).clamp(0, w - 3),
                  child: Container(
                    width: 3,
                    height: 12,
                    decoration: BoxDecoration(
                      color: const Color(0xFFF43E3E),
                      borderRadius: BorderRadius.circular(1.5),
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 8),
            // 평균 배지
            Stack(
              children: [
                const SizedBox(height: 20, width: double.infinity),
                Positioned(
                  left: (avgX - 10).clamp(0, w - 20), // 텍스트 폭만 고려
                  child: const Text(
                    '평균',
                    style: TextStyle(
                      color: Color.fromARGB(255, 223, 58, 58), // 붉은 글씨
                      fontSize: 10,
                      fontWeight: FontWeight.w700,
                      fontFamily: 'Pretendard',
                    ),
                  ),
                ),
              ],
            ),
          ],
        );
      },
    );
  }
}
