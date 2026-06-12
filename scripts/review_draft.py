"""
draft 항목 자동 검수 스크립트 v2
- AI 번역 38건 제거
- 한국어 시각 표현 완전 패턴 탐지
- BLOCKED 키워드 맥락 인식 (동사형 오탐 제거)
- review_state: auto_reviewed / needs_review / reviewed
"""

import json, re
from collections import defaultdict

INPUT        = "data/quotes_public.json"
OUTPUT       = "data/quotes_public.json"
REVIEW_OUT   = "data/needs_review.json"

# ── 한국어 시각 표현 완전 패턴 ────────────────────────────────
KO_HOUR_WORDS = (
    "영|한|두|세|네|다섯|여섯|일곱|여덟|아홉|열|열한|열두"
    "|일|이|삼|사|오|육|칠|팔|구|십|십일|십이"
)
TIME_PATTERNS = [
    # 숫자 시각
    r'\d{1,2}\s*시\s*\d{0,2}\s*분?',
    r'\d{1,2}:\d{2}',
    # 한글 숫자 시각
    rf'(?:{KO_HOUR_WORDS})\s*시(?:\s*(?:\d{{1,2}}|삼십|사십|이십|십)\s*분)?',
    # 시각 고유명사 (확장)
    r'오전|오후|정오|자정|한낮|한밤|백주|새벽|여명|황혼|해거름|해질\s*녘?',
    r'밤중|밤새|밤사이|야밤|심야|한밤중|한밤|밤이\s*깊|깊은\s*밤',
    r'오정|오시|자시|축시|인시|묘시|진시|사시|미시|신시|유시|술시|해시',
    r'삼경|사경|오경|이경|초경',                 # 경(更) 시간법
    r'동이\s*틀|해\s*뜰\s*무렵|해\s*질\s*무렵|닭이\s*울',
    r'\d{1,2}\s*시간\s*(?:후|전|만에)',
]
TIME_RE = re.compile('|'.join(TIME_PATTERNS))

# 시각 표현처럼 보이지만 아닌 것들 (false time words)
FAKE_TIME_WORDS = re.compile(
    r'한시바삐|한시라도|한시도|한시간도|한 시절|한 시각|한시적|한시도\s'
    r'|시절|시흥|시방|시내|시골|시위|시장|시청|시험|시인|시편'
)

# ── 부적절 키워드 (맥락 인식) ────────────────────────────────
# (패턴, 제외 맥락 정규식)  → 제외 맥락과 매칭되면 오탐으로 처리
BLOCKED_PAIRS = [
    # 복합어 내 오탐 제거: 유성기·확성기·전보지 등
    # 앞뒤에 한글이 붙어 있으면 복합어로 판단해 제외
    (re.compile(r'(?<![가-힣])성기(?![가-힣])'), None),   # '성기' 단독 (유성기/확성기 제외)
    (re.compile(r'(?<![가-힣])보지(?![가-힣])'), re.compile(r'(?<![가-힣])보지\s*(못|않|마|말|도)')),
    (re.compile(r'(?<![가-힣])자지(?![가-힣])'), re.compile(r'자지러|자지\s*(않|못|도|말|마)')),
    (re.compile(r'강간'), None),
    (re.compile(r'윤간'), None),
    (re.compile(r'능욕'), None),
    (re.compile(r'겁탈'), None),
    (re.compile(r'음란'), None),
    (re.compile(r'외설'), None),
    (re.compile(r'(?<![유확])음부'), None),               # '음부' 단독 (유음부 등 제외)
    (re.compile(r'목을 매'), None),
    (re.compile(r'투신'), None),
    (re.compile(r'자살'), None),
]

# ── OCR 아티팩트 ──────────────────────────────────────────────
OCR_RE = re.compile(
    r'[■□▲▶◆●★☆※◇○△▽▼◀◈]'           # 특수 도형 문자
    r'|(.)\1{5,}'                           # 6회 이상 동일 문자 반복
    r'|\s{3,}'                              # 3칸 이상 연속 공백
    r'|[가-힣]{1}[a-zA-Z]{3,}[가-힣]{1}'    # 한글 사이에 영문 덩어리
)


def has_time_expr(text: str) -> bool:
    """실제 시각 표현이 있는지 판단"""
    if TIME_RE.search(text):
        # fake time words만 매칭됐는지 확인
        matches = list(TIME_RE.finditer(text))
        for m in matches:
            snippet = text[max(0, m.start()-2):m.end()+2]
            if not FAKE_TIME_WORDS.search(snippet):
                return True
    return False


def check_blocked(text: str):
    """부적절 키워드 탐지 (오탐 제외)"""
    for blocked_re, exclude_re in BLOCKED_PAIRS:
        if blocked_re.search(text):
            if exclude_re and exclude_re.search(text):
                continue   # 오탐 — 동사형
            return blocked_re.pattern
    return None


def check_quality(item):
    issues = []
    text       = item.get("text_ko", "")
    match_type = item.get("match_type", "")
    minute     = item.get("minute")
    author     = item.get("source", {}).get("author", "")

    # 1. 길이
    if len(text) < 15:
        issues.append("TOO_SHORT")
    if len(text) > 450:
        issues.append("TOO_LONG")

    # 2. OCR 아티팩트
    if OCR_RE.search(text):
        issues.append("OCR_ARTIFACT")

    # 3. exact 매칭에 시각 표현 없음
    if match_type == "exact" and minute:
        if not has_time_expr(text):
            issues.append("NO_TIME_EXPR")

    # 4. 부적절 키워드 (오탐 제거 후)
    blocked = check_blocked(text)
    if blocked:
        issues.append(f"BLOCKED:{blocked}")

    # 5. 작가명 누락 (실록류 제외)
    if not author or author.strip() == "":
        source_org = item.get("license", {}).get("source_org", "")
        if "실록" not in source_org and "국사편찬" not in source_org:
            issues.append("NO_AUTHOR")

    return issues


def main():
    with open(INPUT, encoding="utf-8") as f:
        data = json.load(f)
    print(f"원본 총: {len(data)}건")

    # Step 1: AI 번역 제거
    before = len(data)
    data = [d for d in data if d.get("license", {}).get("status") != "translated_from_PD"]
    print(f"AI 번역 제거: {before - len(data)}건 → 잔여 {len(data)}건")

    # Step 2: 검수
    issue_counter = defaultdict(int)
    issue_items   = []

    for item in data:
        if item.get("review_state") == "reviewed":
            continue

        issues = check_quality(item)

        if issues:
            item["review_state"]  = "needs_review"
            item["review_issues"] = issues
            issue_items.append(item)
            for iss in issues:
                issue_counter[iss] += 1
        else:
            item["review_state"] = "auto_reviewed"
            item.pop("review_issues", None)

    # Step 3: 저장
    with open(OUTPUT, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    with open(REVIEW_OUT, "w", encoding="utf-8") as f:
        json.dump(issue_items, f, ensure_ascii=False, indent=2)

    # Step 4: 리포트
    auto_reviewed = sum(1 for d in data if d.get("review_state") == "auto_reviewed")
    needs_review  = sum(1 for d in data if d.get("review_state") == "needs_review")
    reviewed      = sum(1 for d in data if d.get("review_state") == "reviewed")
    total = len(data)

    print(f"\n{'='*50}")
    print(f" 검수 결과 (총 {total:,}건)")
    print(f"{'='*50}")
    print(f"  ✅ reviewed      (수작업 완료)     : {reviewed:,}건")
    print(f"  ✅ auto_reviewed (자동 검수 통과)   : {auto_reviewed:,}건  ({auto_reviewed/total*100:.1f}%)")
    print(f"  ⚠️  needs_review  (수작업 필요)     : {needs_review:,}건  ({needs_review/total*100:.1f}%)")

    print(f"\n{'='*50}")
    print(f" 이슈 유형별")
    print(f"{'='*50}")
    for iss, cnt in sorted(issue_counter.items(), key=lambda x: -x[1]):
        print(f"  {iss:35s}: {cnt:,}건")

    # 유형별 샘플 출력
    print(f"\n{'='*50}")
    print(f" 주요 이슈 샘플")
    print(f"{'='*50}")

    for target_iss in ["BLOCKED:강간", "BLOCKED:음란", "BLOCKED:음부", "BLOCKED:성기",
                        "BLOCKED:목을 매", "BLOCKED:자살", "BLOCKED:투신",
                        "BLOCKED:보지", "BLOCKED:자지",
                        "OCR_ARTIFACT", "TOO_SHORT", "NO_TIME_EXPR"]:
        samples = [d for d in issue_items if target_iss in d.get("review_issues", [])]
        if not samples:
            continue
        print(f"\n[{target_iss}] {len(samples)}건")
        for d in samples[:3]:
            print(f"  [{d['source'].get('author','?')}] {d['text_ko'][:70]}")

    print(f"\n수작업 검수 대상 → {REVIEW_OUT} ({len(issue_items)}건)")


if __name__ == "__main__":
    main()
