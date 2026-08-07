// 7.2 AI 검색 단위 테스트 — 응답 파싱 가드(깨진 매물 제외)·context 직렬화(멀티턴).
import 'package:flutter_test/flutter_test.dart';
import 'package:app/features/ai_search/ai_search_api.dart';
import 'package:app/features/ai_search/chat_message.dart';

void main() {
  group('parseSearchResult', () {
    test('정상 {answer, listings} 파싱', () {
      final r = parseSearchResult({
        'answer': '조건에 맞는 매물 2건입니다.',
        'listings': [
          {
            'id': 'a',
            'manufacturer': '현대',
            'model': '쏘나타',
            'year': 2020,
            'price': 25000000,
            'mileage': 30000,
            'region': '서울',
          },
        ],
      });
      expect(r.answer, contains('2건'));
      expect(r.listings.length, 1);
      expect(r.listings.first.model, '쏘나타');
    });

    test('깨진 매물 원소는 버린다(다른 정상 원소는 유지)', () {
      final r = parseSearchResult({
        'answer': 'x',
        'listings': [
          {'id': 'broken'}, // 필드 누락 → 제외
          {
            'id': 'ok',
            'manufacturer': '기아',
            'model': 'K5',
            'year': 2019,
            'price': 20000000,
            'mileage': 40000,
            'region': '경기',
          },
        ],
      });
      expect(r.listings.length, 1);
      expect(r.listings.first.id, 'ok');
    });

    test('listings 없거나 빈 배열(0건)도 안전', () {
      final r = parseSearchResult({'answer': '조건을 완화해 보세요.', 'listings': []});
      expect(r.answer, contains('완화'));
      expect(r.listings, isEmpty);

      final r2 = parseSearchResult({'answer': 'only answer'});
      expect(r2.listings, isEmpty);
    });

    test('Map 이 아니면 빈 결과', () {
      final r = parseSearchResult('garbage');
      expect(r.answer, '');
      expect(r.listings, isEmpty);
    });
  });

  // Story 16.2 PATCH 1 — AI 검색 결과 카드에 사진을 붙이려면 image_path(api 전용, 경로) →
  // image_url(카드 계약, 공개 URL)로 바꿔야 한다(web resolveCardImage 미러). getPublicUrl은
  // 전역 supabase 인스턴스가 필요해 단위 테스트에서 못 쓰므로, 가짜 imageUrlBuilder를 주입한다.
  group('parseSearchResult — image_path → image_url 매핑(web aiSearch.test.ts 미러)', () {
    Map<String, Object?> baseListing() => {
          'id': 'l1',
          'manufacturer': '현대',
          'model': '아반떼',
          'year': 2021,
          'price': 18000000,
          'mileage': 20000,
          'region': '서울',
        };

    test('image_path가 있으면 주입한 빌더로 image_url을 조립하고, image_path는 버려진다', () {
      final r = parseSearchResult(
        {
          'answer': 'x',
          'listings': [
            {...baseListing(), 'image_path': 'uid/l1/a.webp', 'image_count': 3},
          ],
        },
        imageUrlBuilder: (path) => 'https://cdn.test/$path',
      );
      final card = r.listings.single;
      expect(card.imageUrl, 'https://cdn.test/uid/l1/a.webp');
      expect(card.imagePath, isNull); // 카드는 image_url만 안다 — 경로는 image_url 자리로 소멸한다.
      expect(card.imageCount, 3);
    });

    test(
        'image_path가 null인데 image_count만 있으면 → imageUrl도 imageCount도 0'
        '(사진 준비중 위에 "N장" 배지가 뜨는 모순을 막는 가드)', () {
      final r = parseSearchResult(
        {
          'answer': 'x',
          'listings': [
            {...baseListing(), 'image_path': null, 'image_count': 3},
          ],
        },
        imageUrlBuilder: (path) => 'https://cdn.test/$path',
      );
      final card = r.listings.single;
      expect(card.imageUrl, isNull);
      expect(card.imageCount, 0);
    });

    test('image_path가 공백 문자열이면 경로 없음으로 취급한다', () {
      final r = parseSearchResult(
        {
          'answer': 'x',
          'listings': [
            {...baseListing(), 'image_path': '   ', 'image_count': 5},
          ],
        },
        imageUrlBuilder: (path) => 'https://cdn.test/$path',
      );
      final card = r.listings.single;
      expect(card.imageUrl, isNull);
      expect(card.imageCount, 0);
    });

    test('image_count가 음수면 0으로 하한한다(경로는 정상이라 imageUrl은 채워진다)', () {
      final r = parseSearchResult(
        {
          'answer': 'x',
          'listings': [
            {...baseListing(), 'image_path': 'uid/l1/a.webp', 'image_count': -3},
          ],
        },
        imageUrlBuilder: (path) => 'https://cdn.test/$path',
      );
      final card = r.listings.single;
      expect(card.imageUrl, isNotNull);
      expect(card.imageCount, 0);
    });
  });

  group('buildContext (멀티턴 직렬화)', () {
    test('role/content 만 추려 순서 유지', () {
      final ctx = buildContext([
        const ChatMessage(role: 'user', content: '안녕'),
        const ChatMessage(role: 'assistant', content: '무엇을 찾으세요?'),
      ]);
      expect(ctx.length, 2);
      expect(ctx[0].role, 'user');
      expect(ctx[1].content, '무엇을 찾으세요?');
    });

    test('빈(공백) 턴은 제거(422 자초 방지)', () {
      final ctx = buildContext([
        const ChatMessage(role: 'user', content: '질문'),
        const ChatMessage(role: 'assistant', content: '   '),
      ]);
      expect(ctx.length, 1);
      expect(ctx.first.content, '질문');
    });

    test('최근 12턴만 동봉(초과분 절단, 순서 유지)', () {
      final msgs = List.generate(
        20,
        (i) => ChatMessage(role: i.isEven ? 'user' : 'assistant', content: 't$i'),
      );
      final ctx = buildContext(msgs);
      expect(ctx.length, maxContextTurns);
      // 최근 12개 = t8..t19, 순서 유지.
      expect(ctx.first.content, 't8');
      expect(ctx.last.content, 't19');
    });

    test('content 는 2000자로 절단', () {
      final long = 'a' * 3000;
      final ctx = buildContext([ChatMessage(role: 'user', content: long)]);
      expect(ctx.first.content.length, maxContentLength);
    });
  });
}
