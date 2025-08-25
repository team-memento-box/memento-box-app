import 'package:flutter/material.dart';
import 'core/supabase_service.dart';

class UserProvider with ChangeNotifier {
  // Supabase Auth 관련
  String? id; // Supabase auth.users(id)
  String? email;
  String? accessToken;
  
  // User Profile 정보 (새로운 스키마)
  String? fullName; // full_name 필드
  String? name; // fullName의 별칭 (기존 코드 호환성)
  DateTime? birthDate; // birth_date 필드
  String? gender;
  String? phone;
  String? profileImageUrl; // profile_image_url 필드
  String? profileImg; // profileImageUrl의 별칭 (기존 코드 호환성)
  
  // 온보딩 및 설정
  bool onboardingCompleted = false;
  bool privacyConsent = false;
  bool termsAccepted = false;
  bool notificationEnabled = true;
  bool isGuardian = true; // 기본값은 보호자
  
  // 레거시 필드 (기존 코드 호환성을 위해 유지)
  String? kakaoId;
  String? username;
  
  // 가족 관련 (mypage.dart에서 사용하는 필드들)
  String? familyRole;
  String? familyCode;
  String? familyName;
  String? familyId;
  
  // 추가 필드들
  DateTime? birthday;
  DateTime? createdAt;

  /// 사용자 데이터 설정 (새로운 Supabase 스키마용)
  void setUserFromSupabase({
    required String id,
    String? kakaoId,
    required String email,
    String? fullName,
    DateTime? birthDate,
    String? gender,
    String? phone,
    String? profileImageUrl,
    bool? onboardingCompleted,
    bool? privacyConsent,
    bool? termsAccepted,
    bool? notificationEnabled,
    bool? isGuardian,
    String? accessToken,
  }) {
    this.id = id;
    this.email = email;
    this.fullName = fullName;
    this.name = fullName; // 별칭 설정
    this.birthDate = birthDate;
    this.gender = gender;
    this.phone = phone;
    this.profileImageUrl = profileImageUrl;
    this.profileImg = profileImageUrl; // 별칭 설정
    this.onboardingCompleted = onboardingCompleted ?? false;
    this.privacyConsent = privacyConsent ?? false;
    this.termsAccepted = termsAccepted ?? false;
    this.notificationEnabled = notificationEnabled ?? true;
    this.isGuardian = isGuardian ?? true;
    this.accessToken = accessToken;
    
    notifyListeners();
  }

  /// 기존 코드 호환성을 위한 레거시 setUser 메서드
  void setUser({
    required String kakaoId,
    required String username,
    required String email,
    required String profileImg,
    required String gender,
  }) {
    this.kakaoId = kakaoId;
    this.username = username;
    this.email = email;
    this.profileImg = profileImg;
    this.profileImageUrl = profileImg; // 새로운 필드에도 설정
    this.gender = gender;
    this.name = username; // name 필드에도 설정
    this.fullName = username; // fullName 필드에도 설정
    notifyListeners();
  }

  /// Supabase에서 현재 사용자 정보 로드
  Future<void> loadUserFromSupabase() async {
    final currentUser = SupabaseService.client.auth.currentUser;
    if (currentUser == null) return;

    try {
      // users 테이블에서 프로필 정보 조회
      final profile = await SupabaseService.client
          .from('users')
          .select()
          .eq('id', currentUser.id)
          .maybeSingle();

      if (profile != null) {
        setUserFromSupabase(
          id: currentUser.id,
          email: currentUser.email ?? '',
          fullName: profile['full_name'],
          birthDate: profile['birth_date'] != null 
              ? DateTime.parse(profile['birth_date']) 
              : null,
          gender: profile['gender'],
          phone: profile['phone'],
          profileImageUrl: profile['profile_image_url'],
          onboardingCompleted: profile['onboarding_completed'] ?? false,
          privacyConsent: profile['privacy_consent'] ?? false,
          termsAccepted: profile['terms_accepted'] ?? false,
          notificationEnabled: profile['notification_enabled'] ?? true,
          isGuardian: profile['is_guardian'] ?? true,
          accessToken: SupabaseService.client.auth.currentSession?.accessToken,
        );

        // 가족 정보 로드
        await _loadFamilyInfo(currentUser.id);
        
      } else {
        // 프로필이 없으면 기본값으로 설정
        setUserFromSupabase(
          id: currentUser.id,
          email: currentUser.email ?? '',
          accessToken: SupabaseService.client.auth.currentSession?.accessToken,
        );
      }
    } catch (e) {
      print('사용자 정보 로드 오류: $e');
    }
  }

  /// 가족 정보 로드 (private 메서드)
  Future<void> _loadFamilyInfo(String userId) async {
    try {
      // 1. 사용자의 family_members 레코드 조회
      final memberInfo = await SupabaseService.client
          .from('family_members')
          .select('family_id, family_role')
          .eq('user_id', userId)
          .maybeSingle();

      if (memberInfo != null) {
        // 2. 가족 정보 조회
        final familyInfo = await SupabaseService.client
            .from('families')
            .select('family_code, family_name')
            .eq('id', memberInfo['family_id'])
            .maybeSingle();

        if (familyInfo != null) {
          // 3. 가족 정보 설정
          this.familyId = memberInfo['family_id'];
          this.familyRole = memberInfo['family_role'];
          this.familyCode = familyInfo['family_code'];
          this.familyName = familyInfo['family_name'];
          
          print('✅ 가족 정보 로드 완료: ${familyInfo['family_name']} (${familyInfo['family_code']})');
          notifyListeners();
        }
      } else {
        print('ℹ️ 가족 멤버 정보가 없습니다');
      }
    } catch (e) {
      print('❌ 가족 정보 로드 오류: $e');
    }
  }

  /// 가족 생성 정보 설정
  void setFamilyCreate({
    required String familyId,
    required String familyCode,
    required String familyName,
  }) {
    this.familyId = familyId;
    this.familyCode = familyCode;
    this.familyName = familyName;
    notifyListeners();
  }

  /// 가족 가입 정보 설정
  void setFamilyJoin({
    required String familyId,
    required String familyCode,
    required String familyName,
  }) {
    this.familyId = familyId;
    this.familyCode = familyCode;
    this.familyName = familyName;
    notifyListeners();
  }

  /// 가족 역할 설정
  void setFamilyInfo({required String familyRole}) {
    this.familyRole = familyRole;
    notifyListeners();
  }

  /// 액세스 토큰 설정
  void setAccessToken(String token) {
    this.accessToken = token;
    notifyListeners();
  }

  /// isGuardian 값 설정
  void setIsGuardian(bool isGuardian) {
    this.isGuardian = isGuardian;
    notifyListeners();
  }

  void clearUser() {
    id = null;
    email = null;
    fullName = null;
    name = null;
    birthDate = null;
    gender = null;
    phone = null;
    profileImageUrl = null;
    profileImg = null;
    onboardingCompleted = false;
    privacyConsent = false;
    termsAccepted = false;
    notificationEnabled = true;
    isGuardian = true;
    accessToken = null;
    
    // 레거시 필드들도 클리어
    kakaoId = null;
    username = null;
    
    // 가족 관련 필드들도 클리어
    familyRole = null;
    familyCode = null;
    familyName = null;
    familyId = null;
    
    // 추가 필드들도 클리어
    birthday = null;
    createdAt = null;
    
    notifyListeners();
  }
}
