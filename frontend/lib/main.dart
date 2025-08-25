import 'screens/mypage.dart';
import 'package:provider/provider.dart'; // ✅ 추가✅
import '../user_provider.dart'; // ✅ 추가✅
import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'screens/kakao_signin_screen.dart';
import 'package:memento_box_app/screens/home_screen.dart';
import 'screens/signin_screen.dart'; //홍원추가
import 'screens/home_screen.dart';
import 'screens/gallery_screen.dart';
import 'screens/add_photo_screen.dart';
import 'screens/conversation_screen_simple.dart'; // ✅ 새ka로 만든 대화 스크린 import
import 'screens/intro_screen.dart'; // ✅ 새로 만든 인트로 스크린 import
import 'screens/profile_input_screen.dart'; // 개인정보 입력 화면
import 'screens/0-3-1.dart'; // Guardian 선택 화면
import 'screens/0-3-1-1.dart'; // Guardian 그룹 생성 화면
import 'screens/0-3-2.dart'; // Dependent 코드 입력 화면
import 'screens/Photo_detail_screen.dart'; // Photo detail 화면 추가
import 'screens/report_list_screen.dart'; // Report list 화면 추가
import 'package:flutter_dotenv/flutter_dotenv.dart'; // --홍원 추가--
import 'package:kakao_flutter_sdk_user/kakao_flutter_sdk_user.dart'; // 카카오 SDK 추가
import 'core/supabase_service.dart'; // Supabase 서비스

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  // ✅ .env 파일 로드 (.env 파일은 Memento-Box 폴더에 위치)
  await dotenv.load(fileName: ".env");
  
  // ✅ Kakao SDK 초기화
  KakaoSdk.init(nativeAppKey: dotenv.env['KAKAO_NATIVE_KEY']!);
  
  // ✅ Supabase 초기화
  await SupabaseService.initialize();

  //runApp(const MyCustomApp());
  runApp(
    MultiProvider(
      providers: [
        ChangeNotifierProvider(create: (_) => UserProvider()), // ✅ 추가✅
      ],
      child: const MyCustomApp(),
    ),
  );
}

class MyCustomApp extends StatelessWidget {
  const MyCustomApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Memento Box',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(primarySwatch: Colors.teal, fontFamily: 'Pretendard'),
      // 지역화 설정 추가
      localizationsDelegates: const [
        GlobalMaterialLocalizations.delegate,
        GlobalWidgetsLocalizations.delegate,
        GlobalCupertinoLocalizations.delegate,
      ],
      supportedLocales: const [
        Locale('ko', 'KR'), // 한국어
        Locale('en', 'US'), // 영어
      ],
      locale: const Locale('ko', 'KR'), // 기본 로케일 한국어
      initialRoute: '/signin', 
      // ✅ [onGenerateRoute] 사용으로 변경
      onGenerateRoute: (settings) {
        print('🔍 [onGenerateRoute] Requested route: ${settings.name}');
        print('🔍 [onGenerateRoute] Arguments: ${settings.arguments}');
        if (settings.name != null && settings.name!.startsWith('/home')) {
          return MaterialPageRoute(builder: (context) => const HomeUpdateScreen());
        }
        if (settings.name == '/home') {
          return MaterialPageRoute(builder: (context) => const HomeUpdateScreen());
        }
        if (settings.name == '/signin') {
          return MaterialPageRoute(builder: (context) => const SigninScreen());
        }
        if (settings.name == '/gallery') {
          return MaterialPageRoute(builder: (context) => const GalleryScreen());
        }
        if (settings.name == '/addphoto') {
          return MaterialPageRoute(builder: (context) => const AddPhotoScreen());
        }
        if (settings.name == '/conversation') {
          final args = settings.arguments as Map<String, dynamic>?;
          if (args != null) {
            return MaterialPageRoute(
              builder: (context) => PhotoConversationScreen(
                photoId: args['photoId'] ?? 'temp_photo_id',
                photoUrl: args['photoUrl'] ?? 'temp_photo_url',
                jwtToken: args['jwtToken'] ?? '',
              ),
            );
          } else {
            // 기본값으로 fallback (테스트용)
            return MaterialPageRoute(
              builder: (context) => const PhotoConversationScreen(
                photoId: 'temp_photo_id',
                photoUrl: 'temp_photo_url',
                jwtToken: '',
              ),
            );
          }
        }
        if (settings.name == '/kakao_signin') {
          return MaterialPageRoute(
            builder: (context) => const KakaoSigninScreen(),
            settings: settings, // ✅ arguments 전달 유지
          );
        }

        if (settings.name == '/profile') {
          return MaterialPageRoute(builder: (context) => const MyPage());
        }
        if (settings.name == '/profile-input') {
          return MaterialPageRoute(builder: (context) => const ProfileInputScreen());
        }
        if (settings.name == '/report') {
          return MaterialPageRoute(builder: (context) => const ReportListScreen());
        }
        if (settings.name == '/0-3-1') {
          return MaterialPageRoute(builder: (context) => const GroupSelectScreen());
        }
        if (settings.name == '/0-3-1-1') {
          return MaterialPageRoute(builder: (context) => const GroupCreateScreen());
        }
        if (settings.name == '/0-3-2') {
          return MaterialPageRoute(builder: (context) => const FamilyCodeInputScreen());
        }
        if (settings.name == '/photoDetail') {
          final photoData = settings.arguments as Map<String, dynamic>?;
          if (photoData != null) {
            return MaterialPageRoute(
              builder: (context) => PhotoDetailScreen(photoData: photoData),
            );
          }
        }
        // 카카오 OAuth 콜백 처리 - code 파라미터 감지
        if (settings.name?.contains('code=') == true ||
            settings.name == '/callback' || 
            settings.name == 'callback') {
          print('🔗 [OAuth Callback] Detected OAuth callback: ${settings.name}');
          return MaterialPageRoute(
            builder: (context) => const Scaffold(
              backgroundColor: Colors.white,
              body: Center(
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    CircularProgressIndicator(),
                    SizedBox(height: 16),
                    Text('로그인 처리 중...', 
                         style: TextStyle(fontSize: 16, fontFamily: 'Pretendard')),
                  ],
                ),
              ),
            ),
          );
        }
        // ✅ 알 수 없는 경로 대비 fallback - OAuth 처리중일 가능성 고려
        print('❓ [Unknown Route] Falling back for route: ${settings.name}');
        return MaterialPageRoute(
          builder: (context) => const Scaffold(
            backgroundColor: Colors.white,
            body: Center(
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  CircularProgressIndicator(),
                  SizedBox(height: 16),
                  Text('페이지 로딩 중...', 
                       style: TextStyle(fontSize: 16, fontFamily: 'Pretendard')),
                ],
              ),
            ),
          ),
        );
      },
    );
  }
}
