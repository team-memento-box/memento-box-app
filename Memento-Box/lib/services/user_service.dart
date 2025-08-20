import '../core/supabase_service.dart';

class UserService {
  /// 사용자 프로필 업데이트 (온보딩 완료)
  static Future<bool> updateUserProfile({
    required String userId,
    required String fullName,
    String? birthDate,
    String? gender,
    String? phone,
    String? profileImageUrl,
    bool? privacyConsent,
    bool? termsAccepted,
    bool? notificationEnabled,
  }) async {
    try {
      final updateData = <String, dynamic>{
        'full_name': fullName,
        'onboarding_completed': true,
        'updated_at': DateTime.now().toIso8601String(),
      };

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

      return true;
    } catch (e) {
      print('사용자 프로필 업데이트 오류: $e');
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
    } catch (e) {
      print('로그아웃 오류: $e');
    }
  }
}