import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:provider/provider.dart';
import '../user_provider.dart';
import '../core/supabase_service.dart';

class ProfileInputScreen extends StatefulWidget {
  const ProfileInputScreen({super.key});

  @override
  State<ProfileInputScreen> createState() => _ProfileInputScreenState();
}

class _ProfileInputScreenState extends State<ProfileInputScreen> {
  final _formKey = GlobalKey<FormState>();
  final _phoneController = TextEditingController();
  
  DateTime? _selectedBirthDate;
  String? _selectedGender;
  bool _privacyConsent = false;
  bool _isLoading = false;
  
  @override
  void dispose() {
    _phoneController.dispose();
    super.dispose();
  }

  // 생년월일 선택
  Future<void> _selectBirthDate() async {
    final DateTime? picked = await showDatePicker(
      context: context,
      initialDate: DateTime(1980),
      firstDate: DateTime(1900),
      lastDate: DateTime.now(),
      builder: (context, child) {
        return Theme(
          data: Theme.of(context).copyWith(
            colorScheme: const ColorScheme.light(
              primary: Color(0xFF8CCAA7),
              onPrimary: Colors.white,
              surface: Colors.white,
              onSurface: Colors.black,
            ),
          ),
          child: child!,
        );
      },
    );

    if (picked != null && picked != _selectedBirthDate) {
      setState(() {
        _selectedBirthDate = picked;
      });
    }
  }

  // 개인정보 저장 및 다음 단계로 이동
  Future<void> _saveProfileAndContinue() async {
    if (!_formKey.currentState!.validate()) return;
    if (!_privacyConsent) {
      _showErrorDialog('개인정보 수집 및 이용에 동의해주세요.');
      return;
    }

    setState(() => _isLoading = true);

    try {
      final userProvider = Provider.of<UserProvider>(context, listen: false);
      
      // Supabase users 테이블 업데이트
      final currentUser = SupabaseService.client.auth.currentUser;
      if (currentUser != null) {
        await SupabaseService.client.from('users').update({
          'birth_date': _selectedBirthDate!.toIso8601String().split('T')[0],
          'gender': _selectedGender,
          'phone': _phoneController.text.trim(),
          'privacy_consent': true,
          'terms_accepted': true,
          'onboarding_completed': false, // 아직 온보딩 미완료
        }).eq('id', currentUser.id);

        // UserProvider 업데이트
        print('🔄 [Profile] Updating UserProvider...');
        print('🔄 [Profile] Before - fullName: ${userProvider.fullName}');
        print('🔄 [Profile] Before - profileImg: ${userProvider.profileImg}');
        print('🔄 [Profile] Before - isGuardian: ${userProvider.isGuardian}');
        
        userProvider.setUserFromSupabase(
          id: currentUser.id,
          email: currentUser.email ?? '',
          fullName: userProvider.fullName,
          birthDate: _selectedBirthDate,
          gender: _selectedGender,
          phone: _phoneController.text.trim(),
          profileImageUrl: userProvider.profileImageUrl, // 기존 프로필 이미지 유지
          privacyConsent: true,
          termsAccepted: true,
          onboardingCompleted: false,
          isGuardian: userProvider.isGuardian, // 기존 isGuardian 값 유지
          accessToken: SupabaseService.client.auth.currentSession?.accessToken,
        );
        
        print('🔄 [Profile] After - fullName: ${userProvider.fullName}');
        print('🔄 [Profile] After - profileImg: ${userProvider.profileImg}');
        print('🔄 [Profile] After - isGuardian: ${userProvider.isGuardian}');
      }

      // 다음 화면으로 이동 - isGuardian 값에 따라 결정
      if (mounted) {
        final isGuardian = userProvider.isGuardian;
        print('🧭 Profile saved. isGuardian: $isGuardian');
        
        if (isGuardian) {
          print('🧭 Guardian: navigating to 0-3-1');
          Navigator.pushReplacementNamed(context, '/0-3-1');
        } else {
          print('🧭 Dependent: navigating to 0-3-2');
          Navigator.pushReplacementNamed(context, '/0-3-2');
        }
      }
      
    } catch (e) {
      print('개인정보 저장 오류: $e');
      if (mounted) {
        _showErrorDialog('개인정보 저장 중 오류가 발생했습니다. 다시 시도해주세요.');
      }
    } finally {
      if (mounted) {
        setState(() => _isLoading = false);
      }
    }
  }

  void _showErrorDialog(String message) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('알림'),
        content: Text(message),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('확인'),
          ),
        ],
      ),
    );
  }

  void _showPrivacyPolicy() {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text(
          '개인정보 수집 및 이용 동의',
          style: TextStyle(
            fontSize: 18,
            fontWeight: FontWeight.w700,
            fontFamily: 'Pretendard',
          ),
        ),
        content: const SingleChildScrollView(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(
                '1. 수집하는 개인정보 항목',
                style: TextStyle(fontWeight: FontWeight.w600, fontSize: 14),
              ),
              SizedBox(height: 4),
              Text(
                '• 생년월일, 성별, 전화번호\n• 카카오 로그인을 통한 이메일, 프로필 정보',
                style: TextStyle(fontSize: 13, height: 1.4),
              ),
              SizedBox(height: 12),
              Text(
                '2. 개인정보 수집 및 이용 목적',
                style: TextStyle(fontWeight: FontWeight.w600, fontSize: 14),
              ),
              SizedBox(height: 4),
              Text(
                '• 서비스 제공 및 맞춤형 콘텐츠 제공\n• 연령별 인지 기능 평가 및 분석\n• 고객 지원 및 서비스 개선',
                style: TextStyle(fontSize: 13, height: 1.4),
              ),
              SizedBox(height: 12),
              Text(
                '3. 개인정보 보유 및 이용 기간',
                style: TextStyle(fontWeight: FontWeight.w600, fontSize: 14),
              ),
              SizedBox(height: 4),
              Text(
                '• 서비스 이용 기간 중\n• 회원 탈퇴 시 즉시 파기 (법정 보존 의무가 있는 경우 예외)',
                style: TextStyle(fontSize: 13, height: 1.4),
              ),
              SizedBox(height: 12),
              Text(
                '4. 개인정보 파기 절차 및 방법',
                style: TextStyle(fontWeight: FontWeight.w600, fontSize: 14),
              ),
              SizedBox(height: 4),
              Text(
                '• 전자 파일 형태: 복구 불가능한 방법으로 즉시 삭제\n• 종이 문서: 분쇄 또는 소각',
                style: TextStyle(fontSize: 13, height: 1.4),
              ),
              SizedBox(height: 12),
              Text(
                '※ 위 개인정보 수집에 동의하지 않을 권리가 있으나, 동의를 거부할 경우 서비스 이용이 제한될 수 있습니다.',
                style: TextStyle(fontSize: 12, color: Color(0xFF666666), height: 1.4),
              ),
            ],
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text(
              '확인',
              style: TextStyle(
                color: Color(0xFF8CCAA7),
                fontWeight: FontWeight.w600,
              ),
            ),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final userProvider = Provider.of<UserProvider>(context);
    
    return Scaffold(
      backgroundColor: Colors.white,
      appBar: AppBar(
        title: const Text(
          '개인정보 입력',
          style: TextStyle(
            fontSize: 20,
            fontWeight: FontWeight.w700,
            fontFamily: 'Pretendard',
            color: Colors.white,
          ),
        ),
        backgroundColor: const Color(0xFF8CCAA7),
        centerTitle: true,
        elevation: 0,
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(24),
        child: Form(
          key: _formKey,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // 안내 메시지
              Container(
                width: double.infinity,
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: const Color(0xFF8CCAA7).withOpacity(0.1),
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(
                    color: const Color(0xFF8CCAA7).withOpacity(0.3),
                  ),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        const Icon(
                          Icons.info_outline,
                          color: Color(0xFF8CCAA7),
                          size: 20,
                        ),
                        const SizedBox(width: 8),
                        Text(
                          '환영합니다, ${userProvider.fullName ?? userProvider.username ?? '사용자'}님!',
                          style: const TextStyle(
                            fontSize: 16,
                            fontWeight: FontWeight.w700,
                            fontFamily: 'Pretendard',
                            color: Color(0xFF8CCAA7),
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 8),
                    const Text(
                      '맞춤형 서비스 제공을 위해 추가 정보를 입력해주세요.\n입력하신 정보는 안전하게 보호됩니다.',
                      style: TextStyle(
                        fontSize: 14,
                        fontFamily: 'Pretendard',
                        color: Color(0xFF555555),
                        height: 1.4,
                      ),
                    ),
                  ],
                ),
              ),
              
              const SizedBox(height: 32),
              
              // 생년월일 입력
              const Text(
                '생년월일',
                style: TextStyle(
                  fontSize: 16,
                  fontWeight: FontWeight.w600,
                  fontFamily: 'Pretendard',
                  color: Color(0xFF333333),
                ),
              ),
              const SizedBox(height: 8),
              GestureDetector(
                onTap: _selectBirthDate,
                child: Container(
                  width: double.infinity,
                  padding: const EdgeInsets.all(16),
                  decoration: BoxDecoration(
                    border: Border.all(color: const Color(0xFFDDDDDD)),
                    borderRadius: BorderRadius.circular(12),
                    color: Colors.white,
                  ),
                  child: Row(
                    children: [
                      Icon(
                        Icons.calendar_today,
                        color: Colors.grey[600],
                        size: 20,
                      ),
                      const SizedBox(width: 12),
                      Text(
                        _selectedBirthDate != null
                            ? '${_selectedBirthDate!.year}년 ${_selectedBirthDate!.month.toString().padLeft(2, '0')}월 ${_selectedBirthDate!.day.toString().padLeft(2, '0')}일'
                            : '생년월일을 선택해주세요',
                        style: TextStyle(
                          fontSize: 16,
                          fontFamily: 'Pretendard',
                          color: _selectedBirthDate != null 
                              ? const Color(0xFF333333) 
                              : const Color(0xFF999999),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
              if (_selectedBirthDate == null) ...[
                const SizedBox(height: 4),
                const Text(
                  '생년월일을 선택해주세요',
                  style: TextStyle(
                    fontSize: 12,
                    color: Color(0xFFE74C3C),
                    fontFamily: 'Pretendard',
                  ),
                ),
              ],
              
              const SizedBox(height: 24),
              
              // 성별 선택
              const Text(
                '성별',
                style: TextStyle(
                  fontSize: 16,
                  fontWeight: FontWeight.w600,
                  fontFamily: 'Pretendard',
                  color: Color(0xFF333333),
                ),
              ),
              const SizedBox(height: 8),
              Row(
                children: [
                  Expanded(
                    child: GestureDetector(
                      onTap: () => setState(() => _selectedGender = 'male'),
                      child: Container(
                        padding: const EdgeInsets.all(16),
                        decoration: BoxDecoration(
                          border: Border.all(
                            color: _selectedGender == 'male' 
                                ? const Color(0xFF8CCAA7) 
                                : const Color(0xFFDDDDDD),
                            width: _selectedGender == 'male' ? 2 : 1,
                          ),
                          borderRadius: BorderRadius.circular(12),
                          color: _selectedGender == 'male' 
                              ? const Color(0xFF8CCAA7).withOpacity(0.1)
                              : Colors.white,
                        ),
                        child: Row(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            Icon(
                              Icons.male,
                              color: _selectedGender == 'male'
                                  ? const Color(0xFF8CCAA7)
                                  : const Color(0xFF999999),
                            ),
                            const SizedBox(width: 8),
                            Text(
                              '남성',
                              style: TextStyle(
                                fontSize: 16,
                                fontWeight: FontWeight.w500,
                                fontFamily: 'Pretendard',
                                color: _selectedGender == 'male'
                                    ? const Color(0xFF8CCAA7)
                                    : const Color(0xFF666666),
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: GestureDetector(
                      onTap: () => setState(() => _selectedGender = 'female'),
                      child: Container(
                        padding: const EdgeInsets.all(16),
                        decoration: BoxDecoration(
                          border: Border.all(
                            color: _selectedGender == 'female' 
                                ? const Color(0xFF8CCAA7) 
                                : const Color(0xFFDDDDDD),
                            width: _selectedGender == 'female' ? 2 : 1,
                          ),
                          borderRadius: BorderRadius.circular(12),
                          color: _selectedGender == 'female' 
                              ? const Color(0xFF8CCAA7).withOpacity(0.1)
                              : Colors.white,
                        ),
                        child: Row(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            Icon(
                              Icons.female,
                              color: _selectedGender == 'female'
                                  ? const Color(0xFF8CCAA7)
                                  : const Color(0xFF999999),
                            ),
                            const SizedBox(width: 8),
                            Text(
                              '여성',
                              style: TextStyle(
                                fontSize: 16,
                                fontWeight: FontWeight.w500,
                                fontFamily: 'Pretendard',
                                color: _selectedGender == 'female'
                                    ? const Color(0xFF8CCAA7)
                                    : const Color(0xFF666666),
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                  ),
                ],
              ),
              if (_selectedGender == null) ...[
                const SizedBox(height: 4),
                const Text(
                  '성별을 선택해주세요',
                  style: TextStyle(
                    fontSize: 12,
                    color: Color(0xFFE74C3C),
                    fontFamily: 'Pretendard',
                  ),
                ),
              ],
              
              const SizedBox(height: 24),
              
              // 전화번호 입력
              const Text(
                '전화번호',
                style: TextStyle(
                  fontSize: 16,
                  fontWeight: FontWeight.w600,
                  fontFamily: 'Pretendard',
                  color: Color(0xFF333333),
                ),
              ),
              const SizedBox(height: 8),
              TextFormField(
                controller: _phoneController,
                keyboardType: TextInputType.phone,
                inputFormatters: [
                  FilteringTextInputFormatter.digitsOnly,
                  LengthLimitingTextInputFormatter(11),
                ],
                decoration: InputDecoration(
                  hintText: '010-0000-0000',
                  hintStyle: const TextStyle(
                    color: Color(0xFF999999),
                    fontFamily: 'Pretendard',
                  ),
                  prefixIcon: const Icon(Icons.phone, color: Color(0xFF999999)),
                  border: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(12),
                    borderSide: const BorderSide(color: Color(0xFFDDDDDD)),
                  ),
                  enabledBorder: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(12),
                    borderSide: const BorderSide(color: Color(0xFFDDDDDD)),
                  ),
                  focusedBorder: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(12),
                    borderSide: const BorderSide(color: Color(0xFF8CCAA7), width: 2),
                  ),
                  contentPadding: const EdgeInsets.all(16),
                ),
                validator: (value) {
                  if (value == null || value.trim().isEmpty) {
                    return '전화번호를 입력해주세요';
                  }
                  if (value.length < 10 || value.length > 11) {
                    return '올바른 전화번호를 입력해주세요';
                  }
                  return null;
                },
              ),
              
              const SizedBox(height: 32),
              
              // 개인정보 수집 동의
              Container(
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: const Color(0xFFF8F9FA),
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(color: const Color(0xFFE9ECEF)),
                ),
                child: Column(
                  children: [
                    Row(
                      children: [
                        GestureDetector(
                          onTap: () => setState(() => _privacyConsent = !_privacyConsent),
                          child: Container(
                            width: 24,
                            height: 24,
                            decoration: BoxDecoration(
                              color: _privacyConsent ? const Color(0xFF8CCAA7) : Colors.white,
                              border: Border.all(
                                color: _privacyConsent ? const Color(0xFF8CCAA7) : const Color(0xFFDDDDDD),
                                width: 2,
                              ),
                              borderRadius: BorderRadius.circular(4),
                            ),
                            child: _privacyConsent
                                ? const Icon(Icons.check, color: Colors.white, size: 16)
                                : null,
                          ),
                        ),
                        const SizedBox(width: 12),
                        const Expanded(
                          child: Text(
                            '개인정보 수집 및 이용에 동의합니다',
                            style: TextStyle(
                              fontSize: 14,
                              fontWeight: FontWeight.w500,
                              fontFamily: 'Pretendard',
                              color: Color(0xFF333333),
                            ),
                          ),
                        ),
                        TextButton(
                          onPressed: _showPrivacyPolicy,
                          child: const Text(
                            '상세보기',
                            style: TextStyle(
                              fontSize: 13,
                              color: Color(0xFF8CCAA7),
                              fontWeight: FontWeight.w600,
                              fontFamily: 'Pretendard',
                            ),
                          ),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
              
              const SizedBox(height: 40),
              
              // 다음 버튼
              SizedBox(
                width: double.infinity,
                height: 56,
                child: ElevatedButton(
                  onPressed: _isLoading ? null : _saveProfileAndContinue,
                  style: ElevatedButton.styleFrom(
                    backgroundColor: const Color(0xFF8CCAA7),
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(16),
                    ),
                    elevation: 0,
                  ),
                  child: _isLoading
                      ? const CircularProgressIndicator(color: Colors.white)
                      : const Text(
                          '다음',
                          style: TextStyle(
                            fontSize: 18,
                            fontWeight: FontWeight.w600,
                            fontFamily: 'Pretendard',
                            color: Colors.white,
                          ),
                        ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}