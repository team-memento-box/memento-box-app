// 작성자: 홍원원
// 작성일: 2025.06.10
// lib/utils/routes.dart

class Routes {
  // 로그인//
  static const signin = '/signin'; // 로그인 화면
  static const kakaoSignin = '/kakao_signin'; // 카카오 로그인 화면
  
  static const groupSelect = '/0-3-1'; // 그룹 선택 화면
  static const groupCreate = '/group_create'; // 그룹 생성 화면 (0-3-1-1)
  static const familyCodeInput = '/0-3-2'; // 피보호자
  // 로그인 끝//

  //위젯//
  static const home = '/home'; // 홈 화면
  static const gallery = '/gallery'; // 갤러리 화면

  //보호자
  static const addPhoto = '/addphoto'; // 사진 추가 화면
  static const photoDetail = '/photoDetail'; // 사진 상세 화면
  //피보호자
  static const conversation = '/conversation'; // 대화하기

  static const report = '/report'; // 보고서 화면 
  static const reportDetail = '/reportDetail'; // 보고서 상세 화면

  static const profile = '/profile'; // 프로필 화면
  //위젯 끝//

  //사진첩 없을때
  static const intro = '/intro'; // 소개 화면 (아직 안씀) //
  static const request = '/request';
 
  //음성 테스트
  static const voiceTest = '/voiceTest';

  //대화
  

}