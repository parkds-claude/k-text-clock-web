/* 한문장 — 발견 플랫폼 메인 스크립트 */
(function () {
  'use strict';

  const TIMESLOTS = [
    { key: 'midnight',  label: '한밤',  range: '00:00–01:59' },
    { key: 'dawn',      label: '새벽',  range: '02:00–04:59' },
    { key: 'morning',   label: '아침',  range: '05:00–06:59' },
    { key: 'forenoon',  label: '오전',  range: '07:00–11:59' },
    { key: 'noon',      label: '정오',  range: '12:00–12:59' },
    { key: 'afternoon', label: '오후',  range: '13:00–16:59' },
    { key: 'evening',   label: '저녁',  range: '17:00–19:59' },
    { key: 'night',     label: '밤',    range: '20:00–23:59' },
  ];
  const SLOT_KO = Object.fromEntries(TIMESLOTS.map(t => [t.key, t.label]));
  const PAGE_SIZE = 18;

  // ── 전역 상태
  let allQuotes = [];
  let prevTab = 'timeslot';
  let searchTimer = null;

  // ── DOM 참조
  const el = id => document.getElementById(id);
  const heroText     = el('hero-text');
  const heroSource   = el('hero-source');
  const heroTimeslot = el('hero-timeslot');
  const heroShare    = el('hero-share');
  const browseHeading = el('browse-heading');
  const backBtn      = el('back-btn');
  const timeslotGrid = el('timeslot-grid');
  const authorGrid   = el('author-grid');
  const searchInput  = el('search-input');
  const resultCount  = el('result-count');
  const quoteGrid    = el('quote-grid');
  const loadMore     = el('load-more');
  const filteredGrid = el('filtered-grid');
  const loadMoreF    = el('load-more-filtered');
  const themeBtn     = el('theme-toggle');
  const toast        = el('toast');
  const allTabs      = document.querySelectorAll('.tab');

  // ── 테마
  function initTheme() {
    const saved = localStorage.getItem('hanmunjang-theme') || 'dark';
    document.body.classList.toggle('light', saved === 'light');
    themeBtn.addEventListener('click', () => {
      const isLight = document.body.classList.toggle('light');
      localStorage.setItem('hanmunjang-theme', isLight ? 'light' : 'dark');
    });
  }

  // ── 데이터
  async function loadData() {
    const res = await fetch('data/quotes_web.json');
    allQuotes = await res.json();
  }

  // ── 출처 문자열
  function buildSource(q) {
    const parts = [];
    if (q.author) parts.push(q.author);
    if (q.title)  parts.push(`「${q.title}」`);
    return parts.length ? `— ${parts.join(', ')}` : '';
  }

  // ── 히어로
  function setupHero() {
    const dayOffset = Math.floor((Date.now() - new Date('2026-01-01').getTime()) / 86400000);
    const q = allQuotes[Math.abs(dayOffset) % allQuotes.length];
    if (!q) return;

    heroText.textContent = q.text;
    heroSource.textContent = buildSource(q);
    const sl = SLOT_KO[q.timeslot] || q.timeslot;
    heroTimeslot.textContent = q.minute ? `${sl} ${q.minute}` : sl;
    requestAnimationFrame(() => heroText.classList.add('visible'));
    heroShare.addEventListener('click', () => copyQuote(q));
  }

  // ── 탭 전환
  function switchTab(name, heading) {
    allTabs.forEach(t => {
      const on = t.dataset.tab === name;
      t.classList.toggle('active', on);
      t.setAttribute('aria-selected', on);
    });
    ['timeslot', 'author', 'all', 'filtered'].forEach(id => {
      el(`tab-${id}`).classList.toggle('hidden', id !== name);
    });
    browseHeading.textContent = heading || { timeslot: '시간대별 탐색', author: '작가별 탐색', all: '전체 탐색', filtered: '' }[name] || '';
    backBtn.classList.toggle('hidden', name !== 'filtered');
  }

  function setupTabs() {
    allTabs.forEach(tab => {
      tab.addEventListener('click', () => {
        prevTab = tab.dataset.tab;
        switchTab(tab.dataset.tab);
      });
    });
    backBtn.addEventListener('click', () => switchTab(prevTab === 'filtered' ? 'timeslot' : prevTab));
  }

  // ── 문장 카드 생성
  function makeCard(q) {
    const card = document.createElement('div');
    card.className = 'quote-card';
    const sl = SLOT_KO[q.timeslot] || '';
    const badge = q.minute ? `${sl} ${q.minute}` : sl;
    card.innerHTML = `
      <p class="quote-text">${esc(q.text)}</p>
      <div class="quote-footer">
        <cite class="quote-source">${esc(buildSource(q))}</cite>
        ${badge ? `<span class="quote-badge">${esc(badge)}</span>` : ''}
        <button class="quote-share-btn" aria-label="문장 복사">공유</button>
      </div>
    `;
    card.querySelector('.quote-share-btn').addEventListener('click', e => {
      e.stopPropagation();
      copyQuote(q);
    });
    return card;
  }

  // ── 페이지네이션 렌더
  function renderQuotes(container, moreBtn, quotes, reset) {
    if (reset) {
      container.innerHTML = '';
      container._page = 0;
    }
    const page  = container._page || 0;
    const start = page * PAGE_SIZE;
    const slice = quotes.slice(start, start + PAGE_SIZE);
    const frag  = document.createDocumentFragment();
    slice.forEach(q => frag.appendChild(makeCard(q)));
    container.appendChild(frag);
    container._page = page + 1;

    const hasMore = start + PAGE_SIZE < quotes.length;
    moreBtn.classList.toggle('hidden', !hasMore);
    moreBtn.onclick = hasMore ? () => renderQuotes(container, moreBtn, quotes, false) : null;
  }

  // ── 시간대별
  function setupTimeslotGrid() {
    const countMap = {};
    const sampleMap = {};
    allQuotes.forEach(q => {
      const s = q.timeslot || '';
      countMap[s] = (countMap[s] || 0) + 1;
      if (!sampleMap[s] && q.text) sampleMap[s] = q.text;
    });

    TIMESLOTS.forEach(({ key, label, range }) => {
      const cnt = countMap[key] || 0;
      if (!cnt) return;
      const card = document.createElement('div');
      card.className = 'timeslot-card';
      const sample = (sampleMap[key] || '').slice(0, 45);
      card.innerHTML = `
        <div class="timeslot-label">${label}</div>
        <div class="timeslot-range">${range}</div>
        <div class="timeslot-count">${cnt.toLocaleString()}문장</div>
        <div class="timeslot-sample">${esc(sample)}…</div>
      `;
      card.addEventListener('click', () => showFiltered(
        allQuotes.filter(q => q.timeslot === key),
        `${label} 문장`
      ));
      timeslotGrid.appendChild(card);
    });
  }

  // ── 작가별
  async function setupAuthorGrid() {
    let authors;
    try {
      const res = await fetch('data/authors.json');
      authors = await res.json();
    } catch {
      const map = {};
      allQuotes.forEach(q => {
        const a = q.author || '(무명)';
        if (!map[a]) map[a] = { author: a, count: 0, sample: q.text };
        map[a].count++;
      });
      authors = Object.values(map).sort((a, b) => b.count - a.count);
    }

    authors.slice(0, 40).forEach(({ author, count, sample }) => {
      const card = document.createElement('div');
      card.className = 'author-card';
      card.innerHTML = `
        <div class="author-name">${esc(author)}</div>
        <div class="author-count">${count.toLocaleString()}문장</div>
        <div class="author-sample">${esc((sample || '').slice(0, 55))}…</div>
      `;
      card.addEventListener('click', () => showFiltered(
        allQuotes.filter(q => q.author === author),
        `${author} 문장`
      ));
      authorGrid.appendChild(card);
    });
  }

  // ── 드릴다운
  function showFiltered(quotes, heading) {
    prevTab = 'filtered';
    filteredGrid.innerHTML = '';
    renderQuotes(filteredGrid, loadMoreF, quotes, true);
    switchTab('filtered', heading);
  }

  // ── 전체 탐색 + 검색
  function setupSearchTab() {
    renderQuotes(quoteGrid, loadMore, allQuotes, true);
    resultCount.textContent = `전체 ${allQuotes.length.toLocaleString()}문장`;

    searchInput.addEventListener('input', () => {
      clearTimeout(searchTimer);
      searchTimer = setTimeout(() => {
        const raw = searchInput.value.trim();
        const result = raw
          ? allQuotes.filter(q =>
              q.text.includes(raw) ||
              (q.author && q.author.includes(raw)) ||
              (q.title  && q.title.includes(raw))
            )
          : allQuotes;
        resultCount.textContent = raw
          ? `${result.length.toLocaleString()}건 검색됨`
          : `전체 ${allQuotes.length.toLocaleString()}문장`;
        renderQuotes(quoteGrid, loadMore, result, true);
      }, 220);
    });
  }

  // ── 공유
  function copyQuote(q) {
    const text = `${q.text}\n${buildSource(q)}\n\n— 한문장 (한국 근대문학 명문장)`;
    navigator.clipboard.writeText(text)
      .then(() => showToast('클립보드에 복사했습니다'))
      .catch(() => showToast('복사 실패'));
  }

  function showToast(msg) {
    toast.textContent = msg;
    toast.classList.add('show');
    clearTimeout(toast._timer);
    toast._timer = setTimeout(() => toast.classList.remove('show'), 2400);
  }

  function esc(str) {
    return String(str || '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;');
  }

  // ── 초기화
  async function init() {
    initTheme();
    try {
      await loadData();
    } catch (e) {
      heroText.textContent = '데이터를 불러오지 못했습니다.';
      heroText.classList.add('visible');
      return;
    }
    setupHero();
    setupTabs();
    setupTimeslotGrid();
    await setupAuthorGrid();
    setupSearchTab();
  }

  init();
})();
