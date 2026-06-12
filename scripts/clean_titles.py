#!/usr/bin/env python3
"""슬러그형 작품명 전수 정제.

원본 수집 시 ID 형식("OT-작가-작품명-게재지")이 source.title에 그대로 들어간
항목을 정제한다:
  1. 접두 제거: OT- / NT- / 숫자- / 작가명- / 작가 본명·이명-
  2. 말미 게재지(신문·잡지) 제거 — 화이트리스트 일치 시에만
  3. 언더스코어 → 공백
' - '(공백 하이픈)는 정식 부제 구분이므로 건드리지 않는다.
title이 바뀐 항목은 display_source도 표준형("— 작가, 「작품」")으로 재생성하고,
슬롯 파일(public/data/times/)에 text_ko 매칭으로 전파한다.
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# 작가 본명/이명/오기 → 필명 (첫 세그먼트가 이 목록이면 접두로 보고 제거)
ALIASES = {
    '최학송': '최서해', '김해경': '이상', '심대섭': '심훈',
    '김윤식': '김영랑', '김시창': '김사량', '김사랑': '김사량',
    '이원록': '이육사', '김정식': '김소월', '나경손': '나도향',
}

# 말미 세그먼트가 이 목록이면 게재지로 보고 제거 (편명·권차는 작품 정보라 유지)
MAGAZINES = {
    '조선일보', '매일신보', '동아일보', '중외일보', '약업신문',
    '어린이', '별건곤', '문장', '조광', '여성', '신동아', '인문평론',
    '백민', '소년', '혜성', '조선문단', '제일선', '창조', '시와소설',
    '개벽', '개벽속간', '신천지', '신가정', '야담', '신인문학',
    '조선문학', '삼천리', '삼천리문학', '농업조선', '문예공론',
    '시원', '신여성', '동광', '사해공론', '박문', '신민', '폐허이후',
    '백조', '월간매신', '청년조선', '범우사', '해방',
    # 2차 보강 (한자 표기·추가 게재지·출판사)
    '시대일보', '대한매일신보', '영대', '개조', '중앙', '신소설',
    '문예시대', '춘추', '春秋', '신문학', '신생', '신시대', '불교',
    '민성', '문예춘추', '신생활', '청색지', '신조선', '新朝鮮', '학풍',
    '태양신문', '文章', '광학서포', '평화일보', '여명', '개벽開闢',
    '호수신간', '人文評論', '문예운동', '여시', '대조', '청춘', '배재',
    '개벽18호', '학생', '신사회', '학지광', '조선지광', '시와시론',
    '批判', '朝鮮日報', '조선', '조선의 건축',
}


def clean_title(title: str, author: str) -> str:
    t = (title or '').strip()
    if '-' not in t or ' - ' in t or ' ― ' in t:
        return t.replace('_', ' ')

    # 1) 접두 제거 (반복 적용: OT-67-작가-제목 같은 중첩)
    changed = True
    while changed and '-' in t:
        changed = False
        for pat in (r'^(OT|NT)-', r'^\d+-'):
            new = re.sub(pat, '', t)
            if new != t:
                t, changed = new, True
        head = t.split('-')[0]
        if head == author or ALIASES.get(head) == author:
            t = t[len(head) + 1:]
            changed = True

    # 2) 말미 게재지·연재 회차 번호·빈 세그먼트 제거
    parts = t.split('-')
    while len(parts) >= 2 and (
            parts[-1].strip() in MAGAZINES
            or re.fullmatch(r'\d+', parts[-1].strip())
            or not parts[-1].strip()):
        parts = parts[:-1]
    t = '-'.join(parts)

    return t.replace('_', ' ').strip()


def main() -> int:
    qp = ROOT / 'data' / 'quotes_public.json'
    qs = json.loads(qp.read_text(encoding='utf-8'))

    changed = 0
    new_display = {}  # text_ko → 새 display_source (슬롯 전파용)
    for q in qs:
        s = q.get('source') or {}
        old = s.get('title') or ''
        author = s.get('author') or ''
        new = clean_title(old, author)
        # 작가명만 남고 제목이 사라진 경우(원천 데이터에 제목 자체가 없음):
        # 잘못된 게재지명을 제목으로 쓰지 않고 작가만 표기한다.
        if not new and old.strip():
            print(f"  [제목 미상 → 작가만 표기] {old!r}")
        if new != old:
            s['title'] = new
            ds = f"— {author}, 「{new}」" if new else f"— {author}"
            q['display_source'] = ds
            new_display[(q.get('text_ko') or '').strip()] = ds
            changed += 1
    qp.write_text(json.dumps(qs, ensure_ascii=False, indent=1), encoding='utf-8')
    print(f"원본 정제: {changed}건 / {len(qs)}건")

    # 슬롯 파일 전파
    slot_changed = 0
    for f in sorted((ROOT / 'public' / 'data' / 'times').glob('*.json')):
        entries = json.loads(f.read_text(encoding='utf-8'))
        dirty = False
        for e in entries:
            ds = new_display.get((e.get('text_ko') or '').strip())
            if ds and e.get('display_source') != ds:
                e['display_source'] = ds
                dirty = True
                slot_changed += 1
        if dirty:
            f.write_text(json.dumps(entries, ensure_ascii=False, indent=2) + '\n',
                         encoding='utf-8')
    print(f"슬롯 전파: {slot_changed}건")
    return 0


if __name__ == '__main__':
    sys.exit(main())
