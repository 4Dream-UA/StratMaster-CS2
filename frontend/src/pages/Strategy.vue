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
      <Breadcrumbs :items="[{ label: 'Home', to: '/' }, { label: mapName, to: '/map/' + strategy.map_id }, { label: strategy.title }]" />

      <!-- ═══ HEADER ══════════════════════════════ -->
      <section class="strategy-header">
        <h1 class="strategy-title">{{ strategy.title }}</h1>

        <div class="meta-row">
          <!-- Side / Plant / Speed tags -->
          <span class="tag tag-side">{{ sideLabel }}</span>
          <span class="tag tag-plant">Site {{ strategy.plant }}</span>
          <span class="tag tag-speed">{{ strategy.speed }}</span>

          <!-- Author -->
          <span v-if="strategy.author" class="author">
            by <strong>{{ strategy.author }}</strong>
          </span>

          <!-- Free / Premium badge -->
          <span class="access-badge" :class="strategy.is_free ? 'free' : 'premium'">
            {{ strategy.is_free ? 'Free' : 'Premium' }}
          </span>
        </div>

        <!-- ═══ AT A GLANCE ═══════════════════════
             The three numbers a player actually decides on — how hard it is
             to run, how often it works, and how much setup it needs — as
             readable figures rather than tag soup in the row above. -->
        <div class="glance-row">
          <div class="glance-card">
            <span class="glance-label">Difficulty</span>
            <span class="glance-value difficulty-chip" :class="difficultyKey(strategy.difficulty_stars)">
              {{ difficultyLabel(strategy.difficulty_stars) }}
            </span>
          </div>

          <div class="glance-card">
            <span class="glance-label">Win rate</span>
            <span class="glance-value">{{ strategy.success_rate }}%</span>
            <span class="rate-meter"><span class="rate-meter-fill" :class="winRateKey" :style="{ width: strategy.success_rate + '%' }"></span></span>
          </div>

          <div class="glance-card">
            <span class="glance-label">Utility</span>
            <span class="glance-value">{{ strategy.grenades?.length || 0 }}</span>
            <span class="glance-sub">{{ (strategy.grenades?.length || 0) === 1 ? 'lineup' : 'lineups' }}</span>
          </div>

          <div class="glance-card">
            <span class="glance-label">Execute</span>
            <span class="glance-value">{{ executeLength }}</span>
            <span class="glance-sub">{{ timings.length ? `${timings.length} ${timings.length === 1 ? 'step' : 'steps'}` : 'no timeline' }}</span>
          </div>
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
          <div class="header-actions-buttons">
            <button
              class="share-btn fav-btn" :class="{ active: isFavorited }"
              @click="toggleFavoriteStrategy"
            >
              <svg viewBox="0 0 20 20" :fill="isFavorited ? 'currentColor' : 'none'" width="14" height="14">
                <path d="M10 2.5l2.35 4.76 5.25.76-3.8 3.7.9 5.23L10 14.5l-4.7 2.45.9-5.23-3.8-3.7 5.25-.76z" stroke="currentColor" stroke-width="1.4" stroke-linejoin="round"/>
              </svg>
              {{ isFavorited ? 'Favorited' : 'Favorite' }}
            </button>
            <button class="share-btn" @click="copyLink">
              <svg viewBox="0 0 20 20" fill="none" width="14" height="14">
                <path d="M7 10a2.5 2.5 0 100-5 2.5 2.5 0 000 5zM7 10a2.5 2.5 0 110 5 2.5 2.5 0 010-5zM13 12.5a2.5 2.5 0 100 5 2.5 2.5 0 000-5zM13 7.5a2.5 2.5 0 100-5 2.5 2.5 0 000 5z" stroke="currentColor" stroke-width="1.4" stroke-linejoin="round"/>
                <path d="M9.2 8.6l3.6-2.2M9.2 11.4l3.6 2.2" stroke="currentColor" stroke-width="1.4"/>
              </svg>
              {{ linkCopied ? 'Link copied' : 'Copy link' }}
            </button>
          </div>
        </div>
      </section>

      <!-- ═══ MAIN IMAGE (images[0]) — animated replay if we have one ══ -->
      <section v-if="mainImage" class="main-image-section">
        <TacticsPlayer
          v-if="hasTacticsAnimation"
          :image-url="mainImage.image_url"
          :grenades="strategy.grenades || []"
          :player-paths="strategy.player_paths || []"
          :annotations="strategy.annotations"
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
        <div class="section-head">
          <h2 class="section-title">Execution timeline</h2>
          <button v-if="timingImages.length" type="button" class="section-action" @click="toggleAllSpoilers">
            {{ allSpoilersOpen ? 'Collapse all' : 'Expand all' }}
          </button>
        </div>

        <!-- A rail with a dot per step, rather than a flat list: the round
             number and the gap to the next one are the point of a timing
             list, and a bare "1) 00:10" line doesn't show either. -->
        <ol class="timeline">
          <li v-for="(t, i) in timings" :key="i" class="timeline-step">
            <span class="timeline-dot">{{ i + 1 }}</span>
            <div class="timeline-body">
              <div class="timeline-head">
                <span class="timeline-time">{{ t.time }}</span>
                <span v-if="gapAfter(i)" class="timeline-gap">+{{ gapAfter(i) }}</span>
              </div>
              <p class="timeline-desc">{{ t.description }}</p>

              <div v-if="timingImages[i]" class="spoiler">
                <button
                  class="spoiler-toggle"
                  @click="toggleSpoiler(i)"
                  :aria-expanded="openSpoilers[i]"
                >
                  <span class="spoiler-arrow">{{ openSpoilers[i] ? '▼' : '▶' }}</span>
                  {{ openSpoilers[i] ? 'Hide screenshot' : 'Show screenshot' }}
                </button>
                <div v-show="openSpoilers[i]" class="spoiler-content">
                  <img :src="timingImages[i].image_url" :alt="`Step ${i + 1}`" class="spoiler-img" loading="lazy" />
                </div>
              </div>
            </div>
          </li>
        </ol>
      </section>

      <!-- ═══ GRENADES ════════════════════════════ -->
      <section v-if="strategy.grenades && strategy.grenades.length" id="grenades" class="grenades-section">
        <div class="section-head">
          <h2 class="section-title">Grenades</h2>
          <button v-if="strategy.grenades.length > 1" type="button" class="section-action" @click="toggleAllGrenades">
            {{ allGrenadesOpen ? 'Collapse all' : 'Expand all' }}
          </button>
        </div>

        <!-- What the team needs to buy, before the lineup-by-lineup detail. -->
        <div class="utility-summary">
          <span v-for="g in grenadeCounts" :key="g.type" class="utility-chip">
            <span class="utility-chip-icon" v-html="grenadeIcon(g.type)"></span>
            <span>{{ g.count }}× {{ grenadeTypeLabel(g.type) }}</span>
          </span>
        </div>

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

            <!-- Rendered only once opened (v-if, not v-show): a strategy
                 with a dozen lineups would otherwise start a dozen looping
                 videos on page load, all of them behind a collapsed panel. -->
            <div v-if="openGrenades[i]" class="spoiler-content grenade-content">
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
                loading="lazy"
              />
              <p v-else class="grenade-no-media">No lineup video available yet.</p>
            </div>
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
import { favoritesAPI } from '../api/favorites'
import Header from '../components/Header.vue'
import Footer from '../components/Footer.vue'
import Breadcrumbs from '../components/Breadcrumbs.vue'
import TacticsPlayer from '../components/TacticsPlayer.vue'
import { grenadeTypeLabel } from '../utils/grenadeLabels'
import { difficultyKey, difficultyLabel } from '../utils/difficulty'
import { botDeepLink } from '../config'

const route  = useRoute()
const router = useRouter()

const strategy   = ref(null)
const mapName    = ref('')
const isLoading  = ref(true)
const lockReason = ref(null) // null | 'auth' | 'subscription'
const openSpoilers = ref({})
const openGrenades = ref({})
const isFavorited = ref(false)

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
// animate — a strategy with no paths/trajectories/annotations keeps the plain image.
const hasTacticsAnimation = computed(() => {
  const paths = strategy.value?.player_paths || []
  const grenades = strategy.value?.grenades || []
  const a = strategy.value?.annotations
  return paths.some(p => p.waypoints?.length >= 2) ||
    grenades.some(g => g.from_x != null && g.to_x != null) ||
    !!(a && (a.drawings?.length || a.notes?.length || a.bomb))
})

const timingImages = computed(() => {
  const imgs = strategy.value?.images
  if (!imgs?.length) return []
  // images with order >= 1 sorted by order, one per timing
  return imgs
    .filter(img => img.order >= 1)
    .sort((a, b) => a.order - b.order)
})

// ── At-a-glance figures ────────────────────────────────────────
const winRateKey = computed(() => {
  const rate = strategy.value?.success_rate ?? 0
  if (rate >= 70) return 'high'
  return rate >= 50 ? 'mid' : 'low'
})

function timeToSeconds(mmss) {
  const m = /^(\d{1,2}):(\d{2})$/.exec(mmss || '')
  return m ? Number(m[1]) * 60 + Number(m[2]) : null
}
function formatSeconds(total) {
  return `${Math.floor(total / 60)}:${String(total % 60).padStart(2, '0')}`
}

// How long the whole execute runs, from the first timing to the last —
// null when the timings aren't all mm:ss (they're free text on the admin
// side, so a strategy can legitimately have labels we can't do maths on).
const executeLength = computed(() => {
  const seconds = timings.value.map(t => timeToSeconds(t.time)).filter(s => s != null)
  if (seconds.length < 2) return '—'
  return formatSeconds(Math.max(...seconds) - Math.min(...seconds))
})

// Gap between this step and the next one, so the timeline shows pace and
// not just absolute clock marks.
function gapAfter(i) {
  const a = timeToSeconds(timings.value[i]?.time)
  const b = timeToSeconds(timings.value[i + 1]?.time)
  if (a == null || b == null || b <= a) return null
  return `${b - a}s`
}

const grenadeCounts = computed(() => {
  const counts = new Map()
  for (const g of strategy.value?.grenades || []) {
    counts.set(g.grenade_type, (counts.get(g.grenade_type) || 0) + 1)
  }
  return [...counts].map(([type, count]) => ({ type, count }))
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
// Copies a bot deep link, not the raw site URL — a bare website link opens
// in a plain browser (no Telegram auth) instead of the Mini App.
const linkCopied = ref(false)
function copyLink() {
  navigator.clipboard?.writeText(botDeepLink(`strategy_${strategy.value.id}`))
  linkCopied.value = true
  setTimeout(() => { linkCopied.value = false }, 1800)
}

// ── Favorite ───────────────────────────────────────────────────
async function loadFavoriteStatus() {
  try {
    const favs = await favoritesAPI.listStrategies()
    isFavorited.value = favs.some(s => s.id === strategy.value?.id)
  } catch (e) {
    // Not critical — leave the star unfilled rather than block the page.
  }
}

async function toggleFavoriteStrategy() {
  const next = !isFavorited.value
  isFavorited.value = next
  try {
    next ? await favoritesAPI.addStrategy(strategy.value.id) : await favoritesAPI.removeStrategy(strategy.value.id)
  } catch (e) {
    isFavorited.value = !next // revert on failure
  }
}

// ── Spoiler toggles ────────────────────────────────────────────
function toggleSpoiler(i) {
  openSpoilers.value[i] = !openSpoilers.value[i]
}
function toggleGrenade(i) {
  openGrenades.value[i] = !openGrenades.value[i]
}

const allSpoilersOpen = computed(() => timingImages.value.length > 0 && timings.value.every((_, i) => !timingImages.value[i] || openSpoilers.value[i]))
const allGrenadesOpen = computed(() => (strategy.value?.grenades || []).every((_, i) => openGrenades.value[i]))

function toggleAllSpoilers() {
  const next = !allSpoilersOpen.value
  openSpoilers.value = Object.fromEntries(timings.value.map((_, i) => [i, next]))
}
function toggleAllGrenades() {
  const next = !allGrenadesOpen.value
  openGrenades.value = Object.fromEntries((strategy.value?.grenades || []).map((_, i) => [i, next]))
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
    // The strategy carries its own map_name — this used to pull the whole
    // map list on every strategy view purely to resolve one breadcrumb.
    const strategyRes = await strategiesAPI.getStrategy(route.params.id)
    strategy.value = strategyRes
    mapName.value = strategyRes.map_name || 'Map'
    loadFavoriteStatus()
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

/* ── At a glance ──────────────────────────── */
.glance-row {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(130px, 1fr));
  gap: 10px;
  margin-top: 18px;
}
.glance-card {
  display: flex; flex-direction: column; gap: 6px;
  background: var(--bg-elevated); border: 1px solid var(--line);
  border-radius: 12px; padding: 14px 16px;
}
.glance-label {
  font-size: 10.5px; font-weight: 700; color: var(--text-dim);
  text-transform: uppercase; letter-spacing: .06em;
}
.glance-value {
  font-size: 22px; font-weight: 800; color: var(--text); line-height: 1;
  font-variant-numeric: tabular-nums;
}
.glance-sub { font-size: 11.5px; color: var(--text-dim); font-weight: 600; }

/* Difficulty as a word, colour-coded — see utils/difficulty.js for why
   this replaced a five-star row. */
.difficulty-chip {
  align-self: flex-start;
  font-size: 14px; font-weight: 800;
  padding: 4px 12px; border-radius: 99px;
  border: 1px solid;
}
.difficulty-chip.easy   { color: var(--success); border-color: color-mix(in srgb, var(--success) 45%, transparent); background: color-mix(in srgb, var(--success) 12%, transparent); }
.difficulty-chip.medium { color: var(--accent);  border-color: color-mix(in srgb, var(--accent) 45%, transparent);  background: color-mix(in srgb, var(--accent) 12%, transparent); }
.difficulty-chip.hard   { color: var(--danger);  border-color: color-mix(in srgb, var(--danger) 45%, transparent);  background: color-mix(in srgb, var(--danger) 12%, transparent); }

.rate-meter {
  height: 5px; border-radius: 99px; background: var(--line); overflow: hidden;
}
.rate-meter-fill { display: block; height: 100%; border-radius: 99px; }
.rate-meter-fill.high { background: var(--success); }
.rate-meter-fill.mid  { background: var(--accent); }
.rate-meter-fill.low  { background: var(--danger); }

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
.header-actions-buttons { display: flex; gap: 8px; flex-wrap: wrap; }
.fav-btn.active { border-color: var(--accent); color: var(--accent); background: rgba(255,154,0,.08); }

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

/* ── Section heading with an action on the right ─────── */
.section-head {
  display: flex; align-items: baseline; justify-content: space-between;
  gap: 12px; margin-bottom: 22px;
}
.section-head .section-title { margin-bottom: 0; }
.section-action {
  background: none; border: none; padding: 0;
  color: var(--text-dim); font-size: 12px; font-weight: 700;
  cursor: pointer; text-decoration: underline; white-space: nowrap;
}
@media (hover: hover) and (pointer: fine) {
  .section-action:hover { color: var(--accent); }
}

/* ── Execution timeline ───────────────────── */
.timings-section { margin-bottom: 56px; }

.timeline { list-style: none; margin: 0; padding: 0; }
.timeline-step {
  position: relative;
  display: grid; grid-template-columns: 30px 1fr; gap: 14px;
  padding-bottom: 18px;
}
/* The rail: a line from this step's dot down to the next one. The last
   step has no ::before, so the rail stops at the final dot instead of
   trailing off into empty space. */
.timeline-step:not(:last-child)::before {
  content: '';
  position: absolute; left: 14px; top: 30px; bottom: 0;
  width: 2px; background: var(--line);
}
.timeline-dot {
  width: 30px; height: 30px; border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  background: var(--bg-elevated); border: 1.5px solid var(--accent);
  color: var(--accent); font-size: 12.5px; font-weight: 800;
  flex-shrink: 0; z-index: 1;
}
.timeline-body {
  background: var(--bg-elevated); border: 1px solid var(--line);
  border-radius: 12px; padding: 14px 18px;
  min-width: 0;
}
.timeline-head { display: flex; align-items: baseline; gap: 10px; margin-bottom: 4px; }
.timeline-time {
  font-size: 16px; font-weight: 800; color: var(--accent);
  font-variant-numeric: tabular-nums;
}
.timeline-gap {
  font-size: 11px; font-weight: 700; color: var(--text-dim);
  padding: 2px 8px; border-radius: 99px; background: var(--bg);
}
.timeline-desc { font-size: 14px; color: var(--text); line-height: 1.5; }
.timeline-body .spoiler { margin-top: 12px; }

/* ── Utility summary ──────────────────────── */
.utility-summary { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 18px; }
.utility-chip {
  display: inline-flex; align-items: center; gap: 7px;
  padding: 6px 13px; border-radius: 99px;
  background: var(--bg-elevated); border: 1px solid var(--line);
  color: var(--text); font-size: 12.5px; font-weight: 700;
}
.utility-chip-icon { display: flex; color: var(--accent); }

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