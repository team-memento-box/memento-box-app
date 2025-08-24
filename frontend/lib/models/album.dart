import 'photo.dart';

class Album {
  final String id;
  final String userId;
  final String name;
  final String? description;
  final DateTime createdAt;
  final DateTime updatedAt;
  final List<Photo>? photos;

  Album({
    required this.id,
    required this.userId,
    required this.name,
    this.description,
    required this.createdAt,
    required this.updatedAt,
    this.photos,
  });

  factory Album.fromSupabase(Map<String, dynamic> json) {
    return Album(
      id: json['id'],
      userId: json['user_id'],
      name: json['name'],
      description: json['description'],
      createdAt: DateTime.parse(json['created_at']),
      updatedAt: DateTime.parse(json['updated_at']),
      photos: json['photos'] != null
          ? (json['photos'] as List).map((p) => Photo.fromSupabase(p)).toList()
          : null,
    );
  }

  // 앨범 내 사진 개수
  int get photoCount => photos?.length ?? 0;

  // 대표 이미지 (첫 번째 사진)
  Photo? get coverPhoto => photos?.isNotEmpty == true ? photos!.first : null;

  // 포맷된 생성일
  String get formattedCreatedAt {
    return '${createdAt.year}년 ${createdAt.month.toString().padLeft(2, '0')}월 ${createdAt.day.toString().padLeft(2, '0')}일';
  }
}