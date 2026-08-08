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

  // Story 16.5 — clarify/narrowed_by 파싱(web isValidClarify/isValidNarrowedBy 미러).
  group('parseClarifyPayload', () {
    test('정상 {question, chips} 파싱', () {
      final c = parseClarifyPayload({
        'question': '어떤 용도로 찾으세요?',
        'chips': ['3천만원 이하', 'SUV', '전기차'],
      });
      expect(c, isNotNull);
      expect(c!.question, '어떤 용도로 찾으세요?');
      expect(c.chips, ['3천만원 이하', 'SUV', '전기차']);
    });

    test('chips 가 빈 배열이어도 유효(칩 없음은 렌더 쪽에서 판단)', () {
      final c = parseClarifyPayload({'question': 'q', 'chips': []});
      expect(c, isNotNull);
      expect(c!.chips, isEmpty);
    });

    test('Map 이 아니면 null', () {
      expect(parseClarifyPayload('문자열'), isNull);
      expect(parseClarifyPayload(null), isNull);
    });

    test('question 이 문자열이 아니면 null', () {
      expect(parseClarifyPayload({'question': 123, 'chips': []}), isNull);
    });

    test('chips 가 배열이 아니면 null', () {
      expect(parseClarifyPayload({'question': 'q', 'chips': '아니오'}), isNull);
    });

    test('chips 원소 중 하나라도 문자열이 아니면 전체 null', () {
      expect(
        parseClarifyPayload({
          'question': 'q',
          'chips': ['ok', 123],
        }),
        isNull,
      );
    });

    // 코드리뷰 지적 — 이 규칙(공백뿐인 칩 폐기)은 앱 전용이고(웹 isValidClarify 에는 없다)
    // 어떤 테스트도 지나가지 않아, 지워도 전 스위트가 green 이었다(변이 실측).
    // 빈 라벨 칩이 그려지면 눌러도 _submit 이 조용히 return 하는 "죽은 칩"이 된다.
    test('chips 원소가 빈 문자열이면 전체 null', () {
      expect(parseClarifyPayload({'question': 'q', 'chips': ['']}), isNull);
    });

    test('chips 원소가 공백뿐이면 전체 null', () {
      expect(
        parseClarifyPayload({
          'question': 'q',
          'chips': ['SUV', '   '],
        }),
        isNull,
      );
    });
  });

  group('parseNarrowedBy', () {
    test('정상 문자열 배열 파싱', () {
      final n = parseNarrowedBy(['price<=30000000', 'body_type=SUV', 'fuel=전기']);
      expect(n, ['price<=30000000', 'body_type=SUV', 'fuel=전기']);
    });

    test('빈 배열은 null(채워진 값이 아님, 서버 계약상 항상 고정 3개)', () {
      expect(parseNarrowedBy(<Object?>[]), isNull);
    });

    test('배열이 아니면 null', () {
      expect(parseNarrowedBy('문자열'), isNull);
      expect(parseNarrowedBy(null), isNull);
    });

    test('원소 중 하나라도 문자열이 아니면 전체 null', () {
      expect(parseNarrowedBy(['ok', 123]), isNull);
    });
  });

  group('parseSearchResult — clarify/narrowed_by 통합(I/O 매트릭스)', () {
    test('되묻기 응답: clarify 채워지고 narrowed_by 는 null', () {
      final r = parseSearchResult({
        'answer': '어떤 용도로 찾으세요?',
        'listings': [],
        'clarify': {
          'question': '어떤 용도로 찾으세요?',
          'chips': ['3천만원 이하', 'SUV', '전기차'],
        },
        'narrowed_by': null,
      });
      expect(r.clarify, isNotNull);
      expect(r.clarify!.chips, ['3천만원 이하', 'SUV', '전기차']);
      expect(r.narrowedBy, isNull);
    });

    test('거절 응답: narrowed_by 채워지고 clarify 는 null', () {
      final r = parseSearchResult({
        'answer': '매물 조건과 무관한 질문이에요.',
        'listings': [],
        'clarify': null,
        'narrowed_by': ['price<=30000000', 'body_type=SUV', 'fuel=전기'],
      });
      expect(r.clarify, isNull);
      expect(r.narrowedBy, ['price<=30000000', 'body_type=SUV', 'fuel=전기']);
    });

    test('구조형/하이브리드 응답: 둘 다 null, 기존 파싱 영향 없음', () {
      final r = parseSearchResult({
        'answer': '조건에 맞는 매물 1건입니다.',
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
        'clarify': null,
        'narrowed_by': null,
      });
      expect(r.clarify, isNull);
      expect(r.narrowedBy, isNull);
      expect(r.listings.length, 1);
    });

    test('되묻기 상한 초과 강제 폴백: clarify 없이 listings 로 렌더(칩 없음)', () {
      final r = parseSearchResult({
        'answer': '조건에 맞는 매물을 찾았어요.',
        'listings': [
          {
            'id': 'a',
            'manufacturer': '기아',
            'model': 'K5',
            'year': 2019,
            'price': 20000000,
            'mileage': 40000,
            'region': '경기',
          },
        ],
      });
      expect(r.clarify, isNull);
      expect(r.listings.length, 1);
    });

    test('clarify 필드 형태가 깨지면 null 로 폴백하고 answer/listings 파싱은 계속된다', () {
      final r = parseSearchResult({
        'answer': '조건에 맞는 매물 1건입니다.',
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
        'clarify': '문자열', // 형태 불량
      });
      expect(r.clarify, isNull);
      expect(r.answer, contains('1건'));
      expect(r.listings.length, 1);
    });

    test('narrowed_by 가 형태 불량(문자열)이면 null 로 폴백', () {
      final r = parseSearchResult({'answer': 'x', 'listings': [], 'narrowed_by': 'oops'});
      expect(r.narrowedBy, isNull);
    });
  });
}
