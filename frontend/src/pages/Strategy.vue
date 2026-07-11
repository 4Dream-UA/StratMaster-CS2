<template>
  <main class="strategy-page">
    <Header />

    <div v-if="isLoading" class="loading">
      <div class="spinner"></div>
      <p>Loading strategy...</p>
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
      </section>

      <!-- ═══ MAIN IMAGE (images[0]) ══════════════ -->
      <section v-if="mainImage" class="main-image-section">
        <div class="image-container">
          <img :src="mainImage.image_url" alt="Strategy map" class="main-image" />
        </div>
      </section>

      <!-- ═══ TIMINGS ══════════════════════════════
           timings_description format (one line per timing):
           "00:10 — Rush mid\n00:50 — Plant A\n01:20 — Second contact"
           Each timing at index N links to images[N+1]
      ════════════════════════════════════════════ -->
      <section v-if="timings.length" class="timings-section">
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
              <div v-show="openSpoilers[i]" class="spoiler-content">
                <img :src="timingImages[i].image_url" :alt="`Timing ${i + 1}`" class="spoiler-img" />
              </div>
            </div>
          </div>
        </div>
      </section>

      <!-- ═══ GRENADES ════════════════════════════ -->
      <section v-if="strategy.grenades && strategy.grenades.length" class="grenades-section">
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
              <span class="grenade-type-icon">{{ grenadeIcon(g.grenade_type) }}</span>
              <span class="grenade-type-label">{{ g.grenade_type }}</span>
              <span class="grenade-target">→ {{ g.target }}</span>
              <span class="grenade-timing">{{ g.timing }}</span>
              <span class="spoiler-arrow ml-auto">{{ openGrenades[i] ? '▼' : '▶' }}</span>
            </button>

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
          </div>
        </div>
      </section>

      <!-- ═══ ROLES / NOTES ════════════════════════ -->
      <section v-if="strategy.roles_description" class="roles-section">
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

const route  = useRoute()
const router = useRouter()

const strategy   = ref(null)
const mapName    = ref('')
const isLoading  = ref(true)
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

// ── Spoiler toggles ────────────────────────────────────────────
function toggleSpoiler(i) {
  openSpoilers.value[i] = !openSpoilers.value[i]
}
function toggleGrenade(i) {
  openGrenades.value[i] = !openGrenades.value[i]
}

// ── Grenade helpers ────────────────────────────────────────────
const grenadeIcons = {
  smoke: '💨', flash: '⚡', molotov: '🔥', he: '💣', decoy: '📢',
}
function grenadeIcon(type) {
  return grenadeIcons[type] ?? '🟠'
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
    console.error('Failed to load strategy:', err)
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
.back-btn:hover { border-color: var(--accent); color: var(--accent); }

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
.timing-item:hover { border-color: rgba(255,154,0,0.25); }

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
.spoiler-toggle:hover { border-color: var(--accent); color: var(--accent); }
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

.grenade-type-icon { font-size: 16px; }
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