import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../user_provider.dart';
import '../widgets/tap_widget.dart';
import '../core/supabase_service.dart';

class IntroScreen extends StatefulWidget {
  const IntroScreen({super.key});

  @override
  State<IntroScreen> createState() => _IntroScreenState();
}

class _IntroScreenState extends State<IntroScreen> {
  @override
  void initState() {
    super.initState();

    WidgetsBinding.instance.addPostFrameCallback((_) {
      // 카카오 로그인에서 전달받은 arguments 사용
      final arguments = ModalRoute.of(context)?.settings.arguments as Map<String, dynamic>?;
      
      if (arguments != null) {
        final userId = arguments['user_id'] as String?;
        final email = arguments['email'] as String?;
        final isRegistered = arguments['is_registered'] as bool? ?? false;
        
        // Supabase에서 사용자 프로필 정보 가져오기
        _loadUserProfile(userId, email, isRegistered);
      }
    });
  }

  Future<void> _loadUserProfile(String? userId, String? email, bool isRegistered) async {
    if (userId == null) return;
    
    try {
      if (isRegistered) {
        // 기존 사용자 - 프로필 정보 가져오기
        final profile = await SupabaseService.client
            .from('users')
            .select()
            .eq('id', userId)
            .single();
            
        Provider.of<UserProvider>(context, listen: false).setUser(
          kakaoId: userId,
          username: profile['full_name'] ?? '',
          email: profile['email'] ?? '',
          profileImg: profile['profile_image_url'] ?? '',
          gender: profile['gender'] ?? '',
        );
      } else {
        // 신규 사용자 - 기본 정보만 설정
        Provider.of<UserProvider>(context, listen: false).setUser(
          kakaoId: userId,
          username: '',
          email: email ?? '',
          profileImg: '',
          gender: '',
        );
      }
    } catch (e) {
      print('프로필 로드 오류: $e');
    }
  }

  @override
  Widget build(BuildContext context) {
    final user = Provider.of<UserProvider>(context);
    return Scaffold(
      backgroundColor: const Color(0xFFF7F7F7),
      body: Column(
        children: [
          Text("✅ 카카오ID: ${user.kakaoId}"),
          Text("✅ 이름: ${user.username}"),
          Text("✅ 이메일: ${user.email}"),
          Text("✅ 성별: ${user.gender}"),
          const SizedBox(height: 40),
          _buildStatusBar(),
          const SizedBox(height: 10),
          Expanded(child: Center(child: _buildMainBox())),
        ],
      ),
      bottomNavigationBar: const CustomBottomNavBar(currentIndex: 0),
    );
  }

  Widget _buildStatusBar() {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          const Text(
            '9:41',
            style: TextStyle(
              fontSize: 17,
              fontWeight: FontWeight.w600,
              fontFamily: 'SF Pro',
            ),
          ),
          _buildBatteryIcon(),
        ],
      ),
    );
  }

  Widget _buildBatteryIcon() {
    return SizedBox(
      width: 25,
      height: 13,
      child: Stack(
        children: [
          Opacity(
            opacity: 0.35,
            child: Container(
              decoration: ShapeDecoration(
                shape: RoundedRectangleBorder(
                  side: const BorderSide(width: 1, color: Colors.black),
                  borderRadius: BorderRadius.circular(4.30),
                ),
              ),
            ),
          ),
          Positioned(
            left: 2,
            top: 2,
            child: Container(
              width: 21,
              height: 9,
              decoration: ShapeDecoration(
                color: Colors.black,
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(2.50),
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildMainBox() {
    return Container(
      width: 315,
      padding: const EdgeInsets.symmetric(vertical: 40),
      decoration: BoxDecoration(
        color: const Color(0x1900C8B8),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: const Color(0xFF8CCAA7), width: 3),
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          const Icon(Icons.add_circle, color: Color(0xFF8CCAA7), size: 36),
          const SizedBox(height: 20),
          const Padding(
            padding: EdgeInsets.symmetric(horizontal: 16),
            child: Text(
              '우리 가족만의 보관함을\n만들어 주세요',
              textAlign: TextAlign.center,
              style: TextStyle(
                color: Color(0xFF8CCAA7),
                fontSize: 18,
                fontWeight: FontWeight.w700,
                fontFamily: 'Pretendard',
              ),
            ),
          ),
          const SizedBox(height: 30),
          SizedBox(
            width: 100,
            height: 100,
            child: Image.asset("assets/images/temp_logo.png"),
          ),
        ],
      ),
    );
  }
}
