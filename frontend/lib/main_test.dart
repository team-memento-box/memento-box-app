import 'package:flutter/material.dart';
import 'screens/report_detail_speech.dart';

void main() {
  runApp(const TestApp());
}

class TestApp extends StatelessWidget {
  const TestApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Test Report Detail Speech',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        primarySwatch: Colors.teal, 
        fontFamily: 'Pretendard'
      ),
      home: const ConversationHealthAnalysisScreen(),
    );
  }
}