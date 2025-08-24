import 'package:flutter/material.dart';

class FamilyChatAnalysisScreen extends StatelessWidget {
  const FamilyChatAnalysisScreen({Key? key}) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.white,
      body: Column(
        children: [
          // Status Bar
          const StatusBarWidget(),

          // Header
          const HeaderWidget(),

          // Content Area
          Expanded(
            child: Container(
              color: const Color(0xFFF7F7F7),
              child: Column(
                children: [
                  const ContentHeaderWidget(),
                  Expanded(child: const ReportListWidget()),
                  const WarningMessageWidget(),
                ],
              ),
            ),
          ),
        ],
      ),
      bottomNavigationBar: const CustomBottomNavBar(currentIndex: 3),
    );
  }
}

// 상수 정의
class AppConstants {
  static const String reportTitle = '2025-05-26 13:56 서봉봉님 대화 분석 보고서';
  static const String warningMessage =
      '비정상적인 상태가 의심되는 경우 병원에 방문해 정확한 진단을 진행해주세요.';
  static const String infoMessage =
      'AI가 대화를 분석해 평가한 상태 분석 보고서를 제공합니다.\n본 보고서는 참고 자료이며, 절대적인 해석이 아님을 유의해 주세요.';
}

// 색상 테마
class AppColors {
  static const Color primary = Color(0xFF00C8B8);
  static const Color background = Color(0xFFF7F7F7);
  static const Color textPrimary = Color(0xFF333333);
  static const Color textSecondary = Color(0xFF555555);
  static const Color warning = Color(0xFFE25430);
  static const Color border = Color(0x7F999999);
  static const Color shadow = Color(0x33555555);
}

// 상태바 위젯
class StatusBarWidget extends StatelessWidget {
  const StatusBarWidget({Key? key}) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return Container(
      width: MediaQuery.of(context).size.width,
      height: 54,
      color: AppColors.primary,
      child: Stack(
        children: [
          // 시간 표시
          const Positioned(
            left: 51.92,
            top: 18.34,
            child: Text(
              '9:41',
              style: TextStyle(
                color: Colors.white,
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
                  side: const BorderSide(width: 1, color: Colors.white),
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
                color: Colors.white,
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

// 헤더 위젯
class HeaderWidget extends StatelessWidget {
  const HeaderWidget({Key? key}) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return Container(
      width: MediaQuery.of(context).size.width,
      height: 50,
      color: AppColors.primary,
      child: const Center(
        child: Text(
          '화목한 우리 가족^~^',
          style: TextStyle(
            color: Colors.white,
            fontSize: 24,
            fontFamily: 'Pretendard',
            fontWeight: FontWeight.w800,
          ),
        ),
      ),
    );
  }
}

// 컨텐츠 헤더 위젯
class ContentHeaderWidget extends StatelessWidget {
  const ContentHeaderWidget({Key? key}) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return Container(
      width: MediaQuery.of(context).size.width,
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: const Color.fromARGB(255, 255, 255, 255),
        boxShadow: const [
          BoxShadow(color: Color(0x19777777), blurRadius: 5, spreadRadius: 0),
        ],
      ),
      child: const Text(
        AppConstants.infoMessage,
        textAlign: TextAlign.center,
        style: TextStyle(
          color: Color.fromARGB(255, 0, 0, 0),
          fontSize: 13,
          fontFamily: 'Pretendard',
          fontWeight: FontWeight.w600,
          height: 1.23,
        ),
      ),
    );
  }
}

// 보고서 리스트 위젯
class ReportListWidget extends StatelessWidget {
  const ReportListWidget({Key? key}) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return Container(
      color: Colors.white,
      child: ListView.builder(
        padding: EdgeInsets.zero,
        itemCount: 1, // 원본에서 8개의 동일한 아이템이 있었음
        itemBuilder: (context, index) {
          return ReportItemWidget(
            isSelected: index == 0, // 첫 번째 아이템을 선택된 상태로
          );
        },
      ),
    );
  }
}

// 개별 보고서 아이템 위젯 (클릭 기능 추가)
class ReportItemWidget extends StatelessWidget {
  final bool isSelected;

  const ReportItemWidget({Key? key, this.isSelected = false}) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: () {
        // 상세 보고서 화면으로 이동
        Navigator.pushNamed(context, '/reportDetail');
      },
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
        decoration: BoxDecoration(
          color: Colors.white,
          border: Border(
            top: BorderSide(
              color: isSelected ? AppColors.primary : const Color(0x7F111111),
              width: isSelected ? 2 : 1,
            ),
          ),
          boxShadow: const [
            BoxShadow(color: Color(0x19555555), blurRadius: 5, spreadRadius: 0),
          ],
        ),
        child: Row(
          children: [
            Expanded(
              child: Text(
                AppConstants.reportTitle,
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
                style: const TextStyle(
                  color: AppColors.textSecondary,
                  fontSize: 16,
                  fontFamily: 'Pretendard',
                  fontWeight: FontWeight.w500,
                  height: 1.8,
                ),
              ),
            ),
            const SizedBox(width: 8),
            // 화살표 아이콘 추가
            const Icon(
              Icons.arrow_forward_ios,
              size: 16,
              color: AppColors.textSecondary,
            ),
          ],
        ),
      ),
    );
  }
}

// 경고 메시지 위젯
class WarningMessageWidget extends StatelessWidget {
  const WarningMessageWidget({Key? key}) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return Container(
      width: MediaQuery.of(context).size.width,
      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 8),
      decoration: BoxDecoration(
        color: Colors.white,
        border: Border.all(color: AppColors.primary, width: 2),
        boxShadow: const [
          BoxShadow(color: Color(0x19777777), blurRadius: 5, spreadRadius: 0),
        ],
      ),
      child: const Text(
        AppConstants.warningMessage,
        textAlign: TextAlign.center,
        style: TextStyle(
          color: AppColors.warning,
          fontSize: 12,
          fontFamily: 'Pretendard',
          fontWeight: FontWeight.w700,
          height: 1.25,
        ),
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
      decoration: BoxDecoration(
        color: Colors.white,
        border: const Border(
          top: BorderSide(color: AppColors.border, width: 0.7),
        ),
        boxShadow: const [
          BoxShadow(
            color: AppColors.shadow,
            blurRadius: 10,
            offset: Offset(0, -1),
            spreadRadius: 0,
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
          // 네비게이션 로직 추가
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
              // 현재 페이지이므로 아무것도 하지 않음
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
              color: isSelected ? AppColors.primary : AppColors.textSecondary,
            ),
            const SizedBox(height: 4),
            Text(
              item.label,
              style: TextStyle(
                color: isSelected ? AppColors.primary : AppColors.textSecondary,
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
