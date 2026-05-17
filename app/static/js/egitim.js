/* ── Fero Eğitim — Frontend ─────────────────────────────────────────────── */

let _data       = null;   // son /api/egitim yanıtı
let _reports    = [];     // günlük raporlar
let _filterVal  = '';

// ── Tab yönetimi ──────────────────────────────────────────────────────────
function switchTab(name) {
  document.querySelectorAll('.tab').forEach(t => {
    t.classList.toggle('active', t.dataset.tab === name);
  });
  document.querySelectorAll('.section').forEach(s => {
    s.classList.toggle('active', s.id === 'tab-' + name);
  });
  if (name === 'reports') refreshReports();
}

// ── Stats Row ─────────────────────────────────────────────────────────────
function updateStats(d) {
  setText('statPanel',  d.panel_count);
  setText('statToday',  d.today_count);
  setText('statPollNew', d.last_poll_count || 0);
  setText('statDate',   d.current_date || '—');
  setText('thresholdLabel',  d.threshold_pct || 20);
  setText('thresholdLabel2', d.threshold_pct || 20);
  setText('thresholdVal', '%' + (d.threshold_pct || 20));
  setText('pairsVal', d.total_pairs || 0);
  setLiveStatus(d.live, d.last_error || '');
}

function setText(id, val) {
  const el = document.getElementById(id);
  if (el) el.textContent = val;
}

// ── Kalıcı Panel tablosu ──────────────────────────────────────────────────
function renderPanel(panel) {
  const body  = document.getElementById('panelBody');
  const empty = document.getElementById('panelEmpty');
  if (!body) return;

  const q = _filterVal.toUpperCase();
  const filtered = q ? panel.filter(c => c.symbol.toUpperCase().includes(q)) : panel;

  if (!filtered.length) {
    body.innerHTML = '';
    empty.style.display = 'block';
    return;
  }
  empty.style.display = 'none';

  body.innerHTML = filtered.map((c, i) => {
    const rankClass = i === 0 ? 'gold' : i === 1 ? 'silver' : i === 2 ? 'bronze' : '';
    const isNew = (Date.now() / 1000 - c.added_ts) < 120;  // 2 dakikadan yeni
    return `<tr class="${isNew ? 'new-row' : ''}" onclick="openCoin('${c.symbol}')">
      <td><span class="rank ${rankClass}">${i + 1}</span></td>
      <td class="sym-col">${c.symbol}</td>
      <td>${fmtPct(c.first_pct)}</td>
      <td style="font-family:var(--mono);font-weight:700;color:var(--g)">+${c.max_pct.toFixed(2)}%</td>
      <td style="color:var(--m)">${fmtPrice(c.price_entry)}</td>
      <td style="color:var(--m)">${c.first_seen || '—'}</td>
      <td style="color:var(--m);font-size:10px">${c.first_date || '—'}</td>
    </tr>`;
  }).join('');
}

// ── Bugün Liderleri (sol panel) ───────────────────────────────────────────
function renderTodayList(coins) {
  const el    = document.getElementById('todayList');
  const badge = document.getElementById('todayCountBadge');
  if (!el) return;
  if (badge) badge.textContent = coins.length + ' coin';

  if (!coins.length) {
    el.innerHTML = '<div class="empty-state">Bugün henüz coin girmedi…</div>';
    return;
  }

  el.innerHTML = coins.slice(0, 30).map((c, i) => {
    const rankClass = i === 0 ? 'gold' : i === 1 ? 'silver' : i === 2 ? 'bronze' : '';
    return `<div class="titem" onclick="openCoin('${c.symbol}')">
      <div class="titem-left">
        <span class="titem-sym"><span class="rank ${rankClass}" style="margin-right:5px">${i + 1}</span>${c.symbol}</span>
        <span class="titem-time">İlk: ${c.first_seen || '—'} · $${parseFloat(c.price_entry || 0).toFixed(4)}</span>
      </div>
      <span class="titem-pct">+${c.max_pct.toFixed(2)}%</span>
    </div>`;
  }).join('');
}

// ── Bugün tam tablo (sağ) ─────────────────────────────────────────────────
function renderTodayTable(coins) {
  const body  = document.getElementById('todayBody');
  const empty = document.getElementById('todayEmpty');
  if (!body) return;

  if (!coins.length) {
    body.innerHTML = '';
    empty.style.display = 'block';
    return;
  }
  empty.style.display = 'none';

  body.innerHTML = coins.map((c, i) => {
    const rankClass = i === 0 ? 'gold' : i === 1 ? 'silver' : i === 2 ? 'bronze' : '';
    return `<tr onclick="openCoin('${c.symbol}')">
      <td><span class="rank ${rankClass}">${i + 1}</span></td>
      <td class="sym-col">${c.symbol}</td>
      <td style="font-family:var(--mono);font-weight:700;color:var(--g)">+${c.max_pct.toFixed(2)}%</td>
      <td style="color:var(--m)">${fmtPrice(c.price_entry)}</td>
      <td style="color:var(--m)">${c.first_seen || '—'}</td>
    </tr>`;
  }).join('');
}

// ── Günlük Raporlar ───────────────────────────────────────────────────────
function renderReports(reports, todayLive) {
  const el = document.getElementById('reportsList');
  if (!el) return;

  const allItems = [];

  // Bugünün canlı özeti
  if (todayLive) {
    allItems.push(renderReportCard(todayLive, true));
  }

  // Geçmiş raporlar
  reports.forEach(r => allItems.push(renderReportCard(r, false)));

  if (!allItems.length) {
    el.innerHTML = '<div class="empty-state">Henüz tamamlanan günlük rapor yok.<br>İlk rapor bugün gece yarısında oluşturulacak.</div>';
    return;
  }

  el.innerHTML = allItems.join('');
}

function renderReportCard(r, isLive) {
  const coins = r.top || [];
  const coinsHtml = coins.slice(0, 20).map(c =>
    `<span class="rcoin" onclick="openCoin('${c.symbol}')">
      ${c.symbol} <span class="rcoin-pct">+${(c.max_pct || 0).toFixed(1)}%</span>
    </span>`
  ).join('');

  return `<div class="report-card">
    <div class="report-header">
      <span class="report-date">${isLive ? '📍 ' : '📅 '}${r.date}</span>
      <span class="report-badge ${isLive ? 'live' : ''}">${isLive ? 'BUGÜN (CANLI)' : 'Tamamlandı'}</span>
    </div>
    <div class="report-stat">
      <strong>${r.count}</strong> coin %${r.threshold_pct || 20}+ eşiğini aştı
      ${r.count > 0 ? ` · En yüksek: <strong style="color:var(--g)">${coins[0]?.symbol || '—'} (+${(coins[0]?.max_pct || 0).toFixed(2)}%)</strong>` : ''}
    </div>
    <div class="report-coins">${coinsHtml || '<span style="color:var(--m);font-size:11px">Bu gün eşik aşılmadı</span>'}</div>
  </div>`;
}

// ── API çağrıları ─────────────────────────────────────────────────────────
async function refreshMain() {
  try {
    const d = await fetch('/api/egitim', { cache: 'no-store' })
      .then(r => { if (!r.ok) throw new Error(r.status); return r.json(); });
    _data = d;
    updateStats(d);
    renderPanel(d.panel || []);
    renderTodayList(d.today_top || []);
    renderTodayTable(d.today_top || []);
  } catch (err) {
    setLiveStatus(false, String(err));
  }
}

async function refreshReports() {
  try {
    const [rep, today] = await Promise.all([
      fetch('/api/reports', { cache: 'no-store' }).then(r => r.json()),
      fetch('/api/today',   { cache: 'no-store' }).then(r => r.json()),
    ]);
    _reports = rep.reports || [];
    renderReports(_reports, today);
  } catch {}
}

async function refreshAll() {
  await refreshMain();
}

// ── Filter ────────────────────────────────────────────────────────────────
const filterEl = document.getElementById('filterInput');
if (filterEl) {
  filterEl.addEventListener('input', () => {
    _filterVal = filterEl.value.trim();
    if (_data) renderPanel(_data.panel || []);
  });
}

// ── Bootstrap ─────────────────────────────────────────────────────────────
refreshMain();
setInterval(refreshMain, 30000);   // 30 saniyede bir güncelle (panel kalıcı, sık poll şart değil)
