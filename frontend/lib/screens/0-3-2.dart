// 작성자: gwona
// 작성일: 2025.06.05
// 목적: 피보호자 가족 코드 입력 화면 리팩토링

import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/user_provider.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';
import 'package:flutter_dotenv/flutter_dotenv.dart';
import '../utils/routes.dart';
import '../core/supabase_service.dart';
class FamilyCodeInputScreen extends StatefulWidget {
  const FamilyCodeInputScreen({super.key});

  @override
  State<FamilyCodeInputScreen> createState() => _FamilyCodeInputScreenState();
}

class _FamilyCodeInputScreenState extends State<FamilyCodeInputScreen> {
  final TextEditingController codeController = TextEditingController();

  bool get isCodeEntered => codeController.text.isNotEmpty;

  @override
  void initState() {
    super.initState();
    codeController.addListener(() => setState(() {}));
  }




  Future<void> _submitFamilyCode() async {
    final code = codeController.text.trim();
    
    try {
      final currentUser = SupabaseService.client.auth.currentUser;
      if (currentUser == null) {
        throw Exception('로그인이 필요합니다');
      }

      // 1. 가족 코드로 가족 찾기
      final familyData = await SupabaseService.client
          .from('families')
          .select('*')
          .eq('family_code', code)
          .maybeSingle();

      if (familyData == null) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('유효하지 않은 가족 코드입니다.')),
        );
        return;
      }

      // 2. 이미 가족 멤버인지 확인
      final existingMember = await SupabaseService.client
          .from('family_members')
          .select('id')
          .eq('user_id', currentUser.id)
          .eq('family_id', familyData['id'])
          .maybeSingle();

      if (existingMember != null) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('이미 해당 가족의 멤버입니다.')),
        );
        return;
      }

      // 3. 가족 정보를 Provider에 저장
      final userProvider = Provider.of<UserProvider>(context, listen: false);
      userProvider.setFamilyJoin(
        familyId: familyData['id'],
        familyCode: familyData['family_code'],
        familyName: familyData['family_name'],
      );

      // 4. 성별에 따른 역할 설정
      String? gender = userProvider.gender;
      String familyRole = '';
      if (gender == 'male') {
        familyRole = '아빠';
      } else if (gender == 'female') {
        familyRole = '엄마';
      } else {
        familyRole = '피보호자';
      }
      userProvider.setFamilyInfo(familyRole: familyRole);

      // 5. 가족 멤버로 추가
      await SupabaseService.client
          .from('family_members')
          .insert({
            'user_id': currentUser.id,
            'family_id': familyData['id'],
            'family_role': familyRole,
          });

      // 6. 사용자 테이블에 현재 가족 ID 및 온보딩 완료 업데이트
      await SupabaseService.client
          .from('users')
          .update({
            'current_family_id': familyData['id'],
            'onboarding_completed': true
          })
          .eq('id', currentUser.id);

      print('✅ 피보호자 가족 가입 완료');
      print('✅ 온보딩 완료 처리됨');

      if (mounted) {
        Navigator.pushNamed(context, '/home');
      }
      
    } catch (e) {
      print('❌ 가족 코드 입력 오류: $e');
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('네트워크 오류: $e')),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.white,
      body: SafeArea(
        child: SingleChildScrollView(
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 24.0),
            child: ConstrainedBox(
              constraints: BoxConstraints(
                minHeight: MediaQuery.of(context).size.height - 
                          MediaQuery.of(context).padding.top - 
                          MediaQuery.of(context).padding.bottom,
              ),
              child: Column(
                children: [
                  const SizedBox(height: 40),
                  _buildHeader(),
                  const SizedBox(height: 60),
                  _buildContentCard(),
                  const SizedBox(height: 40),
                  _buildHomeIndicator(),
                  const SizedBox(height: 20),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildHeader() {
    return Column(
      children: [
        Container(
          width: 120,
          height: 120,
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(20),
            boxShadow: [
              BoxShadow(
                color: const Color(0xFF8CCAA7).withOpacity(0.2),
                blurRadius: 20,
                offset: const Offset(0, 8),
              ),
            ],
          ),
          child: ClipRRect(
            borderRadius: BorderRadius.circular(20),
            child: Image.asset(
              "assets/images/temp_logo.png",
              fit: BoxFit.cover,
            ),
          ),
        ),
        const SizedBox(height: 24),
        const Text(
          'MEMENTO BOX',
          style: TextStyle(
            fontSize: 24,
            fontWeight: FontWeight.w700,
            fontFamily: 'Pretendard',
            color: Color(0xFF8CCAA7),
            letterSpacing: 2,
          ),
        ),
      ],
    );
  }

  Widget _buildContentCard() {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(32),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(24),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.05),
            blurRadius: 20,
            offset: const Offset(0, 8),
          ),
        ],
        border: Border.all(
          color: const Color(0xFF8CCAA7).withOpacity(0.1),
          width: 1,
        ),
      ),
      child: Column(
        children: [
          _buildWelcomeText(),
          const SizedBox(height: 40),
          _buildInputField(),
          const SizedBox(height: 32),
          _buildSubmitButton(),
        ],
      ),
    );
  }

  Widget _buildWelcomeText() {
    return Column(
      children: [
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
          decoration: BoxDecoration(
            color: const Color(0xFF8CCAA7).withOpacity(0.1),
            borderRadius: BorderRadius.circular(20),
          ),
          child: const Text(
            '👋 안녕하세요 피보호자님',
            style: TextStyle(
              fontSize: 16,
              fontWeight: FontWeight.w600,
              fontFamily: 'Pretendard',
              color: Color(0xFF8CCAA7),
            ),
          ),
        ),
        const SizedBox(height: 20),
        const Text(
          '보호자님께 전달받은\n가족 코드를 입력해주세요',
          textAlign: TextAlign.center,
          style: TextStyle(
            fontSize: 18,
            fontWeight: FontWeight.w500,
            fontFamily: 'Pretendard',
            color: Color(0xFF333333),
            height: 1.4,
          ),
        ),
        const SizedBox(height: 12),
        Text(
          '가족 코드를 통해 우리 가족만의\n추억 보관함에 함께할 수 있어요',
          textAlign: TextAlign.center,
          style: TextStyle(
            fontSize: 14,
            fontWeight: FontWeight.w400,
            fontFamily: 'Pretendard',
            color: Colors.grey[600],
            height: 1.4,
          ),
        ),
      ],
    );
  }

  Widget _buildInputField() {
    return Container(
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(16),
        boxShadow: [
          BoxShadow(
            color: isCodeEntered 
                ? const Color(0xFF8CCAA7).withOpacity(0.2)
                : Colors.grey.withOpacity(0.1),
            blurRadius: 10,
            offset: const Offset(0, 4),
          ),
        ],
      ),
      child: TextField(
        controller: codeController,
        textAlign: TextAlign.center,
        style: const TextStyle(
          fontSize: 20,
          fontWeight: FontWeight.w600,
          fontFamily: 'Pretendard',
          letterSpacing: 2,
        ),
        decoration: InputDecoration(
          hintText: '가족 코드 입력',
          hintStyle: const TextStyle(
            fontSize: 16,
            color: Color(0xFF999999),
            fontFamily: 'Pretendard',
            letterSpacing: 1,
          ),
          contentPadding: const EdgeInsets.symmetric(
            horizontal: 24,
            vertical: 20,
          ),
          filled: true,
          fillColor: Colors.white,
          border: OutlineInputBorder(
            borderRadius: BorderRadius.circular(16),
            borderSide: BorderSide(
              color: const Color(0xFF8CCAA7).withOpacity(0.3),
              width: 2,
            ),
          ),
          enabledBorder: OutlineInputBorder(
            borderRadius: BorderRadius.circular(16),
            borderSide: BorderSide(
              color: Colors.grey.withOpacity(0.3),
              width: 1,
            ),
          ),
          focusedBorder: OutlineInputBorder(
            borderRadius: BorderRadius.circular(16),
            borderSide: const BorderSide(
              color: Color(0xFF8CCAA7),
              width: 2,
            ),
          ),
          prefixIcon: Icon(
            Icons.family_restroom,
            color: isCodeEntered 
                ? const Color(0xFF8CCAA7)
                : Colors.grey[400],
            size: 24,
          ),
        ),
      ),
    );
  }

  Widget _buildSubmitButton() {
    return Container(
      width: double.infinity,
      height: 56,
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(16),
        boxShadow: isCodeEntered ? [
          BoxShadow(
            color: const Color(0xFF8CCAA7).withOpacity(0.4),
            blurRadius: 12,
            offset: const Offset(0, 6),
          ),
        ] : [],
      ),
      child: ElevatedButton(
        onPressed: isCodeEntered ? _submitFamilyCode : null,
        style: ElevatedButton.styleFrom(
          backgroundColor: isCodeEntered
              ? const Color(0xFF8CCAA7)
              : Colors.grey[300],
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(16),
          ),
          elevation: 0,
        ),
        child: Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              Icons.login,
              color: isCodeEntered ? Colors.white : Colors.grey[500],
              size: 20,
            ),
            const SizedBox(width: 8),
            Text(
              '가족과 함께하기',
              style: TextStyle(
                color: isCodeEntered ? Colors.white : Colors.grey[500],
                fontSize: 18,
                fontWeight: FontWeight.w600,
                fontFamily: 'Pretendard',
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildHomeIndicator() {
    return Center(
      child: Container(
        width: 134,
        height: 4,
        decoration: BoxDecoration(
          color: Colors.grey[400],
          borderRadius: BorderRadius.circular(2),
        ),
      ),
    );
  }
}
