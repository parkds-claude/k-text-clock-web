"""
needs_review 1,394건 자동 처리 스크립트
규칙 기반으로 각 이슈 유형을 해소한다.

처리 규칙:
  OCR_ARTIFACT   → ─ 교정, 연속 공백 정리
  TOO_SHORT      → 시각 표현 있으면 유지, 없으면 제거
  TOO_LONG       → 450자 초과 시 자연 경계(. , ! ?)에서 트리밍
  NO_TIME_EXPR   → exact → timeslot 재분류 (데이터 보존)
  BLOCKED:강간    → 제거
  BLOCKED:기타    → institutional_filter: true 플래그 추가
  NO_AUTHOR      → 실록류이면 유지, 아니면 제거
  오탐(음부 등)  → review_issues 클리어 후 auto_reviewed
"""

import json, re
from collections import defaultdict

INPUT  = "data/quotes_public.json"
OUTPUT = "data/quotes_public.json"

# ── 시각 표현 (광의) ─────────────────────────────────────────
KO_NUMS = "영|한|두|세|네|다섯|여섯|일곱|여덟|아홉|열|열한|열두|일|이|삼|사|오|육|칠|팔|구|십|십일|십이"
BROAD_TIME_RE = re.compile('|'.join([
    r'\d{1,2}\s*시\s*\d{0,2}\s*분?', r'\d{1,2}:\d{2}',
    rf'(?:{KO_NUMS})\s*시',
    r'오전|오후|정오|자정|한낮|한밤|백주|새벽|여명|황혼|해거름|해질\s*녘?',
    r'밤중|밤새|야밤|심야|밤이\s*깊|깊은\s*밤|아닌\s*밤|이\s*밤',
    r'오정|오시|자시|축시|인시|묘시|진시|사시|미시|신시|유시|술시|해시',
    r'삼경|사경|오경|이경|초경',
    r'동이\s*틀|해\s*뜰\s*무렵|해\s*질\s*무렵|닭이\s*울',
    r'아침|저녁|점심',
]))

# 확정 제거 키워드
HARD_REMOVE = re.compile(r'강간')

# institutional_filter 대상
INST_FILTER = re.compile(r'겁탈|음란|목을 매|자살|투신')


def fix_ocr(text: str) -> str:
    text = text.replace('─', '—')     # BOX DRAWING → em dash
    text = re.sub(r'[ \t]{2,}', ' ', text)   # 연속 공백
    text = re.sub(r'\n{3,}', '\n\n', text)   # 연속 줄바꿈
    return text.strip()


def trim_long(text: str, limit: int = 420) -> str:
    if len(text) <= limit:
        return text
    # 자연 경계 탐색 (마침표, 느낌표, 물음표, 쉼표 순)
    for punct in ['.', '!', '?', ',', '…']:
        idx = text.rfind(punct, 0, limit)
        if idx > limit // 2:
            return text[:idx + 1].strip()
    return text[:limit].strip() + '…'


def resolve(item: dict) -> tuple[dict | None, str]:
    """
    반환값: (처리된 item 또는 None(제거), 처리 설명)
    """
    issues = item.get('review_issues', [])
    text   = item.get('text_ko', '')
    source_org = item.get('license', {}).get('source_org', '')

    # ── 확정 제거 ──────────────────────────────────────────
    if HARD_REMOVE.search(text):
        return None, 'REMOVED:강간'

    # ── OCR 교정 ──────────────────────────────────────────
    if 'OCR_ARTIFACT' in issues:
        item['text_ko'] = fix_ocr(text)
        text = item['text_ko']
        issues = [i for i in issues if i != 'OCR_ARTIFACT']

    # ── TOO_LONG 트리밍 ────────────────────────────────────
    if 'TOO_LONG' in issues:
        item['text_ko'] = trim_long(text)
        text = item['text_ko']
        issues = [i for i in issues if i != 'TOO_LONG']

    # ── TOO_SHORT 처리 ─────────────────────────────────────
    if 'TOO_SHORT' in issues:
        if BROAD_TIME_RE.search(text):
            issues = [i for i in issues if i != 'TOO_SHORT']   # 시각 표현 있으면 유지
        else:
            return None, 'REMOVED:TOO_SHORT(시각표현없음)'

    # ── NO_TIME_EXPR → timeslot 재분류 ────────────────────
    if 'NO_TIME_EXPR' in issues:
        item['match_type'] = 'timeslot'    # exact → timeslot 강등
        issues = [i for i in issues if i != 'NO_TIME_EXPR']

    # ── NO_AUTHOR 처리 ─────────────────────────────────────
    if 'NO_AUTHOR' in issues:
        if '실록' in source_org or '국사편찬' in source_org:
            issues = [i for i in issues if i != 'NO_AUTHOR']   # 실록류 — 저자 없음 허용
        else:
            return None, 'REMOVED:NO_AUTHOR'

    # ── BLOCKED 처리 ───────────────────────────────────────
    remaining_blocked = [i for i in issues if i.startswith('BLOCKED:')]
    for b in remaining_blocked:
        kw_part = b.split(':', 1)[-1]
        # 오탐 패턴 클리어 (정규식 패턴 문자열이 남아있는 것)
        if '(?<!' in kw_part or '(?!' in kw_part:
            issues = [i for i in issues if i != b]
            continue
        if INST_FILTER.search(text):
            item['institutional_filter'] = True
            issues = [i for i in issues if i != b]

    # ── 최종 상태 결정 ─────────────────────────────────────
    if issues:
        item['review_issues'] = issues
        item['review_state']  = 'needs_review'
        return item, f'STILL_PENDING:{issues}'
    else:
        item.pop('review_issues', None)
        item['review_state'] = 'auto_reviewed'
        return item, 'RESOLVED'


def main():
    with open(INPUT, encoding='utf-8') as f:
        data = json.load(f)

    total_before = len(data)
    needs = [d for d in data if d.get('review_state') == 'needs_review']
    others = [d for d in data if d.get('review_state') != 'needs_review']

    print(f"처리 대상: {len(needs)}건 (전체 {total_before}건 중)")

    results    = defaultdict(int)
    resolved   = []
    removed    = []
    still_pending = []

    for item in needs:
        processed, reason = resolve(item)
        category = reason.split(':')[0]
        results[category] += 1

        if processed is None:
            removed.append({'reason': reason, 'text': item.get('text_ko','')[:60],
                            'author': item.get('source',{}).get('author','?')})
        elif category == 'RESOLVED':
            resolved.append(processed)
        else:
            still_pending.append(processed)

    # 최종 데이터 재조합
    final_data = others + resolved + still_pending

    with open(OUTPUT, 'w', encoding='utf-8') as f:
        json.dump(final_data, f, ensure_ascii=False, indent=2)

    # ── 리포트 ─────────────────────────────────────────────
    auto_r   = sum(1 for d in final_data if d.get('review_state') == 'auto_reviewed')
    need_r   = sum(1 for d in final_data if d.get('review_state') == 'needs_review')
    reviewed = sum(1 for d in final_data if d.get('review_state') == 'reviewed')
    inst_f   = sum(1 for d in final_data if d.get('institutional_filter'))

    print(f"\n{'='*55}")
    print(f" 처리 결과")
    print(f"{'='*55}")
    print(f"  처리 전 needs_review : {len(needs):,}건")
    print(f"  → RESOLVED           : {results['RESOLVED']:,}건")
    print(f"  → REMOVED            : {len(removed):,}건")
    print(f"  → STILL_PENDING      : {len(still_pending):,}건")

    print(f"\n{'='*55}")
    print(f" 최종 데이터셋 상태 (총 {len(final_data):,}건)")
    print(f"{'='*55}")
    print(f"  reviewed      (수작업 완료)   : {reviewed:,}건")
    print(f"  auto_reviewed (자동 검수 통과): {auto_r:,}건  ({auto_r/len(final_data)*100:.1f}%)")
    print(f"  needs_review  (잔여 미결)     : {need_r:,}건  ({need_r/len(final_data)*100:.1f}%)")
    print(f"  institutional_filter (기관 필터 대상): {inst_f:,}건")

    print(f"\n{'='*55}")
    print(f" 제거된 항목 ({len(removed)}건)")
    print(f"{'='*55}")
    for r in removed:
        print(f"  [{r['author']}] {r['reason']} | {r['text']}")

    print(f"\n{'='*55}")
    print(f" 잔여 미결 ({len(still_pending)}건)")
    print(f"{'='*55}")
    for d in still_pending[:20]:
        print(f"  [{d.get('source',{}).get('author','?')}] {d.get('review_issues')} | {d.get('text_ko','')[:50]}")

    if len(still_pending) > 20:
        print(f"  ... 외 {len(still_pending)-20}건")


if __name__ == '__main__':
    main()
