import 'package:flutter/foundation.dart';

/// 사진 + 대화여부를 함께 들고 다니는 뷰모델.
/// - 백엔드 맵 구조가 약간 달라도 안전하게 파싱되도록 방어코드 포함
class PhotoWithConv {
  final Map<String, dynamic> photoData;
  final bool hasConversation;

  PhotoWithConv({
    required this.photoData,
    required this.hasConversation,
  });

  /// Map -> PhotoWithConv
  factory PhotoWithConv.fromMap(Map<String, dynamic> map) {
    final raw = map['has_conversation'];
    final hasConv = raw is bool ? raw : (raw == 1 || raw == '1' || raw == 'true');
    return PhotoWithConv(photoData: map, hasConversation: hasConv);
  }

  /// 필수/자주 쓰는 필드들 ─ 널/타입 안전 처리
  String get id =>
      (photoData['photo_id'] ?? photoData['id'] ?? '').toString();

  String get url =>
      (photoData['image_url'] ?? photoData['url'] ?? photoData['public_url'] ?? '').toString();

  DateTime get createdAt {
    final v = photoData['upload_date'] ?? photoData['created_at'];
    if (v == null) return DateTime.now();
    if (v is DateTime) return v;
    return DateTime.tryParse(v.toString()) ?? DateTime.now();
  }

  List<String> get tags {
    final t = photoData['tags'];
    if (t is List) return t.map((e) => e.toString()).toList();
    return const [];
  }

  /// 연도 계산 우선순위: tags(YYYY) → taken_at → upload_date(createdAt)
  int get year {
    for (final tag in tags) {
      if (RegExp(r'^\d{4}$').hasMatch(tag)) return int.parse(tag);
    }
    final takenAt = photoData['taken_at'];
    if (takenAt is DateTime) return takenAt.year;
    if (takenAt != null) {
      final dt = DateTime.tryParse(takenAt.toString());
      if (dt != null) return dt.year;
    }
    return createdAt.year;
  }

  /// 계절 계산 우선순위: tags(season) → taken_at → upload_date(createdAt)
  String get season {
    for (final tag in tags) {
      final t = tag.toLowerCase();
      if (t == 'spring' || t == 'summer' || t == 'autumn' || t == 'winter') {
        return t;
      }
    }
    DateTime dateToUse = createdAt;
    final takenAt = photoData['taken_at'];
    if (takenAt is DateTime) {
      dateToUse = takenAt;
    } else if (takenAt != null) {
      final dt = DateTime.tryParse(takenAt.toString());
      if (dt != null) dateToUse = dt;
    }
    return _seasonFromDate(dateToUse);
  }

  static String _seasonFromDate(DateTime d) {
    final m = d.month;
    if (m >= 3 && m <= 5) return 'spring';
    if (m >= 6 && m <= 8) return 'summer';
    if (m >= 9 && m <= 11) return 'autumn';
    return 'winter';
  }
}
