import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';
import 'dart:convert' show utf8;
import 'dart:math';
import 'package:flutter_dotenv/flutter_dotenv.dart';
import '../user_provider.dart';
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
      backgroundColor: Colors.white,
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 24.0),
          child: SingleChildScrollView(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const SizedBox(height: 24),
                // 상단 타이틀
                Text(
                  isCreating ? '가족 그룹 생성하기' : '가족 그룹 가입하기',
                  style: const TextStyle(
                    fontSize: 24,
                    fontWeight: FontWeight.bold,
                    fontFamily: 'Pretendard',
                  ),
                ),
                const SizedBox(height: 8),
                Text(
                  isCreating 
                    ? '가족 그룹을 생성하고 코드를 발급받으세요.'
                    : '가족 그룹 코드를 입력하여 가입하세요.',
                  style: const TextStyle(
                    fontSize: 16,
                    color: Colors.grey,
                    fontFamily: 'Pretendard',
                  ),
                ),
                const SizedBox(height: 32),
                
                // 모드 전환 버튼
                Center(
                  child: Container(
                    decoration: BoxDecoration(
                      color: const Color(0xFFF5F5F5),
                      borderRadius: BorderRadius.circular(12),
                    ),
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        _buildModeButton('생성하기', isCreating),
                        _buildModeButton('가입하기', !isCreating),
                      ],
                    ),
                  ),
                ),
                const SizedBox(height: 32),

                // 생성/가입 컨텐츠
                if (isCreating) ...[
                  if (familyCode == null) ...[
                    TextField(
                      controller: familyNameController,
                      decoration: InputDecoration(
                        hintText: '가족 그룹명을 입력하세요',
                        border: OutlineInputBorder(
                          borderRadius: BorderRadius.circular(12),
                        ),
                        contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 16),
                      ),
                      textInputAction: TextInputAction.done,
                      keyboardType: TextInputType.text,
                      style: const TextStyle(
                        fontFamily: 'Pretendard',
                        fontSize: 16,
                      ),
                    ),
                    const SizedBox(height: 16),
                    Center(
                      child: ElevatedButton(
                        onPressed: _generateCode,
                        style: ElevatedButton.styleFrom(
                          backgroundColor: const Color(0xFF8CCAA7),
                          padding: const EdgeInsets.symmetric(horizontal: 32, vertical: 16),
                          shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(12),
                          ),
                        ),
                        child: const Text(
                          '가족 코드 발급받기',
                          style: TextStyle(
                            fontSize: 18,
                            color: Colors.white,
                            fontFamily: 'Pretendard',
                          ),
                        ),
                      ),
                    ),
                  ] else ...[
                    _buildCodeDisplay(),
                  ],
                ] else ...[
                  TextField(
                    controller: codeInputController,
                    decoration: InputDecoration(
                      hintText: '가족 코드를 입력하세요',
                      errorText: error,
                      border: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(12),
                      ),
                      contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 16),
                    ),
                  ),
                  const SizedBox(height: 16),
                  SizedBox(
                    width: double.infinity,
                    child: ElevatedButton(
                      onPressed: _joinFamily,
                      style: ElevatedButton.styleFrom(
                        backgroundColor: const Color(0xFF8CCAA7),
                        padding: const EdgeInsets.symmetric(vertical: 16),
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(12),
                        ),
                      ),
                      child: const Text(
                        '가족 코드 확인',
                        style: TextStyle(
                          fontSize: 18,
                          color: Colors.white,
                          fontFamily: 'Pretendard',
                        ),
                      ),
                    ),
                  ),
                ],

                if (showRelationDropdown) ...[
                  const SizedBox(height: 32),
                  const Text(
                    '가족 관계를 선택해주세요',
                    style: TextStyle(
                      fontSize: 18,
                      fontWeight: FontWeight.bold,
                      fontFamily: 'Pretendard',
                    ),
                  ),
                  const SizedBox(height: 16),
                  FamilyRelationDropdown(
                    onChanged: _onRelationSelected,
                  ),
                ],
              ],
            ),
          ),
        ),
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
        padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 12),
        decoration: BoxDecoration(
          color: isSelected ? const Color(0xFF8CCAA7) : Colors.transparent,
          borderRadius: BorderRadius.circular(12),
        ),
        child: Text(
          text,
          style: TextStyle(
            color: isSelected ? Colors.white : Colors.black,
            fontSize: 16,
            fontWeight: FontWeight.w600,
            fontFamily: 'Pretendard',
          ),
        ),
      ),
    );
  }

  Widget _buildCodeDisplay() {
    return Container(
      padding: const EdgeInsets.all(24),
      decoration: BoxDecoration(
        color: const Color(0xFFF5F5F5),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.center, // ← 이 줄 추가/수정!
        children: [
          const Text(
            '발급된 가족 코드',
            style: TextStyle(
              fontSize: 16,
              color: Colors.grey,
              fontFamily: 'Pretendard',
            ),
          ),
          const SizedBox(height: 8),
          Text(
            familyCode ?? '',
            style: const TextStyle(
              fontSize: 32,
              fontWeight: FontWeight.bold,
              fontFamily: 'Pretendard',
              letterSpacing: 2,
            ),
          ),
          const SizedBox(height: 16),
          Text(
            '가족 그룹명: ${familyName ?? ''}',
            style: const TextStyle(
              fontSize: 16,
              fontFamily: 'Pretendard',
            ),
          ),
          const SizedBox(height: 16),
          const Text(
            '이 코드를 가족 구성원들과 공유해주세요.',
            style: TextStyle(
              fontSize: 14,
              color: Colors.grey,
              fontFamily: 'Pretendard',
            ),
          ),
        ],
      ),
    );
  }
}