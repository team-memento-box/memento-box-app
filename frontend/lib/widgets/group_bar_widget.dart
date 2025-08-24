import 'package:flutter/material.dart';

class GroupBar extends StatelessWidget implements PreferredSizeWidget {
  final String title;

  const GroupBar({super.key, required this.title});

  @override
  Widget build(BuildContext context) {
    return AppBar(
      automaticallyImplyLeading: false,
      backgroundColor: const Color(0xFF00C8B8),
      elevation: 0,
      toolbarHeight: 80,
      centerTitle: true,
      title: Align(
        alignment: Alignment.bottomCenter,
        child: Text(
          title,
          style: const TextStyle(
            fontSize: 24,
            fontWeight: FontWeight.w800,
            color: Colors.white,
            fontFamily: 'Pretendard',
          ),
        ),
      ),
    );
  }

  @override
  Size get preferredSize => const Size.fromHeight(80);
}
