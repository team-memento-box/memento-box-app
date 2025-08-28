// 작성자: hyunsung
// 작성일: 25.06.02
// 수정자: OH
// 수정일: 25.06.03

import 'package:flutter/material.dart';
import 'package:memento_box_app/utils/audio_service.dart';
import '../widgets/tap_widget.dart';
import '../widgets/group_bar_widget.dart';
import '../widgets/ai_record_play_sheet.dart';
import '../utils/routes.dart';
import '../utils/audio_service.dart';
import '../utils/styles.dart';
import '../widgets/audio_player_widget.dart';
import '../models/photo.dart'; // ← Photo 모델 import 추가
import 'package:provider/provider.dart'; // ✅ Provider import
import '../user_provider.dart'; // ✅ 사용자 Provider import
import '../core/supabase_service.dart'; // ✅ Supabase 서비스 import
import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:flutter_dotenv/flutter_dotenv.dart';

class PhotoDetailScreen extends StatefulWidget {
  final Map<String, dynamic> photoData; // ← Photo Map 데이터로 변경

  const PhotoDetailScreen({Key? key, required this.photoData}) : super(key: key);

  @override
  State<PhotoDetailScreen> createState() => _PhotoDetailScreenState();
}

class _PhotoDetailScreenState extends State<PhotoDetailScreen> {
  late AudioService _audioService;
  final audioPath = 'assets/voice/2025-05-26_서봉봉님_대화분석보고서.mp3';

  @override
  void initState() {
    super.initState();
    _audioService = AudioService();
    
    // 디버깅용 Photo 데이터 출력
    print('=== Photo 데이터 디버깅 ===');
    print('photo_id: ${widget.photoData['photo_id']}');
    print('image_url: ${widget.photoData['image_url']}');
    print('description: ${widget.photoData['description']}');
    print('tags: ${widget.photoData['tags']}');
    print('taken_at: ${widget.photoData['taken_at']}');
    print('upload_date: ${widget.photoData['upload_date']}');
    print('user_name: ${widget.photoData['user_name']}');
    print('family_role: ${widget.photoData['family_role']}');
    print('profile_img: ${widget.photoData['profile_img']}');
    print('user_profile_image: ${widget.photoData['user_profile_image']}');
    print('=====================');
  }

  @override
  void dispose() {
    _audioService.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final familyName = Provider.of<UserProvider>(context, listen: false).familyName ?? '우리 가족';
    final isGuardian = Provider.of<UserProvider>(context).isGuardian ?? true;

    return Scaffold(
      backgroundColor: const Color(0xFFF7F7F7),
      appBar: GroupBar(title: familyName), // ← familyName 사용
      body: Column(
        children: [
          // 프로필 섹션
          Container(
            width: double.infinity,
            height: 80,
            color: Colors.white,
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
            child: Row(
              children: [
                // 프로필 이미지
                ClipRRect(
                  borderRadius: BorderRadius.circular(25),
                  child: widget.photoData['user_profile_image'] != null
                      ? Image.network(
                          widget.photoData['user_profile_image'],
                          width: 50,
                          height: 50,
                          fit: BoxFit.cover,
                          errorBuilder: (context, error, stackTrace) => Container(
                            width: 50,
                            height: 50,
                            color: Colors.grey[300],
                            child: const Icon(Icons.person, color: Colors.white),
                          ),
                        )
                      : Container(
                          width: 50,
                          height: 50,
                          color: Colors.grey[300],
                          child: const Icon(Icons.person, color: Colors.white),
                        ),
                ),
                const SizedBox(width: 16),
                // 정보
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Row(
                        children: [
                          Text(
                            widget.photoData['user_name'] ?? '',
                            style: const TextStyle(
                              fontSize: 18,
                              fontWeight: FontWeight.bold,
                              height: 1.2,
                            ),
                          ),
                          const SizedBox(width: 8),
                          Container(
                            padding: const EdgeInsets.symmetric(
                              horizontal: 6,
                              vertical: 2,
                            ),
                            decoration: BoxDecoration(
                              color: Colors.grey,
                              borderRadius: BorderRadius.circular(10),
                            ),
                            child: Text(
                              widget.photoData['family_role'] ?? '',
                              style: const TextStyle(
                                color: Colors.white,
                                fontFamily: 'Pretendard',
                                fontSize: 13,
                                fontWeight: FontWeight.w800,
                              ),
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 4),
                      Text(
                        _formatDate(widget.photoData['upload_date']),
                        style: const TextStyle(
                          fontFamily: 'Pretendard',
                          fontSize: 15,
                          fontWeight: FontWeight.w600,
                          color: Color(0xFF555555),
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),

          // 메인 이미지
          Expanded(
            child: Container(
              width: double.infinity,
              decoration: BoxDecoration(
                image: DecorationImage(
                  image: NetworkImage(widget.photoData['image_url'] ?? ''),
                  fit: BoxFit.cover,
                ),
              ),
            ),
          ),

          // 하단 정보
          Container(
            color: Colors.white,
            padding: const EdgeInsets.all(20),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Text(
                      '${_getYear()}년',
                      style: const TextStyle(
                        fontSize: 20,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                    const SizedBox(width: 8),
                    Text(
                      _seasonKor(_getSeason()),
                      style: const TextStyle(
                        fontSize: 20,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 8),
                Text(
                  widget.photoData['description'] ?? '',
                  style: const TextStyle(
                    fontFamily: 'Pretendard',
                    fontSize: 16,
                    fontWeight: FontWeight.w700,
                    color: Color(0xFF555555),
                  ),
                ),
                const SizedBox(height: 20),

                // 버튼들
                Row(
                  children: [
                    Expanded(
                      child: isGuardian
                          ? ElevatedButton(
                              onPressed: () async {
                                final storyData = await fetchPhotoStory(widget.photoData['photo_id']);
                                if (storyData != null) {
                                  String audioUrl = '';
                                if (storyData['tts_audio_path'] != null) {
                                  String pathInDb = storyData['tts_audio_path'];
                                  print('Original audio path: $pathInDb');
                                  
                                  // 'fishspeech/' 프리픽스 제거 → 오브젝트 키
                                  final objectKey = pathInDb.startsWith('fishspeech/')
                                      ? pathInDb.substring('fishspeech/'.length)
                                      : pathInDb;
                                  print('Object key: $objectKey');
                                  
                                  // 서명 URL 생성 (60초 유효)
                                  try {
                                    audioUrl = await SupabaseService.client.storage
                                        .from('fishspeech')
                                        .createSignedUrl(objectKey, 60);
                                    print('Generated signed URL: $audioUrl');
                                  } catch (e) {
                                    print('Signed URL 생성 실패: $e');
                                  }
                                }
                                  // source_session_ids에서 첫 번째 세션 ID 가져오기
                                  String? sessionId;
                                  if (storyData['source_session_ids'] != null && 
                                      (storyData['source_session_ids'] as List).isNotEmpty) {
                                    sessionId = (storyData['source_session_ids'] as List)[0];
                                  }
                                  
                                  showSummaryModal(
                                    context,
                                    audioPath: audioUrl,
                                    audioService: _audioService,
                                    summaryText: storyData['story_text'],
                                    createdAt: storyData['created_at'],
                                    sessionId: sessionId,
                                  );
                                } else {
                                  // 스토리가 없으면 기존 방식 사용
                                  final result = await fetchSummaryAndOriginVoice(widget.photoData['photo_id']);
                                  showSummaryModal(
                                    context,
                                    audioPath: result['summary_voice'] ?? '',
                                    audioService: _audioService,
                                    summaryText: result['summaryText'],
                                    createdAt: result['createdAt'],
                                    sessionId: null,
                                  );
                                }
                              },
                              style: ElevatedButton.styleFrom(
                                backgroundColor: const Color(0xFF8CCAA7),
                                padding: const EdgeInsets.symmetric(vertical: 12),
                                shape: RoundedRectangleBorder(
                                  borderRadius: BorderRadius.circular(20),
                                ),
                              ),
                              child: const Text(
                                '대화 듣기',
                                style: TextStyle(
                                  color: Colors.white,
                                  fontSize: 20,
                                  fontWeight: FontWeight.w800,
                                ),
                              ),
                            )
                          : ElevatedButton(
                              onPressed: () async {
                                try {
                                  // Supabase 세션에서 JWT 토큰 가져오기
                                  final session = SupabaseService.client.auth.currentSession;
                                  
                                  if (session == null || session.accessToken.isEmpty) {
                                    // 로그인되지 않은 경우 로그인 화면으로 이동
                                    ScaffoldMessenger.of(context).showSnackBar(
                                      const SnackBar(content: Text('로그인이 필요합니다.'))
                                    );
                                    Navigator.pushNamed(context, '/signin');
                                    return;
                                  }
                                  
                                  // 대화 화면으로 이동 (JWT 토큰과 함께)
                                  Navigator.pushNamed(
                                    context, 
                                    Routes.conversation,
                                    arguments: {
                                      'photoId': widget.photoData['photo_id'],
                                      'photoUrl': widget.photoData['image_url'],
                                      'jwtToken': session.accessToken,
                                    },
                                  );
                                } catch (e) {
                                  print('대화 시작 오류: $e');
                                  ScaffoldMessenger.of(context).showSnackBar(
                                    const SnackBar(content: Text('대화를 시작할 수 없습니다. 다시 시도해주세요.'))
                                  );
                                }
                              },
                              style: ElevatedButton.styleFrom(
                                backgroundColor: const Color(0xFF8CCAA7),
                                padding: const EdgeInsets.symmetric(vertical: 12),
                                shape: RoundedRectangleBorder(
                                  borderRadius: BorderRadius.circular(20),
                                ),
                              ),
                              child: const Text(
                                '대화하기',
                                style: TextStyle(
                                  color: Colors.white,
                                  fontSize: 20,
                                  fontWeight: FontWeight.w800,
                                ),
                              ),
                            ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: OutlinedButton(
                        onPressed: () {
                          Navigator.pop(context);
                        },
                        style: OutlinedButton.styleFrom(
                          side: const BorderSide(
                            color: Color(0xFF8CCAA7),
                            width: 2,
                          ),
                          padding: const EdgeInsets.symmetric(vertical: 12),
                          shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(20),
                          ),
                        ),
                        child: const Text(
                          '목록 보기',
                          style: TextStyle(
                            color: Color(0xFF8CCAA7),
                            fontSize: 20,
                            fontWeight: FontWeight.w800,
                          ),
                        ),
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
        ],
      ),
      bottomNavigationBar: const CustomBottomNavBar(currentIndex: 1),
    );
  }

  // 년도 추출 (gallery_screen.dart의 PhotoWithConv 클래스와 동일한 로직)
  int _getYear() {
    // 1순위: tags에서 년도 정보 추출
    final tags = widget.photoData['tags'] as List<dynamic>?;
    if (tags != null) {
      for (var tag in tags) {
        if (tag is String && RegExp(r'^\d{4}$').hasMatch(tag)) {
          return int.parse(tag);
        }
      }
    }
    
    // 2순위: taken_at 사용
    final takenAt = widget.photoData['taken_at'];
    if (takenAt != null) {
      if (takenAt is DateTime) {
        return takenAt.year;
      } else if (takenAt is String) {
        return DateTime.parse(takenAt).year;
      }
    }
    
    // 3순위: upload_date 사용
    final uploadDate = widget.photoData['upload_date'];
    if (uploadDate is DateTime) {
      return uploadDate.year;
    } else if (uploadDate is String) {
      return DateTime.parse(uploadDate).year;
    }
    
    return DateTime.now().year;
  }

  // 계절 추출 (gallery_screen.dart의 PhotoWithConv 클래스와 동일한 로직)
  String _getSeason() {
    // 1순위: tags에서 계절 정보 추출
    final tags = widget.photoData['tags'] as List<dynamic>?;
    if (tags != null) {
      for (var tag in tags) {
        if (tag is String && ['spring', 'summer', 'autumn', 'winter'].contains(tag.toLowerCase())) {
          return tag.toLowerCase();
        }
      }
    }
    
    // 2순위: taken_at 기준으로 계절 계산
    DateTime dateToUse = DateTime.now();
    final takenAt = widget.photoData['taken_at'];
    
    if (takenAt != null) {
      if (takenAt is DateTime) {
        dateToUse = takenAt;
      } else if (takenAt is String) {
        dateToUse = DateTime.parse(takenAt);
      }
    } else {
      // 3순위: upload_date 사용
      final uploadDate = widget.photoData['upload_date'];
      if (uploadDate is DateTime) {
        dateToUse = uploadDate;
      } else if (uploadDate is String) {
        dateToUse = DateTime.parse(uploadDate);
      }
    }
    
    return _getSeasonFromDate(dateToUse);
  }

  String _getSeasonFromDate(DateTime date) {
    final month = date.month;
    if (month >= 3 && month <= 5) return 'spring';
    if (month >= 6 && month <= 8) return 'summer';
    if (month >= 9 && month <= 11) return 'autumn';
    return 'winter';
  }

  String _formatDate(dynamic date) {
    DateTime dateTime;
    if (date is DateTime) {
      dateTime = date;
    } else if (date is String) {
      dateTime = DateTime.parse(date);
    } else {
      dateTime = DateTime.now();
    }
    
    return '${dateTime.year}년 ${dateTime.month.toString().padLeft(2, '0')}월 ${dateTime.day.toString().padLeft(2, '0')}일';
  }

  String _seasonKor(String eng) {
    switch (eng) {
      case 'spring':
        return '봄';
      case 'summer':
        return '여름';
      case 'autumn':
        return '가을';
      case 'winter':
        return '겨울';
      default:
        return eng;
    }
  }

  // 포토 스토리 데이터 가져오기 (Supabase)
  Future<Map<String, dynamic>?> fetchPhotoStory(String photoId) async {
    print('fetchPhotoStory 호출됨 - photoId: $photoId');
    try {
      final response = await SupabaseService.client
          .from('photo_stories')
          .select()
          .eq('photo_id', photoId)
          .order('created_at', ascending: false)
          .limit(1);

      if (response.isNotEmpty) {
        print('포토 스토리 데이터 가져오기 성공: ${response.first}');
        return response.first as Map<String, dynamic>;
      } else {
        print('해당 photo_id에 대한 스토리가 없습니다.');
        return null;
      }
    } catch (e) {
      print('fetchPhotoStory 에러: $e');
      return null;
    }
  }

  // 스토리 텍스트를 보여주는 모달
  void _showStoryTextModal(BuildContext context, String storyText, String title) {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (context) => DraggableScrollableSheet(
        initialChildSize: 0.7,
        maxChildSize: 0.9,
        minChildSize: 0.3,
        builder: (context, scrollController) => Container(
          decoration: const BoxDecoration(
            color: Colors.white,
            borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
          ),
          child: Column(
            children: [
              // 핸들
              Container(
                margin: const EdgeInsets.symmetric(vertical: 12),
                width: 40,
                height: 4,
                decoration: BoxDecoration(
                  color: Colors.grey[300],
                  borderRadius: BorderRadius.circular(2),
                ),
              ),
              // 제목
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 20),
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Text(
                      title,
                      style: const TextStyle(
                        fontSize: 20,
                        fontWeight: FontWeight.w700,
                        fontFamily: 'Pretendard',
                      ),
                    ),
                    IconButton(
                      onPressed: () => Navigator.pop(context),
                      icon: const Icon(Icons.close),
                    ),
                  ],
                ),
              ),
              const Divider(),
              // 스토리 텍스트
              Expanded(
                child: SingleChildScrollView(
                  controller: scrollController,
                  padding: const EdgeInsets.all(20),
                  child: Text(
                    storyText,
                    style: const TextStyle(
                      fontSize: 16,
                      fontFamily: 'Pretendard',
                      height: 1.6,
                      color: Color(0xFF333333),
                    ),
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Future<Map<String, String?>> fetchSummaryAndOriginVoice(String photoId) async {
    print('fetchSummaryAndOriginVoice 호출됨');
    try {
      final baseUrl = dotenv.env['BASE_URL'];
      if (baseUrl == null) {
        print('BASE_URL이 null입니다!');
        return {'summaryText': null, 'originVoiceUrl': null, 'createdAt': null};
      }

      // 1. 최신 대화 정보 가져오기
      final latestConvRes = await http.get(Uri.parse('$baseUrl/api/photos/$photoId/latest_conversation'));
      if (latestConvRes.statusCode != 200) return {'summaryText': null, 'originVoiceUrl': null};
      final latestConv = jsonDecode(utf8.decode(latestConvRes.bodyBytes));
      
      final convId = latestConv['id'];
      final createdAt = latestConv['created_at'];
      print('convId: $convId');

      // 2. summary_text 가져오기
      final summaryRes = await http.get(Uri.parse('$baseUrl/api/photos/$photoId/conversations/$convId/summary_text'));
      String? summaryText;
      if (summaryRes.statusCode == 200) {
        final summary = jsonDecode(utf8.decode(summaryRes.bodyBytes));
        summaryText = summary['summary_text'];
      }

      // 3. origin_voice 가져오기
      final voiceRes = await http.get(Uri.parse('$baseUrl/api/photos/$photoId/conversations/$convId/summary_voice'));
      String? summary_voice;
      if (voiceRes.statusCode == 200) {
        final voice = jsonDecode(utf8.decode(voiceRes.bodyBytes));
        summary_voice = voice['summary_voice'];
      }

      return {
        'summaryText': summaryText,
        'summary_voice': summary_voice,
        'createdAt': createdAt,
      };
    } catch (e, st) {
      print('fetchSummaryAndOriginVoice 에러: $e');
      print(st);
      return {'summaryText': null, 'summary_voice': null, 'createdAt': null};
    }
  }

}