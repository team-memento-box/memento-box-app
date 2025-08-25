// 작성자: gwona
// 작성일: 2025.06.05
// 목적: 보호자 가족코드/그룹명/관계 등록 화면 리팩토링

import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../user_provider.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';
import 'package:flutter_dotenv/flutter_dotenv.dart';
import '../widgets/family_dropdown.dart';
import '../utils/routes.dart'; 

class GroupSelectScreen extends StatelessWidget {
  const GroupSelectScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.white,
      body: SafeArea(
        child: Column(
          children: [
            // 상단 시계/상태바 영역 (간단히 텍스트로 대체)
            
            const SizedBox(height: 200),
            // 안내 문구
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 30.0),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.center, // 가운데 정렬
                children: [
                  // 1. 이미지 추가
                  Image.asset(
                    'assets/images/temp_logo.png',
                    width: 200, // 원하는 크기로 조절
                    height: 200,
                    fit: BoxFit.contain,
                  ),
                  const SizedBox(height: 16), // 이미지와 텍스트 사이 간격
                  // 2. 안내 문구
                  Consumer<UserProvider>(
                    builder: (context, userProvider, child) => Text(
                      '안녕하세요 ${userProvider.name}님,',
                      textAlign: TextAlign.center,
                      style: const TextStyle(
                        color: Colors.black,
                        fontSize: 21,
                        fontFamily: 'Pretendard',
                        fontWeight: FontWeight.w500,
                        height: 1.19,
                      ),
                    ),
                  ),
                  const SizedBox(height: 8),
                  Text(
                    '저와 함께 기억여행을 시작해볼까요?',
                    textAlign: TextAlign.center,
                    style: const TextStyle(
                      color: Colors.black,
                      fontSize: 19,
                      fontFamily: 'Pretendard',
                      fontWeight: FontWeight.w500,
                      height: 1.42,
                      letterSpacing: -1,
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 32),
            // 가족 그룹 생성하기 버튼
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 30.0),
              child: SizedBox(
                width: double.infinity,
                height: 60,
                child: ElevatedButton(
                  style: ElevatedButton.styleFrom(
                    backgroundColor: const Color(0xFFDFF3F2),
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(20),
                    ),
                    elevation: 0,
                  ),
                  onPressed: () {
                    Navigator.pushNamed(context, '/0-3-1-1');
                  },
                  child: const Text(
                    '기억여행 시작하기',
                    style: TextStyle(
                      color: Color(0xFF8CCAA7),
                      fontSize: 20,
                      fontFamily: 'Pretendard',
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ),
              ),
            ),
            
            // 하단 홈 인디케이터
            
          ],
        ),
      ),
    );
  }
}