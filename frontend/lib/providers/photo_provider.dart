import 'package:flutter/material.dart';
import '../data/photo_api.dart';
import '../models/photo.dart';

class PhotoWithConv {
  final Photo photo;
  final bool hasConversation;

  PhotoWithConv({
    required this.photo,
    this.hasConversation = false,
  });
}

class PhotoProvider with ChangeNotifier {
  List<PhotoWithConv> _photos = [];
  bool _isLoading = false;
  DateTime? _lastUpdated;
  String? _cachedFamilyId;

  List<PhotoWithConv> get photos => _photos;
  bool get isLoading => _isLoading;
  bool get hasData => _photos.isNotEmpty;

  /// 캐시 유효 시간 (5분)
  bool get _isCacheValid {
    if (_lastUpdated == null) return false;
    return DateTime.now().difference(_lastUpdated!) < const Duration(minutes: 5);
  }

  /// 사진 불러오기
  Future<void> loadPhotos(String familyId, {bool forceRefresh = false}) async {
    if (_isLoading) return;

    // 캐시 재사용
    if (!forceRefresh && _isCacheValid && _cachedFamilyId == familyId && hasData) {
      print('📋 Using cached photos (${_photos.length}장)');
      return;
    }

    _isLoading = true;
    notifyListeners();

    try {
      print('🔄 Loading fresh photos for family $familyId');
      final familyPhotos =
          await PhotoApi.fetchRecentFamilyPhotoNewsWithConversations(familyId, limit: 30);

      _photos = familyPhotos.map((photoData) {
        final hasConv = photoData['has_conversation'] ?? false;
        return PhotoWithConv(
          photo: Photo.fromSupabase(photoData),
          hasConversation: hasConv,
        );
      }).toList();

      _cachedFamilyId = familyId;
      _lastUpdated = DateTime.now();

      print('✅ Photos loaded and cached: ${_photos.length}');
    } catch (e) {
      print('❌ Error loading photos: $e');
      rethrow;
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  /// 새 사진 추가 (예: 업로드 직후)
  void addPhoto(PhotoWithConv photo) {
    _photos.insert(0, photo); // 맨 앞에 추가
    notifyListeners();
  }

  /// 강제 갱신 (Pull to Refresh)
  Future<void> refreshPhotos(String familyId) async {
    await loadPhotos(familyId, forceRefresh: true);
  }

  /// 캐시 초기화
  void clearCache() {
    _photos.clear();
    _lastUpdated = null;
    _cachedFamilyId = null;
    notifyListeners();
  }
}
