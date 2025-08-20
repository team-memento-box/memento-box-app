import 'package:flutter/material.dart';
import 'package:supabase_flutter/supabase_flutter.dart';
import '../core/supabase_service.dart';

class KakaoSigninScreen extends StatelessWidget {
  const KakaoSigninScreen({super.key});

  Future<void> _kakaoLoginWithSupabase(BuildContext context) async {
    try {
      // Supabase에서 직접 카카오 OAuth 처리
      final response = await SupabaseService.client.auth.signInWithOAuth(
        OAuthProvider.kakao,
        redirectTo: 'memento://callback', // 앱 딥링크
      );

      if (response) {
        // 로그인 성공 시 사용자 정보 가져오기
        final user = SupabaseService.client.auth.currentUser;
        if (user != null) {
          // users 테이블에서 사용자 프로필 확인
          final profile = await SupabaseService.client
              .from('users')
              .select()
              .eq('id', user.id)
              .maybeSingle();

          if (profile == null) {
            // 신규 사용자 - 기본 프로필 생성
            await SupabaseService.client.from('users').insert({
              'id': user.id,
              'email': user.email,
              'full_name': user.userMetadata?['name'] ?? '',
              'profile_image_url': user.userMetadata?['avatar_url'] ?? '',
              'onboarding_completed': false,
              'privacy_consent': false,
              'terms_accepted': false,
              'notification_enabled': true,
            });
            
            Navigator.pushNamed(context, '/intro', arguments: {
              'user_id': user.id,
              'email': user.email,
              'is_registered': false,
            });
          } else {
            // 기존 사용자
            Navigator.pushNamed(context, '/intro', arguments: {
              'user_id': profile['id'],
              'email': profile['email'],
              'is_registered': profile['onboarding_completed'] ?? false,
            });
          }
        }
      }
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('카카오 로그인 실패: $e')),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.white,
      body: SafeArea(
        child: Stack(
          children: [
            _buildWelcomeText(),
            _buildButtons(context),
          ],
        ),
      ),
    );
  }

  Widget _buildWelcomeText() {
    return const Positioned(
      top: 100,
      left: 30,
      right: 30,
      child: Text(
        '소중한 우리 가족의 추억 기록을 위해\n카카오로 간편하게 로그인하세요.',
        style: TextStyle(fontSize: 18, fontFamily: 'Pretendard'),
        textAlign: TextAlign.center,
      ),
    );
  }

  Widget _buildButtons(BuildContext context) {
    return Positioned(
      top: 200,
      left: 30,
      right: 30,
      child: Column(
        children: [
          _buildLoginButton(
            '카카오로 계속하기',
            const Color(0xFFF9E007),
            Colors.black,
            onTap: () => _kakaoLoginWithSupabase(context),
          ),
        ],
      ),
    );
  }

  Widget _buildLoginButton(
    String text,
    Color bgColor,
    Color textColor, {
    VoidCallback? onTap,
  }) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        width: double.infinity,
        height: 60,
        decoration: BoxDecoration(
          color: bgColor,
          borderRadius: BorderRadius.circular(20),
        ),
        alignment: Alignment.center,
        child: Text(
          text,
          style: TextStyle(
            fontSize: 20,
            fontWeight: FontWeight.w600,
            fontFamily: 'Pretendard',
            color: textColor,
          ),
        ),
      ),
    );
  }
}