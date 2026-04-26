// ── Active nav ─────────────────────────────────────────────────────────────
function setActiveNav() {
  const path = window.location.pathname.split('/').pop() || 'index.html';
  document.querySelectorAll('.nav-links a').forEach(a => {
    const href = a.getAttribute('href');
    if (href === path || (path === '' && href === 'index.html')) {
      a.classList.add('active');
    }
  });
}

// ── Data loading — XHR avoids fetch/CORS issues on Vercel ─────────────────
let _stationData = null;

function loadStationData() {
  if (_stationData) return Promise.resolve(_stationData);

  return new Promise((resolve) => {
    const xhr = new XMLHttpRequest();
    // Absolute URL using current origin — works on Vercel and locally
    const url = window.location.origin + '/data/processed/aersi_station_scores.csv';
    xhr.open('GET', url, true);
    xhr.setRequestHeader('Accept', 'text/plain, text/csv, */*');
    xhr.onload = function () {
      if (xhr.status === 200 && xhr.responseText && xhr.responseText.length > 20) {
        _stationData = parseCSV(xhr.responseText);
        resolve(_stationData);
      } else {
        console.warn('AERSI: CSV load failed, status:', xhr.status);
        resolve([]);
      }
    };
    xhr.onerror = function () {
      console.warn('AERSI: CSV network error');
      resolve([]);
    };
    xhr.send();
  });
}

function parseCSV(text) {
  const lines = text.trim().split('\n');
  if (lines.length < 2) return [];
  const headers = lines[0].split(',').map(h => h.trim().replace(/^"|"$/g, ''));
  return lines.slice(1).map(line => {
    const vals = [];
    let inQuote = false, cur = '';
    for (const ch of line) {
      if (ch === '"') { inQuote = !inQuote; }
      else if (ch === ',' && !inQuote) { vals.push(cur); cur = ''; }
      else cur += ch;
    }
    vals.push(cur);
    const obj = {};
    headers.forEach((h, i) => {
      const v = (vals[i] || '').trim().replace(/^"|"$/g, '');
      obj[h] = (v !== '' && !isNaN(v)) ? parseFloat(v) : v;
    });
    return obj;
  }).filter(r => r.station && r.AERSI !== undefined && !isNaN(r.AERSI));
}

// ── AERSI helpers ──────────────────────────────────────────────────────────
function aersiCategory(v) {
  if (v < 0.8) return { label: 'Very Low',  cls: 'very-low',  color: '#16a34a' };
  if (v < 1.2) return { label: 'Low',       cls: 'low',       color: '#65a30d' };
  if (v < 2.0) return { label: 'Moderate',  cls: 'moderate',  color: '#d97706' };
  if (v < 3.0) return { label: 'High',      cls: 'high',      color: '#ea580c' };
  return         { label: 'Extreme',    cls: 'extreme',   color: '#dc2626' };
}

function fmt(v, d = 2) {
  if (v === undefined || v === null || v === '' || isNaN(v)) return '—';
  return parseFloat(v).toFixed(d);
}

// ── Map overlay ────────────────────────────────────────────────────────────
function openMapOverlay() {
  const overlay = document.getElementById('map-overlay');
  if (!overlay) return;
  overlay.classList.add('open');
  document.body.style.overflow = 'hidden';
}

function closeMapOverlay() {
  const overlay = document.getElementById('map-overlay');
  if (!overlay) return;
  overlay.classList.remove('open');
  document.body.style.overflow = '';
}

// ── Init ───────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  setActiveNav();

  const menuBtn  = document.getElementById('mobile-menu-btn');
  const navLinks = document.querySelector('.nav-links');
  if (menuBtn && navLinks) {
    menuBtn.addEventListener('click', () => {
      const isOpen = navLinks.style.display === 'flex';
      navLinks.style.cssText = isOpen
        ? ''
        : 'display:flex;flex-direction:column;position:absolute;top:var(--nav-h);left:0;right:0;background:var(--bg);border-bottom:1px solid var(--border2);padding:1rem;gap:0.25rem;z-index:999;';
    });
  }

  const overlay = document.getElementById('map-overlay');
  if (overlay) {
    overlay.addEventListener('click', e => { if (e.target === overlay) closeMapOverlay(); });
    document.addEventListener('keydown', e => { if (e.key === 'Escape') closeMapOverlay(); });
  }
});
