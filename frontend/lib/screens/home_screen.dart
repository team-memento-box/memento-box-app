import 'package:flutter/material.dart';
import '../widgets/image_card_widget.dart';
import '../widgets/tap_widget.dart';
import '../widgets/group_bar_widget.dart';
import 'package:provider/provider.dart';
import '../providers/user_provider.dart';
import '../providers/photo_provider.dart';



class HomeUpdateScreen extends StatefulWidget {
  const HomeUpdateScreen({super.key});

  @override
  State<HomeUpdateScreen> createState() => _HomeUpdateScreenState();
}

class _HomeUpdateScreenState extends State<HomeUpdateScreen> {
  @override
  void initState() {
    super.initState();
    _loadRecentNews();
  }

  Future<void> _loadRecentNews() async {
    try {
      final userProvider = Provider.of<UserProvider>(context, listen: false);
      final familyId = userProvider.familyId;

      if (familyId == null || familyId.isEmpty) {
        return;
      }

      // PhotoProvider를 사용하여 캐시된 데이터 로드
      final photoProvider = Provider.of<PhotoProvider>(context, listen: false);
      await photoProvider.loadPhotos(familyId);
    } catch (e) {
      print('❌ Error loading recent news: $e');
    }
  }

  Future<void> _refreshNews() async {
    final userProvider = Provider.of<UserProvider>(context, listen: false);
    final photoProvider = Provider.of<PhotoProvider>(context, listen: false);
    if (userProvider.familyId != null) {
      await photoProvider.refreshPhotos(userProvider.familyId!);
    }
  }

  @override
  Widget build(BuildContext context) {
    final userProvider = Provider.of<UserProvider>(context);

    final familyName = userProvider.familyName ?? '우리 가족';
    
    return Scaffold(
      backgroundColor: Colors.white,
      appBar: GroupBar(title: familyName),
      body: Container(
        color: const Color(0xFFF7F7F7),
        child: RefreshIndicator(
          onRefresh: _refreshNews,
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(16),
            child: Column(
              children: [
                const ProfileHeader(),
                const SizedBox(height: 20),
                const SectionTitle(title: '최근 소식'),
                const SizedBox(height: 10),
                _buildRecentNews(),
              ],
            ),
          ),
        ),
      ),
      bottomNavigationBar: const CustomBottomNavBar(currentIndex: 0),
    );
  }

  Widget _buildRecentNews() {
    return Consumer<PhotoProvider>(
      builder: (context, photoProvider, _) {
        // 로딩 중 (데이터가 없는 상태)
        if (photoProvider.isLoading && !photoProvider.hasData) {
          return const Center(
            child: Padding(
              padding: EdgeInsets.all(20.0),
              child: CircularProgressIndicator(),
            ),
          );
        }

        // 데이터가 없음
        if (photoProvider.photos.isEmpty) {
          return Center(
            child: Padding(
              padding: const EdgeInsets.all(20.0),
              child: Column(
                children: [
                  Icon(Icons.photo_library_outlined, size: 48, color: Colors.grey[400]),
                  const SizedBox(height: 8),
                  Text(
                    '아직 업로드된 사진이 없습니다.\n가족들과 추억을 공유해보세요!',
                    style: TextStyle(color: Colors.grey[600]),
                    textAlign: TextAlign.center,
                  ),
                ],
              ),
            ),
          );
        }

        // 최근 10개 사진만 표시
        final recentPhotos = photoProvider.photos.take(10).toList();

        return Column(
          children: recentPhotos.map<Widget>((photo) {
            final uploadDate = photo.createdAt;
            final formattedDate = '${uploadDate.year}년 ${uploadDate.month.toString().padLeft(2, '0')}월 ${uploadDate.day.toString().padLeft(2, '0')}일';

            return Column(
              children: [
                NewsCard(
                  name: photo.photoData['user_name']?.toString() ?? '이름 없음',
                  role: photo.photoData['family_role']?.toString() ?? '가족',
                  content: '새로운 사진 추가',
                  imageUrl: photo.url,
                  userProfileImage: photo.photoData['user_profile_image']?.toString(),
                  date: formattedDate,
                ),
                const SizedBox(height: 15),
              ],
            );
          }).toList(),
        );
      },
    );
  }
}

class ProfileHeader extends StatelessWidget {
  const ProfileHeader({super.key});

  @override
  Widget build(BuildContext context) {

    final userProvider = Provider.of<UserProvider>(context); // ✅ Provider로 불러오기
    final username = userProvider.name ?? '이름 없음';
    final profileImg = userProvider.profileImg?.replaceFirst('http://', 'https://') ?? ''; // 보안상 쩔수
    final familyRole = userProvider.familyRole ?? '역할 없음';
    
    // 디버깅용 로그 추가
    print('🖼️ [ProfileHeader] username: $username');
    print('🖼️ [ProfileHeader] profileImg: $profileImg');
    print('🖼️ [ProfileHeader] familyRole: $familyRole');

    return Column(
      children: [
        CircleAvatar(
          radius: 50,
          backgroundColor: const Color(0xFFFFC9B3),
          backgroundImage: profileImg.isNotEmpty
              ? NetworkImage(profileImg)
              : null,
          child: profileImg.isEmpty
              ? const Icon(Icons.person, size: 50, color: Colors.white)
              : null,
        ),
        const SizedBox(height: 7),
        Text(
          username, 
          style: const TextStyle(fontSize: 22, fontWeight: FontWeight.w700),
        ),
        const SizedBox(height: 1),
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 2),
          decoration: BoxDecoration(
            color: const Color(0xFF777777),
            borderRadius: BorderRadius.circular(12),
          ),
          child: Text(
            familyRole,
            style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w800),
          ),
        ),
      ],
    );
  }
}

class SectionTitle extends StatelessWidget {
  final String title;
  const SectionTitle({super.key, required this.title});

  @override
  Widget build(BuildContext context) {
    return Align(
      alignment: Alignment.centerLeft,
      child: Text(
        title,
        style: const TextStyle(fontSize: 20, fontWeight: FontWeight.w700),
      ),
    );
  }
}
