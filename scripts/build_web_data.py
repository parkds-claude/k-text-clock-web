#!/usr/bin/env python3
"""웹 배포용 경량 데이터 빌드 — public/data/quotes_web.json + public/data/authors.json"""
import json
import random
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).parent.parent
SRC = ROOT / 'data' / 'quotes_public.json'
OUT_DIR = ROOT / 'public' / 'data'

TIMESLOT_KO = {
    'midnight': '한밤',
    'dawn': '새벽',
    'morning': '아침',
    'forenoon': '오전',
    'noon': '정오',
    'afternoon': '오후',
    'evening': '저녁',
    'night': '밤',
}


def main() -> None:
    with open(SRC, encoding='utf-8') as f:
        qs = json.load(f)

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # 경량 웹 포맷 (필수 필드만, id 제외)
    web = [
        {
            'text': q.get('text_ko', ''),
            'author': (q.get('source') or {}).get('author') or '(무명)',
            'title': (q.get('source') or {}).get('title') or '',
            'minute': q.get('minute', ''),
            'timeslot': q.get('timeslot', ''),
        }
        for q in qs
        if q.get('text_ko', '').strip()
    ]

    out_web = OUT_DIR / 'quotes_web.json'
    with open(out_web, 'w', encoding='utf-8') as f:
        json.dump(web, f, ensure_ascii=False, separators=(',', ':'))
    size_kb = out_web.stat().st_size // 1024
    print(f'quotes_web.json: {len(web):,}건 ({size_kb} KB)')

    # 작가 인덱스
    by_author: dict[str, list] = defaultdict(list)
    for q in web:
        by_author[q['author']].append(q)

    authors = []
    for author, quotes in sorted(by_author.items(), key=lambda x: -len(x[1])):
        works = sorted({q['title'] for q in quotes if q['title']})[:6]
        sample_text = random.choice(quotes)['text']
        authors.append({
            'author': author,
            'count': len(quotes),
            'works': works,
            'sample': sample_text[:60] + ('…' if len(sample_text) > 60 else ''),
        })

    out_authors = OUT_DIR / 'authors.json'
    with open(out_authors, 'w', encoding='utf-8') as f:
        json.dump(authors, f, ensure_ascii=False, indent=2)
    print(f'authors.json: {len(authors):,}명')


if __name__ == '__main__':
    main()
