import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/user_provider.dart';
import '../models/report.dart';
import '../widgets/tap_widget.dart';
import '../widgets/group_bar_widget.dart';
import '../services/user_service.dart';

class ReportDetailCistScreen extends StatefulWidget {
  final Report? report;
  final String sessionId;

  const ReportDetailCistScreen({super.key, this.report, required this.sessionId});

  @override
  State<ReportDetailCistScreen> createState() => _ReportDetailCistScreenState();
}

class _ReportDetailCistScreenState extends State<ReportDetailCistScreen> {
  int _currentCardIndex = 0;
  List<Map<String, dynamic>> _cistCategories = [];
  bool _isLoading = true;
  
  @override
  void initState() {
    super.initState();
    _loadCistData();
  }
  
  Future<void> _loadCistData() async {
    try {
      final sessionId = widget.sessionId;
      
      if (sessionId.isNotEmpty) {
        print('🔍 Loading CIST data for session: $sessionId');
        final cistData = await UserService.getCistDataBySession(sessionId);
        setState(() {
          _cistCategories = cistData;
          _isLoading = false;
        });
      } else {
        print('❌ Session ID not found');
        setState(() {
          _isLoading = false;
        });
      }
    } catch (e) {
      print('❌ CIST 데이터 로딩 오류: $e');
      setState(() {
        _isLoading = false;
      });
    }
  }


  @override
  Widget build(BuildContext context) {
    final familyName = Provider.of<UserProvider>(context).familyName ?? '우리 가족';

    return Scaffold(
      backgroundColor: const Color(0xFFF7F7F7),
      appBar: GroupBar(title: familyName),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(20),
        child: Column(
          children: [
            // 헤더 정보
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(20),
              decoration: BoxDecoration(
                color: Colors.white,
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
                  Text(
                    '${widget.report?.userDisplayName ?? '사용자'}님 인지 건강 지수 분석 결과',
                    textAlign: TextAlign.center,
                    style: const TextStyle(
                      color: Color(0xFF333333),
                      fontSize: 18,
                      fontFamily: 'Pretendard',
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                  const SizedBox(height: 8),
                  Text(
                    _formatDate(DateTime.now()),
                    textAlign: TextAlign.center,
                    style: const TextStyle(
                      color: Color(0xFF777777),
                      fontSize: 12,
                      fontFamily: 'Pretendard',
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ],
              ),
            ),

            const SizedBox(height: 20),

            // CIST 분석 결과 카드
            Container(
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
                crossAxisAlignment: CrossAxisAlignment.center,
                children: [
                  const Text(
                    '인지건강 지수 분석',
                    textAlign: TextAlign.center,
                    style: TextStyle(
                      color: Color(0xFF2A2A2A),
                      fontSize: 25,
                      fontFamily: 'Pretendard',
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                  
                  const SizedBox(height: 20),
                  
                  // 설명 텍스트
                  const Text.rich(
                    TextSpan(
                      children: [
                        TextSpan(
                          text: '이번 대화에서 도출된 인지능력 분석 결과입니다.\n',
                          style: TextStyle(
                            color: Color(0xFF111111),
                            fontSize: 12,
                            fontFamily: 'Pretendard',
                            fontWeight: FontWeight.w500,
                            height: 1.4,
                          ),
                        ),
                        TextSpan(
                          text: 'CIST(인지선별검사)',
                          style: TextStyle(
                            color: Color(0xFF111111),
                            fontSize: 12,
                            fontFamily: 'Pretendard',
                            fontWeight: FontWeight.w700,
                            height: 1.4,
                          ),
                        ),
                        TextSpan(
                          text: '의 질문지를 대화 맥락에 맞춰 적용하고,\n어르신의 답변을 CIST 기준에 따라 평가하였습니다',
                          style: TextStyle(
                            color: Color(0xFF111111),
                            fontSize: 12,
                            fontFamily: 'Pretendard',
                            fontWeight: FontWeight.w500,
                            height: 1.4,
                          ),
                        ),
                      ],
                    ),
                    textAlign: TextAlign.center,
                  ),

                  const SizedBox(height: 30),

                  // CIST 상세 결과 카드
                  _isLoading 
                      ? const Center(
                          child: Padding(
                            padding: EdgeInsets.all(50.0),
                            child: CircularProgressIndicator(),
                          ),
                        )
                      : _cistCategories.isEmpty
                          ? const Center(
                              child: Padding(
                                padding: EdgeInsets.all(50.0),
                                child: Text(
                                  'CIST 데이터가 없습니다.\n대화를 통해 인지 평가를 진행해보세요.',
                                  textAlign: TextAlign.center,
                                  style: TextStyle(
                                    color: Color(0xFF777777),
                                    fontSize: 14,
                                    fontFamily: 'Pretendard',
                                    fontWeight: FontWeight.w500,
                                  ),
                                ),
                              ),
                            )
                          : _buildCISTDetailCard(),

                  const SizedBox(height: 20),

                  // 면책 조항
                  const Text(
                    '본 결과는 참고용 지표이며, 정확한 진단은 전문의 상담을 통해 이루어져야 합니다.',
                    textAlign: TextAlign.center,
                    style: TextStyle(
                      color: Color(0xFF777777),
                      fontSize: 10,
                      fontFamily: 'Pretendard',
                      fontWeight: FontWeight.w500,
                      height: 1.4,
                    ),
                  ),
                ],
              ),
            ),

            const SizedBox(height: 20),

            // 뒤로가기 버튼
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

  Widget _buildCISTDetailCard() {
    if (_cistCategories.isEmpty) {
      return const SizedBox.shrink();
    }

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: const Color(0xFFFCFBF9),
        borderRadius: BorderRadius.circular(16),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.1),
            blurRadius: 4,
            offset: const Offset(0, 2),
          ),
        ],
      ),
      child: Column(
        children: [
          // 카드 네비게이션
          Stack(
            clipBehavior: Clip.none,
            children: [
              // 현재 카드 표시
              _buildCategoryItem(_cistCategories[_currentCardIndex]),
              
              // 왼쪽 화살표 (카드 왼쪽 테두리에 걸치게)
              Positioned(
                left: -80,
                top: 60,
                child: GestureDetector(
                  onTap: () {
                    print('🖱️ Left arrow GestureDetector tapped!');
                    if (_currentCardIndex > 0) {
                      _previousCard();
                    } else {
                      print('⚠️ Left arrow disabled - at first card');
                    }
                  },
                  behavior: HitTestBehavior.opaque, // 클릭 영역 확장
                  child: Container(
                    // color: Colors.red.withOpacity(0.2), // 디버깅용 - 클릭 영역 확인
                    padding: const EdgeInsets.all(25), // 아이콘 기준으로 25px씩 확장
                    child: Opacity(
                      opacity: _currentCardIndex > 0 ? 0.8 : 0.3, // 활성화 상태에 따른 투명도
                      child: Image.asset(
                        'assets/images/left.png',
                        width: 70,
                        height: 70,
                      ),
                    ),
                  ),
                ),
              ),
              
              // 오른쪽 화살표 (카드 오른쪽 테두리에 걸치게, 180도 회전)
              Positioned(
                right: -80,
                top: 60,
                child: GestureDetector(
                  onTap: () {
                    print('🖱️ Right arrow GestureDetector tapped!');
                    if (_currentCardIndex < _cistCategories.length - 1) {
                      _nextCard();
                    } else {
                      print('⚠️ Right arrow disabled - at last card');
                    }
                  },
                  behavior: HitTestBehavior.opaque, // 클릭 영역 확장
                  child: Container(
                    // color: Colors.blue.withOpacity(0.2), // 디버깅용 - 클릭 영역 확인
                    padding: const EdgeInsets.all(25), // 아이콘 기준으로 25px씩 확장
                    child: Opacity(
                      opacity: _currentCardIndex < _cistCategories.length - 1 ? 0.8 : 0.3, // 활성화 상태에 따른 투명도
                      child: Transform.rotate(
                        angle: 3.14159, // 180도 회전 (π 라디안)
                        child: Image.asset(
                          'assets/images/left.png',
                          width: 70,
                          height: 70,
                        ),
                      ),
                    ),
                  ),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
  
  void _previousCard() {
    print('🔙 Previous card clicked - Current index: $_currentCardIndex');
    if (_currentCardIndex > 0) {
      setState(() {
        _currentCardIndex--;
      });
      print('✅ Moved to previous card - New index: $_currentCardIndex');
    } else {
      print('❌ Already at first card');
    }
  }
  
  void _nextCard() {
    print('➡️ Next card clicked - Current index: $_currentCardIndex');
    print('📝 Total categories: ${_cistCategories.length}');
    if (_currentCardIndex < _cistCategories.length - 1) {
      setState(() {
        _currentCardIndex++;
      });
      print('✅ Moved to next card - New index: $_currentCardIndex');
    } else {
      print('❌ Already at last card');
    }
  }

  Widget _buildCategoryItem(Map<String, dynamic> category) {
    return Container(
      margin: const EdgeInsets.only(bottom: 16),
      padding: const EdgeInsets.fromLTRB(8, 8, 8, 8), 


      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // 카테고리 헤더
          Container(
            width: double.infinity,
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: const Color(0xFFF8F2EA),
              borderRadius: BorderRadius.circular(20),
              border: Border.all(color: const Color(0xFFE0E0E0)),
            ),
            child: Row(
              children: [
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                  decoration: BoxDecoration(
                    color: const Color(0xFF8C7E7E),
                    borderRadius: BorderRadius.circular(6),
                  ),
                  child: Text(
                    category['category'],
                    style: const TextStyle(
                      color: Colors.white,
                      fontSize: 12,
                      fontFamily: 'Pretendard',
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Text(
                    category['description'],
                    style: const TextStyle(
                      color: Color(0xFF838383),
                      fontSize: 10,
                      fontFamily: 'Pretendard',
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                ),
              ],
            ),
          ),

          const SizedBox(height: 12),

          // 대화 예시
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // AI 아바타
              
              const SizedBox(width: 8),

              // 질문 말풍선
              Flexible( // ← Expanded 대신 Flexible
                child: Container(
                  padding: const EdgeInsets.all(12),
                  decoration: const BoxDecoration(
                    color: Color(0xFFDEDEDE),
                    borderRadius: BorderRadius.only(
                      topRight: Radius.circular(12),
                      bottomRight: Radius.circular(12),
                      bottomLeft: Radius.circular(12),
                    ),
                  ),
                  child: Text(
                    (category['question'] ?? '').toString().split(':').last.trim(),
                    style: const TextStyle(
                      color: Color(0xFF111111),
                      fontSize: 10,
                      fontFamily: 'Pretendard',
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                ),
              ),
            ],
          ),

          const SizedBox(height: 8),

          // 사용자 답변
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Spacer(), // 오른쪽 정렬 유지
              ConstrainedBox( // 텍스트 길이에 맞추되, 화면 최대 폭 제한
                constraints: const BoxConstraints(maxWidth: 250), // 필요에 따라 조정
                child: Container(
                  padding: const EdgeInsets.all(12),
                  decoration: const BoxDecoration(
                    color: Color(0xFF69BD8D),
                    borderRadius: BorderRadius.only(
                      topLeft: Radius.circular(12),
                      bottomRight: Radius.circular(12),
                      bottomLeft: Radius.circular(12),
                    ),
                  ),
                  child: Text(
                    category['answer'],
                    style: const TextStyle(
                      color: Colors.white,
                      fontSize: 10,
                      fontFamily: 'Pretendard',
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                ),
              ),
            ],
          ),

          const SizedBox(height: 12),

          // 평가 결과
          IntrinsicHeight(
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Container(
                  width: 60,
                  decoration: BoxDecoration(
                    color: Colors.white,
                    borderRadius: BorderRadius.circular(8),
                    border: Border.all(color: const Color(0xFFDEDEDE)),
                  ),
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Padding(
                        padding: const EdgeInsets.only(top: 4), // 원하는 만큼 조정
                        child: Image.asset(
                          category['score'] == 1
                              ? 'assets/images/smile.png'
                              : 'assets/images/lose.png',
                          width: 22,
                          height: 22,
                        ),
                      ),
                      const SizedBox(height: 4),
                      Text.rich(
                        TextSpan(
                          children: [
                            TextSpan(
                              text: category['score'] == 1 ? '정답' : '오답',
                              style: TextStyle(
                                fontSize: 10,
                                fontFamily: 'Pretendard',
                                fontWeight: FontWeight.w700,
                                color: category['score'] == 1
                                    ? const Color(0xFF66A96F) // 초록
                                    : const Color(0xFFFF4848), // 빨강
                              ),
                            ),
                            const TextSpan(
                              text: '입니다!',
                              style: TextStyle(
                                fontSize: 10,
                                fontFamily: 'Pretendard',
                                fontWeight: FontWeight.w700,
                                color: Colors.black, // '입니다!'는 검은색
                              ),
                            ),
                          ],
                        ),
                      )

                    ],
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Container(
                    padding: const EdgeInsets.all(12),
                    decoration: BoxDecoration(
                      color: const Color(0xFF8C7E7E),
                      borderRadius: BorderRadius.circular(8),
                    ),
                    child: Text(
                      category['isCorrect'] 
                          ? '정확한 답변으로 ${category['category']} 능력이 정상 범위에 있습니다.'
                          : '부정확한 답변으로 ${category['category']} 능력에 주의가 필요합니다.',
                      style: const TextStyle(
                        color: Colors.white,
                        fontSize: 9,
                        fontFamily: 'Pretendard',
                        fontWeight: FontWeight.w700,
                        height: 1.4,
                      ),
                    ),
                  ),
                ),
              ],
            ),
          )
        ],
      ),
    );
  }

  String _formatDate(DateTime date) {
    return '${date.year}-${date.month.toString().padLeft(2, '0')}-${date.day.toString().padLeft(2, '0')} ${date.hour.toString().padLeft(2, '0')}:${date.minute.toString().padLeft(2, '0')}';
  }
}