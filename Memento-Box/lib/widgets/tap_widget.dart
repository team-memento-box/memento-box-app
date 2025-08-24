import 'package:flutter/material.dart';

class CustomBottomNavBar extends StatelessWidget {
  final int currentIndex;

  const CustomBottomNavBar({super.key, required this.currentIndex});

  @override
  Widget build(BuildContext context) {
    return BottomNavigationBar(
      type: BottomNavigationBarType.fixed,
      currentIndex: currentIndex,
      selectedItemColor: const Color(0xFF00C8B8),
      unselectedItemColor: const Color(0xFF555555),
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
      items: const [
        BottomNavigationBarItem(icon: Icon(Icons.home), label: '홈'),
        BottomNavigationBarItem(icon: Icon(Icons.photo), label: '사진첩'),
        BottomNavigationBarItem(icon: Icon(Icons.add), label: '사진 추가'),
        BottomNavigationBarItem(icon: Icon(Icons.receipt), label: '보고서'),
        BottomNavigationBarItem(icon: Icon(Icons.person), label: '나의 정보'),
      ],
    );
  }
}
