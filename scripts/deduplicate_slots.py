#!/usr/bin/env python3
"""
슬롯 파일 1건 정리 스크립트

각 public/data/times/HH_MM.json 을 슬롯당 정확히 1건으로 축소한다.

선택 우선순위:
  1. match_type == "exact" 우선
  2. 텍스트 길이 30~80자 선호 (|len - 50| 최소)
  3. 동일 작가 중복 제거 후 선택
"""
import json
import os
import re
import sys

TIMES_DIR = os.path.join(os.path.dirname(__file__), '..', 'public', 'data', 'times')
DRY_RUN = '--dry-run' in sys.argv


def extract_author(display_source: str) -> str:
    m = re.match(r'^[—\-–]\s*(.+?)[,，]', display_source or '')
    return m.group(1).strip() if m else (display_source or '').strip()


def pick_best(quotes: list) -> dict:
    exact = [q for q in quotes if q.get('match_type') == 'exact']
    pool = exact if exact else quotes
    # 작가 중복 제거: 작가별 첫 번째만 남김
    seen = set()
    deduped = []
    for q in pool:
        author = extract_author(q.get('display_source', ''))
        if author not in seen:
            seen.add(author)
            deduped.append(q)
    # 텍스트 길이 50자 기준으로 정렬
    deduped.sort(key=lambda q: abs(len(q.get('text_ko', '')) - 50))
    return deduped[0]


def main():
    stats = {'empty': 0, 'already_1': 0, 'reduced': 0}

    for h in range(24):
        for m in range(60):
            fname = f'{h:02d}_{m:02d}.json'
            fpath = os.path.join(TIMES_DIR, fname)

            with open(fpath, encoding='utf-8') as f:
                data = json.load(f)

            if len(data) == 0:
                stats['empty'] += 1
                continue

            if len(data) == 1:
                stats['already_1'] += 1
                continue

            selected = pick_best(data)
            stats['reduced'] += 1

            if not DRY_RUN:
                with open(fpath, 'w', encoding='utf-8') as f:
                    json.dump([selected], f, ensure_ascii=False, indent=2)

    mode = '[DRY-RUN] ' if DRY_RUN else ''
    print(f'{mode}처리 완료')
    print(f'  이미 1건:  {stats["already_1"]:>5}개 (변경 없음)')
    print(f'  1건으로 축소: {stats["reduced"]:>5}개')
    print(f'  빈 파일:   {stats["empty"]:>5}개 (변경 없음)')
    print(f'  합계:      {sum(stats.values()):>5}개')


if __name__ == '__main__':
    main()
