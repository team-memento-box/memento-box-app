// 작성자: gwona
// 작성일: 2025.06.05
// 목적: 피보호자 가족 코드 입력 화면 리팩토링

import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../user_provider.dart';
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
        Navigator.pushNamed(context, '/intro');
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
        child: Stack(
          children: [
            _buildLogo(),
            _buildTextSection(),
            _buildInputField(),
            _buildSubmitButton(),
            _buildHomeIndicator(),
          ],
        ),
      ),
    );
  }

  Widget _buildLogo() {
    return Positioned(
      top: 153,
      left: 30,
      child: SizedBox(
        width: 88,
        height: 88,
        child: Image.asset("assets/images/temp_logo.png", fit: BoxFit.cover),
      ),
    );
  }

  Widget _buildTextSection() {
    return const Positioned(
      top: 269,
      left: 30,
      right: 30,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            '안녕하세요 피보호자님,',
            textAlign: TextAlign.center,
            style: const TextStyle(
              color: Colors.black,
              fontSize: 21,
              fontFamily: 'Pretendard',
              fontWeight: FontWeight.w500,
              height: 1.19,
            ),
          ),
          const SizedBox(height: 8), // 16에서 8로 변경 (0-3-1.dart와 동일하게)
          Text(
            '보호자님께 전달 받은 가족 코드를 입력해주세요.',
            textAlign: TextAlign.center,
            style: const TextStyle(
              color: Colors.black,
              fontSize: 17,
              fontFamily: 'Pretendard',
              fontWeight: FontWeight.w500,
              height: 1.42,
              letterSpacing: -1,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildInputField() {
    return Positioned(
      top: 406,
      left: 30,
      right: 30,
      child: TextField(
        controller: codeController,
        textAlign: TextAlign.center,
        style: const TextStyle(
          fontSize: 20,
          fontWeight: FontWeight.w600,
          fontFamily: 'Pretendard',
        ),
        decoration: InputDecoration(
          hintText: '가족 코드를 입력해주세요',
          hintStyle: const TextStyle(
            fontSize: 18,
            color: Color(0xFF888888),
            fontFamily: 'Pretendard',
          ),
          contentPadding: const EdgeInsets.symmetric(
            horizontal: 16,
            vertical: 20,
          ),
          filled: true,
          fillColor: Color(0xFFF4F4F4),
          border: OutlineInputBorder(
            borderRadius: BorderRadius.circular(20),
            borderSide: const BorderSide(color: Color(0xFFAEAEAE)),
          ),
          enabledBorder: OutlineInputBorder(
            borderRadius: BorderRadius.circular(20),
            borderSide: const BorderSide(color: Color(0xFFAEAEAE)),
          ),
        ),
      ),
    );
  }

  Widget _buildSubmitButton() {
    return Positioned(
      top: 520,
      left: 50,
      right: 50,
      child: GestureDetector(
        onTap: isCodeEntered
            ? _submitFamilyCode
            : null,
        child: Container(
          height: 60,
          decoration: BoxDecoration(
            color: isCodeEntered
                ? const Color(0xFF00C8B8)
                : const Color(0xFFDFF3F2),
            borderRadius: BorderRadius.circular(20),
          ),
          alignment: Alignment.center,
          child: Text(
            '가족 코드 입력',
            style: TextStyle(
              color: Colors.white,
              fontSize: 20,
              fontWeight: FontWeight.w600,
              fontFamily: 'Pretendard',
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildHomeIndicator() {
    return const Positioned(
      bottom: 10,
      left: 0,
      right: 0,
      child: Center(
        child: SizedBox(
          width: 139,
          height: 5,
          child: DecoratedBox(
            decoration: BoxDecoration(
              color: Colors.black,
              borderRadius: BorderRadius.all(Radius.circular(100)),
            ),
          ),
        ),
      ),
    );
  }
}
