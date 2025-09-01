import 'package:http/http.dart' as http;
import 'package:flutter_dotenv/flutter_dotenv.dart';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:kakao_flutter_sdk_user/kakao_flutter_sdk_user.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../providers/user_provider.dart';
import '../widgets/tap_widget.dart';
import '../widgets/group_bar_widget.dart';
import '../core/supabase_service.dart';

class MyPage extends StatefulWidget {
  const MyPage({super.key});

  @override
  State<MyPage> createState() => _MyPageState();
}

class _MyPageState extends State<MyPage> {
  
  Future<void> _deleteAccount(BuildContext context) async {
    final userProvider = Provider.of<UserProvider>(context, listen: false);
    final currentUser = SupabaseService.client.auth.currentUser;
    
    if (currentUser == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('로그인 정보를 찾을 수 없습니다.')),
      );
      return;
    }
    
    try {
      print('🗑️ Starting account deletion for user: ${currentUser.id}');
      
      // 1. Supabase users 테이블에서 사용자 데이터 삭제 (더 안전한 방법)
      try {
        await SupabaseService.client
            .from('users')
            .delete()
            .eq('id', currentUser.id);
        print('✅ User data deleted from database');
      } catch (dbError) {
        print('⚠️ Database deletion failed: $dbError');
        // 삭제가 실패하면 비활성화로 대체
        try {
          await SupabaseService.client
              .from('users')
              .update({
                'email': 'deleted_${currentUser.id}@memento.box',
                'full_name': '탈퇴한 사용자',
                'profile_image_url': null,
                'phone': null,
                'onboarding_completed': false,
                'updated_at': DateTime.now().toIso8601String(),
              })
              .eq('id', currentUser.id);
          print('✅ User data anonymized');
        } catch (updateError) {
          print('❌ User data anonymization failed: $updateError');
          throw updateError;
        }
      }
      
      // 2. FastAPI 백엔드에서도 데이터 삭제 (기존 로직 유지)
      final kakaoId = userProvider.kakaoId;
      if (kakaoId != null && dotenv.env['BASE_URL'] != null) {
        try {
          final response = await http.delete(
            Uri.parse('${dotenv.env['BASE_URL']}/auth/delete_by_kakao_id/$kakaoId'),
            headers: {
              'Authorization': 'Bearer ${userProvider.accessToken}',
              'Accept': 'application/json',
            },
          );
          print('📡 FastAPI deletion response: ${response.statusCode}');
        } catch (e) {
          print('⚠️ FastAPI deletion failed: $e (continuing...)');
        }
      }
      
      // 3. Supabase 관련 데이터 완전 삭제
      try {
        // 관련된 모든 테이블에서 사용자 데이터 삭제
        print('🗑️ Deleting related data...');
        
        // photos 테이블에서 사용자 사진 삭제
        await SupabaseService.client
            .from('photos')
            .delete()
            .eq('user_id', currentUser.id);
        print('📸 User photos deleted');
        
        // albums 테이블에서 사용자 앨범 삭제
        await SupabaseService.client
            .from('albums')
            .delete()
            .eq('user_id', currentUser.id);
        print('📁 User albums deleted');
        
        // sessions 테이블에서 사용자 세션 삭제
        await SupabaseService.client
            .from('sessions')
            .delete()
            .eq('user_id', currentUser.id);
        print('💬 User sessions deleted');
        
        // conversations 테이블에서 사용자 대화 삭제
        await SupabaseService.client
            .from('conversations')
            .delete()
            .eq('user_id', currentUser.id);
        print('🗨️ User conversations deleted');
        
        // Storage에서 사용자 파일 삭제
        try {
          await SupabaseService.client.storage
              .from('photos')
              .remove(['${currentUser.id}/']);
          print('🗂️ User storage files deleted');
        } catch (storageError) {
          print('⚠️ Storage deletion failed: $storageError');
        }
        
        // 마지막으로 로그아웃 (auth.users는 CASCADE로 인해 자동 정리됨)
        await SupabaseService.client.auth.signOut();
        print('✅ All user data deleted and signed out');
        
      } catch (e) {
        print('⚠️ Data deletion failed: $e');
        // 실패해도 로그아웃은 진행
        await SupabaseService.client.auth.signOut();
      }
      
      print('🔐 User signed out from Supabase');
      
      // 4. 카카오 토큰 완전 삭제 (더 안전한 방법)
      try {
        print('🔑 Clearing Kakao tokens...');

        // 1. 카카오 서버 로그아웃 + 연결해제 먼저
        try {
          await UserApi.instance.logout();
          print('✅ Kakao server logout completed');
        } catch (logoutError) {
          print('⚠️ Kakao server logout failed: $logoutError');
        }

        try {
          await UserApi.instance.unlink();
          print('✅ Kakao account unlinked');
        } catch (unlinkError) {
          print('⚠️ Kakao unlink failed: $unlinkError');
        }

        // 2. 로컬 토큰 강제 삭제 (마지막에)
        await TokenManagerProvider.instance.manager.clear();
        final prefs = await SharedPreferences.getInstance();
        for (String key in prefs.getKeys()) {
          if (key.contains('kakao') || key.contains('oauth') || key.contains('token')) {
            await prefs.remove(key);
            print('🗑️ Removed preference key: $key');
          }
        }
        print('✅ Local Kakao tokens cleared');
      } catch (e) {
        print('❌ Kakao token cleanup failed: $e');
      }

      
      // 5. 로컬 사용자 데이터 클리어
      userProvider.clearUser();
      print('🧹 Local user data cleared');
      
      // 6. 로그인 화면으로 이동
      if (mounted) {
        Navigator.pushNamedAndRemoveUntil(
          context,
          '/signin',
          (route) => false,
        );
        
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('회원 탈퇴가 완료되었습니다.')),
        );
      }
      
    } catch (e) {
      print('❌ Account deletion failed: $e');
      
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('회원 탈퇴 중 오류가 발생했습니다. 다시 시도해주세요.')),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final userProvider = Provider.of<UserProvider>(context);

    return Scaffold(
      backgroundColor: Colors.white,
      appBar: GroupBar(title: '나의 정보'),
      body: SingleChildScrollView(
        child: Column(
          children: [
            Container(
              width: double.infinity,
              height: 209,
              decoration: BoxDecoration(
                color: Colors.white,
                boxShadow: [
                  BoxShadow(
                    color: const Color(0x0C000000),
                    blurRadius: 20,
                    offset: const Offset(0, -1),
                  )
                ],
              ),
              child: Stack(
                children: [
                  Positioned(
                    left: 0,
                    right: 0,
                    top: 18,
                    child: Center(
                      child: CircleAvatar(
                        radius: 50,
                        backgroundColor: const Color(0xFFFFC9B3),
                        backgroundImage: userProvider.profileImg != null && userProvider.profileImg!.isNotEmpty
                            ? NetworkImage(userProvider.profileImg!)
                            : null,
                        child: (userProvider.profileImg == null || userProvider.profileImg!.isEmpty)
                            ? const Icon(Icons.person, size: 50, color: Colors.white)
                            : null,
                      ),
                    ),
                  ),
                  Positioned(
                    left: 0,
                    right: 0,
                    top: 120,
                    child: Center(
                      child: Text(
                        userProvider.name ?? '이름 없음',
                        style: const TextStyle(
                          color: Color(0xFF111111),
                          fontSize: 22,
                          fontFamily: 'Pretendard',
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                    ),
                  ),
                  Positioned(
                    left: 0,
                    right: 0,
                    top: 159,
                    child: Center(
                      child: Container(
                        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
                        decoration: BoxDecoration(
                          color: const Color(0xFF777777),
                          borderRadius: BorderRadius.circular(30),
                        ),
                        child: Text(
                          userProvider.familyRole ?? '역할 없음',
                          style: const TextStyle(
                            color: Colors.white,
                            fontSize: 17,
                            fontFamily: 'Pretendard',
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                      ),
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 20),
            Container(
              width: 329,
              height: 150,
              decoration: BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.circular(20),
                boxShadow: [
                  BoxShadow(
                    color: const Color(0x33555555),
                    blurRadius: 4,
                    offset: const Offset(0, 4),
                  )
                ],
              ),
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  const Text(
                    '발급된 가족 코드',
                    style: TextStyle(
                      color: Color(0xFF555555),
                      fontSize: 14,
                      fontFamily: 'Pretendard',
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                  const SizedBox(height: 10),
                  Text(
                    userProvider.familyCode ?? '코드 없음',
                    style: const TextStyle(
                      color: Colors.black,
                      fontSize: 32,
                      fontFamily: 'Pretendard',
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                  const SizedBox(height: 10),
                  Text(
                    '가족 그룹명: ${userProvider.familyName ?? '그룹명 없음'}',
                    style: const TextStyle(
                      color: Color(0xFF555555),
                      fontSize: 16,
                      fontFamily: 'Pretendard',
                      fontWeight: FontWeight.w600,
                      height: 1.5,
                      letterSpacing: -0.5,
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 20),
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 32),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text(
                    '회원 정보',
                    style: TextStyle(
                      color: Colors.black,
                      fontSize: 15,
                      fontFamily: 'Pretendard',
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                  const SizedBox(height: 20),
                  _InfoRow(label: '이름', value: userProvider.name ?? '이름 없음'),
                  _InfoRow(label: '이메일', value: userProvider.email ?? '이메일 없음'),
                  _InfoRow(label: '연락처', value: userProvider.phone ?? '연락처 없음'),
                  _InfoRow(label: '피보호자와의 관계', value: userProvider.familyRole ?? '역할 없음'),
                ],
              ),
            ),
            const SizedBox(height: 20),
            Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                _ActionButton(
                  text: '회원 탈퇴',
                  onTap: () {
                    showDialog(
                      context: context,
                      builder: (dialogContext) {
                        return AlertDialog(
                          title: const Text('회원 탈퇴'),
                          content: const Text('정말로 회원탈퇴하시겠습니까?'),
                          actions: [
                            TextButton(
                              onPressed: () {
                                Navigator.pop(dialogContext); // 팝업 닫기
                              },
                              child: const Text('아니오'),
                            ),
                            TextButton(
                              onPressed: () {
                                Navigator.pop(dialogContext); // 팝업 닫기
                                Future.delayed(Duration.zero, () async {
                                  await _deleteAccount(context);
                                });
                              },
                              child: const Text('예'),
                            ),
                          ],
                        );
                      },
                    );
                  },
                ),
              ],
            ),
            const SizedBox(height: 20),
          ],
        ),
      ),
      bottomNavigationBar: const CustomBottomNavBar(currentIndex: 4),
    );
  }
}

class _InfoRow extends StatelessWidget {
  final String label;
  final String value;

  const _InfoRow({
    required this.label,
    required this.value,
  });

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 16),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
          Text(
            label,
            style: const TextStyle(
              color: Color(0xFF555555),
              fontSize: 15,
              fontFamily: 'Pretendard',
              fontWeight: FontWeight.w600,
            ),
          ),
          Text(
            value,
            style: const TextStyle(
              color: Color(0xFF555555),
              fontSize: 15,
              fontFamily: 'Pretendard',
              fontWeight: FontWeight.w600,
            ),
          ),
        ],
      ),
    );
  }
}

class _ActionButton extends StatelessWidget {
  final String text;
  final VoidCallback onTap;

  const _ActionButton({
    required this.text,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        width: 150,
        height: 44,
        decoration: BoxDecoration(
          color: Color.fromARGB(255, 255, 255, 255),
      
          borderRadius: BorderRadius.circular(20),
          border: Border.all(
          color: const Color(0xFF8CCAA7), 
          width: 2, // 테두리 두께
        ),
        ),
          
        child: Center(
          child: Text(
            text,
            style: const TextStyle(
              color: const Color(0xFF8CCAA7),
              fontSize: 16,
              fontFamily: 'Pretendard',
              fontWeight: FontWeight.w600,
            ),
          ),
        ),
      ),
    );
  }
}