import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'dart:convert';
import '../data/user_data.dart';
import '../utils/styles.dart';
import '../widgets/tap_widget.dart';
import '../widgets/group_bar_widget.dart';
import 'report_detail_screen.dart'; // ReportDetailScreen import 추가
import 'package:provider/provider.dart';
import '../user_provider.dart';
import '../data/report_api.dart';
import '../models/report.dart';

class ReportListScreen extends StatefulWidget {
  const ReportListScreen({Key? key}) : super(key: key);

  @override
  State<ReportListScreen> createState() => _ReportListScreenState();
}

class _ReportListScreenState extends State<ReportListScreen> {
  List<Report> reports = [];
  bool isLoading = true;

  @override
  void initState() {
    super.initState();
    _loadReports();
  }

  Future<void> _loadReports() async {
    setState(() => isLoading = true);
    try {
      final accessToken = Provider.of<UserProvider>(context, listen: false).accessToken;
      if (accessToken == null) {
        print('==== [DEBUG] No accessToken found!');
        setState(() {
          reports = [];
          isLoading = false;
        });
        return;
      }
      final result = await ReportApi.fetchReports(accessToken);
      print('==== [DEBUG] _loadReports result.length: [32m${result.length}[0m');
      for (var i = 0; i < result.length; i++) {
        print('==== [DEBUG] _loadReports report[$i]: anomalyReport=${result[i].anomalyReport}, created_at=${result[i].created_at}');
      }
      setState(() {
        reports = result;
        isLoading = false;
      });
    } catch (e) {
      print('==== [DEBUG] _loadReports error: $e');
      setState(() {
        reports = [];
        isLoading = false;
      });
      // 에러 처리(토스트 등)
    }
  }

  // 파일명에서 사용자 친화적인 제목 생성
  String _generateDisplayTitle(String fileName) {
    try {
      // 파일명 패턴: "2025-05-26_서봉봉님_대화분석보고서"
      final parts = fileName.split('_');

      if (parts.length >= 2) {
        final datePart = parts[0]; // "2025-05-26"
        final namePart = parts[1]; // "서봉봉님"

        // 날짜 포맷팅 (시간은 임의로 생성하거나 기본값 사용)
        final dateTime = _parseDate(datePart);
        final timeString = _generateTimeString(fileName);

        return '$datePart $timeString $namePart 대화 분석 보고서';
      } else {
        // 패턴이 맞지 않으면 파일명 그대로 사용
        return fileName.replaceAll('_', ' ');
      }
    } catch (e) {
      // 오류 발생 시 파일명 그대로 반환
      return fileName.replaceAll('_', ' ');
    }
  }

  // 날짜 파싱
  DateTime? _parseDate(String dateString) {
    try {
      final dateParts = dateString.split('-');
      if (dateParts.length == 3) {
        return DateTime(
          int.parse(dateParts[0]), // year
          int.parse(dateParts[1]), // month
          int.parse(dateParts[2]), // day
        );
      }
    } catch (e) {
      print('날짜 파싱 오류: $e');
    }
    return null;
  }

  // 파일명 기반으로 시간 문자열 생성 (해시를 이용한 일관된 시간)
  String _generateTimeString(String fileName) {
    // 파일명의 해시를 이용해 일관된 시간 생성
    final hash = fileName.hashCode.abs();
    final hour = (hash % 12) + 9; // 9시-20시 범위
    final minute = (hash ~/ 100) % 60; // 0-59분 범위

    return '${hour.toString().padLeft(2, '0')}:${minute.toString().padLeft(2, '0')}';
  }

  @override
  Widget build(BuildContext context) {
    final familyName = Provider.of<UserProvider>(context).familyName ?? '우리 가족';
    return Scaffold(
      backgroundColor: Colors.white,
      appBar: GroupBar(title: familyName),
      body: Column(
        children: [
          // Content Area
          Expanded(
            child: Container(
              color: const Color(0xFFF7F7F7),
              child: Column(
                children: [
                  const ContentHeaderWidget(),
                  Expanded(
                    child: ReportListWidget(
                      reports: reports,
                      isLoading: isLoading,
                      onRefresh: _loadReports,
                    ),
                  ),
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

// TODO: 나중에 API에서 받아온 설정 데이터로 대체
// 예시: appConfig = await fetchAppConfig();
class AppConstants {
  // TODO: 실제 앱 제목은 API에서 받아올 예정
  static const String appTitle = '시발^~^';

  // TODO: 실제 보고서 관련 텍스트는 API에서 받아올 예정
  static const String reportTitle = '2025-05-26 13:56 서봉봉님 대화 분석 보고서';
  static const String warningMessage =
      '비정상적인 상태가 의심되는 경우 병원에 방문해 정확한 진단을 진행해주세요.';
  static const String infoMessage =
      'AI가 대화를 분석해 평가한 상태 분석 보고서를 제공합니다.\n본 보고서는 참고 자료이며, 절대적인 해석이 아님을 유의해 주세요.';

  // TODO: 에러 메시지들도 API에서 받아와서 다국어 지원 예정
  static const String noReportsMessage = '분석 보고서가 없습니다.';
  static const String addFilesMessage = 'assets/analysis/ 폴더에 .txt 파일을 추가하세요.';
  static const String refreshButtonText = '새로고침';
}

// TODO: 실제 앱 설정 정보를 가져오는 함수 예시 (나중에 사용 예정)
// Future<Map<String, dynamic>> fetchAppConfig() async {
//   final response = await http.get(Uri.parse('${API_BASE_URL}/app-config'));
//   return json.decode(response.body);
// }

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

// 컨텐츠 헤더 위젯
class ContentHeaderWidget extends StatelessWidget {
  const ContentHeaderWidget({Key? key}) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return Container(
      width: MediaQuery.of(context).size.width,
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.white,
        boxShadow: const [
          BoxShadow(color: Color(0x19777777), blurRadius: 5, spreadRadius: 0),
        ],
      ),
      child: Text(
        AppConstants.infoMessage,
        textAlign: TextAlign.center,
        style: smallContentStyle.copyWith(fontSize: 13),
      ),
    );
  }
}

// 보고서 리스트 위젯 (수정됨)
class ReportListWidget extends StatelessWidget {
  final List<Report> reports;
  final bool isLoading;
  final VoidCallback onRefresh;

  const ReportListWidget({
    Key? key,
    required this.reports,
    required this.isLoading,
    required this.onRefresh,
  }) : super(key: key);

  @override
  Widget build(BuildContext context) {
    if (isLoading) {
      return Container(
        color: Colors.white,
        child: const Center(
          child: CircularProgressIndicator(color: AppColors.primary),
        ),
      );
    }

    if (reports.isEmpty) {
      return Container(
        color: Colors.white,
        child: Center(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Text(
                AppConstants.noReportsMessage,
                style: const TextStyle(
                  color: AppColors.textSecondary,
                  fontSize: 16,
                  fontFamily: 'Pretendard',
                  fontWeight: FontWeight.w500,
                ),
              ),
              const SizedBox(height: 8),
              Text(
                AppConstants.addFilesMessage,
                style: const TextStyle(
                  color: AppColors.textSecondary,
                  fontSize: 14,
                  fontFamily: 'Pretendard',
                  fontWeight: FontWeight.w400,
                ),
              ),
              const SizedBox(height: 16),
              ElevatedButton(
                onPressed: onRefresh,
                style: ElevatedButton.styleFrom(
                  backgroundColor: AppColors.primary,
                ),
                child: Text(
                  AppConstants.refreshButtonText,
                  style: const TextStyle(color: Colors.white),
                ),
              ),
            ],
          ),
        ),
      );
    }

    return Container(
      color: Colors.white,
      child: RefreshIndicator(
        onRefresh: () async => onRefresh(),
        child: ListView.builder(
          padding: EdgeInsets.zero,
          itemCount: reports.length,
          itemBuilder: (context, index) {
            final report = reports[index];
            // created_at을 yyyy-MM-dd HH:mm 포맷으로 변환
            String formattedDate = '';
            if (report.created_at != null) {
              final date = report.created_at;
              formattedDate =
                  '${date!.year.toString().padLeft(4, '0')}-${date.month.toString().padLeft(2, '0')}-${date.day.toString().padLeft(2, '0')} ${date.hour.toString().padLeft(2, '0')}:${date.minute.toString().padLeft(2, '0')}';
            }
            return ReportItemWidget(
              isSelected: index == 0,
              displayTitle: formattedDate.isNotEmpty ? '$formattedDate 대화 분석 보고서' : '대화 분석 보고서',
              createdAt: report.created_at?.toString() ?? '',
              report: report,
              allReports: reports,
              currentIndex: index,
            );
          },
        ),
      ),
    );
  }
}

// 개별 보고서 아이템 위젯 (수정됨 - 클릭 기능 추가)
class ReportItemWidget extends StatelessWidget {
  final bool isSelected;
  final String displayTitle;
  final String createdAt;
  final Report report;
  final List<Report> allReports;
  final int? currentIndex;

  const ReportItemWidget({
    Key? key,
    this.isSelected = false,
    required this.displayTitle,
    required this.createdAt,
    required this.report,
    required this.allReports,
    this.currentIndex,
  }) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: () {
        // 상세 보고서 화면으로 이동하면서 전체 리포트 목록과 현재 인덱스도 전달
        Navigator.push(
          context,
          MaterialPageRoute(
            builder: (context) => ReportDetailScreen(
              // 상세화면에 필요한 정보 전달 (예시)
              fileName: displayTitle,
              filePath: '', // asset 기반이 아니므로 빈 값
              allReports: allReports,
              currentIndex: currentIndex,
              reportId: report.reportId,
            ),
          ),
        );
      },
      child: Container(
        height: 55,
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
        decoration: BoxDecoration(
          color: Colors.white,
          border: Border(
            top: BorderSide(
              color: isSelected ? AppColors.primary : const Color(0x7F777777),
              width: isSelected ? 2 : 1.5,
            ),
          ),
          boxShadow: const [
            BoxShadow(color: Color(0x19555555), blurRadius: 5, spreadRadius: 2),
          ],
        ),
        child: Row(
          children: [
            Expanded(
              child: Text(
                displayTitle,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: const TextStyle(
                  color: AppColors.textSecondary,
                  fontSize: 18,
                  fontFamily: 'Pretendard',
                  fontWeight: FontWeight.w500,
                ),
              ),
            ),
            const SizedBox(width: 8),
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
      height: 50,
      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 16),

      decoration: BoxDecoration(
        color: Colors.white,
        border: Border(top: BorderSide(color: AppColors.primary, width: 2)),
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
        ),
      ),
    );
  }
}