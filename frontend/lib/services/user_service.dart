import '../core/supabase_service.dart';

class UserService {
  /// 사용자 프로필 업데이트 (온보딩 완료)
  static Future<bool> updateUserProfile({
    required String userId,
    required String fullName,
    String? birthDate, // DATE 포맷 (YYYY-MM-DD)
    String? gender, // 'male', 'female', 'other'
    String? phone,
    String? profileImageUrl,
    bool? privacyConsent,
    bool? termsAccepted,
    bool? notificationEnabled,
    bool? markOnboardingComplete = true,
  }) async {
    try {
      final updateData = <String, dynamic>{
        'full_name': fullName,
        'updated_at': DateTime.now().toIso8601String(),
      };

      if (markOnboardingComplete == true) {
        updateData['onboarding_completed'] = true;
      }

      // 선택적 필드들 추가
      if (birthDate != null) updateData['birth_date'] = birthDate;
      if (gender != null) updateData['gender'] = gender;
      if (phone != null) updateData['phone'] = phone;
      if (profileImageUrl != null) updateData['profile_image_url'] = profileImageUrl;
      if (privacyConsent != null) updateData['privacy_consent'] = privacyConsent;
      if (termsAccepted != null) updateData['terms_accepted'] = termsAccepted;
      if (notificationEnabled != null) updateData['notification_enabled'] = notificationEnabled;

      await SupabaseService.client
          .from('users')
          .update(updateData)
          .eq('id', userId);

      print('✅ User profile updated successfully for: $userId');
      return true;
    } catch (e) {
      print('❌ 사용자 프로필 업데이트 오류: $e');
      return false;
    }
  }

  /// 사용자 프로필 조회
  static Future<Map<String, dynamic>?> getUserProfile(String userId) async {
    try {
      final profile = await SupabaseService.client
          .from('users')
          .select()
          .eq('id', userId)
          .single();
      
      return profile;
    } catch (e) {
      print('사용자 프로필 조회 오류: $e');
      return null;
    }
  }

  /// 사용자 계정 삭제
  static Future<bool> deleteUser(String userId) async {
    try {
      await SupabaseService.client
          .from('users')
          .delete()
          .eq('id', userId);
      
      // Supabase Auth에서도 로그아웃
      await SupabaseService.client.auth.signOut();
      
      return true;
    } catch (e) {
      print('사용자 계정 삭제 오류: $e');
      return false;
    }
  }

  /// 로그아웃
  static Future<void> logout() async {
    try {
      await SupabaseService.client.auth.signOut();
      print('✅ User logged out successfully');
    } catch (e) {
      print('❌ 로그아웃 오류: $e');
    }
  }

  /// OAuth 로그인 후 사용자 프로필 생성 또는 업데이트
  static Future<String?> createOrUpdateUserProfile({
    required String userId,
    required String email,
    String? fullName,
    String? profileImageUrl,
    bool? isGuardian,
  }) async {
    try {
      final user = SupabaseService.client.auth.currentUser;
      
      // JWT 토큰이 완전히 설정될 때까지 잠시 대기
      await Future.delayed(const Duration(milliseconds: 500));
      
      // 현재 인증 상태 확인
      final currentUser = SupabaseService.client.auth.currentUser;
      final session = SupabaseService.client.auth.currentSession;
      print('🔐 Auth check - User ID: ${currentUser?.id}, JWT exists: ${session?.accessToken != null}');
      
      if (currentUser == null) {
        throw Exception('인증된 사용자가 없습니다');
      }
      
      // Supabase에서 auth.uid() 값 확인을 위한 디버깅 쿼리
      try {
        final authCheck = await SupabaseService.client
            .rpc('get_current_user_id'); // 이 함수가 없다면 에러가 날 것임
        print('🔐 Supabase auth.uid(): $authCheck');
      } catch (e) {
        print('🔐 auth.uid() 확인 실패 (함수 없음): $e');
      }
      
      // 직접 SQL로 확인 (위험하지만 디버깅용)
      try {
        final testAuth = await SupabaseService.client
            .from('users')
            .select('id')
            .limit(1);
        print('🔐 Users 테이블 읽기 권한 확인: 성공');
      } catch (e) {
        print('🔐 Users 테이블 읽기 권한 확인: $e');
      }
      
      // upsert with onConflict 사용 (id가 auth.uid()와 동일해야 함)
      print('🔄 UPSERT 시도 (onConflict: id)');
      await SupabaseService.client.from('users').upsert({
        'id': currentUser.id, // 👈 auth.uid()와 동일해야 함
        'email': currentUser.email,
        'full_name': currentUser.userMetadata?['full_name'] ?? fullName ?? '',
        'profile_image_url': currentUser.userMetadata?['avatar_url'] ?? 
                            currentUser.userMetadata?['picture'] ?? 
                            currentUser.userMetadata?['profile_image_url'] ?? 
                            currentUser.userMetadata?['thumbnail_image_url'] ?? 
                            profileImageUrl ?? '',
        'onboarding_completed': false,
        'privacy_consent': false,
        'terms_accepted': false,
        'notification_enabled': true,
        'is_guardian': isGuardian ?? true,
        'updated_at': DateTime.now().toIso8601String(),
      }, onConflict: 'id');
      print('✅ UPSERT 완료');

      print('✅ 사용자 프로필 upsert 완료: $userId');
      return userId;
    } catch (e) {
      print('❌ 사용자 프로필 생성/업데이트 오류: $e');
      print('❌ 오류 타입: ${e.runtimeType}');
      print('❌ 오류 상세: ${e.toString()}');
      return null;
    }
  }

  /// 현재 인증된 사용자의 프로필 존재 여부 확인
  static Future<bool> hasUserProfile(String userId) async {
    try {
      print('🔍 hasUserProfile 체크 시작 - userId: $userId');
      
      final profile = await SupabaseService.client
          .from('users')
          .select('id, full_name, email')
          .eq('id', userId)
          .maybeSingle();
      
      print('🔍 hasUserProfile 결과: ${profile != null ? "존재함" : "없음"}');
      if (profile != null) {
        print('🔍 기존 프로필 정보: ${profile['full_name']} (${profile['email']})');
      }
      
      return profile != null;
    } catch (e) {
      print('❌ 프로필 확인 오류: $e');
      return false;
    }
  }

  /// 사용자의 온보딩 상태 확인
  static Future<bool> isOnboardingCompleted(String userId) async {
    try {
      final profile = await SupabaseService.client
          .from('users')
          .select('onboarding_completed')
          .eq('id', userId)
          .single();
      
      return profile['onboarding_completed'] ?? false;
    } catch (e) {
      print('❌ 온보딩 상태 확인 오류: $e');
      return false;
    }
  }
}