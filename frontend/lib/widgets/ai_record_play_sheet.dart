import 'package:flutter/material.dart';
import '../utils/styles.dart';
import 'origin_record_play_sheet.dart';
import 'audio_player_widget.dart';
import '../utils/audio_service.dart';

// 'assets/voice/2025-05-26_서봉봉님_대화분석보고서.mp3';

void showSummaryModal(
  BuildContext context, {
  required String audioPath,
  required AudioService audioService,
  String? summaryText,
  String? createdAt,
}) {
  showModalBottomSheet(
    context: context,
    isScrollControlled: true,
    backgroundColor: const Color.fromARGB(230, 255, 255, 255),
    shape: const RoundedRectangleBorder(
      borderRadius: BorderRadius.vertical(top: Radius.circular(25)),
    ),
    builder: (_) =>
        SummaryModal(audioPath: audioPath, 
        audioService: audioService, 
        summaryText: summaryText, 
        createdAt: createdAt
      ),
  );
}

class SummaryModal extends StatefulWidget {
  final String audioPath;
  final AudioService audioService;
  final String? summaryText;
  final String? createdAt;

  const SummaryModal({
    super.key,
    required this.audioPath,
    required this.audioService,
    this.summaryText,
    this.createdAt,
  });

  @override
  State<SummaryModal> createState() => _SummaryModalState();
}

class _SummaryModalState extends State<SummaryModal>
    with SingleTickerProviderStateMixin {
  bool showTranscript = false;

  @override
  Widget build(BuildContext context) {
    final date = widget.createdAt != null ? DateTime.parse(widget.createdAt!) : DateTime.now();
    final formatted = '${date.year}년 ${date.month}월 ${date.day}일';

    return SingleChildScrollView(
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 10),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(
              width: 60,
              height: 5,
              margin: const EdgeInsets.only(bottom: 16),
              decoration: BoxDecoration(
                color: Colors.grey[400],
                borderRadius: BorderRadius.circular(10),
              ),
            ),
            Stack(
              alignment: Alignment.center,
              children: [
                Text(
                  '$formatted 대화 요약본',
                  style: mainContentStyle,
                  textAlign: TextAlign.center,
                ),
                if (showTranscript)
                  Align(
                    alignment: Alignment.centerLeft,
                    child: IconButton(
                      icon: const Icon(Icons.arrow_back_ios_new_rounded),
                      onPressed: () {
                        setState(() => showTranscript = false);
                      },
                    ),
                  ),
              ],
            ),
            const SizedBox(height: 12),
            Column(
              children: [
                AudioPlayerWidget(
                  audioPath: widget.audioPath,
                  audioService: widget.audioService,
                ),
              ],
            ),
            const SizedBox(height: 10),
            AnimatedSize(
              duration: const Duration(milliseconds: 300),
              curve: Curves.easeInOut,
              child: Column(
                children: [
                  if (!showTranscript)
                    Row(
                      children: [
                        Expanded(
                          child: ElevatedButton(
                            onPressed: () {
                              setState(() => showTranscript = true);
                            },
                            style: ElevatedButton.styleFrom(
                              backgroundColor: const Color(0xFF00C8B8),
                              padding: const EdgeInsets.symmetric(vertical: 10),
                              shape: RoundedRectangleBorder(
                                borderRadius: BorderRadius.circular(20),
                              ),
                            ),
                            child: const Text(
                              '내용 보기',
                              style: TextStyle(
                                color: Colors.white,
                                fontSize: 18,
                                fontFamily: 'Pretendard',
                                fontWeight: FontWeight.w800,
                              ),
                            ),
                          ),
                        ),
                        const SizedBox(width: 13),
                        Expanded(
                          child: OutlinedButton(
                            onPressed: () {
                              Navigator.pop(context); // 현재 모달 닫기
                              Future.delayed(
                                const Duration(milliseconds: 100),
                                () {
                                  if (context.mounted) {
                                    showOriginalModal(
                                      context,
                                      audioPath: widget.audioPath,
                                      audioService: widget.audioService,
                                    ); // 새 모달 열기
                                  }
                                },
                              );
                            },
                            style: OutlinedButton.styleFrom(
                              side: const BorderSide(
                                color: Color(0xFF00C8B8),
                                width: 2,
                              ),
                              shape: RoundedRectangleBorder(
                                borderRadius: BorderRadius.circular(20),
                              ),
                              padding: const EdgeInsets.symmetric(vertical: 10),
                            ),
                            child: const Text(
                              '원본 듣기',
                              style: TextStyle(
                                fontSize: 18,
                                fontWeight: FontWeight.w800,
                                color: Color(0xFF00C8B8),
                              ),
                            ),
                          ),
                        ),
                      ],
                    ),
                  if (showTranscript)
                    Container(
                      width: double.infinity,
                      margin: const EdgeInsets.symmetric(horizontal: 8),
                      padding: const EdgeInsets.symmetric(
                        horizontal: 12,
                        vertical: 10,
                      ),
                      decoration: BoxDecoration(
                        border: Border.all(
                          color: const Color(0xFF00C8B8),
                          width: 2,
                        ),
                        borderRadius: BorderRadius.circular(10),
                      ),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const Text(
                            '대화 내용:',
                            style: TextStyle(
                              color: Color(0xFF00C8B8),
                              fontSize: 14,
                              fontFamily: 'Pretendard',
                              fontWeight: FontWeight.w700,
                            ),
                          ),
                          const SizedBox(height: 8),
                          Text(
                            widget.summaryText ?? '요약 내용이 없습니다.',
                            style: const TextStyle(
                              color: Color(0xFF333333),
                              fontSize: 14,
                              fontFamily: 'Pretendard',
                              fontWeight: FontWeight.w500,
                              height: 1.4,
                            ),
                          ),
                          const SizedBox(height: 15),
                        ],
                      ),
                    ),
                  const SizedBox(height: 20),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}
