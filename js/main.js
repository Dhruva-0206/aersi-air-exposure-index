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

// ── Data loading ───────────────────────────────────────────────────────────
let _stationData = null;

async function loadStationData() {
  if (_stationData) return _stationData;
  // Try multiple paths to handle both local and deployed environments
  const paths = [
    'data/processed/aersi_station_scores.csv',
    '/data/processed/aersi_station_scores.csv',
    './data/processed/aersi_station_scores.csv',
  ];
  for (const path of paths) {
    try {
      const res = await fetch(path);
      if (!res.ok) continue;
      const text = await res.text();
      if (!text || text.trim().length < 10) continue;
      _stationData = parseCSV(text);
      if (_stationData.length > 0) return _stationData;
    } catch (e) {
      continue;
    }
  }
  console.warn('Could not load station data from any path.');
  return [];
}

function parseCSV(text) {
  const lines = text.trim().split('\n');
  if (lines.length < 2) return [];
  const headers = lines[0].split(',').map(h => h.trim().replace(/^"|"$/g, ''));
  return lines.slice(1).map(line => {
    // Handle quoted fields with commas inside
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

  // Mobile menu
  const menuBtn = document.getElementById('mobile-menu-btn');
  const navLinks = document.querySelector('.nav-links');
  if (menuBtn && navLinks) {
    menuBtn.addEventListener('click', () => {
      const isOpen = navLinks.style.display === 'flex';
      navLinks.style.cssText = isOpen
        ? ''
        : 'display:flex;flex-direction:column;position:absolute;top:var(--nav-h);left:0;right:0;background:var(--bg);border-bottom:1px solid var(--border2);padding:1rem;gap:0.25rem;z-index:999;';
    });
  }

  // Close overlay on backdrop click
  const overlay = document.getElementById('map-overlay');
  if (overlay) {
    overlay.addEventListener('click', e => {
      if (e.target === overlay) closeMapOverlay();
    });
    document.addEventListener('keydown', e => {
      if (e.key === 'Escape') closeMapOverlay();
    });
  }
});
