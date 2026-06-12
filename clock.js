/* 한문장 시계 — 한국 문학 문장 표시 (Phase 1: 10분 단위 슬롯) */
(function () {
  'use strict';

  // Phase 1=10, Phase 2=5, Phase 3=1
  const SLOT_GRANULARITY = 5;

  const SLOT_KO = {
    midnight: '한밤', dawn: '새벽', morning: '아침', forenoon: '오전',
    noon: '정오', afternoon: '오후', evening: '저녁', night: '밤',
  };

  const el = id => document.getElementById(id);
  const clockTimeEl  = el('clock-time');
  const clockText    = el('clock-text');
  const clockSource  = el('clock-source');
  const clockMatch   = el('clock-match');
  const clockNext    = el('clock-next');
  const clockShare   = el('clock-share');
  const themeBtn     = el('theme-toggle');
  const toast        = el('toast');

  let currentPool = [];
  let currentIdx  = 0;
  let lastMinute  = -1;

  // ── 테마
  (function initTheme() {
    const saved = localStorage.getItem('hanmunjang-theme') || 'dark';
    document.body.classList.toggle('light', saved === 'light');
    themeBtn.addEventListener('click', () => {
      const isLight = document.body.classList.toggle('light');
      localStorage.setItem('hanmunjang-theme', isLight ? 'light' : 'dark');
    });
  })();

  // ── 시각 문자열
  function formatTime(h, m) {
    return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}`;
  }

  // ── 문장 안에서 시각 표현 하이라이트
  function highlightTime(text, h, m) {
    const hh = String(h).padStart(2, '0');
    const mm = String(m).padStart(2, '0');
    const korHour = ['영', '한', '두', '세', '네', '다섯', '여섯', '일곱', '여덟', '아홉', '열', '열한', '열두',
                     '열세', '열네', '열다섯', '열여섯', '열일곱', '열여덟', '열아홉', '스물', '스물한', '스물두', '스물세', '스물네'][h] || '';
    const patterns = [
      `${hh}:${mm}`,
      `${h}시\\s*${m}분`,
      `${korHour}\\s*시`,
    ];
    let result = text;
    patterns.forEach(pat => {
      try {
        result = result.replace(new RegExp(`(${pat})`, 'g'), '<mark>$1</mark>');
      } catch { /* invalid regex는 건너뜀 */ }
    });
    return result;
  }

  // ── 문장 표시
  function displayQuote(entry, h, m) {
    clockText.classList.remove('visible');
    setTimeout(() => {
      clockText.innerHTML = highlightTime(entry.text_ko || '', h, m);
      clockSource.textContent = entry.display_source || '';
      const badge = entry.match_type === 'exact' ? '정확 매칭' : '시간대 매칭';
      clockMatch.textContent = badge;
      clockText.classList.add('visible');
    }, 350);
  }

  // ── 슬롯 JSON 로드 (SLOT_GRANULARITY 단위로 정렬된 파일)
  async function loadSlot(h, m) {
    const mAligned = Math.floor(m / SLOT_GRANULARITY) * SLOT_GRANULARITY;
    const key = `${String(h).padStart(2,'0')}_${String(mAligned).padStart(2,'0')}`;
    try {
      const res = await fetch(`data/times/${key}.json`);
      if (!res.ok) throw new Error('not found');
      return await res.json();
    } catch {
      return [];
    }
  }

  // ── 매 초 업데이트 (슬롯 경계에서만 문장 교체)
  async function tick() {
    const now = new Date();
    const h = now.getHours();
    const m = now.getMinutes();

    // 실제 시각은 매 초 표시
    clockTimeEl.textContent = formatTime(h, m);

    // 슬롯 단위로만 문장 교체
    const slot = Math.floor((h * 60 + m) / SLOT_GRANULARITY);
    if (slot !== lastMinute) {
      lastMinute = slot;
      currentPool = await loadSlot(h, m);
      currentIdx = 0;
      if (currentPool.length) displayQuote(currentPool[currentIdx], h, m);
    }
  }

  // ── 다른 문장 버튼
  function showNext() {
    if (!currentPool.length) return;
    currentIdx = (currentIdx + 1) % currentPool.length;
    const now = new Date();
    displayQuote(currentPool[currentIdx], now.getHours(), now.getMinutes());
  }

  clockNext.addEventListener('click', showNext);

  // ── 공유
  clockShare.addEventListener('click', () => {
    const entry = currentPool[currentIdx];
    if (!entry) return;
    const text = `${entry.text_ko}\n${entry.display_source || ''}\n\n— 한문장 시계 (한국 근대문학 명문장)`;
    navigator.clipboard.writeText(text)
      .then(() => showToast('클립보드에 복사했습니다'))
      .catch(() => showToast('복사 실패'));
  });

  function showToast(msg) {
    toast.textContent = msg;
    toast.classList.add('show');
    clearTimeout(toast._timer);
    toast._timer = setTimeout(() => toast.classList.remove('show'), 2400);
  }

  // ── 시작 — 정각 초에 동기화
  tick();
  setInterval(tick, 1000);
})();
