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

  /// 특정 세션의 CIST 데이터 조회 (리포트용)
  static Future<List<Map<String, dynamic>>> getCistDataBySession(String sessionId) async {
    try {
      print('🔍 CIST 데이터 조회 시작 - sessionId: $sessionId');
      
      // 해당 세션의 CIST 대화 조회
      final conversations = await SupabaseService.client
          .from('conversations')
          .select('id, session_id, cist_category, cist_score, is_cist_item, question_text, user_response_text')
          .eq('session_id', sessionId)
          .eq('is_cist_item', true)
          .filter('cist_category', 'in', '(registration,recall,naming,time_orientation)')
          .order('conversation_order', ascending: true);
      
      print('📊 해당 세션의 CIST 데이터: ${conversations.length}개');
      
      // 카테고리별로 그룹화하고 최신 데이터만 사용
      final Map<String, Map<String, dynamic>> categoryData = {};
      
      for (final conversation in conversations) {
        final category = conversation['cist_category'] as String;
        if (!categoryData.containsKey(category)) {
          categoryData[category] = {
            'category': _getCategoryDisplayName(category),
            'description': _getCategoryDescription(category),
            'question': conversation['question_text'] ?? '',
            'answer': conversation['user_response_text'] ?? '',
            'score': conversation['cist_score'] ?? 0,
            'isCorrect': (conversation['cist_score'] ?? 0) == 1,
          };
        }
      }
      
      // 순서를 맞춰서 반환
      final orderedCategories = ['time_orientation', 'registration', 'recall', 'naming'];
      final result = <Map<String, dynamic>>[];
      
      for (final category in orderedCategories) {
        if (categoryData.containsKey(category)) {
          result.add(categoryData[category]!);
        }
      }
      
      print('✅ CIST 데이터 처리 완료: ${result.length}개 카테고리');
      return result;
    } catch (e) {
      print('❌ CIST 데이터 조회 오류: $e');
      return [];
    }
  }
  
  /// CIST 카테고리의 표시용 이름 반환
  static String _getCategoryDisplayName(String category) {
    switch (category) {
      case 'time_orientation':
        return '시간지남력';
      case 'registration':
        return '기억력 등록';
      case 'recall':
        return '회상';
      case 'naming':
        return '명명';
      default:
        return category;
    }
  }
  
  /// CIST 카테고리의 설명 반환
  static String _getCategoryDescription(String category) {
    switch (category) {
      case 'time_orientation':
        return '현재 자신이 놓인 시간, 날짜, 계절 등의 상황을 올바르게 인식하는 능력';
      case 'registration':
        return '새로운 정보를 기억하고 저장하는 능력';
      case 'recall':
        return '이전에 학습한 정보를 기억해내는 능력';
      case 'naming':
        return '사물의 이름을 정확히 기억하고 표현하는 능력';
      default:
        return '인지 능력 평가 항목';
    }
  }
}