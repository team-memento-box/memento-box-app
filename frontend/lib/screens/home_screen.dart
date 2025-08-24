import 'package:flutter/material.dart';
import '../widgets/image_card_widget.dart';
import '../widgets/tap_widget.dart';
import 'package:provider/provider.dart';
import '../user_provider.dart';
import '../data/photo_api.dart';



class HomeUpdateScreen extends StatefulWidget {
  const HomeUpdateScreen({super.key});

  @override
  State<HomeUpdateScreen> createState() => _HomeUpdateScreenState();
}

class _HomeUpdateScreenState extends State<HomeUpdateScreen> {
  List<Map<String, dynamic>> recentNews = [];
  bool isLoading = true;
  String? errorMessage;

  @override
  void initState() {
    super.initState();
    _loadRecentNews();
  }

  Future<void> _loadRecentNews() async {
    try {
      setState(() {
        isLoading = true;
        errorMessage = null;
      });

      final userProvider = Provider.of<UserProvider>(context, listen: false);
      final familyId = userProvider.familyId;

      if (familyId == null || familyId.isEmpty) {
        setState(() {
          errorMessage = '가족 정보를 찾을 수 없습니다.';
          isLoading = false;
        });
        return;
      }

      final news = await PhotoApi.fetchRecentFamilyPhotoNews(familyId, limit: 10);
      
      setState(() {
        recentNews = news;
        isLoading = false;
      });
    } catch (e) {
      print('❌ Error loading recent news: $e');
      setState(() {
        errorMessage = '최근 소식을 불러오는데 실패했습니다.';
        isLoading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final userProvider = Provider.of<UserProvider>(context);

    return Scaffold(
      backgroundColor: const Color(0xFFF7F7F7),
      appBar: PreferredSize(
        preferredSize: Size.fromHeight(80.0),
        child: AppBar(
          title: Text(
            userProvider.familyName ?? '우리 가족',
            style: const TextStyle(
              fontSize: 25,
              fontWeight: FontWeight.w800,
              fontFamily: 'Pretendard',
              letterSpacing: 0,
              color: Colors.white,
            ),
          ),
          centerTitle: true,
          backgroundColor: const Color(0xFF8CCAA7),
        ),
      ),
      body: RefreshIndicator(
        onRefresh: _loadRecentNews,
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
      bottomNavigationBar: const CustomBottomNavBar(currentIndex: 0),
    );
  }

  Widget _buildRecentNews() {
    if (isLoading) {
      return const Center(
        child: Padding(
          padding: EdgeInsets.all(20.0),
          child: CircularProgressIndicator(),
        ),
      );
    }

    if (errorMessage != null) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(20.0),
          child: Column(
            children: [
              Icon(Icons.error_outline, size: 48, color: Colors.grey[400]),
              const SizedBox(height: 8),
              Text(
                errorMessage!,
                style: TextStyle(color: Colors.grey[600]),
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 8),
              ElevatedButton(
                onPressed: _loadRecentNews,
                child: const Text('다시 시도'),
              ),
            ],
          ),
        ),
      );
    }

    if (recentNews.isEmpty) {
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

    return Column(
      children: recentNews.map<Widget>((news) {
        final uploadDate = news['upload_date'] as DateTime;
        final formattedDate = '${uploadDate.year}년 ${uploadDate.month.toString().padLeft(2, '0')}월 ${uploadDate.day.toString().padLeft(2, '0')}일';

        return Column(
          children: [
            NewsCard(
              name: news['user_name'] ?? '이름 없음',
              role: news['family_role'] ?? '가족',
              content: news['content'] ?? '새로운 사진 추가',
              imageUrl: news['image_url'],
              userProfileImage: news['user_profile_image'],
              date: formattedDate,
            ),
            const SizedBox(height: 15),
          ],
        );
      }).toList(),
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
