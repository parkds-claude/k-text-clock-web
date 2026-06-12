# 한문장 — 시각별 문학 인용구 데이터 아카이브

> 매 분(分)마다, 그 시각이 등장하는 문학의 문장. 텍스트 시계를 만들기 위한 공개 데이터셋.

[K-Text Clock (M5Stack CoreS3 텍스트 시계)](https://github.com/parkds-claude/k-text-clock-cores3)의
데이터 저장소입니다. 누구나 이 데이터로 자신만의 텍스트 시계(기기·위젯·앱)를 만들 수 있습니다.

## 데이터 구성

| 파일 | 내용 | 건수 |
|------|------|------|
| `data/quotes_public.json` | 한국문학 원본 (출처·라이선스 근거 포함) | 7,461 |
| `public/data/times/HH_MM.json` | 분당 큐레이션 슬롯 × 1,440 (시계용) | 1,440 |
| `data/en/quotes_en_pd.json` | 영문 고전 — 한국어 번역 + 영어 원문 | 77 |
| `data/en/quotes_en_litclock.json` | 영문 현대문학 — 영어 원문만 | 1,709 |

시계용 슬롯은 GitHub Pages로 서빙됩니다:

```
https://parkds-claude.github.io/k-text-clock-web/data/times/HH_MM.json
```

```json
[{ "text_ko": "도 (벽시계를 보고) 무얼 아직 열 시 반인데요.",
   "display_source": "— 홍사용, 「할미꽃」",
   "minute": "10:30", "match_type": "exact" }]
```

`match_type`: `exact` = 문장 속 시각이 슬롯 시각과 일치 / `timeslot` = 같은 시간대의 문장

### 데이터 현황 (정직한 안내)

| | 분 단위 정확 매칭 | 비고 |
|---|---|---|
| 한국문학 | **117 / 1,440분** | 나머지 분은 같은 시간대 문장으로 채움 — **수집 진행 중** |
| 영미문학 | **1,361 / 1,440분 (95%)** | Literature Clock 데이터 유래 |

시각이 등장하는 한국문학 PD 문장을 계속 수집하고 있습니다 → [기여 가이드](CONTRIBUTING.md)

## 데이터 출처와 저작권

### 한국문학 (7,461건)

| 구분 | 가져온 곳 | 저작권 | 라이선스 |
|------|----------|--------|---------|
| 고전 시조·가사·조선왕조실록 | [위키문헌](https://ko.wikisource.org) 등 | Public Domain | CC BY-NC 4.0 |
| 근대문학 (저자 사후 70년 이상) | [위키문헌](https://ko.wikisource.org) 등 | Public Domain | CC BY-NC 4.0 |

- 수록 기준: 저자 사후 70년 이상 경과 (대한민국 저작권법)
- 항목별 원문 출처 URL은 `quotes_public.json`의 `source.url`에,
  PD 판정 근거(사망 연도·법적 기준)는 `license` 필드에 기록

### 영문 문학 (1,786건)

| 구분 | 가져온 곳 | 저작권 | 라이선스 |
|------|----------|--------|---------|
| 고전 77건 (한역 포함) | [Project Gutenberg](https://www.gutenberg.org) | Public Domain | CC BY-NC 4.0 |
| 현대문학 1,709건 (영어 원문만) | [JohannesNE/literature-clock](https://github.com/JohannesNE/literature-clock) | 단문 인용 | CC BY-NC-SA 2.5 (승계) |

- 고전 77건의 항목별 Project Gutenberg 원문 링크는 `source_url` 필드에 기록
- 현대문학 1,709건의 한국어 번역본은 번역권 문제로 공개하지 않습니다 — 상세: [data/en/README.md](data/en/README.md)

### 출처 표기 원칙

- 모든 문장은 데이터에 **작가·작품**을 표기합니다 (`display_source`, 예: `— 이상, 「날개」`)
- 이 데이터를 사용하는 시계·앱도 화면에 출처를 함께 표시해 주세요 (CC BY-NC 조건)

**출처 오류·저작권 문의**: [GitHub Issues](../../issues)로 알려주세요. 확인 즉시 수정·삭제합니다.

## 프로젝트 구조

```
k-text-clock-web/
├── public/data/times/        ← 분당 슬롯 × 1440 (GitHub Pages 서빙)
├── data/
│   ├── quotes_public.json    ← 한국문학 원본
│   └── en/                   ← 영문 데이터 (라이선스 별도, README 참조)
├── scripts/
│   ├── build_public.py       ← 원본에서 PD 데이터 추출
│   ├── build_1440.py         ← 시각별 슬롯 빌드
│   ├── clean_titles.py       ← 작품명 정제
│   └── fix_display_source.py ← 출처 표기 검증·보정
└── .github/workflows/deploy.yml
```

데이터 빌드는 로컬에서 실행 후 커밋합니다 (CI는 정적 배포만 — 큐레이션 보존).

## 인용구 기여

읽던 책에서 시각이 등장하는 PD 문장을 발견하셨다면 → [CONTRIBUTING.md](CONTRIBUTING.md)

## 라이선스

- 인용구 데이터: **CC BY-NC 4.0** (출처 표기 필수, 비영리) — 영문 일부는 CC BY-NC-SA 2.5, [LICENSE](LICENSE) 참조
- 코드: MIT
