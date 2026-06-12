# 한문장 — 한국 근대문학 명문장 아카이브

> 한국의 시간을 만나다 — 이상·김소월·백석·채만식… 한국 문학의 빛나는 문장들을 발견하세요.

**[→ 지금 바로 보기](https://parkds-claude.github.io/k-text-clock-web/)**

---

## 특징

- **7,400건+** 한국어 인용구 (저작권 만료 PD 작품만) + 영문 인용구 1,700건+
- **작가별 탐색** — 김동인, 채만식, 이광수, 현진건 등 63명
- **시간대별 탐색** — 한밤·새벽·아침·오전·정오·오후·저녁·밤
- **전체 검색** — 문장·작가·작품명 실시간 검색
- **오늘의 한 문장** — 날짜별 큐레이션 문장
- **시계 모드** — 지금 이 시각의 문장 (clock.html)
- 다크/라이트 테마
- 모바일 반응형
- 광고 없음, 추적 없음

## 페이지 구성

| 페이지 | 설명 |
|--------|------|
| `index.html` | 메인 발견 플랫폼 (작가·시간대·검색) |
| `clock.html` | 시계 모드 — 매 분 현재 시각 문장 표시 |

## 데이터 출처

| 구분 | 출처 | 저작권 | 라이선스 |
|------|------|--------|---------|
| 고전 시조·가사·실록 | 위키문헌 등 | Public Domain | CC BY-NC 4.0 |
| 한국 근대문학 (사후 70년 이상) | 위키문헌 등 | Public Domain | CC BY-NC 4.0 |
| 영문 고전 77건 (한역 포함) | Project Gutenberg | Public Domain | CC BY-NC 4.0 |
| 영문 현대문학 1,709건 (영어 원문만) | [literature-clock](https://github.com/JohannesNE/literature-clock) | 단문 인용 | CC BY-NC-SA 2.5 |

영문 데이터 상세: [data/en/README.md](data/en/README.md)

- 수록 기준: 저자 사후 70년 이상 경과, 대한민국 저작권법 기준
- 모든 문장은 화면과 데이터에 **작가·작품 출처를 함께 표기**합니다
  (`display_source`, 예: `— 이상, 「날개」`)
- 원문 텍스트 출처: 위키문헌(ko.wikisource.org) 등 — 각 항목의 `source.url`에 기록
- 각 항목의 `license` 필드에 PD 판정 근거(사망 연도·법적 기준)를 명시합니다

**출처 오류·저작권 문의**: 표기 오류를 발견하셨거나 저작권 관련 문의가 있으시면
[GitHub Issues](../../issues)로 알려주세요. 확인 즉시 수정·삭제합니다.

## 관련 프로젝트

- [k-text-clock-cores3](https://github.com/parkds-claude/k-text-clock-cores3) — M5Stack CoreS3로 만드는 실물 텍스트 시계 (이 레포의 데이터를 사용)

## 프로젝트 구조

```
k-text-clock-web/
├── public/               ← 배포 대상 (GitHub Pages)
│   ├── index.html        ← 발견 플랫폼 메인
│   ├── clock.html        ← 시계 모드
│   ├── style.css         ← 공통 스타일
│   ├── main.js           ← 발견 플랫폼 로직
│   ├── clock.js          ← 시계 로직
│   └── data/
│       ├── quotes_web.json    ← 경량 인용구 데이터
│       ├── authors.json       ← 작가 인덱스
│       └── times/             ← HH_MM.json × 1440
├── data/
│   └── quotes_public.json    ← 원본 PD 데이터 (7,524건)
├── scripts/
│   ├── build_public.py        ← 원본에서 PD 데이터 추출
│   ├── build_web_data.py      ← 웹 배포용 경량 빌드
│   └── build_1440.py          ← 시각별 JSON 빌드
└── .github/workflows/deploy.yml
```

## 인용구 기여

→ [CONTRIBUTING.md](CONTRIBUTING.md)

## 라이선스

- 인용구 데이터: **CC BY-NC 4.0** (출처 표기 필수, 비영리) — 영문 일부는 CC BY-NC-SA 2.5, [LICENSE](LICENSE) 참조
- 코드: MIT
