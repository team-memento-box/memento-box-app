import '../core/supabase_service.dart';
import '../lib/models/album.dart';
import '../lib/models/photo.dart';

class AlbumApi {
  /// 사용자의 모든 앨범 조회
  static Future<List<Album>> fetchAlbums(String userId, {bool includePhotos = false}) async {
    try {
      print('📁 Fetching albums for user: $userId');
      
      String selectQuery = 'id, user_id, name, description, created_at, updated_at';
      if (includePhotos) {
        selectQuery += ', photos!album_id(*)';
      }

      final response = await SupabaseService.client
          .from('albums')
          .select(selectQuery)
          .eq('user_id', userId)
          .order('created_at', ascending: false);
      
      print('✅ Found ${response.length} albums');
      
      return response.map((json) => Album.fromSupabase(json)).toList();
    } catch (e) {
      print('❌ Error fetching albums: $e');
      throw Exception('앨범 목록을 불러오지 못했습니다: $e');
    }
  }

  /// 새 앨범 생성
  static Future<Album> createAlbum({
    required String userId,
    required String name,
    String? description,
  }) async {
    try {
      print('📁 Creating new album: $name');
      
      final albumData = {
        'user_id': userId,
        'name': name,
        'description': description,
      };

      final response = await SupabaseService.client
          .from('albums')
          .insert(albumData)
          .select()
          .single();

      print('✅ Album created: ${response['id']}');
      
      return Album.fromSupabase(response);
    } catch (e) {
      print('❌ Error creating album: $e');
      throw Exception('앨범 생성에 실패했습니다: $e');
    }
  }

  /// 앨범 정보 업데이트
  static Future<Album> updateAlbum({
    required String albumId,
    required String userId,
    String? name,
    String? description,
  }) async {
    try {
      print('📝 Updating album: $albumId');
      
      final updateData = <String, dynamic>{
        'updated_at': DateTime.now().toIso8601String(),
      };

      if (name != null) updateData['name'] = name;
      if (description != null) updateData['description'] = description;

      final response = await SupabaseService.client
          .from('albums')
          .update(updateData)
          .eq('id', albumId)
          .eq('user_id', userId)
          .select()
          .single();

      print('✅ Album updated successfully');
      
      return Album.fromSupabase(response);
    } catch (e) {
      print('❌ Error updating album: $e');
      throw Exception('앨범 정보 업데이트에 실패했습니다: $e');
    }
  }

  /// 앨범 삭제
  static Future<void> deleteAlbum(String albumId, String userId) async {
    try {
      print('🗑️ Deleting album: $albumId');
      
      // 앨범 내 사진들의 album_id를 null로 설정 (사진은 유지)
      await SupabaseService.client
          .from('photos')
          .update({'album_id': null})
          .eq('album_id', albumId)
          .eq('user_id', userId);
      
      // 앨범 삭제
      await SupabaseService.client
          .from('albums')
          .delete()
          .eq('id', albumId)
          .eq('user_id', userId);
      
      print('✅ Album deleted successfully');
    } catch (e) {
      print('❌ Error deleting album: $e');
      throw Exception('앨범 삭제에 실패했습니다: $e');
    }
  }

  /// 특정 앨범의 사진들 조회
  static Future<List<Photo>> getAlbumPhotos(String albumId, String userId) async {
    try {
      print('📸 Fetching photos for album: $albumId');
      
      final response = await SupabaseService.client
          .from('photos')
          .select()
          .eq('album_id', albumId)
          .eq('user_id', userId)
          .eq('is_deleted', false)
          .order('created_at', ascending: false);
      
      print('✅ Found ${response.length} photos in album');
      
      return response.map((json) => Photo.fromSupabase(json)).toList();
    } catch (e) {
      print('❌ Error fetching album photos: $e');
      throw Exception('앨범 사진을 불러오지 못했습니다: $e');
    }
  }

  /// 사진을 앨범에 추가
  static Future<void> addPhotoToAlbum(String photoId, String albumId, String userId) async {
    try {
      print('➕ Adding photo to album: $photoId -> $albumId');
      
      await SupabaseService.client
          .from('photos')
          .update({'album_id': albumId})
          .eq('id', photoId)
          .eq('user_id', userId);
      
      print('✅ Photo added to album successfully');
    } catch (e) {
      print('❌ Error adding photo to album: $e');
      throw Exception('사진을 앨범에 추가하는데 실패했습니다: $e');
    }
  }

  /// 사진을 앨범에서 제거 (사진은 유지, 앨범 관계만 제거)
  static Future<void> removePhotoFromAlbum(String photoId, String userId) async {
    try {
      print('➖ Removing photo from album: $photoId');
      
      await SupabaseService.client
          .from('photos')
          .update({'album_id': null})
          .eq('id', photoId)
          .eq('user_id', userId);
      
      print('✅ Photo removed from album successfully');
    } catch (e) {
      print('❌ Error removing photo from album: $e');
      throw Exception('앨범에서 사진 제거에 실패했습니다: $e');
    }
  }

  /// 앨범별 통계 조회
  static Future<Map<String, dynamic>> getAlbumStats(String userId) async {
    try {
      // 총 앨범 수
      final albumCount = await SupabaseService.client
          .from('albums')
          .select('id')
          .eq('user_id', userId)
          .count();

      // 앨범 없는 사진 수
      final unalbumedPhotos = await SupabaseService.client
          .from('photos')
          .select('id')
          .eq('user_id', userId)
          .is_('album_id', null)
          .eq('is_deleted', false)
          .count();

      // 가장 사진이 많은 앨범
      final albumPhotoCounts = await SupabaseService.client
          .from('photos')
          .select('album_id')
          .eq('user_id', userId)
          .eq('is_deleted', false)
          .not('album_id', 'is', null);

      final albumCountMap = <String, int>{};
      for (final photo in albumPhotoCounts) {
        final albumId = photo['album_id'].toString();
        albumCountMap[albumId] = (albumCountMap[albumId] ?? 0) + 1;
      }

      String? mostPopularAlbumId;
      int maxPhotoCount = 0;
      albumCountMap.forEach((albumId, count) {
        if (count > maxPhotoCount) {
          maxPhotoCount = count;
          mostPopularAlbumId = albumId;
        }
      });

      return {
        'total_albums': albumCount,
        'unalbumed_photos': unalbumedPhotos,
        'most_popular_album_id': mostPopularAlbumId,
        'max_photo_count_in_album': maxPhotoCount,
        'album_photo_counts': albumCountMap,
      };
    } catch (e) {
      print('❌ Error getting album stats: $e');
      throw Exception('앨범 통계 조회에 실패했습니다: $e');
    }
  }
}