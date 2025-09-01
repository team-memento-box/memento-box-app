import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../utils/routes.dart';
import '../utils/styles.dart';
import '../user_provider.dart';

class CustomBottomNavBar extends StatelessWidget {
  final int currentIndex;

  const CustomBottomNavBar({super.key, required this.currentIndex});

  @override
  Widget build(BuildContext context) {
    final isGuardian = context.watch<UserProvider>().isGuardian;
    Color selected_color = const Color(0xFF62BE8A);
    Color unselected_color = const Color(0xFF777777);

    return BottomNavigationBar(
      type: BottomNavigationBarType.fixed,
      currentIndex: currentIndex,
      selectedItemColor: selected_color,
      unselectedItemColor: unselected_color,
      selectedLabelStyle: tapLabelStyle,
      unselectedLabelStyle: tapLabelStyle,
      onTap: (index) {
        switch (index) {
          case 0:
            Navigator.pushReplacementNamed(context, '/home');
            break;
          case 1:
            Navigator.pushReplacementNamed(context, '/gallery');
            break;
          case 2:
            Navigator.pushReplacementNamed(context, '/addphoto');
            break;
          case 3:
            Navigator.pushReplacementNamed(context, '/report');
            break;
          case 4:
            Navigator.pushReplacementNamed(context, '/profile');
            break;
        }
      },
      items: [
        BottomNavigationBarItem(
          icon: Image.asset('assets/icons/Home.png'),
          activeIcon: Image.asset(
            'assets/icons/Home_fill.png',
            color: selected_color, // 덮어씌울 색상
            colorBlendMode: BlendMode.srcIn, // 색상만 입히기
          ),
          label: '홈',
        ),
        BottomNavigationBarItem(
          icon: Image.asset('assets/icons/Image.png'),
          activeIcon: Image.asset(
            'assets/icons/Image_fill.png',
            color: selected_color, // 덮어씌울 색상
            colorBlendMode: BlendMode.srcIn, // 색상만 입히기
          ),
          label: '사진첩',
        ),
        BottomNavigationBarItem(
          icon: Image.asset(
            isGuardian == true
                ? 'assets/icons/Add.png'
                : 'assets/icons/Comment-plus.png',
          ),
          activeIcon: Image.asset(
            isGuardian == true
                ? 'assets/icons/Add_fill.png'
                : 'assets/icons/Comment-plus_fill.png',
            color: selected_color, // 덮어씌울 색상
            colorBlendMode: BlendMode.srcIn, // 색상만 입히기
          ),
          label: isGuardian == true ? '사진 추가' : '대화하기',
        ),
        BottomNavigationBarItem(
          icon: Image.asset('assets/icons/Invoice.png'),
          activeIcon: Image.asset(
            'assets/icons/Invoice_fill.png',
            color: selected_color, // 덮어씌울 색상
            colorBlendMode: BlendMode.srcIn, // 색상만 입히기
          ),
          label: '보고서',
        ),
        BottomNavigationBarItem(
          icon: Image.asset('assets/icons/User.png'),
          activeIcon: Image.asset(
            'assets/icons/User_fill.png',
            color: selected_color, // 덮어씌울 색상
            colorBlendMode: BlendMode.srcIn, // 색상만 입히기
          ),
          label: '나의 정보',
        ),
      ],
    );
  }
}
