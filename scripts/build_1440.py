#!/usr/bin/env python3
"""시각별 JSON 빌드 — public/data/times/HH_MM.json × 1440개"""
import json
import random
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).parent.parent
SRC = ROOT / 'data' / 'quotes_public.json'
OUT_DIR = ROOT / 'public' / 'data' / 'times'
MAX_PER_SLOT = 5

TIMESLOT_MAP = {
    'midnight':  range(0,   120),   # 00:00–01:59
    'dawn':      range(120, 300),   # 02:00–04:59
    'morning':   range(300, 420),   # 05:00–06:59
    'forenoon':  range(420, 720),   # 07:00–11:59
    'noon':      range(720, 780),   # 12:00–12:59
    'afternoon': range(780, 1020),  # 13:00–16:59
    'evening':   range(1020, 1200), # 17:00–19:59
    'night':     range(1200, 1440), # 20:00–23:59
}


def _minute_index(minute_str: str) -> int | None:
    try:
        h, m = map(int, minute_str.split(':'))
        return h * 60 + m
    except Exception:
        return None


def main() -> None:
    with open(SRC, encoding='utf-8') as f:
        qs = json.load(f)

    # 분별 exact 매핑
    exact: dict[int, list] = defaultdict(list)
    for q in qs:
        idx = _minute_index(q.get('minute', ''))
        if idx is not None and q.get('text_ko', '').strip():
            exact[idx].append(q)

    # timeslot 역매핑
    slot_for_minute: dict[int, str] = {}
    for slot, rng in TIMESLOT_MAP.items():
        for i in rng:
            slot_for_minute[i] = slot

    timeslot_pool: dict[str, list] = defaultdict(list)
    for q in qs:
        s = q.get('timeslot', '')
        if s and q.get('text_ko', '').strip():
            timeslot_pool[s].append(q)

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    exact_cnt = slot_cnt = fallback_cnt = 0
    for total_min in range(1440):
        h, m = divmod(total_min, 60)
        key = f'{h:02d}_{m:02d}'

        if total_min in exact:
            pool = exact[total_min]
            exact_cnt += 1
        elif slot_for_minute.get(total_min) in timeslot_pool:
            slot = slot_for_minute[total_min]
            pool = timeslot_pool[slot]
            slot_cnt += 1
        else:
            pool = qs
            fallback_cnt += 1

        sample = random.sample(pool, min(MAX_PER_SLOT, len(pool)))
        entries = [
            {
                'text_ko': q.get('text_ko', ''),
                'display_source': q.get('display_source', ''),
                'minute': q.get('minute', ''),
                'match_type': 'exact' if total_min in exact and q in exact[total_min] else 'timeslot',
            }
            for q in sample
        ]

        with open(OUT_DIR / f'{key}.json', 'w', encoding='utf-8') as f:
            json.dump(entries, f, ensure_ascii=False, separators=(',', ':'))

    print(f'빌드 완료: 1440개 파일 (exact {exact_cnt} / timeslot {slot_cnt} / fallback {fallback_cnt})')


if __name__ == '__main__':
    main()
