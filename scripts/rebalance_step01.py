#!/usr/bin/env python3
"""
Step01 슬롯 재배정 스크립트

배정 순서:
  1. 단독 작가 슬롯 강제 배정 (해당 작가만 exact match 있음)
  2. 다중 작가 슬롯 → cap 준수하며 최적 선택
  3. exact 없는 슬롯 → timeslot 풀에서 cap 준수 선택
  4. 미배정 슬롯 → cap 완화하여 최선 선택 (마지막 수단)

영어권 작가(라틴 문자 포함) 제외. 작가당 AUTHOR_CAP 슬롯 상한.
"""
import json, os, re, sys
from collections import defaultdict, Counter

TIMES_DIR = os.path.join(os.path.dirname(__file__), '..', 'public', 'data', 'times')
QUOTES_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'quotes_public.json')
DRY_RUN = '--dry-run' in sys.argv
AUTHOR_CAP = 5


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
        m = re.match(r'^[—\-–]\s*(.+?)(\s*「|\s*$)', ds or '')
        if m:
            a = m.group(1).strip()
    return a


def is_en(author: str) -> bool:
    return bool(re.search(r'[A-Za-z]', author))


def score(q: dict) -> float:
    match_penalty = 0 if q.get('match_type') == 'exact' else 100
    len_penalty = abs(len(q.get('text_ko', '')) - 50)
    return match_penalty + len_penalty


def clean_title(raw: str, author: str = '') -> str:
    """'OT-강경애-동정-청년조선' → '동정' (작품명만 추출)"""
    import re as _re
    if _re.match(r'^[A-Za-z]{1,3}-', raw or ''):
        parts = raw.split('-')
        # 영문 prefix, 숫자, 작가명 건너뜀 → 첫 번째 한국어 비작가 파트가 작품명
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
    with open(QUOTES_PATH, encoding='utf-8') as f:
        all_quotes = json.load(f)

    # 한국 작가 문장 인덱스 구축
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

    # Step01 슬롯 분류
    sole: list[tuple] = []    # (h, m, author) — 유일 exact 작가
    multi: list[tuple] = []   # (h, m) — 복수 exact 작가
    no_exact: list[tuple] = [] # (h, m) — exact 없음

    for h in range(24):
        for m in range(0, 60, 10):
            slot_min = f'{h:02d}:{m:02d}'
            authors = {get_author(q) for q in by_minute.get(slot_min, [])}
            authors.discard('')
            if len(authors) == 1:
                sole.append((h, m, list(authors)[0]))
            elif len(authors) > 1:
                multi.append((h, m))
            else:
                no_exact.append((h, m))

    author_counts: Counter = Counter()
    results: dict[tuple, dict] = {}

    # ── 1패스: 단독 exact 슬롯 강제 배정 (cap 무관)
    for h, m, forced_author in sole:
        slot_min = f'{h:02d}:{m:02d}'
        candidates = [q for q in by_minute[slot_min] if get_author(q) == forced_author]
        candidates.sort(key=score)
        if candidates:
            results[(h, m)] = candidates[0]
            author_counts[forced_author] += 1

    # ── 2패스: 복수 exact 슬롯 — cap 준수하며 최적 선택
    for h, m in multi:
        slot_min = f'{h:02d}:{m:02d}'
        pool = [q for q in by_minute[slot_min]]
        pool.sort(key=lambda q: (author_counts[get_author(q)], score(q)))
        q = pick_from(pool, author_counts, AUTHOR_CAP)
        if q:
            results[(h, m)] = q
            author_counts[get_author(q)] += 1

    # ── 3패스: timeslot 폴백 슬롯
    for h, m in no_exact:
        ts = TIMESLOT_MAP[h]
        pool = by_timeslot.get(ts, [])
        # 현재 배정 수 적은 작가 우선
        sorted_pool = sorted(pool, key=lambda q: (author_counts[get_author(q)], score(q)))
        q = pick_from(sorted_pool, author_counts, AUTHOR_CAP)
        if q:
            results[(h, m)] = q
            author_counts[get_author(q)] += 1

    # ── 4패스: 미배정 슬롯 cap 완화하여 채우기
    unassigned = [(h, m) for h in range(24) for m in range(0, 60, 10)
                  if (h, m) not in results]
    for h, m in unassigned:
        slot_min = f'{h:02d}:{m:02d}'
        ts = TIMESLOT_MAP[h]
        pool = by_minute.get(slot_min) or by_timeslot.get(ts, [])
        pool = sorted(pool, key=lambda q: (author_counts[get_author(q)], score(q)))
        if pool:
            q = pool[0]  # 상한 완화
            results[(h, m)] = q
            author_counts[get_author(q)] += 1

    # ── 결과 출력
    print(f'배정 완료: {len(results)}개 / 미배정: {144 - len(results)}개')
    print(f'고유 작가 수: {len(author_counts)}명')

    forced_authors = {a for _, _, a in sole}
    violations = [(a, c) for a, c in author_counts.items()
                  if c > AUTHOR_CAP and a not in forced_authors]
    forced_over = [(a, c) for a, c in author_counts.items()
                   if c > AUTHOR_CAP and a in forced_authors]

    if forced_over:
        print(f'단독슬롯 강제 초과 (불가피): {[f"{a}={c}" for a,c in forced_over]}')
    if violations:
        print(f'cap 초과 (개선 필요): {[f"{a}={c}" for a,c in violations]}')
    else:
        print(f'cap({AUTHOR_CAP}) 초과 없음 ✅ (단독슬롯 강제 제외)')

    print()
    print('작가별 슬롯 수 (상위 20):')
    for author, cnt in author_counts.most_common(20):
        bar = '█' * cnt
        forced_mark = ' [단독강제]' if author in forced_authors and cnt > AUTHOR_CAP else ''
        print(f'  {author:<22} {cnt:>3}건  {bar}{forced_mark}')

    print()
    print('변경되는 슬롯:')
    changed = 0
    for h in range(24):
        for m in range(0, 60, 10):
            fname = f'{h:02d}_{m:02d}.json'
            with open(os.path.join(TIMES_DIR, fname)) as f:
                old = json.load(f)[0]
            new_q = results.get((h, m))
            if not new_q:
                print(f'  {h:02d}:{m:02d}  ⚠ 미배정')
                continue
            old_ds = old.get('display_source', '')
            new_ds = new_q.get('display_source', '')
            if old_ds != new_ds:
                old_a = re.match(r'^[—\-–]\s*(.+?)[,，「\s]', old_ds or '')
                old_a = old_a.group(1).strip() if old_a else '?'
                print(f'  {h:02d}:{m:02d}  {old_a:<22} → {get_author(new_q)}')
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
