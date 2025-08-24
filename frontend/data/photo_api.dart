import '../core/supabase_service.dart';
import '../lib/models/photo.dart';
import 'dart:io';
import 'dart:typed_data';

class PhotoApi {
  /// 사용자의 모든 사진 조회
  static Future<List<Photo>> fetchPhotos(String userId, {
    String? albumId,
    List<String>? tags,
    bool? isFavorite,
    int? limit,
    int? offset,
  }) async {
    try {
      print('📸 Fetching photos for user: $userId');
      
      var query = SupabaseService.client
          .from('photos')
          .select()
          .eq('user_id', userId)
          .eq('is_deleted', false);

      if (albumId != null) {
        query = query.eq('album_id', albumId);
      }

      if (isFavorite != null) {
        query = query.eq('is_favorite', isFavorite);
      }

      if (tags != null && tags.isNotEmpty) {
        query = query.contains('tags', tags);
      }

      if (limit != null) {
        query = query.limit(limit);
      }

      if (offset != null) {
        query = query.range(offset, offset + (limit ?? 20) - 1);
      }

      query = query.order('created_at', ascending: false);

      final response = await query;
      
      print('✅ Found ${response.length} photos');
      
      return response.map((json) => Photo.fromSupabase(json)).toList();
    } catch (e) {
      print('❌ Error fetching photos: $e');
      throw Exception('사진 목록을 불러오지 못했습니다: $e');
    }
  }

  /// 사진 업로드
  static Future<Photo> uploadPhoto({
    required String userId,
    required File imageFile,
    required String originalFilename,
    String? description,
    List<String>? tags,
    String? albumId,
    DateTime? takenAt,
    String? locationName,
    double? latitude,
    double? longitude,
  }) async {
    try {
      print('📤 Uploading photo: $originalFilename');
      
      // 파일 정보 가져오기
      final bytes = await imageFile.readAsBytes();
      final fileSize = bytes.length;
      final mimeType = _getMimeType(originalFilename);
      
      // 고유한 파일명 생성
      final timestamp = DateTime.now().millisecondsSinceEpoch;
      final extension = originalFilename.split('.').last;
      final filename = '${timestamp}_${userId.substring(0, 8)}.$extension';
      final filePath = '$userId/$filename';
      
      // Supabase Storage에 업로드
      await SupabaseService.client.storage
          .from('photos')
          .uploadBinary(filePath, bytes);
      
      print('✅ File uploaded to storage: $filePath');
      
      // 이미지 메타데이터 추출 (선택사항)
      int? width, height;
      // TODO: 이미지 라이브러리를 사용해 실제 해상도 추출
      
      // DB에 메타데이터 저장
      final photoData = {
        'user_id': userId,
        'file_name': filename, // 레거시 호환성
        'filename': filename,
        'original_filename': originalFilename,
        'file_path': filePath,
        'file_size': fileSize,
        'mime_type': mimeType,
        'width': width,
        'height': height,
        'description': description,
        'tags': tags ?? [],
        'album_id': albumId,
        'taken_at': takenAt?.toIso8601String(),
        'location_name': locationName,
        'latitude': latitude,
        'longitude': longitude,
        'is_favorite': false,
        'is_deleted': false,
      };

      final response = await SupabaseService.client
          .from('photos')
          .insert(photoData)
          .select()
          .single();

      print('✅ Photo metadata saved: ${response['id']}');
      
      return Photo.fromSupabase(response);
    } catch (e) {
      print('❌ Error uploading photo: $e');
      throw Exception('사진 업로드에 실패했습니다: $e');
    }
  }

  /// 사진 삭제 (soft delete)
  static Future<void> deletePhoto(String photoId, String userId) async {
    try {
      print('🗑️ Deleting photo: $photoId');
      
      await SupabaseService.client
          .from('photos')
          .update({'is_deleted': true})
          .eq('id', photoId)
          .eq('user_id', userId);
      
      print('✅ Photo marked as deleted');
    } catch (e) {
      print('❌ Error deleting photo: $e');
      throw Exception('사진 삭제에 실패했습니다: $e');
    }
  }

  /// 사진 완전 삭제 (storage + db)
  static Future<void> permanentDeletePhoto(String photoId, String userId) async {
    try {
      print('💥 Permanently deleting photo: $photoId');
      
      // 먼저 파일 경로 조회
      final photo = await SupabaseService.client
          .from('photos')
          .select('file_path')
          .eq('id', photoId)
          .eq('user_id', userId)
          .single();
      
      final filePath = photo['file_path'];
      
      // Storage에서 파일 삭제
      await SupabaseService.client.storage
          .from('photos')
          .remove([filePath]);
      
      // DB에서 레코드 삭제
      await SupabaseService.client
          .from('photos')
          .delete()
          .eq('id', photoId)
          .eq('user_id', userId);
      
      print('✅ Photo permanently deleted');
    } catch (e) {
      print('❌ Error permanently deleting photo: $e');
      throw Exception('사진 완전 삭제에 실패했습니다: $e');
    }
  }

  /// 사진 즐겨찾기 토글
  static Future<void> toggleFavorite(String photoId, String userId) async {
    try {
      // 현재 상태 조회
      final current = await SupabaseService.client
          .from('photos')
          .select('is_favorite')
          .eq('id', photoId)
          .eq('user_id', userId)
          .single();
      
      final newFavoriteStatus = !current['is_favorite'];
      
      await SupabaseService.client
          .from('photos')
          .update({'is_favorite': newFavoriteStatus})
          .eq('id', photoId)
          .eq('user_id', userId);
      
      print('✅ Photo favorite status updated: $newFavoriteStatus');
    } catch (e) {
      print('❌ Error toggling favorite: $e');
      throw Exception('즐겨찾기 설정에 실패했습니다: $e');
    }
  }

  /// 사진 정보 업데이트
  static Future<Photo> updatePhoto({
    required String photoId,
    required String userId,
    String? description,
    List<String>? tags,
    String? albumId,
    String? locationName,
    double? latitude,
    double? longitude,
  }) async {
    try {
      print('📝 Updating photo: $photoId');
      
      final updateData = <String, dynamic>{
        'updated_at': DateTime.now().toIso8601String(),
      };

      if (description != null) updateData['description'] = description;
      if (tags != null) updateData['tags'] = tags;
      if (albumId != null) updateData['album_id'] = albumId;
      if (locationName != null) updateData['location_name'] = locationName;
      if (latitude != null) updateData['latitude'] = latitude;
      if (longitude != null) updateData['longitude'] = longitude;

      final response = await SupabaseService.client
          .from('photos')
          .update(updateData)
          .eq('id', photoId)
          .eq('user_id', userId)
          .select()
          .single();

      print('✅ Photo updated successfully');
      
      return Photo.fromSupabase(response);
    } catch (e) {
      print('❌ Error updating photo: $e');
      throw Exception('사진 정보 업데이트에 실패했습니다: $e');
    }
  }

  /// 앨범별 사진 개수 조회
  static Future<Map<String, int>> getPhotoCountsByAlbum(String userId) async {
    try {
      final response = await SupabaseService.client
          .from('photos')
          .select('album_id')
          .eq('user_id', userId)
          .eq('is_deleted', false);

      final counts = <String, int>{};
      for (final photo in response) {
        final albumId = photo['album_id']?.toString() ?? 'no_album';
        counts[albumId] = (counts[albumId] ?? 0) + 1;
      }

      return counts;
    } catch (e) {
      print('❌ Error getting photo counts: $e');
      throw Exception('사진 개수 조회에 실패했습니다: $e');
    }
  }

  /// MIME 타입 추정
  static String _getMimeType(String filename) {
    final extension = filename.toLowerCase().split('.').last;
    switch (extension) {
      case 'jpg':
      case 'jpeg':
        return 'image/jpeg';
      case 'png':
        return 'image/png';
      case 'gif':
        return 'image/gif';
      case 'webp':
        return 'image/webp';
      default:
        return 'image/jpeg';
    }
  }
}