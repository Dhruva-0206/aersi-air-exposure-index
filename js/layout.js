// Shared nav and footer — injected by each page

function renderNav() {
  return `
  <nav class="nav">
    <a href="index.html" class="nav-brand">
      <span class="nav-brand-dot"></span>
      AERSI
    </a>
    <ul class="nav-links">
      <li><a href="index.html">Home</a></li>
      <li><a href="map.html">Map</a></li>
      <li><a href="explore.html">Explore</a></li>
      <li><a href="methodology.html">Methodology</a></li>
      <li><a href="about.html">About</a></li>
    </ul>
    <div class="nav-right">
      <span class="nav-live-badge">
        <span class="nav-live-dot"></span>
        LIVE DATA
      </span>
      <button class="theme-toggle" id="theme-toggle" title="Toggle theme">☀️</button>
      <button class="mobile-menu-btn" id="mobile-menu-btn">☰</button>
    </div>
  </nav>`;
}

function renderFooter() {
  return `
  <footer class="footer">
    <div class="container">
      <div class="footer-grid">
        <div>
          <div class="footer-brand">AERSI</div>
          <p class="footer-desc">
            Air Exposure Severity Index — a station-level rolling index
            that captures the intensity, persistence, and volatility of
            air pollution exposure across India.
          </p>
        </div>
        <div>
          <div class="footer-heading">Navigate</div>
          <ul class="footer-links">
            <li><a href="index.html">Home</a></li>
            <li><a href="map.html">Map</a></li>
            <li><a href="explore.html">Explore</a></li>
            <li><a href="methodology.html">Methodology</a></li>
            <li><a href="about.html">About</a></li>
          </ul>
        </div>
        <div>
          <div class="footer-heading">Data</div>
          <ul class="footer-links">
            <li><a href="https://data.gov.in" target="_blank">CPCB via data.gov.in</a></li>
            <li><a href="https://github.com/Dhruva-0206/aersi-air-exposure-index" target="_blank">GitHub Repository</a></li>
            <li><a href="methodology.html">Formula Reference</a></li>
          </ul>
        </div>
      </div>
      <div class="footer-bottom">
        <span>© 2026 AERSI · aersi.live</span>
        <span>Data updates daily at 10:30 AM IST · Built with CPCB open data</span>
      </div>
    </div>
  </footer>`;
}
