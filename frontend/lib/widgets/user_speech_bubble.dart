import 'package:flutter/material.dart';

class UserSpeechBubble extends StatelessWidget {
  final String text;
  final bool isActive;

  const UserSpeechBubble({
    required this.text,
    required this.isActive,
    super.key,
  });

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 20),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.center,
        children: [
          Image.asset(
            'assets/icons/Mic.png',
            color: isActive ? Color(0xFFD95753) : null,
            // Color(0xFF555555)
            colorBlendMode: BlendMode.srcIn,
          ),
          const SizedBox(width: 12),
          Flexible(
            child: Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: const Color(0xFFDEDEDE),
                borderRadius: BorderRadius.circular(10),
              ),
              child: Text(
                text,
                style: const TextStyle(
                  fontSize: 24,
                  fontWeight: FontWeight.w700,
                  fontFamily: 'Pretendard',
                  height: 1.2,
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}
