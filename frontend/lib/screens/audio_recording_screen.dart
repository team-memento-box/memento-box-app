import 'package:flutter/material.dart';
import 'dart:io';
import '../services/dementia_analysis_service.dart';
import 'report_speech_screen.dart';

/// 음성 녹음 및 분석 화면 (예시)
class AudioRecordingScreen extends StatefulWidget {
  const AudioRecordingScreen({Key? key}) : super(key: key);

  @override
  State<AudioRecordingScreen> createState() => _AudioRecordingScreenState();
}

class _AudioRecordingScreenState extends State<AudioRecordingScreen> {
  bool _isAnalyzing = false;

  /// 음성 파일 분석 및 결과 화면으로 이동
  Future<void> _analyzeAudioFile(File audioFile) async {
    setState(() {
      _isAnalyzing = true;
    });

    try {
      // 백엔드 API 호출
      final result = await DementiaAnalysisService.analyzeAudioFile(
        audioFile: audioFile,
        userId: "user123",       // 실제로는 현재 로그인된 사용자 ID
        familyId: "family456",   // 실제로는 사용자의 가족 ID
        photoId: "photo789",     // 선택사항: 관련된 사진 ID
      );

      // API 응답을 UI 데이터로 변환
      final healthData = result.toHealthAnalysisData(
        userName: "서봉봉",      // 실제로는 사용자 이름
        ageGroup: "60대",        // 실제로는 사용자 연령대
        ageGroupAverageRatio: 0.25, // 연령대별 평균 비율
      );

      // 결과 화면으로 이동
      if (mounted) {
        Navigator.push(
          context,
          MaterialPageRoute(
            builder: (context) => ConversationHealthAnalysisScreen(
              data: healthData,
            ),
          ),
        );
      }
    } catch (e) {
      // 오류 처리
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('분석 중 오류가 발생했습니다: $e'),
            backgroundColor: Colors.red,
          ),
        );
      }
    } finally {
      setState(() {
        _isAnalyzing = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('음성 치매 분석'),
      ),
      body: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Text(
              '음성을 녹음하고 분석해보세요',
              style: TextStyle(fontSize: 18),
            ),
            const SizedBox(height: 20),
            
            // 녹음 버튼 (실제 녹음 기능은 여기에 구현)
            ElevatedButton(
              onPressed: _isAnalyzing ? null : () {
                // TODO: 실제 음성 녹음 기능 구현
                // 임시로 테스트 파일 사용
                _showTestDialog();
              },
              child: const Text('음성 녹음 시작'),
            ),
            
            const SizedBox(height: 20),
            
            if (_isAnalyzing)
              const Column(
                children: [
                  CircularProgressIndicator(),
                  SizedBox(height: 10),
                  Text('음성을 분석하고 있습니다...'),
                ],
              ),
          ],
        ),
      ),
    );
  }

  /// 테스트용 다이얼로그
  void _showTestDialog() {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('테스트'),
        content: const Text('실제 녹음 기능이 구현되면, 녹음된 파일을 분석합니다.\n\n현재는 테스트용으로 더미 데이터를 사용합니다.'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('취소'),
          ),
          TextButton(
            onPressed: () {
              Navigator.pop(context);
              _showTestResult();
            },
            child: const Text('테스트 실행'),
          ),
        ],
      ),
    );
  }

  /// 테스트용 결과 표시 (실제 API 호출 없이)
  void _showTestResult() {
    // 실제 API 응답과 동일한 형태의 테스트 데이터
    final testResult = DementiaAnalysisResult(
      success: true,
      audioFile: "test_audio.wav",
      totalSegments: 8,
      dementiaDetected: true,
      dementiaSegmentsCount: 5,
      normalSegmentsCount: 3,
      dementiaRatio: 0.625,
      segmentDetails: [], // 실제로는 세그먼트 상세 정보
      overallPrediction: 1,
      overallPredictionLabel: "AD(1)",
      classNames: ["CN(0)", "AD(1)"],
    );

    // UI 데이터로 변환
    final healthData = testResult.toHealthAnalysisData(
      userName: "서봉봉",
      ageGroup: "60대",
      ageGroupAverageRatio: 0.25,
    );

    // 결과 화면으로 이동
    Navigator.push(
      context,
      MaterialPageRoute(
        builder: (context) => ConversationHealthAnalysisScreen(
          data: healthData,
        ),
      ),
    );
  }
}