import 'package:flutter/material.dart';
import 'package:supabase_flutter/supabase_flutter.dart';
import 'package:provider/provider.dart';
import 'package:kakao_flutter_sdk_user/kakao_flutter_sdk_user.dart' as kakao;
import '../core/supabase_service.dart';
import '../services/user_service.dart';
import '../user_provider.dart';
import 'dart:async';

class KakaoSigninScreen extends StatefulWidget {
  const KakaoSigninScreen({super.key});

  @override
  State<KakaoSigninScreen> createState() => _KakaoSigninScreenState();
}

class _KakaoSigninScreenState extends State<KakaoSigninScreen> with WidgetsBindingObserver {
  StreamSubscription<AuthState>? _authSubscription;
  bool _isLoading = false;
  Timer? _checkTimer;
  String? _userType; // guardian 또는 dependent

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    _setupAuthListener();
    _checkCurrentSession();
  }

  


  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    _authSubscription?.cancel();
    _checkTimer?.cancel();
    super.dispose();
  }

  // 앱이 포그라운드로 돌아올 때 호출
  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    super.didChangeAppLifecycleState(state);
    print('🔄 App lifecycle changed: $state');
    
    if (state == AppLifecycleState.resumed) {
      print('📱 App resumed - checking session...');
      _checkCurrentSession();
    }
  }

  void _checkCurrentSession() {
    final session = SupabaseService.client.auth.currentSession;
    final user = SupabaseService.client.auth.currentUser;
    
    print('🔍 Current session: ${session?.accessToken != null ? "EXISTS" : "NULL"}');
    print('🔍 Current user: ${user?.id ?? "NULL"}');
    
    if (user != null && _isLoading) {
      print('✅ Found user after OAuth - handling login...');
      _handleSuccessfulLogin(user);
    }
  }

  void _setupAuthListener() {
    print('🎧 Setting up auth listener...');
    
    _authSubscription = SupabaseService.client.auth.onAuthStateChange.listen((data) {
      print('🔥 Auth state changed: ${data.event}');
      print('🔥 Session exists: ${data.session != null}');
      print('🔥 User ID: ${data.session?.user?.id ?? "NULL"}');
      
      if (data.event == AuthChangeEvent.signedIn && data.session?.user != null) {
        print('✅ Sign in event detected!');
        _handleSuccessfulLogin(data.session!.user!);
      } else if (data.event == AuthChangeEvent.signedOut) {
        print('👋 Sign out event detected');
        setState(() {
          _isLoading = false;
        });
      }
    });
  }

  Future<void> _handleSuccessfulLogin(User user) async {
    print('🎉 Handling successful login for user: ${user.id}');
    
    setState(() {
      _isLoading = false;
    });

    try {
      // arguments에서 userType 강제로 다시 가져오기
      final arguments = ModalRoute.of(context)?.settings.arguments as Map<String, dynamic>?;
      print('🔍 Arguments in _handleSuccessfulLogin: $arguments');
      if (arguments != null) {
        final newUserType = arguments['userType'] as String?;
        print('🔍 User type from arguments: $newUserType');
        print('🔍 Current _userType before update: $_userType');
        _userType = newUserType;
        print('🔍 User type retrieved in _handleSuccessfulLogin: $_userType');
      } else {
        print('❌ No arguments found in _handleSuccessfulLogin');
      }
      
      print('📊 Checking user profile...');
      
      // Supabase OAuth에서 사용자 정보 획득
      final kakaoId = user.userMetadata?['kakao_id']?.toString() ?? user.id;
      final nickname = user.userMetadata?['full_name'] ?? 
                      user.userMetadata?['name'] ?? 
                      user.userMetadata?['nickname'] ?? '';
      final email = user.email ?? '';
      final profileImageUrl = user.userMetadata?['avatar_url'] ?? 
                             user.userMetadata?['picture'] ?? 
                             user.userMetadata?['profile_image_url'] ?? 
                             user.userMetadata?['thumbnail_image_url'] ?? '';
      
      print('📱 Supabase User - ID: $kakaoId, Nickname: $nickname, Email: $email, ProfileImage: $profileImageUrl');
      print('🔍 All metadata: ${user.userMetadata}');
      print('🔍 Final UserType: $_userType');
      
      // 1. 프로필 존재 여부 확인
      final hasProfile = await UserService.hasUserProfile(user.id);
      print('🔍 Has profile: $hasProfile, userType: $_userType');
      
      if (!hasProfile) {
        print('🆕 Creating new user profile...');
        
        // 2. 신규 사용자 - 프로필 생성
        final isGuardian = _userType == 'guardian';
        print('🔍 NEW USER: _userType=$_userType, isGuardian=$isGuardian');
        final userId = await UserService.createOrUpdateUserProfile(
          userId: user.id,
          email: email,
          fullName: nickname,
          profileImageUrl: profileImageUrl,
          isGuardian: isGuardian,
        );

        if (userId == null) {
          throw Exception('Failed to create user profile');
        }

        print('✅ Profile created successfully');

        // UserProvider에 사용자 정보 로드 및 isGuardian 값 설정
        if (mounted) {
          final userProvider = Provider.of<UserProvider>(context, listen: false);
          await userProvider.loadUserFromSupabase();
          // userType 기반으로 isGuardian 값 명시적 설정
          if (_userType != null) {
            final isGuardianValue = _userType == 'guardian';
            userProvider.setIsGuardian(isGuardianValue);
            print('✅ Set UserProvider isGuardian to: $isGuardianValue (based on userType: $_userType)');
          }
        }

        if (mounted) {
          print('🧭 New user: navigating to profile input screen');
          Navigator.pushNamed(context, '/profile-input');
        }
      } else {
        print('👋 Existing user login');
        
        // 기존 사용자 - is_guardian 값 업데이트 (userType이 있는 경우)
        if (_userType != null) {
          final isGuardian = _userType == 'guardian';
          await SupabaseService.client
              .from('users')
              .update({'is_guardian': isGuardian})
              .eq('id', user.id);
          print('✅ Updated existing user is_guardian to: $isGuardian');
          
          // UserProvider의 isGuardian 값도 업데이트
          final userProvider = Provider.of<UserProvider>(context, listen: false);
          userProvider.setIsGuardian(isGuardian);
          print('✅ Updated UserProvider isGuardian to: $isGuardian');
        }
        
        // 기존 사용자 - 온보딩 상태 확인
        final onboardingCompleted = await UserService.isOnboardingCompleted(user.id);
        
        // UserProvider에 사용자 정보 로드
        if (mounted) {
          final userProvider = Provider.of<UserProvider>(context, listen: false);
          await userProvider.loadUserFromSupabase();
        }

        if (mounted) {
          final userProvider = Provider.of<UserProvider>(context, listen: false);
          final isGuardianUser = userProvider.isGuardian;
          
          // _userType 기반으로 네비게이션 결정 (DB 값보다 우선)
          final shouldGoToGuardianFlow = _userType == 'guardian';
          
          print('🧭 Existing user navigation: userType=$_userType, isGuardianUser=$isGuardianUser, shouldGoToGuardianFlow=$shouldGoToGuardianFlow, onboardingCompleted=$onboardingCompleted');
          
          if (onboardingCompleted) {
            print('🧭 Existing user: Direct to home');
            Navigator.pushNamed(context, '/home');
          } else {
            print('🧭 Existing user: navigating to profile input screen');
            Navigator.pushNamed(context, '/profile-input');
          }
        }
      }
    } catch (e) {
      print('❌ Error handling login: $e');
      
      setState(() {
        _isLoading = false;
      });
      
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('프로필 처리 중 오류: $e')),
        );
      }
    }
  }

  Future<void> _kakaoLoginWithSupabase(BuildContext context) async {
    if (_isLoading) {
      print('⏳ Already loading, ignoring tap');
      return;
    }

    print('🚀 Starting Kakao OAuth...');
    
    setState(() {
      _isLoading = true;
    });

    try {
      // 현재 세션 상태 로깅
      final currentUser = SupabaseService.client.auth.currentUser;
      print('👤 Current user before OAuth: ${currentUser?.id ?? "NULL"}');
      
      // 기존 세션이 있으면 먼저 로그아웃
      if (currentUser != null) {
        print('🚪 기존 세션 발견 - 로그아웃 후 재로그인');
        await SupabaseService.client.auth.signOut();
        
        // 로그아웃 후 잠시 대기
        await Future.delayed(const Duration(milliseconds: 1000));
        print('✅ 로그아웃 완료');
      }
      
      // OAuth 시작
      await SupabaseService.client.auth.signInWithOAuth(
        OAuthProvider.kakao,
        redirectTo: 'memento://callback',
        
        queryParams: {
          'prompt': 'login', // 👈 기존 세션 무시, 항상 로그인 강제
        },
      );
      
      print('✅ OAuth call completed, waiting for callback...');
      
      // 5초 후에도 세션이 없으면 수동 체크 시작
      _checkTimer = Timer.periodic(const Duration(seconds: 2), (timer) {
        print('⏰ Checking session... (${timer.tick * 2}s)');
        _checkCurrentSession();
        
        if (timer.tick > 15) { // 30초 후 타임아웃
          print('⏰ Timeout - stopping timer');
          timer.cancel();
          if (_isLoading) {
            setState(() {
              _isLoading = false;
            });
            ScaffoldMessenger.of(context).showSnackBar(
              const SnackBar(content: Text('로그인 시간이 초과되었습니다. 다시 시도해주세요.')),
            );
          }
        }
      });
      
    } catch (e) {
      print('❌ OAuth error: $e');
      
      setState(() {
        _isLoading = false;
      });
      
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('카카오 로그인 실패: $e')),
        );
      }
    }
  }

  @override
    Widget build(BuildContext context) {
      print('🏗️ Build method called');
      final arguments = ModalRoute.of(context)?.settings.arguments as Map<String, dynamic>?;
      print('🏗️ Arguments in build: $arguments');
      
      if (arguments != null) {
        final newUserType = arguments['userType'] as String?;
        if (_userType != newUserType) {
          _userType = newUserType;
          print('🔍 User type updated in build: $_userType');
        }
      } else {
        print('❌ No arguments found in build method');
      }

      return Scaffold(
        backgroundColor: Colors.white,
        body: SafeArea(
          child: Stack(
            children: [
              _buildWelcomeText(),
              _buildButtons(context),
              _buildDebugInfo(),
              if (_isLoading) _buildLoadingOverlay(),
            ],
          ),
        ),
      );
    }

  Widget _buildDebugInfo() {
    final user = SupabaseService.client.auth.currentUser;
    final session = SupabaseService.client.auth.currentSession;
    
    return Positioned(
      bottom: 50,
      left: 16,
      right: 16,
      child: Container(
        padding: const EdgeInsets.all(8),
        decoration: BoxDecoration(
          color: Colors.grey.shade100,
          borderRadius: BorderRadius.circular(8),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisSize: MainAxisSize.min,
          children: [
            Text('Debug Info:', style: TextStyle(fontWeight: FontWeight.bold)),
            Text('User: ${user?.id ?? "NULL"}'),
            Text('Session: ${session != null ? "EXISTS" : "NULL"}'),
            Text('Loading: $_isLoading'),
            Text('UserType: ${_userType ?? "NULL"}'), // 추가
          ],
        ),
      ),
    );
  }

  Widget _buildLoadingOverlay() {
    return Container(
      color: Colors.black26,
      child: const Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            CircularProgressIndicator(),
            SizedBox(height: 16),
            Text(
              '카카오 로그인 중...\n잠시만 기다려주세요',
              textAlign: TextAlign.center,
              style: TextStyle(
                color: Colors.white,
                fontSize: 16,
                fontFamily: 'Pretendard',
              ),
            ),
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
            _isLoading ? '로그인 중...' : '카카오로 계속하기',
            const Color(0xFFF9E007),
            Colors.black,
            onTap: _isLoading ? null : () => _kakaoLoginWithSupabase(context),
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
          color: onTap == null ? Colors.grey.shade300 : bgColor,
          borderRadius: BorderRadius.circular(20),
        ),
        alignment: Alignment.center,
        child: Text(
          text,
          style: TextStyle(
            fontSize: 20,
            fontWeight: FontWeight.w600,
            fontFamily: 'Pretendard',
            color: onTap == null ? Colors.grey.shade600 : textColor,
          ),
        ),
      ),
    );
  }
}