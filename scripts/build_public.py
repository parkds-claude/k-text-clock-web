#!/usr/bin/env python3
"""G1+G2 안전 공개 데이터 추출 — 저작권 위험 제거 후 data/quotes_public.json 생성"""
import json
from pathlib import Path

ROOT = Path(__file__).parent.parent
MASTER = ROOT.parent / 'k-text-clock' / 'data' / 'quotes.json'
DEST = ROOT / 'data' / 'quotes_public.json'

BLOCKED_AUTHORS = frozenset({
    '최남선', '박인환', '이무영', '노천명', '권구현', '계용묵', '변영로', '황석우'
})
LITCLOCK_PATTERNS = ('JohannesNE/literature-clock', 'litclock', 'literature-clock')


def _is_litclock(q: dict) -> bool:
    lic = q.get('license', {})
    src_org = str(lic.get('source_org', ''))
    basis = str(lic.get('basis', ''))
    return (any(p in src_org for p in LITCLOCK_PATTERNS)
            or 'CC BY-NC-SA' in basis)


def _is_blocked(q: dict) -> bool:
    author = str((q.get('source') or {}).get('author') or '')
    return author in BLOCKED_AUTHORS


def is_safe_public(q: dict) -> bool:
    if q.get('tier') not in (0, 1):
        return False
    if q.get('license', {}).get('release_blocker') is True:
        return False
    if _is_litclock(q):
        return False
    if _is_blocked(q):
        return False
    return True


def main() -> None:
    with open(MASTER, encoding='utf-8') as f:
        qs = json.load(f)

    safe = [q for q in qs if is_safe_public(q)]
    print(f'추출: {len(safe):,}건 / 전체 {len(qs):,}건')

    DEST.parent.mkdir(parents=True, exist_ok=True)
    with open(DEST, 'w', encoding='utf-8') as f:
        json.dump(safe, f, ensure_ascii=False, indent=2)
    print(f'저장: {DEST}')


if __name__ == '__main__':
    main()
