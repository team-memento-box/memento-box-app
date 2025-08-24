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
      // 먼저 기존 프로필이 있는지 확인
      final existing = await SupabaseService.client
          .from('users')
          .select()
          .eq('id', userId)
          .maybeSingle();

      if (existing != null) {
        print('✅ 기존 사용자 프로필 존재: $userId');
        return userId;
      }

      // 새 사용자 프로필 생성
      final profileData = {
        'id': userId,
        'email': email,
        'full_name': fullName ?? '',
        'profile_image_url': profileImageUrl ?? '',
        'onboarding_completed': false,
        'privacy_consent': false,
        'terms_accepted': false,
        'notification_enabled': true,
        'is_guardian': isGuardian ?? true,
      };

      await SupabaseService.client
          .from('users')
          .insert(profileData);

      print('✅ 새 사용자 프로필 생성: $userId');
      return userId;
    } catch (e) {
      print('❌ 사용자 프로필 생성/업데이트 오류: $e');
      return null;
    }
  }

  /// 현재 인증된 사용자의 프로필 존재 여부 확인
  static Future<bool> hasUserProfile(String userId) async {
    try {
      final profile = await SupabaseService.client
          .from('users')
          .select()
          .eq('id', userId)
          .maybeSingle();
      
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