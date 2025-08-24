import 'package:flutter/material.dart';

class ReportDetailScreen extends StatelessWidget {
  const ReportDetailScreen({Key? key}) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF7F7F7),
      body: Column(
        children: [
          // Status Bar
          const StatusBarWidget(),

          // Header Section
          _buildHeader(),

          // Content Section
          Expanded(
            child: SingleChildScrollView(
              padding: const EdgeInsets.all(16),
              child: Column(
                children: [
                  _buildProfileSection(),
                  const SizedBox(height: 16),
                  _buildAnalysisReport(),
                  const SizedBox(height: 24),
                  _buildBackToListButton(context),
                ],
              ),
            ),
          ),
        ],
      ),
      bottomNavigationBar: const CustomBottomNavBar(currentIndex: 3),
    );
  }

  Widget _buildHeader() {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.symmetric(vertical: 16),
      decoration: const BoxDecoration(
        color: Color.fromARGB(255, 254, 255, 255),
        boxShadow: [
          BoxShadow(
            color: Color(0x33555555),
            blurRadius: 10,
            offset: Offset(0, -1),
          ),
        ],
      ),
      child: Column(
        children: [
          const Text(
            '서봉봉님 대화 분석 보고서',
            style: TextStyle(
              color: Color.fromARGB(255, 0, 0, 0),
              fontSize: 24,
              fontFamily: 'Pretendard',
              fontWeight: FontWeight.w800,
            ),
          ),
          const SizedBox(height: 4),
          const Text(
            '2025-05-26 13:56',
            style: TextStyle(
              color: Color(0xFF777777),
              fontSize: 15,
              fontFamily: 'Pretendard',
              fontWeight: FontWeight.w600,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildProfileSection() {
    return Column(
      children: [
        Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Profile Image
            Container(
              width: 100,
              height: 100,
              decoration: BoxDecoration(
                borderRadius: BorderRadius.circular(10),
                image: const DecorationImage(
                  image: AssetImage('../assets/photos/3.png'),
                  fit: BoxFit.cover,
                ),
              ),
            ),
            const SizedBox(width: 16),

            // Middle section - empty space
            const Expanded(child: SizedBox()),

            // Right section - Play Button
            Container(
              width: 50,
              height: 50,
              decoration: const BoxDecoration(
                color: Color(0xFF8CCAA7),
                shape: BoxShape.circle,
                boxShadow: [
                  BoxShadow(
                    color: Color(0x33555555),
                    blurRadius: 5,
                    offset: Offset(0, 2),
                  ),
                ],
              ),
              child: const Icon(
                Icons.play_arrow,
                color: Colors.white,
                size: 28,
              ),
            ),
          ],
        ),

        const SizedBox(height: 20),

        // Duration Text - full width
        Container(
          width: double.infinity,
          child: const Text(
            '전체 대화 길이: 1시간 25분 29초',
            style: TextStyle(
              color: Color(0xFF555555),
              fontSize: 16,
              fontFamily: 'Pretendard',
              fontWeight: FontWeight.w600,
            ),
          ),
        ),

        const SizedBox(height: 12),

        // Simple Progress Bar
        _buildSimpleProgressBar(),
      ],
    );
  }

  Widget _buildSimpleProgressBar() {
    return Container(
      width: double.infinity,
      height: 6,
      decoration: BoxDecoration(
        color: const Color(0xFFE0E0E0),
        borderRadius: BorderRadius.circular(3),
      ),
      child: FractionallySizedBox(
        widthFactor: 0.35, // 35% progress
        alignment: Alignment.centerLeft,
        child: Container(
          decoration: BoxDecoration(
            color: const Color(0xFF8CCAA7),
            borderRadius: BorderRadius.circular(3),
          ),
        ),
      ),
    );
  }

  Widget _buildAnalysisReport() {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: const Color(0xFF8CCAA7), width: 2),
        boxShadow: const [BoxShadow(color: Color(0x19777777), blurRadius: 5)],
      ),
      child: const Text(
        '''📌 전체 답변: 7회
🔍 다소 어긋난 답변: 1회
💭 전반적 감정: 긍정적 (주요 감정: 무력감)

감정 상태:
  • 무력감: 3회
  • 그리움: 2회
  • 애정: 2회

어긋난 답변 정도:
  • 꽤 어긋남: 1회

어긋난 답변 상세:
1번째 - 2025-05-30 02:42:45
   질문: 아, 그러셨군요. 힘드셨던 기억이 있으셨다면, 그 마음을 헤아리고 싶어요. 그래도 가족과 함께했던 따뜻한 순간이 힘이 되셨던 적도 있으셨겠죠? 사진 속 가족처럼 함께 앉아 대화를 나누던 모습이 떠오르시나요?
   답변: ㅏ
   상태: [무력감]''',
        style: TextStyle(
          color: Color(0xFF333333),
          fontSize: 16,
          fontFamily: 'Pretendard',
          fontWeight: FontWeight.w500,
          height: 1.4,
        ),
      ),
    );
  }

  Widget _buildBackToListButton(BuildContext context) {
    return Container(
      width: double.infinity,
      height: 50,
      child: ElevatedButton(
        onPressed: () {
          Navigator.pushNamed(context, '/report');
        },
        style: ElevatedButton.styleFrom(
          backgroundColor: const Color(0xFF8CCAA7),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(20),
          ),
          elevation: 0,
        ),
        child: const Text(
          '목록 보기',
          style: TextStyle(
            color: Colors.white,
            fontSize: 20,
            fontFamily: 'Pretendard',
            fontWeight: FontWeight.w800,
          ),
        ),
      ),
    );
  }
}

// 상태바 위젯
class StatusBarWidget extends StatelessWidget {
  const StatusBarWidget({Key? key}) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return Container(
      width: MediaQuery.of(context).size.width,
      height: 54,
      color: Colors.white,
      child: Stack(
        children: [
          // 시간 표시
          const Positioned(
            left: 51.92,
            top: 18.34,
            child: Text(
              '9:41',
              style: TextStyle(
                color: Colors.black,
                fontSize: 17,
                fontFamily: 'SF Pro',
                fontWeight: FontWeight.w600,
                height: 1.29,
              ),
            ),
          ),
          // 배터리 아이콘
          Positioned(right: 20, top: 23, child: _buildBatteryIcon()),
        ],
      ),
    );
  }

  Widget _buildBatteryIcon() {
    return SizedBox(
      width: 25,
      height: 13,
      child: Stack(
        children: [
          Opacity(
            opacity: 0.35,
            child: Container(
              decoration: ShapeDecoration(
                shape: RoundedRectangleBorder(
                  side: const BorderSide(width: 1, color: Colors.black),
                  borderRadius: BorderRadius.circular(4.30),
                ),
              ),
            ),
          ),
          Positioned(
            left: 2,
            top: 2,
            child: Container(
              width: 21,
              height: 9,
              decoration: ShapeDecoration(
                color: Colors.black,
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(2.50),
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

// 커스텀 하단 네비게이션 바 위젯
class CustomBottomNavBar extends StatelessWidget {
  final int currentIndex;

  const CustomBottomNavBar({Key? key, required this.currentIndex})
    : super(key: key);

  @override
  Widget build(BuildContext context) {
    final List<BottomNavItem> navItems = [
      BottomNavItem(label: '홈', icon: Icons.home),
      BottomNavItem(label: '사진첩', icon: Icons.photo_library),
      BottomNavItem(label: '사진 추가', icon: Icons.add_a_photo),
      BottomNavItem(label: '보고서', icon: Icons.description),
      BottomNavItem(label: '나의 정보', icon: Icons.person),
    ];

    return Container(
      height: 80,
      decoration: const BoxDecoration(
        color: Colors.white,
        border: Border(top: BorderSide(color: Color(0x7F999999), width: 0.7)),
        boxShadow: [
          BoxShadow(
            color: Color(0x33555555),
            blurRadius: 10,
            offset: Offset(0, -1),
          ),
        ],
      ),
      child: Row(
        children: navItems.asMap().entries.map((entry) {
          int index = entry.key;
          BottomNavItem item = entry.value;
          bool isSelected = index == currentIndex;

          return _buildNavItem(context, item, isSelected, index);
        }).toList(),
      ),
    );
  }

  Widget _buildNavItem(
    BuildContext context,
    BottomNavItem item,
    bool isSelected,
    int index,
  ) {
    return Expanded(
      child: GestureDetector(
        onTap: () {
          switch (index) {
            case 0:
              Navigator.pushNamed(context, '/home');
              break;
            case 1:
              Navigator.pushNamed(context, '/gallery');
              break;
            case 2:
              Navigator.pushNamed(context, '/addphoto');
              break;
            case 3:
              Navigator.pushNamed(context, '/report');
              break;
            case 4:
              // 나의 정보 페이지 (라우트 추가 필요)
              break;
          }
        },
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              item.icon,
              size: 30,
              color: isSelected
                  ? const Color(0xFF8CCAA7)
                  : const Color(0xFF555555),
            ),
            const SizedBox(height: 4),
            Text(
              item.label,
              style: TextStyle(
                color: isSelected
                    ? const Color(0xFF8CCAA7)
                    : const Color(0xFF555555),
                fontSize: 12,
                fontFamily: 'Pretendard',
                fontWeight: FontWeight.w700,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

// 하단 네비게이션 아이템 모델
class BottomNavItem {
  final String label;
  final IconData icon;

  BottomNavItem({required this.label, required this.icon});
}
