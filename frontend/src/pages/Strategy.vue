<template>
  <main class="strategy-page">
    <Header />

    <div v-if="isLoading" class="loading">
      <div class="spinner"></div>
      <p>Loading strategy...</p>
    </div>

    <div v-else-if="lockReason" class="wrap locked-wrap">
      <section class="locked-card">
        <span class="locked-icon">
          <svg viewBox="0 0 24 24" fill="none" width="28" height="28">
            <rect x="5" y="11" width="14" height="9" rx="2" stroke="currentColor" stroke-width="1.6"/>
            <path d="M8 11V8a4 4 0 018 0v3" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/>
          </svg>
        </span>
        <h1>{{ lockReason === 'auth' ? 'Sign in to view this strategy' : 'Premium strategy' }}</h1>
        <p>
          {{ lockReason === 'auth'
            ? 'Open StratMaster inside Telegram to sign in and continue.'
            : 'This strategy is part of the premium library. Unlock it — along with every map, lineup and timing — with a subscription.' }}
        </p>
        <router-link v-if="lockReason !== 'auth'" to="/pricing" class="btn-primary locked-cta">Unlock Premium</router-link>
        <button class="back-btn locked-back" @click="router.push('/')">Back to Maps</button>
      </section>
    </div>

    <div v-else-if="!strategy" class="loading">
      <p>Strategy not found.</p>
    </div>

    <div v-else class="wrap strategy-content">

      <!-- ═══ BREADCRUMB ══════════════════════════ -->
      <nav class="breadcrumb" aria-label="Breadcrumb">
        <button class="back-btn" @click="router.push('/')">
          <svg viewBox="0 0 16 16" fill="none" width="14" height="14">
            <path d="M10 3L5 8l5 5" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
          Home
        </button>
        <span class="breadcrumb-sep">/</span>
        <button class="back-btn" @click="router.push('/map/' + strategy.map_id)">
          {{ mapName }} Strategies
        </button>
      </nav>

      <!-- ═══ HEADER ══════════════════════════════ -->
      <section class="strategy-header">
        <h1 class="strategy-title">{{ strategy.title }}</h1>

        <div class="meta-row">
          <!-- Side / Plant / Speed tags -->
          <span class="tag tag-side">{{ sideLabel }}</span>
          <span class="tag tag-plant">Site {{ strategy.plant }}</span>
          <span class="tag tag-speed">{{ strategy.speed }}</span>

          <span class="meta-divider" aria-hidden="true"></span>

          <!-- Difficulty -->
          <span class="difficulty-group">
            <span class="difficulty-label">Difficulty</span>
            <span class="stars">
              <span
                v-for="i in 5" :key="i"
                class="star"
                :class="{ filled: i <= strategy.difficulty_stars }"
              >★</span>
            </span>
          </span>

          <span class="meta-divider" aria-hidden="true"></span>

          <!-- Success rate -->
          <span class="success-rate">
            <span class="rate-num">{{ strategy.success_rate }}%</span>
            <span class="rate-lbl">win rate</span>
          </span>

          <!-- Author -->
          <span v-if="strategy.author" class="author">
            by <strong>{{ strategy.author }}</strong>
          </span>

          <!-- Free / Premium badge -->
          <span class="access-badge" :class="strategy.is_free ? 'free' : 'premium'">
            {{ strategy.is_free ? 'Free' : 'Premium' }}
          </span>
        </div>

        <div class="header-actions-row">
          <nav v-if="quickNavItems.length" class="quick-nav">
            <a
              v-for="item in quickNavItems" :key="item.id"
              :href="'#' + item.id"
              class="quick-nav-item"
              @click.prevent="scrollToSection(item.id)"
            >{{ item.label }}</a>
          </nav>
          <button class="share-btn" @click="copyLink">
            <svg viewBox="0 0 20 20" fill="none" width="14" height="14">
              <path d="M7 10a2.5 2.5 0 100-5 2.5 2.5 0 000 5zM7 10a2.5 2.5 0 110 5 2.5 2.5 0 010-5zM13 12.5a2.5 2.5 0 100 5 2.5 2.5 0 000-5zM13 7.5a2.5 2.5 0 100-5 2.5 2.5 0 000 5z" stroke="currentColor" stroke-width="1.4" stroke-linejoin="round"/>
              <path d="M9.2 8.6l3.6-2.2M9.2 11.4l3.6 2.2" stroke="currentColor" stroke-width="1.4"/>
            </svg>
            {{ linkCopied ? 'Link copied' : 'Copy link' }}
          </button>
        </div>
      </section>

      <!-- ═══ MAIN IMAGE (images[0]) — animated replay if we have one ══ -->
      <section v-if="mainImage" class="main-image-section">
        <TacticsPlayer
          v-if="hasTacticsAnimation"
          :image-url="mainImage.image_url"
          :grenades="strategy.grenades || []"
          :player-paths="strategy.player_paths || []"
        />
        <div v-else class="image-container">
          <img :src="mainImage.image_url" alt="Strategy map" class="main-image" />
        </div>
      </section>

      <!-- ═══ TIMINGS ══════════════════════════════
           timings_description format (one line per timing):
           "00:10 — Rush mid\n00:50 — Plant A\n01:20 — Second contact"
           Each timing at index N links to images[N+1]
      ════════════════════════════════════════════ -->
      <section v-if="timings.length" id="timings" class="timings-section">
        <h2 class="section-title">Timings</h2>

        <div class="timings-list">
          <div
            v-for="(t, i) in timings"
            :key="i"
            class="timing-item"
          >
            <!-- Timing label: "1) 00:10" -->
            <div class="timing-header">
              <span class="timing-index">{{ i + 1 }})</span>
              <span class="timing-time">{{ t.time }}</span>
              <span class="timing-desc">{{ t.description }}</span>
            </div>

            <!-- Spoiler image: images[i+1] -->
            <div v-if="timingImages[i]" class="spoiler">
              <button
                class="spoiler-toggle"
                @click="toggleSpoiler(i)"
                :aria-expanded="openSpoilers[i]"
              >
                <span class="spoiler-arrow">{{ openSpoilers[i] ? '▼' : '▶' }}</span>
                {{ openSpoilers[i] ? 'Hide screenshot' : 'Show screenshot' }}
              </button>
              <transition name="expand">
                <div v-show="openSpoilers[i]" class="spoiler-content">
                  <img :src="timingImages[i].image_url" :alt="`Timing ${i + 1}`" class="spoiler-img" />
                </div>
              </transition>
            </div>
          </div>
        </div>
      </section>

      <!-- ═══ GRENADES ════════════════════════════ -->
      <section v-if="strategy.grenades && strategy.grenades.length" id="grenades" class="grenades-section">
        <h2 class="section-title">Grenades</h2>

        <div class="grenades-list">
          <div
            v-for="(g, i) in strategy.grenades"
            :key="g.id"
            class="grenade-item"
          >
            <button
              class="spoiler-toggle grenade-toggle"
              @click="toggleGrenade(i)"
              :aria-expanded="openGrenades[i]"
            >
              <span class="grenade-type-icon" v-html="grenadeIcon(g.grenade_type)"></span>
              <span class="grenade-type-label">{{ grenadeTypeLabel(g.grenade_type) }}</span>
              <span class="grenade-target">→ {{ g.target }}</span>
              <span class="grenade-timing">{{ g.timing }}</span>
              <span class="spoiler-arrow ml-auto">{{ openGrenades[i] ? '▼' : '▶' }}</span>
            </button>

            <transition name="expand">
              <div v-show="openGrenades[i]" class="spoiler-content grenade-content">
              <video
                v-if="g.video_url && isVideo(g.video_url)"
                :src="g.video_url"
                class="grenade-media"
                autoplay loop muted playsinline
              />
              <img
                v-else-if="g.video_url"
                :src="g.video_url"
                :alt="`${g.grenade_type} to ${g.target}`"
                class="grenade-media"
              />
              <p v-else class="grenade-no-media">No lineup video available yet.</p>
              </div>
            </transition>
          </div>
        </div>
      </section>

      <!-- ═══ ROLES / NOTES ════════════════════════ -->
      <section v-if="strategy.roles_description" id="roles" class="roles-section">
        <h2 class="section-title">Roles & Notes</h2>
        <p class="roles-text">{{ strategy.roles_description }}</p>
      </section>

    </div>

    <Footer />
  </main>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { strategiesAPI } from '../api/strategies'
import Header from '../components/Header.vue'
import Footer from '../components/Footer.vue'
import TacticsPlayer from '../components/TacticsPlayer.vue'
import { grenadeTypeLabel } from '../utils/grenadeLabels'

const route  = useRoute()
const router = useRouter()

const strategy   = ref(null)
const mapName    = ref('')
const isLoading  = ref(true)
const lockReason = ref(null) // null | 'auth' | 'subscription'
const openSpoilers = ref({})
const openGrenades = ref({})

// ── Parsing helpers ────────────────────────────────────────────

// timings_description: "00:10 — Rush mid\n00:50 — Plant A"
// Each line → { time, description }
const timings = computed(() => {
  const raw = strategy.value?.timings_description
  if (!raw) return []
  return raw
    .split('\n')
    .map(line => line.trim())
    .filter(Boolean)
    .map(line => {
      // Split on first " — " or " - " or first space
      const match = line.match(/^(\d{1,2}:\d{2})\s*[—\-–]\s*(.+)$/)
      if (match) return { time: match[1], description: match[2] }
      // Fallback: first word = time, rest = description
      const parts = line.split(' ')
      return { time: parts[0], description: parts.slice(1).join(' ') }
    })
})

// images[0] = main map overview
// images[1..N] = timing screenshots (index i → timing i-1)
const mainImage = computed(() => {
  const imgs = strategy.value?.images
  if (!imgs?.length) return null
  return imgs.find(img => img.order === 0) ?? imgs[0]
})

// Only swap in the animated player when there's actually something to
// animate — a strategy with no paths/trajectories keeps the plain image.
const hasTacticsAnimation = computed(() => {
  const paths = strategy.value?.player_paths || []
  const grenades = strategy.value?.grenades || []
  return paths.some(p => p.waypoints?.length >= 2) ||
    grenades.some(g => g.from_x != null && g.to_x != null)
})

const timingImages = computed(() => {
  const imgs = strategy.value?.images
  if (!imgs?.length) return []
  // images with order >= 1 sorted by order, one per timing
  return imgs
    .filter(img => img.order >= 1)
    .sort((a, b) => a.order - b.order)
})

// Side display label
const sideLabel = computed(() => {
  if (!strategy.value) return ''
  return strategy.value.side === 'T_side' ? 'Terrorist' : 'Counter-Terrorist'
})

// ── Quick nav ──────────────────────────────────────────────────
const quickNavItems = computed(() => {
  const items = []
  if (timings.value.length) items.push({ id: 'timings', label: 'Timings' })
  if (strategy.value?.grenades?.length) items.push({ id: 'grenades', label: 'Grenades' })
  if (strategy.value?.roles_description) items.push({ id: 'roles', label: 'Roles' })
  return items
})
function scrollToSection(id) {
  document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

// ── Share ──────────────────────────────────────────────────────
const linkCopied = ref(false)
function copyLink() {
  navigator.clipboard?.writeText(window.location.href)
  linkCopied.value = true
  setTimeout(() => { linkCopied.value = false }, 1800)
}

// ── Spoiler toggles ────────────────────────────────────────────
function toggleSpoiler(i) {
  openSpoilers.value[i] = !openSpoilers.value[i]
}
function toggleGrenade(i) {
  openGrenades.value[i] = !openGrenades.value[i]
}

// ── Grenade helpers ────────────────────────────────────────────
// Simple stroke-based SVGs matching the rest of the site's icon style —
// emoji rendered inconsistently across OS/browsers (blank on some Android/Linux fonts).
const grenadeIcons = {
  smoke: '<svg viewBox="0 0 20 20" fill="none" width="16" height="16"><circle cx="7" cy="12" r="3.2" stroke="currentColor" stroke-width="1.5"/><circle cx="12" cy="9" r="4" stroke="currentColor" stroke-width="1.5"/><circle cx="14.5" cy="13.5" r="2.2" stroke="currentColor" stroke-width="1.5"/></svg>',
  flash: '<svg viewBox="0 0 20 20" fill="none" width="16" height="16"><path d="M11 2L4 12h5l-1 6 8-11h-5l1-5z" stroke="currentColor" stroke-width="1.4" stroke-linejoin="round"/></svg>',
  molotov: '<svg viewBox="0 0 20 20" fill="none" width="16" height="16"><path d="M8 8c-2 2-3 4-3 6a5 5 0 0010 0c0-2-1-4-3-6l-2-4-2 4z" stroke="currentColor" stroke-width="1.4" stroke-linejoin="round"/><path d="M9 3.5h2" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/></svg>',
  he: '<svg viewBox="0 0 20 20" fill="none" width="16" height="16"><circle cx="10" cy="11" r="6" stroke="currentColor" stroke-width="1.5"/><path d="M10 5V2M13 3l1.5-1.5M7 3L5.5 1.5" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/></svg>',
  decoy: '<svg viewBox="0 0 20 20" fill="none" width="16" height="16"><path d="M4 8v4l3 1v-6l-3 1z" stroke="currentColor" stroke-width="1.4" stroke-linejoin="round"/><path d="M7 7l7-3v12l-7-3" stroke="currentColor" stroke-width="1.4" stroke-linejoin="round"/><path d="M15.5 8.5a2 2 0 010 3" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/></svg>',
}
const defaultGrenadeIcon = '<svg viewBox="0 0 20 20" fill="none" width="16" height="16"><circle cx="10" cy="11" r="6" stroke="currentColor" stroke-width="1.5"/></svg>'
function grenadeIcon(type) {
  return grenadeIcons[type] ?? defaultGrenadeIcon
}
function isVideo(url) {
  return /\.(mp4|webm|mov|gif)(\?|$)/i.test(url)
}

// ── Fetch ──────────────────────────────────────────────────────
onMounted(async () => {
  // The browser's own scroll restoration (used on router.back()/forward())
  // fights with our manual scroll-to-top below and is what causes pages
  // to open mid-scroll — turn it off and let us control scroll position.
  if ('scrollRestoration' in window.history) {
    window.history.scrollRestoration = 'manual'
  }
  window.scrollTo({ top: 0, behavior: 'auto' })

  try {
    const [strategyRes, maps] = await Promise.all([
      strategiesAPI.getStrategy(route.params.id),
      strategiesAPI.getMaps(),
    ])
    strategy.value = strategyRes
    mapName.value = maps.find(m => m.id === strategyRes.map_id)?.name ?? 'Map'
  } catch (err) {
    const status = err.response?.status
    if (status === 401) lockReason.value = 'auth'
    else if (status === 403) lockReason.value = 'subscription'
    else console.error('Failed to load strategy:', err)
  } finally {
    isLoading.value = false
  }
})
</script>

<style scoped>
.strategy-page {
  min-height: 100vh;
  background: var(--bg);
}

.loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 60vh;
  gap: 16px;
  color: var(--text-dim);
}

.spinner {
  width: 36px; height: 36px;
  border: 2.5px solid var(--line);
  border-top-color: var(--accent);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

/* ── Locked / paywall state ───────────────────── */
.locked-wrap {
  min-height: 60vh;
  display: flex; align-items: center; justify-content: center;
  padding: 36px 20px;
}
.locked-card {
  max-width: 420px;
  text-align: center;
  background: var(--bg-elevated);
  border: 1px solid rgba(255,154,0,0.3);
  border-radius: var(--radius-lg, 16px);
  padding: 44px 32px;
}
.locked-icon {
  display: inline-flex; align-items: center; justify-content: center;
  width: 56px; height: 56px; margin: 0 auto 20px;
  border-radius: 50%;
  background: rgba(255,154,0,0.12);
  color: var(--accent);
}
.locked-card h1 {
  font-size: 21px; font-weight: 800; color: var(--text);
  margin-bottom: 10px; letter-spacing: -0.01em;
}
.locked-card p {
  font-size: 14px; color: var(--text-dim); line-height: 1.6;
  margin-bottom: 26px;
}
.locked-cta { width: 100%; justify-content: center; margin-bottom: 12px; }
.locked-back { width: 100%; justify-content: center; }

.strategy-content {
  padding: 36px 20px 110px;
  max-width: 720px;
  margin: 0 auto;
}

/* ── Breadcrumb ───────────────────────────── */
.breadcrumb {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 32px;
}
.breadcrumb-sep {
  color: var(--text-dim);
  font-size: 13px;
  opacity: 0.6;
}

.back-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  background: var(--bg-elevated);
  border: 1px solid var(--line);
  color: var(--text-dim);
  padding: 8px 16px;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: border-color 0.2s, color 0.2s;
}
@media (hover: hover) and (pointer: fine) {
  .back-btn:hover { border-color: var(--accent); color: var(--accent); }
}

/* ── Header ───────────────────────────────── */
.strategy-header { margin-bottom: 40px; }

.strategy-title {
  font-size: clamp(22px, 4.5vw, 34px);
  font-weight: 700;
  letter-spacing: -0.01em;
  color: var(--text);
  margin-bottom: 20px;
  line-height: 1.2;
}

.meta-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 12px;
}

/* Tags */
.tag {
  padding: 5px 12px;
  border-radius: 99px;
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.02em;
  border: 1px solid var(--line);
  background: var(--bg-elevated);
  color: var(--text-dim);
}
.tag-side  { border-color: rgba(255,154,0,0.35); color: var(--accent); }
.tag-plant { border-color: var(--line); }
.tag-speed { border-color: var(--line); }

/* Divider between meta groups */
.meta-divider {
  width: 1px;
  height: 18px;
  background: var(--line);
  flex-shrink: 0;
}

/* Difficulty */
.difficulty-group {
  display: flex;
  align-items: center;
  gap: 7px;
}
.difficulty-label {
  font-size: 11px;
  font-weight: 600;
  color: var(--text-dim);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

/* Stars */
.stars { display: flex; gap: 2px; }
.star { font-size: 16px; color: var(--line); line-height: 1; }
.star.filled { color: var(--accent); }

/* Success rate */
.success-rate {
  display: flex;
  align-items: baseline;
  gap: 4px;
}
.rate-num {
  font-size: 20px;
  font-weight: 700;
  color: var(--accent);
  line-height: 1;
}
.rate-lbl {
  font-size: 11px;
  color: var(--text-dim);
  text-transform: uppercase;
  letter-spacing: 0.06em;
}

/* Author */
.author { font-size: 13px; color: var(--text-dim); }
.author strong { color: var(--text); }

/* Access badge */
.access-badge {
  padding: 4px 13px;
  border-radius: 99px;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.03em;
}
.access-badge.premium {
  background: rgba(255,154,0,0.12);
  border: 1px solid rgba(255,154,0,0.35);
  color: var(--accent);
}
.access-badge.free {
  background: transparent;
  border: 1px solid var(--accent);
  color: var(--accent);
}

/* ── Quick nav + share ────────────────────── */
.header-actions-row {
  display: flex; align-items: center; justify-content: space-between;
  flex-wrap: wrap; gap: 12px;
  margin-top: 22px;
  padding-top: 18px;
  border-top: 1px solid var(--line);
}
.quick-nav { display: flex; gap: 8px; flex-wrap: wrap; }
.quick-nav-item {
  padding: 6px 14px; border-radius: 99px;
  background: var(--bg-elevated); border: 1px solid var(--line);
  color: var(--text-dim); font-size: 12px; font-weight: 600;
  text-decoration: none; transition: border-color .2s, color .2s;
}
@media (hover: hover) and (pointer: fine) {
  .quick-nav-item:hover { border-color: var(--accent); color: var(--accent); }
}
.share-btn {
  display: inline-flex; align-items: center; gap: 6px;
  background: transparent; border: 1px solid var(--line);
  color: var(--text-dim); padding: 7px 14px; border-radius: 8px;
  font-size: 12px; font-weight: 600; cursor: pointer;
  transition: border-color .2s, color .2s;
  flex-shrink: 0;
}
@media (hover: hover) and (pointer: fine) {
  .share-btn:hover { border-color: var(--accent); color: var(--accent); }
}

/* ── Main image ───────────────────────────── */
.main-image-section { margin-bottom: 56px; }
.image-container {
  border-radius: 14px;
  overflow: hidden;
  border: 1px solid var(--line);
}
.main-image { width: 100%; height: auto; display: block; }

/* ── Section title ────────────────────────── */
.section-title {
  font-size: 19px;
  font-weight: 700;
  letter-spacing: -0.005em;
  color: var(--text);
  margin-bottom: 22px;
}

/* ── Timings ──────────────────────────────── */
.timings-section { margin-bottom: 56px; }

.timings-list {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.timing-item {
  background: var(--bg-elevated);
  border: 1px solid var(--line);
  border-radius: 12px;
  padding: 18px 20px;
  transition: border-color 0.2s;
}
@media (hover: hover) and (pointer: fine) {
  .timing-item:hover { border-color: rgba(255,154,0,0.25); }
}

.timing-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
}
.timing-index {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-dim);
  min-width: 18px;
}
.timing-time {
  font-size: 16px;
  font-weight: 700;
  color: var(--accent);
  font-variant-numeric: tabular-nums;
  min-width: 48px;
}
.timing-desc {
  font-size: 14px;
  color: var(--text);
  line-height: 1.5;
}

/* ── Spoiler shared ───────────────────────── */
.spoiler { margin-top: 4px; }

.spoiler-toggle {
  display: flex;
  align-items: center;
  gap: 8px;
  background: var(--bg);
  border: 1.5px solid var(--line);
  color: var(--text-dim);
  padding: 9px 16px;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  width: 100%;
  text-align: left;
  transition: border-color 0.2s, color 0.2s;
}
@media (hover: hover) and (pointer: fine) {
  .spoiler-toggle:hover { border-color: var(--accent); color: var(--accent); }
}
.spoiler-arrow { font-size: 10px; }
.ml-auto { margin-left: auto; }

.spoiler-content {
  margin-top: 12px;
  border-radius: 10px;
  overflow: hidden;
}
.spoiler-img {
  width: 100%;
  height: auto;
  display: block;
  border-radius: 10px;
}

/* ── Grenades ─────────────────────────────── */
.grenades-section { margin-bottom: 56px; }

.grenades-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.grenade-item { }

.grenade-toggle {
  background: var(--bg-elevated) !important;
}

.grenade-type-icon { display: inline-flex; color: var(--accent); flex-shrink: 0; }
.grenade-type-label {
  font-size: 13px;
  font-weight: 600;
  color: var(--accent);
  text-transform: capitalize;
  min-width: 60px;
}
.grenade-target {
  font-size: 13px;
  color: var(--text);
  flex: 1;
}
.grenade-timing {
  font-size: 12px;
  color: var(--text-dim);
  font-variant-numeric: tabular-nums;
}

/* Smooth expand/collapse for spoilers */
.expand-enter-active, .expand-leave-active {
  transition: opacity 0.2s ease, transform 0.2s ease;
}
.expand-enter-from, .expand-leave-to {
  opacity: 0;
  transform: translateY(-6px);
}

.grenade-content {
  background: var(--bg-elevated);
  border: 1px solid var(--line);
  border-radius: 10px;
  padding: 16px;
  margin-top: 8px;
}
.grenade-media {
  width: 100%;
  height: auto;
  border-radius: 8px;
  display: block;
}
.grenade-no-media {
  color: var(--text-dim);
  font-size: 14px;
  text-align: center;
  padding: 20px 0;
}

/* ── Roles ────────────────────────────────── */
.roles-section { margin-bottom: 56px; }
.roles-text {
  color: var(--text-dim);
  font-size: 15px;
  line-height: 1.8;
  background: var(--bg-elevated);
  border: 1px solid var(--line);
  border-radius: 12px;
  padding: 22px 24px;
}
</style>