#!/usr/bin/env python3
"""
Step02 슬롯 재배정 스크립트 (HH_05, HH_15, HH_25, HH_35, HH_45, HH_55)

Step01(HH_X0)은 고정, Step02 신규 144슬롯만 재배정.
작가 상한(AUTHOR_CAP_TOTAL)은 288슬롯 전체 기준으로 적용.
Step01의 작가 카운트를 기준점으로 사용해 잔여 쿼터 계산.
"""
import json, os, re, sys
from collections import defaultdict, Counter

TIMES_DIR = os.path.join(os.path.dirname(__file__), '..', 'public', 'data', 'times')
QUOTES_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'quotes_public.json')
DRY_RUN = '--dry-run' in sys.argv

# 288슬롯 기준 cap (Step01 cap=5/144 = 3.5% → 288*3.5% ≈ 10)
AUTHOR_CAP_TOTAL = 10

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
        ds = q.get('display_source', '')
        m = re.match(r'^[—\-–]\s*(.+?)\s*[,，「]', ds or '')
        if m:
            a = m.group(1).strip()
    return a


def get_author_from_display(ds: str) -> str:
    m = re.match(r'^[—\-–]\s*(.+?)\s*[,，「]', ds or '')
    return m.group(1).strip() if m else ''


def is_en(author: str) -> bool:
    return bool(re.search(r'[A-Za-z]', author))


def score(q: dict) -> float:
    match_penalty = 0 if q.get('match_type') == 'exact' else 100
    len_penalty = abs(len(q.get('text_ko', '')) - 50)
    return match_penalty + len_penalty


def clean_title(raw: str, author: str = '') -> str:
    import re as _re
    if _re.match(r'^[A-Za-z]{1,3}-', raw or ''):
        parts = raw.split('-')
        skip = {author} if author else set()
        ko_parts = [p for p in parts[1:] if p
                    and not _re.match(r'^\d+$', p)
                    and not _re.match(r'^[A-Za-z]', p)
                    and p not in skip]
        return ko_parts[0] if ko_parts else raw
    return raw


def to_slot_entry(q: dict) -> dict:
    author = get_author(q)
    raw_title = (q.get('source') or {}).get('title', '') or ''
    title = clean_title(raw_title, author)
    display = q.get('display_source') or (f'— {author}, 「{title}」' if author else '')
    return {
        'text_ko': q['text_ko'],
        'display_source': display,
        'minute': q.get('minute', ''),
        'match_type': q.get('match_type', 'timeslot'),
    }


def pick_from(pool: list, author_counts: Counter, cap: int) -> dict | None:
    for q in pool:
        author = get_author(q)
        if author and author_counts[author] < cap:
            return q
    return None


def main():
    # ── Step01 작가 카운트 로드 (기준점)
    step01_counts: Counter = Counter()
    for h in range(24):
        for m in range(0, 60, 10):
            with open(os.path.join(TIMES_DIR, f'{h:02d}_{m:02d}.json')) as f:
                q = json.load(f)[0]
            author = get_author_from_display(q.get('display_source', ''))
            if author:
                step01_counts[author] += 1

    print(f'Step01 기준 작가 수: {len(step01_counts)}명')
    print(f'Step02 cap_total: {AUTHOR_CAP_TOTAL} (288슬롯 기준)')
    print(f'Step02 신규 슬롯별 여유 쿼터 = cap_total - step01_count')
    print()

    # ── quotes_public.json 한국 작가 인덱스
    with open(QUOTES_PATH, encoding='utf-8') as f:
        all_quotes = json.load(f)

    by_minute: dict[str, list] = defaultdict(list)
    by_timeslot: dict[str, list] = defaultdict(list)
    for q in all_quotes:
        author = get_author(q)
        if not author or is_en(author):
            continue
        if q.get('minute'):
            by_minute[q['minute']].append(q)
        if q.get('timeslot'):
            by_timeslot[q['timeslot']].append(q)

    for pool in list(by_minute.values()) + list(by_timeslot.values()):
        pool.sort(key=score)

    # ── Step02 신규 슬롯 분류 (HH_05,15,25,35,45,55)
    step02_slots = [(h, m) for h in range(24) for m in range(5, 60, 10)]

    sole: list[tuple] = []
    multi: list[tuple] = []
    no_exact: list[tuple] = []

    for h, m in step02_slots:
        slot_min = f'{h:02d}:{m:02d}'
        authors = {get_author(q) for q in by_minute.get(slot_min, [])}
        authors.discard('')
        if len(authors) == 1:
            sole.append((h, m, list(authors)[0]))
        elif len(authors) > 1:
            multi.append((h, m))
        else:
            no_exact.append((h, m))

    print(f'슬롯 분류: 단독exact={len(sole)}, 다중exact={len(multi)}, timeslot폴백={len(no_exact)}')

    # Step01 카운트를 초기값으로 사용
    author_counts = Counter(step01_counts)
    results: dict[tuple, dict] = {}

    # 1패스: 단독 exact 강제 배정
    for h, m, forced_author in sole:
        slot_min = f'{h:02d}:{m:02d}'
        candidates = [q for q in by_minute[slot_min] if get_author(q) == forced_author]
        candidates.sort(key=score)
        if candidates:
            results[(h, m)] = candidates[0]
            author_counts[forced_author] += 1

    # 2패스: 다중 exact — 현재 카운트 낮은 작가 우선
    for h, m in multi:
        slot_min = f'{h:02d}:{m:02d}'
        pool = sorted(by_minute[slot_min],
                      key=lambda q: (author_counts[get_author(q)], score(q)))
        q = pick_from(pool, author_counts, AUTHOR_CAP_TOTAL)
        if q:
            results[(h, m)] = q
            author_counts[get_author(q)] += 1

    # 3패스: timeslot 폴백
    for h, m in no_exact:
        ts = TIMESLOT_MAP[h]
        pool = sorted(by_timeslot.get(ts, []),
                      key=lambda q: (author_counts[get_author(q)], score(q)))
        q = pick_from(pool, author_counts, AUTHOR_CAP_TOTAL)
        if q:
            results[(h, m)] = q
            author_counts[get_author(q)] += 1

    # 4패스: 미배정 cap 완화
    unassigned = [(h, m) for h, m in step02_slots if (h, m) not in results]
    for h, m in unassigned:
        slot_min = f'{h:02d}:{m:02d}'
        ts = TIMESLOT_MAP[h]
        pool = sorted(
            by_minute.get(slot_min, []) or by_timeslot.get(ts, []),
            key=lambda q: (author_counts[get_author(q)], score(q))
        )
        if pool:
            q = pool[0]
            results[(h, m)] = q
            author_counts[get_author(q)] += 1

    # ── 결과 출력
    step02_only = Counter(get_author(q) for q in results.values())
    combined = Counter(step01_counts) + step02_only

    print(f'\n배정 완료: {len(results)}/144개')
    print(f'미배정: {144 - len(results)}개')

    forced_authors = {a for _, _, a in sole}
    violations = [(a, c) for a, c in combined.items()
                  if c > AUTHOR_CAP_TOTAL and a not in forced_authors]
    forced_over = [(a, c) for a, c in combined.items()
                   if c > AUTHOR_CAP_TOTAL and a in forced_authors]

    if forced_over:
        print(f'단독슬롯 강제 초과: {[f"{a}={c}" for a, c in forced_over]}')
    if violations:
        print(f'cap 초과: {[f"{a}={c}" for a, c in violations]}')
    else:
        print(f'cap({AUTHOR_CAP_TOTAL}) 초과 없음 ✅')

    print()
    print('288슬롯 전체 작가 분포 (Step01+Step02, 상위 20):')
    for author, cnt in combined.most_common(20):
        s1 = step01_counts[author]
        s2 = step02_only[author]
        bar = '█' * cnt
        mark = ' [강제]' if author in forced_authors and cnt > AUTHOR_CAP_TOTAL else ''
        print(f'  {author:<22} 합계{cnt:>3}건 (S1={s1}+S2={s2})  {bar}{mark}')

    # ── 변경 내역
    print('\n변경되는 슬롯 (이전→신규):')
    changed = 0
    for h, m in step02_slots:
        fname = f'{h:02d}_{m:02d}.json'
        with open(os.path.join(TIMES_DIR, fname)) as f:
            old = json.load(f)[0]
        new_q = results.get((h, m))
        if not new_q:
            print(f'  {h:02d}:{m:02d} ⚠ 미배정')
            continue
        old_a = get_author_from_display(old.get('display_source', '')) or '(빈값)'
        new_a = get_author(new_q)
        if old_a != new_a:
            print(f'  {h:02d}:{m:02d}  {old_a:<22} → {new_a}')
            changed += 1
    print(f'총 교체: {changed}개')

    if not DRY_RUN:
        for (h, m), q in results.items():
            fname = f'{h:02d}_{m:02d}.json'
            fpath = os.path.join(TIMES_DIR, fname)
            with open(fpath, 'w', encoding='utf-8') as f:
                json.dump([to_slot_entry(q)], f, ensure_ascii=False, indent=2)
        print(f'\n파일 저장 완료: {len(results)}개')
    else:
        print('\n[DRY-RUN] 파일 저장 생략')


if __name__ == '__main__':
    main()
