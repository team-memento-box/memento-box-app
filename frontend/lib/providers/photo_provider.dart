import 'package:flutter/foundation.dart';
import '../models/photo_with_conv.dart';
import '../data/photo_api.dart';

/// 갤러리 캐시 + 로딩 상태를 관리하는 Provider
///
/// - 최초 진입 시 네트워크 로드 후 메모리 캐시 보관
/// - TTL(기본 5분) 안 재진입 시 캐시 즉시 렌더
/// - Pull-to-refresh 또는 버튼 새로고침시 강제 갱신
class PhotoProvider with ChangeNotifier {
  PhotoProvider({Duration? ttl}) : _ttl = ttl ?? const Duration(minutes: 5);

  final Duration _ttl;

  List<PhotoWithConv> _photos = [];
  bool _isLoading = false;
  bool _isRefreshing = false;
  DateTime? _lastUpdated;
  String? _cachedFamilyId;

  // ── Getters
  List<PhotoWithConv> get photos => _photos;
  bool get isLoading => _isLoading;
  bool get isRefreshing => _isRefreshing;
  bool get hasData => _photos.isNotEmpty;

  bool get _isCacheValid {
    if (_lastUpdated == null) return false;
    return DateTime.now().difference(_lastUpdated!) < _ttl;
  }

  /// 가족별 사진 로드 (캐시 사용)
  Future<void> loadPhotos(String familyId, {bool forceRefresh = false}) async {
    // 중복 호출 방지
    if (_isLoading && !forceRefresh) return;

    // 캐시 유효 + 동일 가족 + 데이터 있으면 네트워크 호출 생략
    if (!forceRefresh && _isCacheValid && _cachedFamilyId == familyId && hasData) {
      if (kDebugMode) print('📋 [PhotoProvider] Using cached photos (${_photos.length})');
      return;
    }

    _isLoading = true;
    notifyListeners();

    try {
      if (kDebugMode) {
        print('🔄 [PhotoProvider] Loading photos from API (family: $familyId, force: $forceRefresh)');
      }

      // 1차 시도: 대화여부 포함 API
      List<Map<String, dynamic>> raw;
      try {
        raw = await PhotoApi.fetchRecentFamilyPhotoNewsWithConversations(
          familyId,
          limit: 30,
        );
      } catch (e) {
        if (kDebugMode) {
          print('⚠️ [PhotoProvider] WithConversations 실패 → fallback 사용: $e');
        }
        // 2차 시도: 원래 API (대화여부 없음)
        final fallback = await PhotoApi.fetchRecentFamilyPhotoNews(
          familyId,
          limit: 30,
        );
        // has_conversation 필드가 없으므로 false로 세팅
        raw = fallback.map((m) => {...m, 'has_conversation': false}).toList();
      }

      _photos = raw.map((m) => PhotoWithConv.fromMap(m)).toList();
      _cachedFamilyId = familyId;
      _lastUpdated = DateTime.now();

      if (kDebugMode) {
        print('✅ [PhotoProvider] Loaded ${_photos.length} photos (cached)');
      }
    } catch (e) {
      if (kDebugMode) print('❌ [PhotoProvider] loadPhotos error: $e');
      rethrow;
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  /// 강제 새로고침 (네트워크 재요청)
  Future<void> refreshPhotos(String familyId) async {
    if (_isRefreshing) return;
    _isRefreshing = true;
    notifyListeners();

    try {
      await loadPhotos(familyId, forceRefresh: true);
    } finally {
      _isRefreshing = false;
      notifyListeners();
    }
  }

  /// 새 사진 업로드 직후 캐시에 반영하고 싶을 때
  void addPhoto(PhotoWithConv photo) {
    _photos.insert(0, photo);
    _lastUpdated = DateTime.now();
    notifyListeners();
  }

  /// 특정 사진의 대화 여부를 나중에 업데이트할 때
  void markConversation(String photoId, {bool hasConversation = true}) {
    final idx = _photos.indexWhere((p) => p.id == photoId);
    if (idx == -1) return;
    final map = Map<String, dynamic>.from(_photos[idx].photoData);
    map['has_conversation'] = hasConversation;
    _photos[idx] = PhotoWithConv.fromMap(map);
    notifyListeners();
  }

  /// 로그아웃/가족 전환 등 캐시 모두 초기화
  void clearCache() {
    _photos = [];
    _lastUpdated = null;
    _cachedFamilyId = null;
    notifyListeners();
  }
}
