import 'package:flutter/material.dart';

class AssistantBubble extends StatelessWidget {
  final String text;
  final bool isActive;

  const AssistantBubble({
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
            'assets/icons/Robot.png',
            color: isActive ? Color(0xFF00C8B8) : null,
            colorBlendMode: BlendMode.srcIn,
          ),
          // child: const CircleAvatar(
          //   radius: 24,
          //   backgroundImage: AssetImage(
          //     'assets/icons/Robot.png',
          //     color: isActive ? Color(0xFFD95753) : null,
          //   ),
          // ),
          // Container(
          //   width: 48,
          //   height: 48,
          //   decoration: BoxDecoration(
          //     shape: BoxShape.circle,
          //     color: isActive ? Color(0xFF00C8B8) : Colors.transparent,
          //     border: isActive
          //         ? Border.all(color: Colors.orange, width: 3)
          //         : null,
          //   ),
          // ),
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
