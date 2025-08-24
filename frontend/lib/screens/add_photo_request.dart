import 'package:flutter/material.dart';
import '../widgets/tap_widget.dart';
import '../widgets/group_bar_widget.dart';
import 'package:provider/provider.dart';
import '../user_provider.dart';

class AddPhotoRequestScreen extends StatelessWidget {
  const AddPhotoRequestScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final familyName = Provider.of<UserProvider>(context).familyName ?? '우리 가족';
    return Scaffold(
      backgroundColor: const Color(0xFFF7F7F7),
      appBar: GroupBar(title: familyName),
      body: Column(
        children: [
          const SizedBox(height: 20),
          Expanded(
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 20),
              child: _buildMainBox(),
            ),
          ),
        ],
      ),
      bottomNavigationBar: const CustomBottomNavBar(
        currentIndex: 1,
      ),
    );
  }

  Widget _buildMainBox() {
    return Container(
      width: double.infinity,
      margin: const EdgeInsets.only(bottom: 20),
      padding: const EdgeInsets.symmetric(vertical: 60),
      decoration: BoxDecoration(
        color: const Color(0x1900C8B8),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: const Color(0xFF00C8B8), width: 3),
      ),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          const Icon(Icons.heart_broken, color: Color(0xFF00C8B8), size: 48),
          const SizedBox(height: 40),
          const Text(
            '아직 생성된\n보관함이 없어요.\n\n보호자에게 보관함 만들기를\n요청해주세요.',
            textAlign: TextAlign.center,
            style: TextStyle(
              color: Color(0xFF00C8B8),
              fontSize: 20,
              fontWeight: FontWeight.w700,
              fontFamily: 'Pretendard',
              height: 1.4,
            ),
          ),
          const SizedBox(height: 60),
          SizedBox(
            width: 120,
            height: 120,
            child: Image.asset("assets/images/heart.png"),
          ),
        ],
      ),
    );
  }
}
