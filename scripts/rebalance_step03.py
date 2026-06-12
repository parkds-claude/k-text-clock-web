#!/usr/bin/env python3
"""
Step03 슬롯 재배정 스크립트 (전체 1,440슬롯)

알고리즘은 Step01과 동일. 파라미터만 다름:
  - 대상: 1,440슬롯 (HH_00~HH_59)
  - cap: 1440 * 3.5% ≈ 50
"""
import json, os, re, sys
from collections import defaultdict, Counter

TIMES_DIR = os.path.join(os.path.dirname(__file__), '..', 'public', 'data', 'times')
QUOTES_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'quotes_public.json')
DRY_RUN = '--dry-run' in sys.argv
AUTHOR_CAP = 50

TIMESLOT_MAP = {
    0: 'midnight', 1: 'midnight', 2: 'midnight',
    3: 'dawn', 4: 'dawn', 5: 'dawn',
    6: 'morning', 7: 'morning', 8: 'morning',
    9: 'forenoon', 10: 'forenoon', 11: 'forenoon',
    12: 'noon',
    13: 'afternoon', 14: 'afternoon', 15: 'afternoon', 16: 'afternoon',
    17: 'evening', 18: 'evening', 19: 'evening',
    20: 'night', 21: 'night', 22: 'night', 23: 'night',
}


def get_author(q: dict) -> str:
    a = (q.get('source') or {}).get('author') or ''
    if not a:
        m = re.match(r'^[—\-–]\s*(.+?)\s*[,，「]', q.get('display_source', '') or '')
        if m: a = m.group(1).strip()
    return a


def is_en(a: str) -> bool:
    return bool(re.search(r'[A-Za-z]', a))


def score(q: dict) -> float:
    return (0 if q.get('match_type') == 'exact' else 100) + abs(len(q.get('text_ko', '')) - 50)


def to_slot_entry(q: dict) -> dict:
    author = get_author(q)
    title = (q.get('source') or {}).get('title', '') or ''
    display = q.get('display_source') or (f'— {author}, 「{title}」' if author else '')
    return {'text_ko': q['text_ko'], 'display_source': display,
            'minute': q.get('minute', ''), 'match_type': q.get('match_type', 'timeslot')}


def pick_from(pool, counts, cap):
    for q in pool:
        a = get_author(q)
        if a and counts[a] < cap:
            return q
    return None


def main():
    with open(QUOTES_PATH, encoding='utf-8') as f:
        all_quotes = json.load(f)

    by_minute: dict = defaultdict(list)
    by_timeslot: dict = defaultdict(list)
    for q in all_quotes:
        a = get_author(q)
        if not a or is_en(a): continue
        if q.get('minute'): by_minute[q['minute']].append(q)
        if q.get('timeslot'): by_timeslot[q['timeslot']].append(q)
    for pool in list(by_minute.values()) + list(by_timeslot.values()):
        pool.sort(key=score)

    # 슬롯 분류
    sole, multi, no_exact = [], [], []
    for h in range(24):
        for m in range(60):
            slot_min = f'{h:02d}:{m:02d}'
            authors = {get_author(q) for q in by_minute.get(slot_min, [])} - {''}
            if len(authors) == 1:
                sole.append((h, m, list(authors)[0]))
            elif len(authors) > 1:
                multi.append((h, m))
            else:
                no_exact.append((h, m))

    counts: Counter = Counter()
    results: dict = {}

    # 1패스: 단독 exact 강제
    for h, m, forced in sole:
        slot_min = f'{h:02d}:{m:02d}'
        pool = sorted([q for q in by_minute[slot_min] if get_author(q) == forced], key=score)
        if pool:
            results[(h, m)] = pool[0]
            counts[forced] += 1

    # 2패스: 다중 exact
    for h, m in multi:
        slot_min = f'{h:02d}:{m:02d}'
        pool = sorted(by_minute[slot_min], key=lambda q: (counts[get_author(q)], score(q)))
        q = pick_from(pool, counts, AUTHOR_CAP)
        if q:
            results[(h, m)] = q
            counts[get_author(q)] += 1

    # 3패스: timeslot 폴백
    for h, m in no_exact:
        ts = TIMESLOT_MAP[h]
        pool = sorted(by_timeslot.get(ts, []), key=lambda q: (counts[get_author(q)], score(q)))
        q = pick_from(pool, counts, AUTHOR_CAP)
        if q:
            results[(h, m)] = q
            counts[get_author(q)] += 1

    # 4패스: 미배정 cap 완화
    for h in range(24):
        for m in range(60):
            if (h, m) in results: continue
            slot_min = f'{h:02d}:{m:02d}'
            ts = TIMESLOT_MAP[h]
            pool = sorted(by_minute.get(slot_min, []) or by_timeslot.get(ts, []),
                          key=lambda q: (counts[get_author(q)], score(q)))
            if pool:
                results[(h, m)] = pool[0]
                counts[get_author(pool[0])] += 1

    # ── 결과 출력
    exact_cnt = sum(1 for q in results.values() if q.get('match_type') == 'exact')
    ts_cnt = len(results) - exact_cnt
    forced_authors = {a for _, _, a in sole}
    violations = [(a, c) for a, c in counts.items()
                  if c > AUTHOR_CAP and a not in forced_authors]

    print(f'배정 완료: {len(results)}/1440개 | 미배정: {1440 - len(results)}개')
    print(f'exact match: {exact_cnt}개 ({exact_cnt/14.4:.1f}%)')
    print(f'timeslot 폴백: {ts_cnt}개 ({ts_cnt/14.4:.1f}%)')
    print(f'고유 작가: {len(counts)}명')
    if violations:
        print(f'cap({AUTHOR_CAP}) 초과: {[f"{a}={c}" for a,c in violations]}')
    else:
        print(f'cap({AUTHOR_CAP}) 초과 없음 ✅')

    print()
    print('작가별 슬롯 수 (상위 15):')
    for a, c in counts.most_common(15):
        bar = '█' * min(c, 50)
        mark = ' [단독강제]' if a in forced_authors and c > AUTHOR_CAP else ''
        print(f'  {a:<22} {c:>4}건  {bar}{mark}')

    if not DRY_RUN:
        for (h, m), q in results.items():
            fname = f'{h:02d}_{m:02d}.json'
            with open(os.path.join(TIMES_DIR, fname), 'w', encoding='utf-8') as f:
                json.dump([to_slot_entry(q)], f, ensure_ascii=False, indent=2)
        print(f'\n파일 저장 완료: {len(results)}개')
    else:
        print('\n[DRY-RUN] 파일 저장 생략')


if __name__ == '__main__':
    main()
