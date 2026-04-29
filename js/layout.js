function renderNav() {
  return `
  <nav class="nav">
    <a href="index.html" class="nav-brand">
      <span class="nav-brand-mark">AE</span>
      AERSI
    </a>
    <ul class="nav-links">
      <li><a href="index.html">Home</a></li>
      <li><a href="why.html">Why AERSI?</a></li>
      <li><a href="explore.html">Explore</a></li>
      <li><a href="methodology.html">Methodology</a></li>
      <li><a href="about.html">About</a></li>
    </ul>
    <div class="nav-right">
      <span class="nav-live">
        <span class="nav-live-dot"></span>
        LIVE · <span id="nav-station-count">547</span> STATIONS
      </span>
      <a href="map.html" class="nav-cta">View Map →</a>
      <button class="mobile-menu-btn" id="mobile-menu-btn" style="display:none;">☰</button>
    </div>
  </nav>`;
}

function renderFooter() {
  return `
  <footer class="footer">
    <div class="container">
      <div class="footer-grid">
        <div>
          <div class="footer-brand">
            <span class="footer-brand-mark">AE</span>
            AERSI
          </div>
          <p class="footer-desc">
            Air Exposure Severity Index — a station-level rolling index
            that captures the intensity, persistence, and volatility of
            air pollution exposure across India. Updated daily.
          </p>
        </div>
        <div>
          <div class="footer-heading">Navigate</div>
          <ul class="footer-links">
            <li><a href="index.html">Home</a></li>
            <li><a href="map.html">Live Map</a></li>
            <li><a href="why.html">Why AERSI?</a></li>
            <li><a href="methodology.html">Methodology</a></li>
            <li><a href="about.html">About</a></li>
          </ul>
        </div>
        <div>
          <div class="footer-heading">Data</div>
          <ul class="footer-links">
            <li><a href="https://data.gov.in" target="_blank">CPCB via data.gov.in</a></li>
            <li><a href="methodology.html">Formula Reference</a></li>
          </ul>
        </div>
        <div>
          <div class="footer-heading">Contact</div>
          <ul class="footer-links">
            <li><a href="about.html">About the Project</a></li>
            <li><a href="mailto:aersi.org@gmail.com">aersi.org@gmail.com</a></li>
            <li><a href="https://www.linkedin.com/in/dhruva-chakrabarty/" target="_blank">LinkedIn</a></li>
          </ul>
        </div>
      </div>
      <div class="footer-bottom">
        <span>© 2026 AERSI · aersi.live · Built by Dhruva Chakrabarty</span>
        <span>Data: CPCB · Updated daily 10:30 AM IST</span>
      </div>
    </div>
  </footer>`;
}
