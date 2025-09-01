import 'package:flutter/material.dart';

class GroupBar extends StatelessWidget implements PreferredSizeWidget {
  final String title;
  final List<Widget>? actions;
  final Widget? leading;

  const GroupBar({
      super.key,
      required this.title,
      this.actions,   // ← 추가
      this.leading,   // ← 추가
    });
  @override
  Widget build(BuildContext context) {
    return AppBar(
      automaticallyImplyLeading: false,
      backgroundColor: const Color(0xFF8CCAA7),
      elevation: 0,
      toolbarHeight: 80,
      centerTitle: true,
      leading: leading, 
      actions: actions,
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
