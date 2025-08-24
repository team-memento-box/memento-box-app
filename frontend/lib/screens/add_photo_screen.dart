import 'package:flutter_dotenv/flutter_dotenv.dart';
import 'package:flutter/cupertino.dart';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../widgets/tap_widget.dart';
import '../user_provider.dart';
import 'package:image_picker/image_picker.dart';
import 'dart:io';
import '../widgets/group_bar_widget.dart';
import '../utils/styles.dart';
import 'package:path/path.dart' as path;
import '../core/supabase_service.dart';
import 'package:supabase_flutter/supabase_flutter.dart';
import 'dart:typed_data';

class AddPhotoScreen extends StatefulWidget {
  const AddPhotoScreen({super.key});

  @override
  State<AddPhotoScreen> createState() => _AddPhotoScreenState();
}

class _AddPhotoScreenState extends State<AddPhotoScreen> {
  final List<String> years = ['2023', '2024', '2025', '2026', '2027'];
  final List<String> seasons = ['봄', '여름', '가을', '겨울'];

  int selectedYearIndex = 2;
  int selectedSeasonIndex = 1;

  File? _selectedImage;
  final TextEditingController _descController = TextEditingController();

  bool get isAllFilled {
    return _selectedImage != null && _descController.text.trim().isNotEmpty;
  }

  String getSeasonEng(String korean) {
    switch (korean) {
      case '봄':
        return 'spring';
      case '여름':
        return 'summer';
      case '가을':
        return 'autumn';
      case '겨울':
        return 'winter';
      default:
        return '';
    }
  }

  void _showYearSeasonPicker() {
    showModalBottomSheet(
      context: context,
      backgroundColor:const Color.fromARGB(230, 255, 255, 255),
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(25)),
      ),
      builder: (BuildContext context) {
        return Padding(
          padding: const EdgeInsets.symmetric(horizontal: 30, vertical: 10),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Container(
                width: 60,
                height: 5,
                margin: const EdgeInsets.only(bottom: 16),
                decoration: BoxDecoration(
                  color: Colors.grey[400],
                  borderRadius: BorderRadius.circular(10),
                ),
              ),
              const SizedBox(height: 8),
              Row(
                children: [
                  Text(
                    '연도 계절 선택',
                    style: maxContentStyle.copyWith(fontSize: 22),
                    textAlign: TextAlign.center,
                  ),
                ],
              ),
              SizedBox(
                height: 240,
                child: Row(
                  children: [
                    Expanded(
                      child: CupertinoPicker(
                        scrollController: FixedExtentScrollController(
                          initialItem: selectedYearIndex,
                        ),
                        itemExtent: 40,
                        onSelectedItemChanged: (index) {
                          setState(() {
                            selectedYearIndex = index;
                          });
                        },
                        children: years
                            .map((y) => Center(
                                  child: Text(
                                    y,
                                    style: const TextStyle(
                                      fontSize: 20,
                                      fontWeight: FontWeight.bold,
                                    ),
                                  ),
                                ))
                            .toList(),
                      ),
                    ),
                    Expanded(
                      child: CupertinoPicker(
                        scrollController: FixedExtentScrollController(
                          initialItem: selectedSeasonIndex,
                        ),
                        itemExtent: 40,
                        onSelectedItemChanged: (index) {
                          setState(() {
                            selectedSeasonIndex = index;
                          });
                        },
                        children: seasons
                            .map((s) => Center(
                                  child: Text(
                                    s,
                                    style: const TextStyle(
                                      fontSize: 20,
                                      fontWeight: FontWeight.bold,
                                    ),
                                  ),
                                ))
                            .toList(),
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
        );
      },
    );
  }

  Future<void> _pickImage() async {
    final picker = ImagePicker();
    final picked = await picker.pickImage(source: ImageSource.gallery);
    if (picked != null) {
      setState(() {
        _selectedImage = File(picked.path);
      });
    }
  }


  Future<Map<String, String?>> _getOrCreateFamilyAlbum() async {
    try {
      final user = SupabaseService.client.auth.currentUser;
      if (user == null) return {'albumId': null, 'familyId': null};

      // 사용자 정보에서 current_family_id 가져오기
      final userData = await SupabaseService.client
          .from('users')
          .select('current_family_id')
          .eq('id', user.id)
          .single();

      final familyId = userData['current_family_id'] as String?;
      if (familyId == null) {
        print('⚠️ [Album] 사용자에게 설정된 가족이 없습니다.');
        return {'albumId': null, 'familyId': null};
      }

      print('📚 [Album] 가족 ID: $familyId');

      // 해당 가족의 기본 앨범 조회
      final existingAlbums = await SupabaseService.client
          .from('albums')
          .select('id')
          .eq('family_id', familyId)
          .eq('name', '가족 앨범')
          .limit(1);

      if (existingAlbums.isNotEmpty) {
        final albumId = existingAlbums.first['id'] as String;
        print('📚 [Album] 기존 앨범 사용: $albumId');
        return {'albumId': albumId, 'familyId': familyId};
      }

      // 기본 앨범이 없으면 새로 생성
      final newAlbum = await SupabaseService.client
          .from('albums')
          .insert({
            'user_id': user.id,
            'family_id': familyId,
            'name': '가족 앨범',
            'description': '가족 사진을 모아둔 앨범입니다.',
          })
          .select('id')
          .single();

      final albumId = newAlbum['id'] as String;
      print('📚 [Album] 새 앨범 생성: $albumId');
      return {'albumId': albumId, 'familyId': familyId};

    } catch (e) {
      print('❌ [Album] 앨범 생성/조회 실패: $e');
      return {'albumId': null, 'familyId': null};
    }
  }

  Future<void> _uploadPhoto() async {
    try {
      final user = SupabaseService.client.auth.currentUser;
      if (user == null) {
        throw Exception('사용자가 로그인되지 않았습니다.');
      }

      final year = int.parse(years[selectedYearIndex]);
      final season = getSeasonEng(seasons[selectedSeasonIndex]);
      final description = _descController.text.trim();
      final file = _selectedImage!;
      
      // 가족 앨범 ID 가져오기/생성
      final albumData = await _getOrCreateFamilyAlbum();
      final albumId = albumData['albumId'];
      final familyId = albumData['familyId'];
      
      // 파일 읽기
      final bytes = await file.readAsBytes();
      final fileName = path.basename(file.path);
      final fileExtension = path.extension(fileName).toLowerCase();
      final timestamp = DateTime.now().millisecondsSinceEpoch;
      final storagePath = '$familyId/${user.id}_$timestamp$fileExtension';

      print('📤 [Supabase] 파일 업로드 시작: $storagePath');
      
      // Supabase Storage에 파일 업로드 (인증 포함)
      final uploadResult = await SupabaseService.client.storage
          .from('photos')
          .uploadBinary(
            storagePath, 
            bytes,
            fileOptions: const FileOptions(
              upsert: false,
            ),
          );
      
      print('📤 [Supabase] 파일 업로드 완료: $uploadResult');
      
      print('📤 [Supabase] Storage 경로: $storagePath');
      
      // 파일 정보 가져오기
      final fileInfo = await file.stat();
      
      // photos 테이블에 메타데이터 저장
      final photoData = {
        'user_id': user.id,
        'file_name': fileName,
        'filename': fileName,
        'original_filename': fileName,
        'file_path': storagePath,
        'file_size': fileInfo.size,
        'mime_type': _getMimeType(fileExtension),
        'description': description,
        'tags': [year.toString(), season],
        'album_id': albumId,
        'taken_at': DateTime(year, _getSeasonMonth(season), 1).toIso8601String(),
        'is_favorite': false,
        'is_deleted': false,
      };
      
      print('📤 [Supabase] DB 저장 데이터: $photoData');
      
      final insertResult = await SupabaseService.client
          .from('photos')
          .insert(photoData)
          .select()
          .single();
      
      print('📤 [Supabase] DB 저장 완료: $insertResult');
      
      if (!mounted) return;
      
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('사진 업로드 성공!')),
      );
      
      // 폼 초기화
      setState(() {
        _selectedImage = null;
        _descController.clear();
      });
      
    } catch (e) {
      print('❌ [Supabase] 업로드 실패: $e');
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('업로드 실패: $e')),
      );
    }
  }
  
  String _getMimeType(String extension) {
    switch (extension) {
      case '.jpg':
      case '.jpeg':
        return 'image/jpeg';
      case '.png':
        return 'image/png';
      case '.gif':
        return 'image/gif';
      default:
        return 'image/jpeg';
    }
  }
  
  int _getSeasonMonth(String season) {
    switch (season) {
      case 'spring':
        return 3;
      case 'summer':
        return 6;
      case 'autumn':
        return 9;
      case 'winter':
        return 12;
      default:
        return 1;
    }
  }

  @override
  Widget build(BuildContext context) {
    String selectedText = '${years[selectedYearIndex]} ${seasons[selectedSeasonIndex]}';

    return GestureDetector(
      onTap: () {
        FocusScope.of(context).unfocus();
      },
      child: Scaffold(
        backgroundColor: const Color(0xFFF7F7F7),
        appBar: GroupBar(
          title: Provider.of<UserProvider>(context, listen: false).familyName ?? '우리 가족',
        ),
        body: Padding(
          padding: const EdgeInsets.all(20.0),
          child: SingleChildScrollView(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // 연도/계절 선택
                GestureDetector(
                  onTap: _showYearSeasonPicker,
                  child: Row(
                    children: [
                      Text(
                        selectedText,
                        style: const TextStyle(
                          fontSize: 25,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                      const SizedBox(width: 5),
                      const Icon(Icons.arrow_forward_ios_rounded),
                    ],
                  ),
                ),
                const SizedBox(height: 20),

                // 사진 업로드 박스
                // 사진 업로드 박스
                Container(
                  width: double.infinity,
                  height: 250,
                  decoration: BoxDecoration(
                    border: _selectedImage == null ? Border.all( // _selectedImage가 null일 때만 border 표시
                      color: const Color(0xFF8CCAA7),
                      width: 3,
                    ) : null,
                    borderRadius: BorderRadius.circular(20),
                    color: _selectedImage == null ? const Color.fromARGB(255, 226, 252, 237) : null, // _selectedImage가 null일 때만 배경색 표시
                  ),
                  alignment: Alignment.center,
                  child: GestureDetector(
                    onTap: _pickImage,
                    child: _selectedImage == null
                        ? Column( // _selectedImage가 null일 때만 Column 표시
                            mainAxisAlignment: MainAxisAlignment.center,
                            children: [
                              Image.asset(
                                'assets/icons/Add_fill.png',
                                width: 50,
                                height: 50,
                                color: const Color(0xFF8CCAA7),
                                colorBlendMode: BlendMode.srcIn,
                              ),
                              const SizedBox(height: 10),
                              const Text(
                                '사진을 추가해주세요',
                                style: TextStyle(
                                  fontSize: 25,
                                  fontWeight: FontWeight.w700,
                                  color: Color(0xFF8CCAA7),
                                ),
                              ),
                            ],
                          )
                        : ClipRRect( // _selectedImage가 있을 때는 사진만 표시
                            borderRadius: BorderRadius.circular(20),
                            child: Image.file(
                              _selectedImage!,
                              fit: BoxFit.cover,
                              width: double.infinity,
                              height: 250,
                            ),
                          ),
                  ),
                ),
                const SizedBox(height: 30),
                // 사진 설명 입력 영역
                const Text(
                  '사진 설명',
                  style: TextStyle(fontSize: 21, fontWeight: FontWeight.w600),
                ),
                const SizedBox(height: 10),
                TextField(
                  controller: _descController,
                  maxLines: 3,
                  maxLength: 100,
                  style: smallContentStyle.copyWith(color: Color(0xFF333333)),
                  decoration: InputDecoration(
                    hintText: '사진에 대해 설명하는 글을 간단하게 작성해주세요.',
                    hintStyle: smallContentStyle.copyWith(
                      color: Color(0xFF777777),
                    ),
                    filled: true,
                    fillColor: Colors.white,
                    contentPadding: const EdgeInsets.all(10),
                    border: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(10),
                      borderSide: const BorderSide(color: Color(0x66999999)),
                    ),
                    enabledBorder: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(10),
                      borderSide: const BorderSide(color: Color(0x66999999)),
                    ),
                  ),
                ),
                const SizedBox(height: 30),

                // 사진 추가 버튼
                Center(
                  child: ElevatedButton(
                    onPressed: isAllFilled
                        ? () async {
                            final user = SupabaseService.client.auth.currentUser;
                            if (user != null) {
                              await _uploadPhoto();
                            } else {
                              if (!mounted) return;
                              ScaffoldMessenger.of(context).showSnackBar(
                                const SnackBar(content: Text('로그인이 필요합니다.')),
                              );
                            }
                          }
                        : null,
                    style: ElevatedButton.styleFrom(
                      backgroundColor: isAllFilled
                          ? const Color(0xFF8CCAA7)
                          : const Color(0xFFDFF3F2),
                      minimumSize: const Size(double.infinity, 60),
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(20),
                      ),
                    ),
                    child: Text(
                      '사진 추가하기',
                      style: TextStyle(
                        fontSize: 22,
                        fontWeight: FontWeight.w800,
                        fontFamily: 'Pretendard',
                        letterSpacing: 1,
                        color: isAllFilled ? Colors.white : const Color(0xFF888888),
                      ),
                    ),
                  ),
                ),
              ],
            ),
          ),
        ),
        bottomNavigationBar: const CustomBottomNavBar(currentIndex: 2),
      ),
    );
  }
}