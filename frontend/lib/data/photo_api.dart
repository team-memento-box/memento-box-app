import '../core/supabase_service.dart';
import '../models/photo.dart';
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
      
      // 기본 쿼리 빌드
      var query = SupabaseService.client
          .from('photos')
          .select()
          .eq('user_id', userId)
          .eq('is_deleted', false);

      // 조건부 필터링
      if (albumId != null) {
        query = query.eq('album_id', albumId);
      }
      if (isFavorite != null) {
        query = query.eq('is_favorite', isFavorite);
      }
      if (tags != null && tags.isNotEmpty) {
        query = query.contains('tags', tags);
      }

      // 정렬 및 제한 (메서드 체이닝으로 한 번에 처리)
      final responseQuery = query.order('created_at', ascending: false);
      
      final finalQuery = limit != null 
          ? (offset != null 
              ? responseQuery.range(offset, offset + limit - 1)
              : responseQuery.limit(limit))
          : responseQuery;

      final response = await finalQuery;
      
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

  /// 최근 가족 구성원들의 사진 업로드 소식 조회
  static Future<List<Map<String, dynamic>>> fetchRecentFamilyPhotoNews(String familyId, {int limit = 10}) async {
    try {
      print('📰 Fetching recent family photo news for family: $familyId');
      
      // 디버깅: 가족 정보 확인
      print('🔍 Debug: Checking family exists...');
      final familyCheck = await SupabaseService.client
          .from('families')
          .select('id, family_name')
          .eq('id', familyId);
      print('🔍 Debug: Family found: ${familyCheck.length} families');
      if (familyCheck.isNotEmpty) {
        print('🔍 Debug: Family name: ${familyCheck.first['family_name']}');
      }
      
      // 먼저 가족 구성원들의 정보 조회 (JOIN 없이)
      print('🔍 Debug: Fetching family members without join...');
      final familyMembersOnly = await SupabaseService.client
          .from('family_members')
          .select('user_id, family_role')
          .eq('family_id', familyId);
      
      print('🔍 Debug: Found ${familyMembersOnly.length} family members without join');
      for (final member in familyMembersOnly) {
        print('🔍 Debug: Member - user_id: ${member['user_id']}, role: ${member['family_role']}');
      }
      
      // 특별히 더미 사용자가 있는지 확인
      print('🔍 Debug: Specifically checking for dummy user a0a5035a-430b-4ed1-a127-bc9ca00da480...');
      final dummyUserCheck = await SupabaseService.client
          .from('family_members')
          .select('user_id, family_role, family_id')
          .eq('user_id', 'a0a5035a-430b-4ed1-a127-bc9ca00da480');
      
      print('🔍 Debug: Dummy user found in family_members: ${dummyUserCheck.length} records');
      for (final record in dummyUserCheck) {
        print('🔍 Debug: Dummy user record - family_id: ${record['family_id']}, role: ${record['family_role']}');
      }
      
      // 전체 family_members 테이블에서 해당 가족의 모든 구성원 확인
      print('🔍 Debug: All members for family $familyId...');
      final allFamilyMembers = await SupabaseService.client
          .from('family_members')
          .select('user_id, family_role, joined_at')
          .eq('family_id', familyId);
      
      print('🔍 Debug: All family members count: ${allFamilyMembers.length}');
      for (final member in allFamilyMembers) {
        print('🔍 Debug: All members - user_id: ${member['user_id']}, role: ${member['family_role']}, joined: ${member['joined_at']}');
      }
      
      // 각 사용자 정보를 개별적으로 조회
      print('🔍 Debug: Fetching user details for each member...');
      print('🔍 Debug: familyMembersOnly length: ${familyMembersOnly.length}');
      final familyMembers = <Map<String, dynamic>>[];
      
      for (int i = 0; i < familyMembersOnly.length; i++) {
        final memberData = familyMembersOnly[i];
        final userId = memberData['user_id'];
        print('🔍 Debug: Processing member $i: $userId (${memberData['family_role']})');
        
        print('🔍 Debug: Querying users table with id: $userId');
        final userInfo = await SupabaseService.client
            .from('users')
            .select('full_name, profile_image_url')
            .eq('id', userId)
            .maybeSingle();
        
        print('🔍 Debug: User query result: $userInfo');
        
        if (userInfo != null) {
          print('🔍 Debug: Found user: ${userInfo['full_name']}');
          familyMembers.add({
            'user_id': userId,
            'family_role': memberData['family_role'],
            'users': userInfo,
          });
        } else {
          print('🔍 Debug: User $userId not found in users table, using fallback');
          familyMembers.add({
            'user_id': userId,
            'family_role': memberData['family_role'],
            'users': {
              'full_name': '이름 없음 (${memberData['family_role']})',
              'profile_image_url': null,
            },
          });
        }
      }
      
      print('🔍 Debug: Final family members count: ${familyMembers.length}');
      
      if (familyMembers.isEmpty) {
        print('⚠️ No family members found for family: $familyId');
        
        // 디버깅: 가족 구성원 테이블 전체 확인
        print('🔍 Debug: Checking all family_members table...');
        final allMembers = await SupabaseService.client
            .from('family_members')
            .select('family_id, user_id, family_role')
            .limit(10);
        print('🔍 Debug: Total family members in DB: ${allMembers.length}');
        for (final member in allMembers) {
          print('🔍 Debug: Member - family_id: ${member['family_id']}, user_id: ${member['user_id']}, role: ${member['family_role']}');
        }
        
        return [];
      }
      
      // 각 가족 구성원의 사진들을 개별적으로 조회하고 합치기
      List<Map<String, dynamic>> allPhotos = [];
      
      for (final member in familyMembers) {
        final userId = member['user_id'];
        final user = member['users'] as Map<String, dynamic>;
        final familyRole = member['family_role'] ?? '가족';
        
        print('🔍 Debug: Checking photos for user: $userId (${user['full_name']})');
        
        final photos = await SupabaseService.client
            .from('photos')
            .select('id, user_id, filename, original_filename, file_path, description, created_at')
            .eq('user_id', userId)
            .eq('is_deleted', false)
            .order('created_at', ascending: false)
            .limit(limit);
        
        print('🔍 Debug: Found ${photos.length} photos for user: ${user['full_name']}');
        
        if (photos.isEmpty) {
          // 디버깅: 해당 사용자의 모든 사진 확인 (삭제된 것 포함)
          print('🔍 Debug: Checking all photos for user (including deleted)...');
          final allUserPhotos = await SupabaseService.client
              .from('photos')
              .select('id, user_id, filename, is_deleted, created_at')
              .eq('user_id', userId);
          print('🔍 Debug: Total photos for user: ${allUserPhotos.length}');
          for (final photo in allUserPhotos) {
            print('🔍 Debug: Photo - id: ${photo['id']}, filename: ${photo['filename']}, is_deleted: ${photo['is_deleted']}, created_at: ${photo['created_at']}');
          }
        }
        
        for (final photo in photos) {
          // Private storage이므로 signed URL 사용
          String? imageUrl;
          try {
            final signedUrl = await SupabaseService.client.storage
                .from('photos')
                .createSignedUrl(photo['file_path'], 3600); // 1시간 유효
            imageUrl = signedUrl;
            print('🔍 Debug: Created signed URL: $imageUrl');
          } catch (e) {
            print('❌ Error creating signed URL: $e');
            // 실제 파일이 없으므로 테스트 이미지로 fallback
            final photoId = photo['id'] as String;
            imageUrl = 'https://picsum.photos/400/300?random=${photoId.hashCode.abs()}';
            print('🔍 Debug: Using fallback image: $imageUrl');
          }
          
          allPhotos.add({
            'photo_id': photo['id'],
            'user_id': photo['user_id'],
            'user_name': user['full_name'] ?? '이름 없음',
            'user_profile_image': user['profile_image_url'],
            'family_role': familyRole,
            'content': '새로운 사진 추가',
            'image_url': imageUrl,
            'upload_date': DateTime.parse(photo['created_at']),
            'original_filename': photo['original_filename'],
            'description': photo['description'],
          });
        }
      }
      
      // 업로드 날짜순으로 정렬하고 제한
      allPhotos.sort((a, b) => (b['upload_date'] as DateTime).compareTo(a['upload_date'] as DateTime));
      if (allPhotos.length > limit) {
        allPhotos = allPhotos.take(limit).toList();
      }
      
      print('✅ Found ${allPhotos.length} recent photo uploads');
      return allPhotos;
      
    } catch (e) {
      print('❌ Error fetching recent family photo news: $e');
      print('❌ Stack trace: $e');
      throw Exception('최근 가족 사진 소식을 불러오지 못했습니다: $e');
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