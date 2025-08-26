import 'package:flutter/material.dart';

class InfoDialog {
  /// 인지 건강 지수 설명 팝업
  static void showCognitiveInfo(BuildContext context) {
    showDialog(
      context: context,
      barrierDismissible: true,
      barrierColor: Colors.black.withOpacity(0.5),
      builder: (BuildContext context) {
        return const _InfoDialogWidget(
          title: '인지 건강 지수',
          icon: Icons.psychology,
          description: 'CIST(Cognitive Impairment Screening Test) 기반으로 인지기능을 평가하여 \n도출되는 지수입니다.\n\n지능, 기억력, 주의력, 언어능력 등 \n인지기능의 여러 영역을 종합적으로 \n평가하여 나이 대비 인지 상태를 \n알려드립니다.',
        );
      },
    );
  }
  
  /// 대화 건강 지수 설명 팝업
  static void showConversationInfo(BuildContext context) {
    showDialog(
      context: context,
      barrierDismissible: true,
      barrierColor: Colors.black.withOpacity(0.5),
      builder: (BuildContext context) {
        return const _InfoDialogWidget(
          title: '대화 건강 지수',
          icon: Icons.record_voice_over,
          description: '음성과 언어(텍스트) 분석을 기반으로 \n도출되는 대화 능력 지수입니다.\n\n대화의 유창성, 단어 선택, 언어 구조, \n음성의 명확성 등을 종합적으로 \n분석하여 의사소통 능력을 \n평가합니다.',
        );
      },
    );
  }
}

/// 재사용 가능한 정보 다이얼로그 위젯
class _InfoDialogWidget extends StatelessWidget {
  final String title;
  final IconData icon;
  final String description;

  const _InfoDialogWidget({
    required this.title,
    required this.icon,
    required this.description,
  });

  @override
  Widget build(BuildContext context) {
    return Dialog(
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(20),
      ),
      child: Container(
        padding: const EdgeInsets.all(24),
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(20),
          boxShadow: [
            BoxShadow(
              color: Colors.black.withOpacity(0.1),
              blurRadius: 10,
              offset: const Offset(0, 5),
            ),
          ],
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            // 아이콘
            Container(
              width: 60,
              height: 60,
              decoration: BoxDecoration(
                color: const Color(0xFF7CD0A0).withOpacity(0.1),
                shape: BoxShape.circle,
              ),
              child: Icon(
                icon,
                color: const Color(0xFF7CD0A0),
                size: 30,
              ),
            ),
            
            const SizedBox(height: 16),
            
            // 제목
            Text(
              title,
              style: const TextStyle(
                fontSize: 20,
                fontWeight: FontWeight.w700,
                fontFamily: 'Pretendard',
                color: Color(0xFF111111),
              ),
            ),
            
            const SizedBox(height: 12),
            
            // 설명
            Text(
              description,
              style: const TextStyle(
                fontSize: 14,
                fontWeight: FontWeight.w500,
                fontFamily: 'Pretendard',
                color: Color(0xFF555555),
                height: 1.5,
              ),
              textAlign: TextAlign.center,
            ),
            
            const SizedBox(height: 20),
            
            // 확인 버튼
            SizedBox(
              width: double.infinity,
              child: ElevatedButton(
                onPressed: () => Navigator.pop(context),
                style: ElevatedButton.styleFrom(
                  backgroundColor: const Color(0xFF7CD0A0),
                  padding: const EdgeInsets.symmetric(vertical: 12),
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(12),
                  ),
                  elevation: 0,
                ),
                child: const Text(
                  '확인',
                  style: TextStyle(
                    color: Colors.white,
                    fontSize: 16,
                    fontWeight: FontWeight.w600,
                    fontFamily: 'Pretendard',
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}