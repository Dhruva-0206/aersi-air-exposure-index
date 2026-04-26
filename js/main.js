// ── Theme ──────────────────────────────────────────────────────────────────

const THEME_KEY = 'aersi-theme';

function getTheme() {
  return localStorage.getItem(THEME_KEY) ||
    (window.matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark');
}

function applyTheme(theme) {
  document.documentElement.setAttribute('data-theme', theme);
  localStorage.setItem(THEME_KEY, theme);
  const btn = document.getElementById('theme-toggle');
  if (btn) btn.textContent = theme === 'dark' ? '☀️' : '🌙';
}

function toggleTheme() {
  applyTheme(getTheme() === 'dark' ? 'light' : 'dark');
}

// Apply immediately to avoid flash
applyTheme(getTheme());

// ── Active nav link ────────────────────────────────────────────────────────

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
  try {
    const res = await fetch('data/processed/aersi_station_scores.csv');
    const text = await res.text();
    _stationData = parseCSV(text);
    return _stationData;
  } catch (e) {
    console.error('Failed to load station data:', e);
    return [];
  }
}

function parseCSV(text) {
  const lines = text.trim().split('\n');
  const headers = lines[0].split(',').map(h => h.trim());
  return lines.slice(1).map(line => {
    const vals = line.split(',');
    const obj = {};
    headers.forEach((h, i) => {
      const v = (vals[i] || '').trim();
      obj[h] = isNaN(v) || v === '' ? v : parseFloat(v);
    });
    return obj;
  }).filter(r => r.station && !isNaN(r.AERSI));
}

// ── AERSI helpers ──────────────────────────────────────────────────────────

function aersiCategory(v) {
  if (v < 0.8)  return { label: 'Very Low',  cls: 'very-low',  color: '#22c55e' };
  if (v < 1.2)  return { label: 'Low',       cls: 'low',       color: '#84cc16' };
  if (v < 2.0)  return { label: 'Moderate',  cls: 'moderate',  color: '#eab308' };
  if (v < 3.0)  return { label: 'High',      cls: 'high',      color: '#f97316' };
  return           { label: 'Extreme',    cls: 'extreme',   color: '#ef4444' };
}

function fmt(v, d = 2) {
  if (v === undefined || v === null || isNaN(v)) return '—';
  return parseFloat(v).toFixed(d);
}

// ── Init ───────────────────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {
  setActiveNav();

  const toggleBtn = document.getElementById('theme-toggle');
  if (toggleBtn) toggleBtn.addEventListener('click', toggleTheme);

  // Mobile menu
  const menuBtn = document.getElementById('mobile-menu-btn');
  const navLinks = document.querySelector('.nav-links');
  if (menuBtn && navLinks) {
    menuBtn.addEventListener('click', () => {
      navLinks.style.display = navLinks.style.display === 'flex' ? 'none' : 'flex';
    });
  }
});