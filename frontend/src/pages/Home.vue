<template>
  <main class="home-page">
    <Header />

    <!-- ═══ HERO ═══════════════════════════════════════════════ -->
    <section class="hero">
      <div class="hero-watermark" aria-hidden="true">
        <img src="../assets/logo.png" alt="" class="watermark-img" />
      </div>
      <div class="hero-glow" aria-hidden="true"></div>

      <div class="wrap hero-content">
        <div class="eyebrow fade-up">
          <span class="pulse-dot"></span> Pro Players Choice
        </div>

        <h1 class="fade-up delay-1">
          Dominate Every Map.<br>
          <span class="gradient-text">Win Every Round.</span>
        </h1>

        <p class="lead fade-up delay-2">
          Premium CS2 strategies, grenade lineups and pro-level tactics —
          built by esports professionals to boost your winrate fast.
        </p>

        <div class="stat-row fade-up delay-3">
          <div class="stat-line">
            <div class="stat">
              <div class="stat-num">{{ mapsCount }}+</div>
              <div class="stat-lbl">Maps</div>
            </div>
            <div class="stat-divider"></div>
            <div class="stat">
              <div class="stat-num">{{ strategiesCount }}+</div>
              <div class="stat-lbl">Strategies</div>
            </div>
          </div>
          <div class="stat-line">
            <div class="stat">
              <div class="stat-num">500+</div>
              <div class="stat-lbl">Premium Users</div>
            </div>
            <div class="stat-divider"></div>
            <div class="stat">
              <div class="stat-num">92%</div>
              <div class="stat-lbl">Winrate Boost</div>
            </div>
          </div>
        </div>

        <div class="cta-row fade-up delay-4">
          <button class="btn-primary">Get Premium Access</button>
          <button class="btn-secondary" @click="scrollToMaps">Browse Strategies ↓</button>
        </div>

        <div class="trust-strip fade-up delay-5">
          <span>Instant access</span>
          <span>All maps included</span>
          <span>Weekly updates</span>
          <span>Cancel anytime</span>
        </div>
      </div>
    </section>

    <!-- ═══ WHY SECTION ════════════════════════════════════════ -->
    <section class="why-section">
      <div class="wrap">
        <div class="section-head fade-up">
          <div class="eyebrow"><span class="pulse-dot"></span> Why StratMaster</div>
          <h2>Everything you need<br>to climb the ranks</h2>
        </div>

        <div class="why-grid">
          <div
            v-for="(item, i) in whyItems"
            :key="item.title"
            class="why-card fade-up"
            :class="`delay-${i % 3 + 1}`"
          >
            <div class="why-card-top">
              <span class="why-num">0{{ i + 1 }}</span>
              <div class="why-line"></div>
            </div>
            <h3>{{ item.title }}</h3>
            <p>{{ item.desc }}</p>
          </div>
        </div>
      </div>
    </section>

    <!-- ═══ MAPS / CATALOG ════════════════════════════════════= -->
    <section class="maps-section" id="strategies">
      <div class="wrap">
        <div class="section-head fade-up">
          <div class="eyebrow"><span class="pulse-dot"></span> Strategy Catalog</div>
          <h2>Choose Your Map</h2>
          <p>Grenade lineups, site executes and retake setups for T and CT — every major map covered.</p>
        </div>

        <div class="search-wrap fade-up delay-1">
          <svg class="search-icon" viewBox="0 0 20 20" fill="none">
            <circle cx="9" cy="9" r="6" stroke="currentColor" stroke-width="1.5"/>
            <path d="M14 14l3 3" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
          </svg>
          <input
            v-model="searchQuery"
            type="text"
            class="search-input"
            placeholder="Search maps…"
            @input="onSearch"
          />
          <button v-if="searchQuery" class="search-clear" @click="clearSearch">✕</button>
        </div>

        <div v-if="isLoading" class="loader-row">
          <div class="spinner"></div>
          <span>Loading maps…</span>
        </div>

        <div v-else-if="filteredMaps.length === 0" class="no-results">
          <span>No maps found for <em>"{{ searchQuery }}"</em></span>
        </div>

        <div v-else class="cards-grid" ref="gridRef">
          <div
            v-for="map in filteredMaps"
            :key="map.id"
            class="map-card"
          >
            <div class="map-thumb">
              <span class="map-thumb-name">{{ map.name }}</span>
              <div class="map-thumb-overlay"></div>
            </div>
            <div class="map-card-body">
              <h3>{{ map.name }}</h3>
              <p class="map-card-link">View tactics &amp; lineups →</p>
            </div>
            <div class="map-card-glow"></div>
          </div>
        </div>
      </div>
    </section>

    <!-- ═══ FINAL CTA ══════════════════════════════════════════ -->
    <section class="final-cta-section" id="pricing">
      <div class="wrap">
        <div class="cta-box fade-up">
          <div class="cta-box-glow" aria-hidden="true"></div>

          <div class="cta-inner">
            <div class="cta-left">
              <div class="cta-badge">Limited Offer</div>
              <h2>Join the Elite</h2>
              <p>
                Unlock every map, every strategy, every grenade lineup
                used by top-ranked teams worldwide.
              </p>
              <div class="cta-actions">
                <button class="btn-primary cta-btn-main">Get Premium Now</button>
                <button class="btn-secondary" id="referral">Share &amp; Earn Coins</button>
              </div>
            </div>

            <div class="cta-right">
              <div class="cta-feature-list">
                <div class="cta-feature">
                  <div class="cta-feature-check"></div>
                  <div>
                    <strong>All maps unlocked</strong>
                    <span>Full access to every supported map</span>
                  </div>
                </div>
                <div class="cta-feature">
                  <div class="cta-feature-check"></div>
                  <div>
                    <strong>Pro-level tactics</strong>
                    <span>Strategies vetted by high-ranked players</span>
                  </div>
                </div>
                <div class="cta-feature">
                  <div class="cta-feature-check"></div>
                  <div>
                    <strong>Weekly updates</strong>
                    <span>New strategies added every week</span>
                  </div>
                </div>
                <div class="cta-feature">
                  <div class="cta-feature-check"></div>
                  <div>
                    <strong>Grenade lineups</strong>
                    <span>Precise smoke &amp; flash positions for every site</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>

    <Footer />
  </main>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick, watch } from 'vue'
import Header from '../components/Header.vue'
import Footer from '../components/Footer.vue'

// ── Stub data (replace with API calls in Stage 3) ──────────────
const allMaps = [
  { id: 1, name: 'Mirage' },
  { id: 2, name: 'Inferno' },
  { id: 3, name: 'Dust2' },
  { id: 4, name: 'Nuke' },
  { id: 5, name: 'Ancient' },
  { id: 6, name: 'Anubis' },
]
const maps        = ref([...allMaps])
const isLoading   = ref(false)
const searchQuery = ref('')
const gridRef     = ref(null)

const mapsCount       = computed(() => maps.value.length)
const strategiesCount = computed(() => maps.value.length * 15)

// ── Search — case-insensitive, trims whitespace ────────────────
const filteredMaps = computed(() => {
  const q = searchQuery.value.trim().toLowerCase()
  if (!q) return allMaps
  return allMaps.filter(m => m.name.toLowerCase().includes(q))
})

function onSearch() { /* v-model handles reactivity */ }
function clearSearch() { searchQuery.value = '' }

// ── Why items — no emojis, clean copy ─────────────────────────
const whyItems = [
  {
    title: 'Pro-Sourced Tactics',
    desc:  'Every strategy is reviewed by active high-ranked players and esports coaches before publishing.'
  },
  {
    title: 'Grenade Lineups',
    desc:  'Exact smoke, flash, molotov and HE positions for every site entry on every supported map.'
  },
  {
    title: 'Fast Execution Setups',
    desc:  'Rush setups timed under 40 seconds — coordinated, precise and designed to overwhelm defenses.'
  },
  {
    title: 'Real Winrate Data',
    desc:  'Each strategy displays a success rate derived from thousands of ranked match simulations.'
  },
  {
    title: 'Subscriber-Only Content',
    desc:  'Premium strategies are locked and not available on any public database or YouTube channel.'
  },
  {
    title: 'Weekly Meta Updates',
    desc:  'As patches drop and metas shift, strategies are revised and new ones added every week.'
  },
]

// ── Intersection Observer ──────────────────────────────────────
let observer = null

function observeAll() {
  if (!observer) return
  document.querySelectorAll('.fade-up:not(.visible)').forEach(el => observer.observe(el))
}

onMounted(() => {
  observer = new IntersectionObserver(
    entries => entries.forEach(e => {
      if (e.isIntersecting) {
        e.target.classList.add('visible')
        observer.unobserve(e.target)
      }
    }),
    { threshold: 0.1 }
  )
  observeAll()
})

onUnmounted(() => observer?.disconnect())

function scrollToMaps() {
  document.getElementById('strategies')?.scrollIntoView({ behavior: 'smooth' })
}
</script>

<style scoped>
.home-page {
  min-height: 100vh;
  background: var(--bg);
}

/* ── Hero ─────────────────────────────────────────────── */
.hero {
  position: relative;
  padding: 110px 0 100px;
  overflow: hidden;
}
.hero-watermark {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  pointer-events: none;
  z-index: 0;
}
.watermark-img {
  width: min(640px, 90vw);
  opacity: 0.10;
  filter: grayscale(40%);
  animation: watermark-drift 10s ease-in-out infinite;
}
@keyframes watermark-drift {
  0%,100% { transform: scale(1) translateY(0); }
  50%      { transform: scale(1.04) translateY(-12px); }
}
.hero-glow {
  position: absolute;
  top: -80px; left: 50%;
  transform: translateX(-50%);
  width: 800px; height: 600px;
  background: radial-gradient(ellipse, rgba(255,154,0,0.13) 0%, transparent 68%);
  pointer-events: none;
  z-index: 0;
}
.hero-content { position: relative; z-index: 1; }

/* Eyebrow */
.eyebrow {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  background: var(--bg-elevated);
  border: 1px solid var(--line);
  border-radius: 99px;
  padding: 6px 16px;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--accent);
  margin-bottom: 28px;
}
.pulse-dot {
  width: 7px; height: 7px;
  background: var(--accent);
  border-radius: 50%;
  box-shadow: 0 0 8px var(--accent);
  animation: pulse 2s ease-in-out infinite;
  flex-shrink: 0;
}
@keyframes pulse {
  0%,100% { box-shadow: 0 0 0 0   rgba(255,154,0,0.5); }
  50%      { box-shadow: 0 0 0 8px rgba(255,154,0,0); }
}

h1 {
  font-size: clamp(36px, 7vw, 60px);
  font-weight: 900;
  line-height: 1.1;
  letter-spacing: -0.03em;
  margin-bottom: 24px;
  color: var(--text);
}
.gradient-text {
  background: linear-gradient(90deg, var(--accent), var(--accent-2));
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
}
.lead {
  font-size: 17px;
  color: var(--text-dim);
  line-height: 1.75;
  max-width: 520px;
  margin-bottom: 48px;
}

/* Stats */
.stat-row {
  display: flex;
  flex-direction: column;
  gap: 20px;
  margin-bottom: 48px;
}
.stat-line {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 0;
}
.stat { padding: 0 28px; }
.stat:first-child { padding-left: 0; }
.stat-divider { width: 1px; height: 40px; background: var(--line); flex-shrink: 0; }
.stat-num {
  font-size: 34px; font-weight: 900;
  color: var(--text); letter-spacing: -0.04em; line-height: 1;
}
.stat-lbl {
  font-size: 12px; font-weight: 600;
  color: var(--accent); letter-spacing: 0.1em;
  text-transform: uppercase; margin-top: 6px;
}

/* CTA row */
.cta-row { display: flex; gap: 14px; flex-wrap: wrap; margin-bottom: 36px; }

/* Trust strip */
.trust-strip { display: flex; gap: 0; flex-wrap: wrap; }
.trust-strip span {
  font-size: 13px; font-weight: 500;
  color: var(--text-dim);
  padding: 0 20px;
  border-left: 1px solid var(--line);
}
.trust-strip span:first-child { padding-left: 0; border-left: none; }

/* ── Why section ──────────────────────────────────────── */
.why-section { padding: 80px 0; }

.section-head { text-align: center; margin-bottom: 52px; }
.section-head h2 {
  font-size: clamp(28px, 5vw, 42px);
  font-weight: 800; letter-spacing: -0.03em; margin-top: 16px;
}
.section-head p {
  color: var(--text-dim); font-size: 17px;
  line-height: 1.65; max-width: 520px;
  margin: 14px auto 0;
}

.why-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 1px;
  background: var(--line);
  border: 1px solid var(--line);
  border-radius: var(--radius-lg);
  overflow: hidden;
}
.why-card {
  background: var(--bg-elevated);
  padding: 36px 32px;
  transition: background 0.25s;
}
.why-card:hover { background: var(--bg-elevated-2); }

.why-card-top {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 20px;
}
.why-num {
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 0.12em;
  color: var(--accent);
  font-variant-numeric: tabular-nums;
  flex-shrink: 0;
}
.why-line {
  flex: 1;
  height: 1px;
  background: linear-gradient(90deg, rgba(255,154,0,0.5), transparent);
}
.why-card h3 {
  font-size: 17px; font-weight: 700;
  letter-spacing: -0.01em; margin-bottom: 10px;
  color: var(--text);
}
.why-card p {
  font-size: 14px; color: var(--text-dim); line-height: 1.7;
}

/* ── Maps section ─────────────────────────────────────── */
.maps-section { padding: 80px 0 100px; }

.search-wrap {
  position: relative;
  max-width: 440px;
  margin: 0 auto 44px;
  display: flex;
  align-items: center;
}
.search-icon {
  position: absolute;
  left: 16px;
  width: 17px; height: 17px;
  color: var(--text-dim);
  flex-shrink: 0;
}
.search-input {
  width: 100%;
  padding: 14px 44px 14px 46px;
  background: var(--bg-elevated);
  border: 1.5px solid var(--line);
  border-radius: 12px;
  font-size: 15px; font-family: inherit;
  color: var(--text);
  transition: border-color 0.2s, box-shadow 0.2s;
}
.search-input::placeholder { color: var(--text-dim); }
.search-input:focus {
  outline: none;
  border-color: var(--accent);
  box-shadow: 0 0 0 3px rgba(255,154,0,0.12);
}
.search-clear {
  position: absolute;
  right: 14px;
  background: none; border: none;
  color: var(--text-dim); font-size: 14px;
  cursor: pointer; padding: 4px;
  transition: color 0.2s;
}
.search-clear:hover { color: var(--text); }

.loader-row {
  display: flex; align-items: center; justify-content: center;
  gap: 14px; padding: 60px 0;
  color: var(--text-dim); font-size: 15px;
}
.spinner {
  width: 26px; height: 26px;
  border: 2.5px solid var(--line);
  border-top-color: var(--accent);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

.no-results {
  text-align: center; padding: 60px 0;
  color: var(--text-dim); font-size: 15px;
}
.no-results em { color: var(--text); font-style: normal; font-weight: 600; }

/* Cards grid */
.cards-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(290px, 1fr));
  gap: 20px;
}
.map-card {
  background: var(--bg-elevated);
  border: 1px solid var(--line);
  border-radius: var(--radius-lg);
  overflow: hidden;
  cursor: pointer;
  position: relative;
  transition: border-color 0.25s, transform 0.25s;
}
.map-card:hover {
  border-color: rgba(255,154,0,0.4);
  transform: translateY(-5px);
}
.map-card:hover .map-card-glow  { opacity: 1; }
.map-card:hover .map-card-link  { color: var(--accent); }

.map-card-glow {
  position: absolute; bottom: 0; left: 0; right: 0;
  height: 60px;
  background: linear-gradient(to top, rgba(255,154,0,0.1), transparent);
  opacity: 0; transition: opacity 0.3s;
  pointer-events: none; z-index: 0;
}
.map-thumb {
  aspect-ratio: 16/9;
  background: repeating-linear-gradient(
    45deg,
    var(--bg-elevated-2) 0 2px,
    var(--bg-elevated) 2px 14px
  );
  display: flex; align-items: center; justify-content: center;
  position: relative;
}
.map-thumb-name {
  font-size: 26px; font-weight: 900;
  letter-spacing: 0.08em; text-transform: uppercase;
  color: rgba(255,255,255,0.10); z-index: 2;
}
.map-thumb-overlay {
  position: absolute; inset: 0;
  background: linear-gradient(to top, var(--bg-elevated) 0%, transparent 60%);
  z-index: 1;
}
.map-card-body { padding: 20px 22px 24px; position: relative; z-index: 1; }
.map-card-body h3 {
  font-size: 20px; font-weight: 700;
  letter-spacing: -0.01em; margin-bottom: 8px;
}
.map-card-link {
  font-size: 14px; font-weight: 600;
  color: var(--text-dim); transition: color 0.2s;
}

/* ── Final CTA ────────────────────────────────────────── */
.final-cta-section { padding: 40px 0 80px; }

.cta-box {
  position: relative;
  background: var(--bg-elevated);
  border: 1px solid var(--line);
  border-radius: var(--radius-xl);
  overflow: hidden;
}
.cta-box-glow {
  position: absolute;
  top: -100px; right: -100px;
  width: 500px; height: 500px;
  background: radial-gradient(ellipse, rgba(255,154,0,0.08) 0%, transparent 65%);
  pointer-events: none;
}

/* Two-column layout inside CTA */
.cta-inner {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0;
  position: relative;
  z-index: 1;
}
.cta-left {
  padding: 64px 48px 64px 56px;
  border-right: 1px solid var(--line);
}
.cta-right {
  padding: 64px 56px 64px 48px;
  display: flex;
  align-items: center;
}

.cta-badge {
  display: inline-block;
  background: rgba(255,154,0,0.12);
  color: var(--accent);
  border: 1px solid rgba(255,154,0,0.3);
  font-size: 11px; font-weight: 700;
  letter-spacing: 0.12em; text-transform: uppercase;
  padding: 5px 14px; border-radius: 99px;
  margin-bottom: 20px;
}
.cta-left h2 {
  font-size: clamp(28px, 4vw, 42px);
  font-weight: 900; letter-spacing: -0.03em;
  margin-bottom: 16px; line-height: 1.1;
}
.cta-left > p {
  color: var(--text-dim); font-size: 16px;
  line-height: 1.7; margin-bottom: 36px;
}
.cta-actions { display: flex; gap: 12px; flex-wrap: wrap; }
.cta-btn-main { font-size: 15px; }

/* Feature list in right column */
.cta-feature-list { display: flex; flex-direction: column; gap: 24px; width: 100%; }
.cta-feature {
  display: grid;
  grid-template-columns: 20px 1fr;
  gap: 14px;
  align-items: start;
}
.cta-feature-check {
  width: 18px; height: 18px; margin-top: 2px;
  border: 1.5px solid var(--accent);
  border-radius: 4px; flex-shrink: 0;
  position: relative;
}
.cta-feature-check::after {
  content: '';
  position: absolute;
  top: 3px; left: 5px;
  width: 5px; height: 9px;
  border: 2px solid var(--accent);
  border-top: none; border-left: none;
  transform: rotate(45deg);
}
.cta-feature strong {
  display: block;
  font-size: 15px; font-weight: 700;
  color: var(--text); margin-bottom: 3px;
}
.cta-feature span {
  font-size: 13px; color: var(--text-dim); line-height: 1.5;
}

/* ── Responsive ───────────────────────────────────────── */
@media (max-width: 900px) {
  .why-grid { grid-template-columns: 1fr 1fr; }
  .cta-inner { grid-template-columns: 1fr; }
  .cta-left { border-right: none; border-bottom: 1px solid var(--line); padding: 48px 32px; }
  .cta-right { padding: 40px 32px 48px; }
}
@media (max-width: 640px) {
  .hero { padding: 80px 0 70px; }
  .stat-row { gap: 14px; }
  .stat-line { gap: 0; }
  .stat { padding: 0 16px; }
  .stat:first-child { padding-left: 0; }
  .why-grid { grid-template-columns: 1fr; }
  .trust-strip span { padding: 6px 0; border-left: none; width: 50%; }
  .trust-strip span:first-child { border-left: none; }
}
</style>