import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../widgets/group_bar_widget.dart';
import '../widgets/tap_widget.dart';
import '../utils/styles.dart';

import '../providers/user_provider.dart';
import '../providers/photo_provider.dart';
import '../models/photo_with_conv.dart';
import '../utils/routes.dart';

class GalleryScreen extends StatefulWidget {
  const GalleryScreen({super.key});

  @override
  State<GalleryScreen> createState() => _GalleryScreenState();
}

class _GalleryScreenState extends State<GalleryScreen> {
  @override
  void initState() {
    super.initState();
    _boot();
  }

  Future<void> _boot() async {
    try {
      final userProvider = Provider.of<UserProvider>(context, listen: false);

      // User가 비어 있으면 Supabase에서 로드
      if (userProvider.id == null) {
        await userProvider.loadUserFromSupabase();
      }
      if (!mounted) return;

      // 가족 정보 없으면 로그인으로
      if (userProvider.familyId == null) {
        Navigator.of(context).pushReplacementNamed('/signin');
        return;
      }

      // ✅ PhotoProvider로 (캐시 고려) 로드
      final photoProvider = Provider.of<PhotoProvider>(context, listen: false);
      await photoProvider.loadPhotos(userProvider.familyId!);
    } catch (e) {
      if (!mounted) return;
      Navigator.of(context).pushReplacementNamed('/signin');
    }
  }

  Future<void> _refresh() async {
    final userProvider = Provider.of<UserProvider>(context, listen: false);
    final photoProvider = Provider.of<PhotoProvider>(context, listen: false);
    if (userProvider.familyId != null) {
      await photoProvider.refreshPhotos(userProvider.familyId!);
    }
  }

  @override
  Widget build(BuildContext context) {
    // 최소 리빌드를 위해 select 사용
    final familyName =
        context.select<UserProvider, String?>((u) => u.familyName) ?? '우리 가족';

    return Scaffold(
      backgroundColor: const Color(0xFFF7F7F7),
      appBar: GroupBar(
        title: familyName,
      ),
      body: Consumer<PhotoProvider>(
        builder: (context, photoProvider, _) {
          // 최초 로드 중
          if (photoProvider.isLoading && !photoProvider.hasData) {
            return const Center(child: CircularProgressIndicator());
          }

          // 데이터 없음
          if (photoProvider.photos.isEmpty) {
            return RefreshIndicator(
              onRefresh: _refresh,
              child: ListView(
                children: [
                  const SizedBox(height: 120),
                  Icon(Icons.photo_library_outlined,
                      size: 64, color: Colors.grey[400]),
                  const SizedBox(height: 16),
                  Center(
                    child: Text(
                      '아직 업로드된 사진이 없습니다.',
                      style: TextStyle(
                        fontSize: 18,
                        fontWeight: FontWeight.w600,
                        color: Colors.grey[700],
                      ),
                    ),
                  ),
                  const SizedBox(height: 8),
                  Center(
                    child: Text(
                      '사진을 추가해서 추억을 공유해보세요!',
                      style: TextStyle(fontSize: 14, color: Colors.grey[600]),
                    ),
                  ),
                ],
              ),
            );
          }

          // ── 기존 그룹화/정렬 로직 그대로 유지 ──
          final grouped = <String, List<PhotoWithConv>>{};
          for (var pwc in photoProvider.photos) {
            final key = '${pwc.year}년 ${_seasonKor(pwc.season)}';
            grouped.putIfAbsent(key, () => []).add(pwc);
          }

          final sortedGroupEntries = grouped.entries.toList();
          sortedGroupEntries.sort((a, b) {
            final aYear = int.parse(a.key.split('년')[0]);
            final aSeason = a.key.split('년 ')[1];
            final bYear = int.parse(b.key.split('년')[0]);
            final bSeason = b.key.split('년 ')[1];
            if (aYear != bYear) return bYear.compareTo(aYear);
            final order = {'겨울': 0, '가을': 1, '여름': 2, '봄': 3};
            return (order[aSeason] ?? 4).compareTo(order[bSeason] ?? 4);
          });

          for (var entry in sortedGroupEntries) {
            entry.value.sort((a, b) => b.createdAt.compareTo(a.createdAt));
          }

          return RefreshIndicator(
            onRefresh: _refresh, // Pull-to-refresh
            child: ListView(
              padding: const EdgeInsets.symmetric(horizontal: 16),
              children: sortedGroupEntries.map((entry) {
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
                      gridDelegate:
                          const SliverGridDelegateWithFixedCrossAxisCount(
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
                            aspectRatio: 1.49,
                            child: Stack(
                              fit: StackFit.expand,
                              children: [
                                ClipRRect(
                                  borderRadius: BorderRadius.circular(10),
                                  child: Image.network(
                                    pwc.url,
                                    fit: BoxFit.cover,
                                    errorBuilder: (c, e, s) =>
                                        const Icon(Icons.broken_image),
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
            ),
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
