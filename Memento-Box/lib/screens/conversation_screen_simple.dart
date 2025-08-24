import 'package:flutter/material.dart';

class PhotoConversationScreen extends StatefulWidget {
  final String photoId;
  final String photoUrl;

  const PhotoConversationScreen({
    Key? key,
    required this.photoId,
    required this.photoUrl,
  }) : super(key: key);

  @override
  State<PhotoConversationScreen> createState() => _PhotoConversationScreenState();
}

class _PhotoConversationScreenState extends State<PhotoConversationScreen> {
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('사진 대화'),
        backgroundColor: Colors.blue,
      ),
      body: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Text(
              '사진 대화 화면',
              style: TextStyle(fontSize: 24),
            ),
            const SizedBox(height: 20),
            Text('Photo ID: ${widget.photoId}'),
            Text('Photo URL: ${widget.photoUrl}'),
            const SizedBox(height: 20),
            const Text(
              '음성인식 기능은 개발 중입니다.',
              style: TextStyle(fontSize: 16, color: Colors.grey),
            ),
          ],
        ),
      ),
    );
  }
}