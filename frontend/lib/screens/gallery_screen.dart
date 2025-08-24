// 작성자: OH
// 작성일: 2025.05
// 수정일: 2025.06.03

import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';
import 'package:flutter_dotenv/flutter_dotenv.dart';
import '../widgets/group_bar_widget.dart';
import '../widgets/tap_widget.dart';
import '../utils/styles.dart';
import '../user_provider.dart';
import '../utils/routes.dart';
import '../models/photo.dart';
import 'intro_screen.dart';

class PhotoWithConv {
  final Photo photo;
  final bool hasConversation;
  PhotoWithConv({required this.photo, required this.hasConversation});
}

Future<List<PhotoWithConv>> fetchPhotosWithConv(BuildContext context) async {
  final userProvider = Provider.of<UserProvider>(context, listen: false);
  final accessToken = userProvider.accessToken;
  final baseUrl = dotenv.env['BASE_URL']!;
  final url = Uri.parse('$baseUrl/api/photos/');
  final response = await http.get(
    url,
    headers: {
      'Authorization': 'Bearer $accessToken',
      'Accept': 'application/json',
    },
  );
  if (response.statusCode == 200) {
    final List<dynamic> data = jsonDecode(utf8.decode(response.bodyBytes));
    List<PhotoWithConv> result = [];
    for (var json in data) {
      final photo = Photo.fromSupabase(json);
      // conversation 존재 여부 확인
      final convRes = await http.get(
        Uri.parse('$baseUrl/api/photos/${photo.id}/latest_conversation'),
        headers: {'Authorization': 'Bearer $accessToken'},
      );
      final hasConv = convRes.statusCode == 200;
      result.add(PhotoWithConv(photo: photo, hasConversation: hasConv));
    }
    return result;
  } else {
    throw Exception('사진 목록 불러오기 실패: \\${response.statusCode}');
  }
}

// ... (생략: import 및 fetchPhotosWithConv 등 기존 코드 동일)

class GalleryScreen extends StatefulWidget {
  const GalleryScreen({super.key});

  @override
  State<GalleryScreen> createState() => _GalleryScreenState();
}

class _GalleryScreenState extends State<GalleryScreen> {
  late Future<List<PhotoWithConv>> _photosFuture;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => _loadPhotos());
  }

  void _loadPhotos() {
    setState(() {
      _photosFuture = fetchPhotosWithConv(context);
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF7F7F7),
      appBar: GroupBar(
        title: Provider.of<UserProvider>(context, listen: false).familyName ?? '우리 가족',
      ),
      body: FutureBuilder<List<PhotoWithConv>>(
        future: _photosFuture,
        builder: (context, snapshot) {
          if (snapshot.connectionState == ConnectionState.waiting) {
            return const Center(child: CircularProgressIndicator());
          }
          if (snapshot.hasError) {
            return const IntroScreen();
          }
          final photoWithConvs = snapshot.data ?? [];
          if (photoWithConvs.isEmpty) {
            return const IntroScreen();
          }
          // 연도, 계절별로 그룹화
          final grouped = <String, List<PhotoWithConv>>{};
          for (var pwc in photoWithConvs) {
            final key = '${pwc.photo.year}년 ${_seasonKor(pwc.photo.season)}';
            grouped.putIfAbsent(key, () => []).add(pwc);
          }
          return ListView(
            padding: const EdgeInsets.symmetric(horizontal: 16),
            children: grouped.entries.map((entry) {
              return Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const SizedBox(height: 16),
                  Text(entry.key, style: maxContentStyle),
                  const SizedBox(height: 12),
                  GridView.builder(
                    shrinkWrap: true,
                    physics: const NeverScrollableScrollPhysics(),
                    itemCount: entry.value.length,
                    gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
                      crossAxisCount: 2,
                      crossAxisSpacing: 8,
                      mainAxisSpacing: 16,
                      childAspectRatio: 1.49,
                    ),
                    itemBuilder: (context, index) {
                      final pwc = entry.value[index];
                      return GestureDetector(
                        onTap: () {
                          Navigator.pushNamed(
                            context,
                            Routes.photoDetail,
                            arguments: pwc.photo,
                          );
                        },
                        child: AspectRatio(
                          aspectRatio: 1.49, // childAspectRatio와 맞춤
                          child: Stack(
                            fit: StackFit.expand,
                            children: [
                              ClipRRect(
                                borderRadius: BorderRadius.circular(10),
                                child: Image.network(
                                  pwc.photo.url,
                                  fit: BoxFit.cover,
                                  errorBuilder: (c, e, s) => const Icon(Icons.broken_image),
                                ),
                              ),
                              if (pwc.hasConversation)
                                Positioned(
                                  bottom: 8,
                                  right: 2,
                                  child: Image.asset(
                                    'assets/images/finger.png',
                                    width: 50,
                                    height: 50,
                                  ),
                                ),
                            ],
                          ),
                        ),
                      );
                    },
                  ),
                ],
              );
            }).toList(),
          );
        },
      ),
      bottomNavigationBar: const CustomBottomNavBar(currentIndex: 1),
    );
  }

  String _seasonKor(String eng) {
    switch (eng) {
      case 'spring':
        return '봄';
      case 'summer':
        return '여름';
      case 'autumn':
        return '가을';
      case 'winter':
        return '겨울';
      default:
        return eng;
    }
  }
}