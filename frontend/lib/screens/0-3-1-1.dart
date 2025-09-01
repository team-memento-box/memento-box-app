import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';
import 'dart:convert' show utf8;
import 'dart:math';
import 'package:flutter_dotenv/flutter_dotenv.dart';
import '../providers/user_provider.dart';
import '../widgets/family_dropdown.dart';
import '../utils/routes.dart';
import '../core/supabase_service.dart';

class GroupCreateScreen extends StatefulWidget {
  const GroupCreateScreen({super.key});

  @override
  State<GroupCreateScreen> createState() => _GroupCreateScreenState();
}

class _GroupCreateScreenState extends State<GroupCreateScreen> {
  final TextEditingController codeInputController = TextEditingController();
  final TextEditingController familyNameController = TextEditingController();
  String? familyCode;
  String? familyId;
  String? familyName;
  String? error;
  bool showRelationDropdown = false;
  bool isCreating = true; // true: 생성 모드, false: 가입 모드

  /// 6자리 가족 코드 생성
  String _generateFamilyCode() {
    final random = Random();
    return List.generate(6, (index) => random.nextInt(10)).join();
  }



  Future<void> _generateCode() async {
    if (isCreating && familyNameController.text.trim().isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('가족 그룹명을 입력해주세요')),
      );
      return;
    }

    try {
      final currentUser = SupabaseService.client.auth.currentUser;
      if (currentUser == null) {
        throw Exception('로그인이 필요합니다');
      }

      // 1. 가족 코드 생성 (중복 확인 포함)
      String generatedCode;
      bool isUnique = false;
      int attempts = 0;
      
      do {
        generatedCode = _generateFamilyCode();
        final existing = await SupabaseService.client
            .from('families')
            .select('id')
            .eq('family_code', generatedCode)
            .maybeSingle();
        
        isUnique = existing == null;
        attempts++;
        
        if (attempts > 10) {
          throw Exception('가족 코드 생성에 실패했습니다. 다시 시도해주세요.');
        }
      } while (!isUnique);

      // 2. Supabase에 가족 생성
      final familyData = await SupabaseService.client
          .from('families')
          .insert({
            'family_code': generatedCode,
            'family_name': familyNameController.text.trim(),
            'created_by': currentUser.id,
          })
          .select()
          .single();

      // 3. 현재 사용자를 가족 멤버로 추가
      await SupabaseService.client
          .from('family_members')
          .insert({
            'user_id': currentUser.id,
            'family_id': familyData['id'],
            'family_role': '보호자',
          });

      // 4. 사용자 테이블에 현재 가족 ID 업데이트
      await SupabaseService.client
          .from('users')
          .update({'current_family_id': familyData['id']})
          .eq('id', currentUser.id);

      setState(() {
        familyCode = familyData['family_code'];
        familyId = familyData['id'];
        familyName = familyData['family_name'];
        showRelationDropdown = true;
      });

      Provider.of<UserProvider>(context, listen: false).setFamilyCreate(
        familyId: familyData['id'],
        familyCode: familyData['family_code'],
        familyName: familyData['family_name'],
      );

      print('✅ 가족 생성 성공: ${familyData['family_code']}');
      
    } catch (e) {
      print('❌ 가족 생성 오류: $e');
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('가족 코드 발급 실패: $e')),
      );
    }
  }

  Future<void> _joinFamily() async {
    final code = codeInputController.text.trim();
    
    try {
      final currentUser = SupabaseService.client.auth.currentUser;
      if (currentUser == null) {
        throw Exception('로그인이 필요합니다');
      }

      print('🔍 Looking for family code: $code');
      print('🔍 Current user ID: ${currentUser.id}');

      // 1. 가족 코드로 가족 찾기
      final familyData = await SupabaseService.client
          .from('families')
          .select('*')
          .eq('family_code', code)
          .maybeSingle();

      print('🔍 Family search result: $familyData');

      if (familyData == null) {
        print('❌ No family found with code: $code');
        setState(() {
          error = '가족 코드가 올바르지 않습니다.';
          showRelationDropdown = false;
        });
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
        setState(() {
          error = '이미 해당 가족의 멤버입니다.';
          showRelationDropdown = false;
        });
        return;
      }

      setState(() {
        familyId = familyData['id'];
        familyCode = familyData['family_code'];
        familyName = familyData['family_name'];
        showRelationDropdown = true;
        error = null;
      });

      Provider.of<UserProvider>(context, listen: false).setFamilyJoin(
        familyId: familyData['id'],
        familyCode: familyData['family_code'],
        familyName: familyData['family_name'],
      );

      print('✅ 가족 찾기 성공: ${familyData['family_name']}');
      
    } catch (e) {
      print('❌ 가족 가입 오류: $e');
      setState(() {
        error = '네트워크 오류: $e';
        showRelationDropdown = false;
      });
    }
  }

  Future<void> _onRelationSelected(String? value) async {
    if (value != null && value.isNotEmpty) {
      final userProvider = Provider.of<UserProvider>(context, listen: false);
      userProvider.setFamilyInfo(familyRole: value);

      try {
        final currentUser = SupabaseService.client.auth.currentUser;
        if (currentUser == null) {
          throw Exception('로그인이 필요합니다');
        }

        if (familyId == null) {
          throw Exception('가족 ID가 없습니다');
        }

        // 1. 가족 멤버로 추가 (생성 모드가 아닌 경우에만)
        if (!isCreating) {
          await SupabaseService.client
              .from('family_members')
              .insert({
                'user_id': currentUser.id,
                'family_id': familyId!,
                'family_role': value,
              });

          // 2. 사용자 테이블에 현재 가족 ID 업데이트
          await SupabaseService.client
              .from('users')
              .update({'current_family_id': familyId!})
              .eq('id', currentUser.id);
        } else {
          // 생성 모드에서는 이미 멤버가 추가되어 있으므로 역할만 업데이트
          await SupabaseService.client
              .from('family_members')
              .update({'family_role': value})
              .eq('user_id', currentUser.id)
              .eq('family_id', familyId!);
        }

        // 3. 온보딩 완료 처리
        await SupabaseService.client
            .from('users')
            .update({'onboarding_completed': true})
            .eq('id', currentUser.id);

        print('✅ 가족 멤버 추가/업데이트 완료');
        print('✅ 온보딩 완료 처리됨');
        
        if (mounted) {
          Navigator.pushNamed(context, '/home');
        }
        
      } catch (e) {
        print('❌ 가족 관계 설정 오류: $e');
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('가족 관계 설정 실패: $e')),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF8F9FA),
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        elevation: 0,
        leading: IconButton(
          icon: const Icon(Icons.arrow_back, color: Color(0xFF333333)),
          onPressed: () => Navigator.pop(context),
        ),
        title: const Text(
          '가족 설정',
          style: TextStyle(
            fontSize: 20,
            fontWeight: FontWeight.w700,
            fontFamily: 'Pretendard',
            color: Color(0xFF333333),
          ),
        ),
        centerTitle: true,
      ),
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(24.0),
          child: Column(
            children: [
              _buildHeader(),
              const SizedBox(height: 32),
              _buildModeSelector(),
              const SizedBox(height: 32),
              _buildMainCard(),
              if (showRelationDropdown) ...[
                const SizedBox(height: 24),
                _buildRelationCard(),
              ],
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildHeader() {
    return Column(
      children: [
        Container(
          width: 80,
          height: 80,
          decoration: BoxDecoration(
            color: const Color(0xFF8CCAA7).withOpacity(0.1),
            borderRadius: BorderRadius.circular(20),
          ),
          child: Icon(
            isCreating ? Icons.group_add : Icons.group,
            size: 40,
            color: const Color(0xFF8CCAA7),
          ),
        ),
        const SizedBox(height: 20),
        Text(
          isCreating ? '가족 그룹 생성하기' : '가족 그룹 가입하기',
          style: const TextStyle(
            fontSize: 24,
            fontWeight: FontWeight.w700,
            fontFamily: 'Pretendard',
            color: Color(0xFF333333),
          ),
        ),
        const SizedBox(height: 8),
        Text(
          isCreating 
            ? '새로운 가족 그룹을 만들고\n가족들을 초대해보세요'
            : '가족 코드를 입력하여\n기존 가족 그룹에 참여하세요',
          textAlign: TextAlign.center,
          style: TextStyle(
            fontSize: 16,
            color: Colors.grey[600],
            fontFamily: 'Pretendard',
            height: 1.4,
          ),
        ),
      ],
    );
  }

  Widget _buildModeSelector() {
    return Container(
      padding: const EdgeInsets.all(4),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(16),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.05),
            blurRadius: 10,
            offset: const Offset(0, 2),
          ),
        ],
      ),
      child: Row(
        children: [
          Expanded(child: _buildModeButton('생성하기', isCreating)),
          Expanded(child: _buildModeButton('가입하기', !isCreating)),
        ],
      ),
    );
  }

  Widget _buildMainCard() {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(24),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(20),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.05),
            blurRadius: 15,
            offset: const Offset(0, 5),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          if (isCreating) ...[
            if (familyCode == null) ...[
              _buildCreateContent(),
            ] else ...[
              _buildCodeDisplay(),
            ],
          ] else ...[
            _buildJoinContent(),
          ],
        ],
      ),
    );
  }

  Widget _buildCreateContent() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Icon(
              Icons.family_restroom,
              color: const Color(0xFF8CCAA7),
              size: 24,
            ),
            const SizedBox(width: 8),
            const Text(
              '가족 그룹명 설정',
              style: TextStyle(
                fontSize: 18,
                fontWeight: FontWeight.w600,
                fontFamily: 'Pretendard',
                color: Color(0xFF333333),
              ),
            ),
          ],
        ),
        const SizedBox(height: 16),
        Container(
          decoration: BoxDecoration(
            color: const Color(0xFFF8F9FA),
            borderRadius: BorderRadius.circular(12),
            border: Border.all(
              color: Colors.grey.withOpacity(0.2),
            ),
          ),
          child: TextField(
            controller: familyNameController,
            decoration: const InputDecoration(
              hintText: '우리 가족',
              hintStyle: TextStyle(
                color: Color(0xFF999999),
                fontFamily: 'Pretendard',
              ),
              border: InputBorder.none,
              contentPadding: EdgeInsets.all(16),
              prefixIcon: Icon(
                Icons.edit,
                color: Color(0xFF8CCAA7),
              ),
            ),
            textInputAction: TextInputAction.done,
            style: const TextStyle(
              fontFamily: 'Pretendard',
              fontSize: 16,
              fontWeight: FontWeight.w500,
            ),
          ),
        ),
        const SizedBox(height: 24),
        SizedBox(
          width: double.infinity,
          height: 52,
          child: ElevatedButton(
            onPressed: _generateCode,
            style: ElevatedButton.styleFrom(
              backgroundColor: const Color(0xFF8CCAA7),
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(12),
              ),
              elevation: 0,
            ),
            child: const Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Icon(Icons.qr_code, color: Colors.white, size: 20),
                SizedBox(width: 8),
                Text(
                  '가족 코드 발급받기',
                  style: TextStyle(
                    fontSize: 16,
                    fontWeight: FontWeight.w600,
                    color: Colors.white,
                    fontFamily: 'Pretendard',
                  ),
                ),
              ],
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildJoinContent() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Icon(
              Icons.input,
              color: const Color(0xFF8CCAA7),
              size: 24,
            ),
            const SizedBox(width: 8),
            const Text(
              '가족 코드 입력',
              style: TextStyle(
                fontSize: 18,
                fontWeight: FontWeight.w600,
                fontFamily: 'Pretendard',
                color: Color(0xFF333333),
              ),
            ),
          ],
        ),
        const SizedBox(height: 16),
        Container(
          decoration: BoxDecoration(
            color: const Color(0xFFF8F9FA),
            borderRadius: BorderRadius.circular(12),
            border: Border.all(
              color: error != null 
                  ? Colors.red.withOpacity(0.5)
                  : Colors.grey.withOpacity(0.2),
            ),
          ),
          child: TextField(
            controller: codeInputController,
            textAlign: TextAlign.center,
            decoration: InputDecoration(
              hintText: '6자리 코드 입력',
              hintStyle: const TextStyle(
                color: Color(0xFF999999),
                fontFamily: 'Pretendard',
              ),
              border: InputBorder.none,
              contentPadding: const EdgeInsets.all(16),
              prefixIcon: const Icon(
                Icons.numbers,
                color: Color(0xFF8CCAA7),
              ),
              errorText: error,
              errorStyle: const TextStyle(
                fontFamily: 'Pretendard',
                fontSize: 12,
              ),
            ),
            keyboardType: TextInputType.text,
            style: const TextStyle(
              fontFamily: 'Pretendard',
              fontSize: 18,
              fontWeight: FontWeight.w600,
              letterSpacing: 2,
            ),
          ),
        ),
        const SizedBox(height: 24),
        SizedBox(
          width: double.infinity,
          height: 52,
          child: ElevatedButton(
            onPressed: _joinFamily,
            style: ElevatedButton.styleFrom(
              backgroundColor: const Color(0xFF8CCAA7),
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(12),
              ),
              elevation: 0,
            ),
            child: const Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Icon(Icons.search, color: Colors.white, size: 20),
                SizedBox(width: 8),
                Text(
                  '가족 찾기',
                  style: TextStyle(
                    fontSize: 16,
                    fontWeight: FontWeight.w600,
                    color: Colors.white,
                    fontFamily: 'Pretendard',
                  ),
                ),
              ],
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildRelationCard() {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(24),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(20),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.05),
            blurRadius: 15,
            offset: const Offset(0, 5),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(
                Icons.people,
                color: const Color(0xFF8CCAA7),
                size: 24,
              ),
              const SizedBox(width: 8),
              const Text(
                '가족 관계 선택',
                style: TextStyle(
                  fontSize: 18,
                  fontWeight: FontWeight.w600,
                  fontFamily: 'Pretendard',
                  color: Color(0xFF333333),
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Text(
            '가족 구성원들과의 관계를 선택해주세요',
            style: TextStyle(
              fontSize: 14,
              color: Colors.grey[600],
              fontFamily: 'Pretendard',
            ),
          ),
          const SizedBox(height: 16),
          FamilyRelationDropdown(
            onChanged: _onRelationSelected,
          ),
        ],
      ),
    );
  }

  Widget _buildModeButton(String text, bool isSelected) {
    return GestureDetector(
      onTap: () {
        setState(() {
          isCreating = text == '생성하기';
          familyCode = null;
          familyId = null;
          showRelationDropdown = false;
          error = null;
          codeInputController.clear();
        });
      },
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
        decoration: BoxDecoration(
          color: isSelected ? const Color(0xFF8CCAA7) : Colors.transparent,
          borderRadius: BorderRadius.circular(12),
        ),
        child: Center(
          child: Text(
            text,
            style: TextStyle(
              color: isSelected ? Colors.white : const Color(0xFF666666),
              fontSize: 15,
              fontWeight: FontWeight.w600,
              fontFamily: 'Pretendard',
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildCodeDisplay() {
    return Column(
      children: [
        // 성공 아이콘
        Container(
          width: 60,
          height: 60,
          decoration: BoxDecoration(
            color: const Color(0xFF8CCAA7).withOpacity(0.1),
            borderRadius: BorderRadius.circular(30),
          ),
          child: const Icon(
            Icons.check_circle,
            size: 30,
            color: Color(0xFF8CCAA7),
          ),
        ),
        const SizedBox(height: 20),
        
        const Text(
          '가족 코드가 생성되었어요! 🎉',
          style: TextStyle(
            fontSize: 18,
            fontWeight: FontWeight.w700,
            fontFamily: 'Pretendard',
            color: Color(0xFF333333),
          ),
        ),
        const SizedBox(height: 24),
        
        // 코드 표시 카드
        Container(
          width: double.infinity,
          padding: const EdgeInsets.all(20),
          decoration: BoxDecoration(
            color: const Color(0xFF8CCAA7).withOpacity(0.1),
            borderRadius: BorderRadius.circular(16),
            border: Border.all(
              color: const Color(0xFF8CCAA7).withOpacity(0.3),
              width: 1,
            ),
          ),
          child: Column(
            children: [
              const Text(
                '가족 코드',
                style: TextStyle(
                  fontSize: 14,
                  color: Color(0xFF8CCAA7),
                  fontWeight: FontWeight.w600,
                  fontFamily: 'Pretendard',
                ),
              ),
              const SizedBox(height: 8),
              Text(
                familyCode ?? '',
                style: const TextStyle(
                  fontSize: 32,
                  fontWeight: FontWeight.w800,
                  fontFamily: 'Pretendard',
                  letterSpacing: 4,
                  color: Color(0xFF333333),
                ),
              ),
              const SizedBox(height: 12),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                decoration: BoxDecoration(
                  color: Colors.white,
                  borderRadius: BorderRadius.circular(20),
                ),
                child: Text(
                  familyName ?? '',
                  style: const TextStyle(
                    fontSize: 14,
                    fontWeight: FontWeight.w600,
                    fontFamily: 'Pretendard',
                    color: Color(0xFF8CCAA7),
                  ),
                ),
              ),
            ],
          ),
        ),
        const SizedBox(height: 20),
        
        Container(
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            color: const Color(0xFFF8F9FA),
            borderRadius: BorderRadius.circular(12),
          ),
          child: Row(
            children: [
              Icon(
                Icons.info_outline,
                size: 20,
                color: Colors.grey[600],
              ),
              const SizedBox(width: 8),
              Expanded(
                child: Text(
                  '이 코드를 가족 구성원들과 공유해서\n함께 추억을 기록해보세요',
                  style: TextStyle(
                    fontSize: 13,
                    color: Colors.grey[600],
                    fontFamily: 'Pretendard',
                    height: 1.4,
                  ),
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }
}