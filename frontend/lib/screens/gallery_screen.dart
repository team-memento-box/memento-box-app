// 작성자: OH
// 작성일: 2025.05
// 수정일: 2025.06.03

import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../widgets/group_bar_widget.dart';
import '../widgets/tap_widget.dart';
import '../utils/styles.dart';
import '../user_provider.dart';
import '../utils/routes.dart';
import '../models/photo.dart';
import '../data/photo_api.dart';
import 'intro_screen.dart';

class PhotoWithConv {
  final Map<String, dynamic> photoData;
  final bool hasConversation;
  PhotoWithConv({required this.photoData, required this.hasConversation});
  
  // Photo 객체처럼 사용할 수 있도록 getter 추가
  String get id => photoData['photo_id'];
  String get url => photoData['image_url'] ?? '';
  DateTime get createdAt => photoData['upload_date'];
  
  // tags에서 년도와 계절 정보를 추출
  int get year {
    print('🔍 Debug year - photoData keys: ${photoData.keys.toList()}');
    print('🔍 Debug year - photo_id: ${photoData['photo_id']}');
    
    // 1순위: tags에서 년도 정보 추출
    final tags = photoData['tags'] as List<dynamic>?;
    print('🔍 Debug year - tags: $tags');
    if (tags != null) {
      for (var tag in tags) {
        if (tag is String && RegExp(r'^\d{4}$').hasMatch(tag)) {
          print('✅ Found year in tags: $tag');
          return int.parse(tag);
        }
      }
    }
    
    // 2순위: taken_at 사용
    final takenAt = photoData['taken_at'];
    print('🔍 Debug year - taken_at: $takenAt');
    if (takenAt != null) {
      if (takenAt is DateTime) {
        print('✅ Using taken_at DateTime: ${takenAt.year}');
        return takenAt.year;
      } else if (takenAt is String) {
        final parsedYear = DateTime.parse(takenAt).year;
        print('✅ Using taken_at String: $parsedYear');
        return parsedYear;
      }
    }
    
    // 3순위: upload_date 사용
    print('⚠️ Fallback to upload_date: ${createdAt.year}');
    return createdAt.year;
  }
  
  String get season {
    print('🔍 Debug season - photoData keys: ${photoData.keys.toList()}');
    print('🔍 Debug season - photo_id: ${photoData['photo_id']}');
    
    // 1순위: tags에서 계절 정보 추출
    final tags = photoData['tags'] as List<dynamic>?;
    print('🔍 Debug season - tags: $tags');
    if (tags != null) {
      for (var tag in tags) {
        if (tag is String && ['spring', 'summer', 'autumn', 'winter'].contains(tag.toLowerCase())) {
          print('✅ Found season in tags: $tag');
          return tag.toLowerCase();
        }
      }
    }
    
    // 2순위: taken_at 기준으로 계절 계산
    final takenAt = photoData['taken_at'];
    print('🔍 Debug season - taken_at: $takenAt');
    DateTime dateToUse = createdAt;
    
    if (takenAt != null) {
      if (takenAt is DateTime) {
        dateToUse = takenAt;
        print('✅ Using taken_at DateTime for season calculation');
      } else if (takenAt is String) {
        dateToUse = DateTime.parse(takenAt);
        print('✅ Using taken_at String for season calculation');
      }
    } else {
      print('⚠️ No taken_at, using upload_date for season calculation');
    }
    
    final calculatedSeason = _getSeason(dateToUse);
    print('✅ Calculated season: $calculatedSeason from date: $dateToUse');
    return calculatedSeason;
  }
  
  String _getSeason(DateTime date) {
    final month = date.month;
    if (month >= 3 && month <= 5) return 'spring';
    if (month >= 6 && month <= 8) return 'summer';
    if (month >= 9 && month <= 11) return 'autumn';
    return 'winter';
  }
}

Future<List<PhotoWithConv>> fetchPhotosWithConv(BuildContext context) async {
  try {
    final userProvider = Provider.of<UserProvider>(context, listen: false);
    final familyId = userProvider.familyId;
    
    if (familyId == null || familyId.isEmpty) {
      throw Exception('가족 정보를 찾을 수 없습니다.');
    }
    
    // Supabase에서 가족 사진 목록 조회 (home_screen.dart와 같은 방식)
    final familyPhotos = await PhotoApi.fetchRecentFamilyPhotoNews(familyId, limit: 1000);
    List<PhotoWithConv> result = [];
    
    for (var photoData in familyPhotos) {
      // home_screen.dart와 같은 방식으로 Map 데이터 직접 사용
      // TODO: 대화 존재 여부 확인 로직을 추후 Supabase 기반으로 구현
      // 현재는 모든 사진에 대해 false로 설정
      final hasConv = false;
      result.add(PhotoWithConv(photoData: photoData, hasConversation: hasConv));
    }
    
    return result;
  } catch (e) {
    print('❌ Error fetching photos with conversations: $e');
    rethrow;
  }
}

// ... (생략: import 및 fetchPhotosWithConv 등 기존 코드 동일)

class GalleryScreen extends StatefulWidget {
  const GalleryScreen({super.key});

  @override
  State<GalleryScreen> createState() => _GalleryScreenState();
}

class _GalleryScreenState extends State<GalleryScreen> {
  Future<List<PhotoWithConv>>? _photosFuture;

  @override
  void initState() {
    super.initState();
    _initializeAndLoadPhotos();
  }

  Future<void> _initializeAndLoadPhotos() async {
    try {
      // UserProvider가 초기화되지 않았다면 Supabase에서 사용자 정보 로드
      final userProvider = Provider.of<UserProvider>(context, listen: false);
      if (userProvider.id == null) {
        await userProvider.loadUserFromSupabase();
      }
      
      // 여전히 사용자 정보가 없으면 로그인 화면으로 이동
      if (userProvider.id == null && mounted) {
        Navigator.of(context).pushReplacementNamed('/signin');
        return;
      }
      
      _loadPhotos();
    } catch (e) {
      print('❌ Error initializing user: $e');
      // 오류 발생 시 로그인 화면으로 이동
      if (mounted) {
        Navigator.of(context).pushReplacementNamed('/signin');
      }
    }
  }

  void _loadPhotos() {
    setState(() {
      _photosFuture = fetchPhotosWithConv(context);
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF7F7F7),
      appBar: GroupBar(
        title: Provider.of<UserProvider>(context, listen: false).familyName ?? '우리 가족',
      ),
      body: _photosFuture == null
        ? const Center(child: CircularProgressIndicator())
        : FutureBuilder<List<PhotoWithConv>>(
        future: _photosFuture!,
        builder: (context, snapshot) {
          if (snapshot.connectionState == ConnectionState.waiting) {
            return const Center(child: CircularProgressIndicator());
          }
          if (snapshot.hasError) {
            return Center(
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Icon(Icons.error_outline, size: 64, color: Colors.grey[400]),
                  const SizedBox(height: 16),
                  Text(
                    '사진을 불러오는 중 오류가 발생했습니다.',
                    style: TextStyle(fontSize: 16, color: Colors.grey[600]),
                  ),
                  const SizedBox(height: 8),
                  ElevatedButton(
                    onPressed: _loadPhotos,
                    child: const Text('다시 시도'),
                  ),
                ],
              ),
            );
          }
          final photoWithConvs = snapshot.data ?? [];
          if (photoWithConvs.isEmpty) {
            return Center(
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Icon(Icons.photo_library_outlined, size: 64, color: Colors.grey[400]),
                  const SizedBox(height: 16),
                  Text(
                    '아직 업로드된 사진이 없습니다.',
                    style: TextStyle(fontSize: 18, fontWeight: FontWeight.w600, color: Colors.grey[700]),
                  ),
                  const SizedBox(height: 8),
                  Text(
                    '사진을 추가해서 추억을 공유해보세요!',
                    style: TextStyle(fontSize: 14, color: Colors.grey[600]),
                  ),
                ],
              ),
            );
          }
          // 연도, 계절별로 그룹화
          final grouped = <String, List<PhotoWithConv>>{};
          for (var pwc in photoWithConvs) {
            final key = '${pwc.year}년 ${_seasonKor(pwc.season)}';
            grouped.putIfAbsent(key, () => []).add(pwc);
          }
          return ListView(
            padding: const EdgeInsets.symmetric(horizontal: 16),
            children: grouped.entries.map((entry) {
              return Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const SizedBox(height: 16),
                  Text(entry.key, style: maxContentStyle),
                  const SizedBox(height: 12),
                  GridView.builder(
                    shrinkWrap: true,
                    physics: const NeverScrollableScrollPhysics(),
                    itemCount: entry.value.length,
                    gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
                      crossAxisCount: 2,
                      crossAxisSpacing: 8,
                      mainAxisSpacing: 16,
                      childAspectRatio: 1.49,
                    ),
                    itemBuilder: (context, index) {
                      final pwc = entry.value[index];
                      return GestureDetector(
                        onTap: () {
                          Navigator.pushNamed(
                            context,
                            Routes.photoDetail,
                            arguments: pwc.photoData,
                          );
                        },
                        child: AspectRatio(
                          aspectRatio: 1.49, // childAspectRatio와 맞춤
                          child: Stack(
                            fit: StackFit.expand,
                            children: [
                              ClipRRect(
                                borderRadius: BorderRadius.circular(10),
                                child: Image.network(
                                  pwc.url,
                                  fit: BoxFit.cover,
                                  errorBuilder: (c, e, s) => const Icon(Icons.broken_image),
                                ),
                              ),
                              if (pwc.hasConversation)
                                Positioned(
                                  bottom: 8,
                                  right: 2,
                                  child: Image.asset(
                                    'assets/images/finger.png',
                                    width: 50,
                                    height: 50,
                                  ),
                                ),
                            ],
                          ),
                        ),
                      );
                    },
                  ),
                ],
              );
            }).toList(),
          );
        },
      ),
      bottomNavigationBar: const CustomBottomNavBar(currentIndex: 1),
    );
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
}