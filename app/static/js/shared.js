function showToast(msg) {
  const el = document.getElementById('copyToast');
  if (!el) return;
  el.textContent = msg; el.style.display = 'block';
  clearTimeout(el._t);
  el._t = setTimeout(() => { el.style.display = 'none'; }, 2000);
}

function copyText(text) {
  if (navigator.clipboard && window.isSecureContext) {
    return navigator.clipboard.writeText(text).catch(() => {});
  }
  const ta = document.createElement('textarea');
  ta.value = text; ta.style.position = 'fixed'; ta.style.opacity = '0';
  document.body.appendChild(ta); ta.focus(); ta.select();
  try { document.execCommand('copy'); } catch {}
  document.body.removeChild(ta);
}

function openCoin(symbol) {
  const pair = String(symbol || '').trim().toUpperCase()
    .replace(/^BINANCE:/, '').replace(/\.P$/, '').replace(/[^A-Z0-9]/g, '');
  const futSym = pair.endsWith('USDT') ? pair : `${pair}USDT`;
  copyText(futSym);
  showToast(futSym + ' kopyalandı');
  window.open(`https://www.tradingview.com/chart/rsEEPbkd/?symbol=BINANCE%3A${futSym}.P`, '_blank');
  setTimeout(() => window.open(`https://www.coinglass.com/tv/Binance_${futSym}`, '_blank'), 200);
}

function setLiveStatus(live, reason = '') {
  const dot = document.getElementById('liveDot');
  const val = document.getElementById('statusVal');
  if (dot) dot.className = 'ldot' + (live ? '' : ' offline');
  if (val) {
    val.textContent = live ? 'LIVE' : (reason ? 'HATA' : 'OFFLINE');
    val.style.color = live ? 'var(--g)' : 'var(--r)';
    val.title = reason || '';
  }
}

function fmtPct(v, decimals = 2) {
  const n = parseFloat(v);
  if (isNaN(n)) return '<span style="color:var(--m)">—</span>';
  const s = (n >= 0 ? '+' : '') + n.toFixed(decimals) + '%';
  const c = n > 0 ? 'var(--g)' : n < 0 ? 'var(--r)' : 'var(--m)';
  return `<span style="color:${c};font-weight:700">${s}</span>`;
}

function fmtPrice(v) {
  const n = parseFloat(v);
  if (isNaN(n)) return '—';
  if (n >= 1000) return '$' + n.toLocaleString('en-US', { maximumFractionDigits: 2 });
  if (n >= 1)    return '$' + n.toFixed(4);
  return '$' + n.toFixed(6);
}
