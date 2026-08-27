<template>
  <main class="strategies-page">
    <Header />

    <div v-if="isLoading" class="loading">
      <div class="spinner"></div>
      <p>Loading strategies...</p>
    </div>

    <div v-else class="wrap strategies-content">

      <!-- ═══ BACK + TITLE ════════════════════════════════════ -->
      <section class="page-header">
        <button class="back-btn" @click="router.push('/#strategies')">
          <svg viewBox="0 0 16 16" fill="none" width="14" height="14">
            <path d="M10 3L5 8l5 5" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
          Back to Maps
        </button>
        <h1>{{ mapName }} <span class="accent">Strategies</span></h1>
      </section>

      <!-- ═══ SEARCH ══════════════════════════════════════════ -->
      <div class="search-wrap">
        <svg class="search-icon" viewBox="0 0 20 20" fill="none">
          <circle cx="9" cy="9" r="6" stroke="currentColor" stroke-width="1.5"/>
          <path d="M14 14l3 3" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
        </svg>
        <input
          v-model="search"
          type="text"
          class="search-input"
          placeholder="Search strategies…"
        />
        <button v-if="search" class="search-clear" @click="search = ''">✕</button>
      </div>

      <!-- ═══ FILTERS ══════════════════════════════════════════ -->
      <div class="filters-block">

        <!-- Side -->
        <div class="filter-group">
          <div class="filter-label">Side</div>
          <div class="filter-chips">
            <button
              v-for="opt in SIDE_OPTS" :key="opt.value"
              class="chip"
              :class="{ active: filters.side === opt.value }"
              @click="toggleFilter('side', opt.value)"
            >{{ opt.label }}</button>
          </div>
        </div>

        <!-- Plant -->
        <div class="filter-group">
          <div class="filter-label">Plant</div>
          <div class="filter-chips">
            <button
              v-for="opt in PLANT_OPTS" :key="opt.value"
              class="chip"
              :class="{ active: filters.plant === opt.value }"
              @click="toggleFilter('plant', opt.value)"
            >{{ opt.label }}</button>
          </div>
        </div>

        <!-- Speed -->
        <div class="filter-group">
          <div class="filter-label">Speed</div>
          <div class="filter-chips">
            <button
              v-for="opt in SPEED_OPTS" :key="opt.value"
              class="chip"
              :class="{ active: filters.speed === opt.value }"
              @click="toggleFilter('speed', opt.value)"
            >{{ opt.label }}</button>
          </div>
        </div>

        <!-- Buy type -->
        <div class="filter-group">
          <div class="filter-label">Buy Type</div>
          <div class="filter-chips">
            <button
              v-for="tag in BUY_TAGS" :key="tag"
              class="chip"
              :class="{ active: filters.buy_tags === tag }"
              @click="toggleFilter('buy_tags', tag)"
            >{{ tag }}</button>
          </div>
        </div>

        <!-- Access -->
        <div class="filter-group">
          <div class="filter-label">Access</div>
          <div class="filter-chips">
            <button
              class="chip chip-free"
              :class="{ active: filters.is_free === true }"
              @click="toggleAccess(true)"
            >Free</button>
            <button
              class="chip chip-premium"
              :class="{ active: filters.is_free === false }"
              @click="toggleAccess(false)"
            >Premium</button>
          </div>
        </div>

        <!-- Reset -->
        <button v-if="hasActiveFilters" class="reset-btn" @click="resetFilters">
          Reset all filters
        </button>
      </div>

      <!-- ═══ COUNT ═════════════════════════════════════════════ -->
      <p class="results-count">
        <template v-if="loadingFiltered">Searching…</template>
        <template v-else>
          <strong>{{ strategies.length }}</strong>
          {{ strategies.length === 1 ? 'strategy' : 'strategies' }} found
        </template>
      </p>

      <!-- ═══ GRID ══════════════════════════════════════════════ -->
      <div v-if="loadingFiltered" class="loader-row">
        <div class="spinner"></div>
      </div>

      <div v-else-if="strategies.length === 0" class="no-results">
        No strategies match the selected filters.
      </div>

      <div v-else class="strategies-grid">
        <div
          v-for="s in strategies"
          :key="s.id"
          class="strategy-card"
          @click="router.push('/strategy/' + s.id)"
        >
          <div class="card-thumb">
            <img v-if="s.main_image_url" :src="s.main_image_url" :alt="s.title" class="card-img"/>
            <div v-else class="card-placeholder">
              <span>{{ s.title.charAt(0) }}</span>
            </div>
            <div class="card-overlay"></div>
            <div class="card-badges">
              <span class="badge badge-side">{{ s.side === 'T_side' ? 'T' : 'CT' }}</span>
              <span class="badge badge-plant">{{ s.plant }}</span>
              <span class="badge badge-speed">{{ speedLabel(s.speed) }}</span>
            </div>
            <span class="badge-access" :class="s.is_free ? 'free' : 'premium'">
              {{ s.is_free ? 'Free' : 'Premium' }}
            </span>
            <button
              type="button" class="fav-btn" :class="{ active: favoriteIds.has(s.id) }"
              @click.stop="toggleFavorite(s)"
              :aria-label="favoriteIds.has(s.id) ? 'Remove from favorites' : 'Add to favorites'"
            >
              <svg viewBox="0 0 20 20" :fill="favoriteIds.has(s.id) ? 'currentColor' : 'none'" width="15" height="15">
                <path d="M10 2.5l2.35 4.76 5.25.76-3.8 3.7.9 5.23L10 14.5l-4.7 2.45.9-5.23-3.8-3.7 5.25-.76z" stroke="currentColor" stroke-width="1.4" stroke-linejoin="round"/>
              </svg>
            </button>
          </div>

          <div class="card-body">
            <h3>{{ s.title }}</h3>
            <div class="card-meta">
              <span class="difficulty-group">
                <span class="difficulty-label">Difficulty</span>
                <span class="stars">
                  <span v-for="i in 5" :key="i" class="star" :class="{ on: i <= s.difficulty_stars }">★</span>
                </span>
              </span>
              <span class="meta-divider" aria-hidden="true"></span>
              <span class="win-rate">{{ s.success_rate }}% win rate</span>
            </div>
            <div v-if="s.buy_tags && s.buy_tags.length" class="card-tags">
              <span v-for="t in s.buy_tags" :key="t.id" class="card-tag">{{ t.name }}</span>
            </div>
            <p class="card-link">View strategy →</p>
          </div>
        </div>
      </div>

    </div>

    <Footer />
  </main>
</template>

<script setup>
import { ref, reactive, computed, watch, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { strategiesAPI } from '../api/strategies'
import { favoritesAPI } from '../api/favorites'
import Header from '../components/Header.vue'
import Footer from '../components/Footer.vue'

const route  = useRoute()
const router = useRouter()

const mapId           = parseInt(route.params.id)
const mapName         = ref('')
const strategies      = ref([])
const isLoading       = ref(true)      // page-level: hides whole page
const loadingFiltered = ref(false)     // filter-level: shows spinner in grid
const search          = ref('')

const filters = reactive({
  side:     null,
  plant:    null,
  speed:    null,
  buy_tags: null,
  is_free:  null,
})

const SIDE_OPTS = [
  { value: 'T_side',  label: 'T — Terrorist' },
  { value: 'CT_side', label: 'CT — Counter-Terrorist' },
]
const PLANT_OPTS = [
  { value: 'A', label: 'Site A' },
  { value: 'B', label: 'Site B' },
]
const SPEED_OPTS = [
  { value: 'fast',   label: '< 40 sec' },
  { value: 'medium', label: '40 – 120 sec' },
  { value: 'slow',   label: '120+ sec' },
]
const BUY_TAGS = ['Eco Round', 'Full Buy', 'Force Buy', 'Pistol Round']

function speedLabel(v) {
  return { fast: '< 40s', medium: '40-120s', slow: '120+s' }[v] ?? v
}

function toggleFilter(key, value) {
  filters[key] = filters[key] === value ? null : value
}

function toggleAccess(val) {
  filters.is_free = filters.is_free === val ? null : val
}

const hasActiveFilters = computed(() =>
  filters.side !== null || filters.plant !== null || filters.speed !== null ||
  filters.buy_tags !== null || filters.is_free !== null || search.value !== ''
)

function resetFilters() {
  filters.side     = null
  filters.plant    = null
  filters.speed    = null
  filters.buy_tags = null
  filters.is_free  = null
  search.value     = ''
}

async function fetchStrategies() {
  loadingFiltered.value = true
  try {
    const params = { map_id: mapId }

    // Single-select filters — wrap in array for API
    if (filters.side)           params.side     = [filters.side]
    if (filters.plant)          params.plant    = [filters.plant]
    if (filters.speed)          params.speed    = [filters.speed]
    if (filters.buy_tags)       params.buy_tags = [filters.buy_tags]
    if (filters.is_free !== null) params.is_free = filters.is_free
    if (search.value)           params.search   = search.value

    const res = await strategiesAPI.getStrategies(params)

    // API returns { total, strategies } — handle both just in case
    strategies.value = Array.isArray(res) ? res : (res.strategies ?? [])
  } catch (e) {
    console.error('[Strategies] fetch error:', e)
    strategies.value = []
  } finally {
    loadingFiltered.value = false
  }
}

// Debounce search
let searchTimer = null
watch(search, () => {
  clearTimeout(searchTimer)
  searchTimer = setTimeout(fetchStrategies, 350)
})

// Watch filters — but only after mount (initialized flag prevents premature calls)
let initialized = false
watch(
  () => ({ ...filters }),
  () => { if (initialized) fetchStrategies() },
  { deep: true }
)

// ── Favorite strategies ────────────────────
const favoriteIds = ref(new Set())

async function loadFavoriteIds() {
  try {
    const favs = await favoritesAPI.listStrategies()
    favoriteIds.value = new Set(favs.map(s => s.id))
  } catch (e) {
    // Not critical to the page — just leave every star unfilled.
  }
}

async function toggleFavorite(s) {
  const isFav = favoriteIds.value.has(s.id)
  const next = new Set(favoriteIds.value)
  isFav ? next.delete(s.id) : next.add(s.id)
  favoriteIds.value = next
  try {
    isFav ? await favoritesAPI.removeStrategy(s.id) : await favoritesAPI.addStrategy(s.id)
  } catch (e) {
    await loadFavoriteIds() // out of sync — resync from the server
  }
}

onMounted(async () => {
  // Always open at the top — without this, the browser can keep the
  // scroll offset from whatever page you navigated from, which lands
  // you mid-page or on the footer if this page is shorter.
  window.scrollTo({ top: 0, behavior: 'auto' })

  try {
    const maps = await strategiesAPI.getMaps()
    mapName.value = maps.find(m => m.id === mapId)?.name ?? ''
    await fetchStrategies()
    loadFavoriteIds()
  } catch (e) {
    console.error('[Strategies] mount error:', e)
  } finally {
    isLoading.value = false
    initialized = true  // Now watch can trigger refetches
  }
})
</script>

<style scoped>
.strategies-page { min-height: 100vh; background: var(--bg); }

.loading {
  display: flex; flex-direction: column;
  align-items: center; justify-content: center;
  min-height: 60vh; gap: 16px; color: var(--text-dim);
}

.strategies-content { padding: 28px 20px 100px; }

/* ── Back + title ─────────────────────────────── */
.page-header { margin-bottom: 28px; }

.back-btn {
  display: inline-flex; align-items: center; gap: 6px;
  background: var(--bg-elevated); border: 1px solid var(--line);
  color: var(--text-dim); padding: 8px 16px; border-radius: 8px;
  font-size: 13px; font-weight: 600; cursor: pointer;
  text-decoration: none;
  transition: border-color .2s, color .2s;
  margin-bottom: 20px;
}
.back-btn:hover { border-color: var(--accent); color: var(--accent); }

.page-header h1 {
  font-size: clamp(28px, 6vw, 44px); font-weight: 900;
  letter-spacing: -.02em; line-height: 1.1; color: var(--text);
}
.accent { color: var(--accent); }

/* ── Search ───────────────────────────────────── */
.search-wrap {
  position: relative; margin-bottom: 28px;
  display: flex; align-items: center;
}
.search-icon {
  position: absolute; left: 14px;
  width: 16px; height: 16px; color: var(--text-dim);
}
.search-input {
  width: 100%; padding: 12px 40px 12px 42px;
  background: var(--bg-elevated); border: 1.5px solid var(--line);
  border-radius: 10px; font-size: 14px; font-family: inherit;
  color: var(--text); transition: border-color .2s, box-shadow .2s;
}
.search-input::placeholder { color: var(--text-dim); }
.search-input:focus {
  outline: none; border-color: var(--accent);
  box-shadow: 0 0 0 3px rgba(255,154,0,.12);
}
.search-clear {
  position: absolute; right: 12px; background: none; border: none;
  color: var(--text-dim); font-size: 13px; cursor: pointer; padding: 4px;
}
.search-clear:hover { color: var(--text); }

/* ── Filters ──────────────────────────────────── */
.filters-block {
  background: var(--bg-elevated);
  border: 1px solid var(--line);
  border-radius: 14px;
  padding: 20px 20px 16px;
  margin-bottom: 20px;
  display: flex; flex-direction: column; gap: 14px;
}

.filter-group {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 10px;
}

.filter-label {
  font-size: 11px; font-weight: 700; letter-spacing: .08em;
  text-transform: uppercase; color: var(--text-dim);
}

.filter-chips { display: flex; flex-wrap: wrap; gap: 8px; }

.chip {
  padding: 5px 14px; border-radius: 99px;
  background: var(--bg); border: 1.5px solid var(--line);
  font-size: 12px; font-weight: 600; color: var(--text-dim);
  cursor: pointer; transition: all .18s; white-space: nowrap;
}
@media (hover: hover) and (pointer: fine) {
  .chip:hover { border-color: var(--accent); color: var(--accent); }
}
.chip:active { border-color: var(--accent); color: var(--accent); }
.chip.active {
  background: rgba(255,154,0,.12);
  border-color: var(--accent);
  color: var(--accent);
}
.chip-free.active  { background: rgba(80,220,100,.12); border-color: #50dc64; color: #50dc64; }
.chip-premium.active { background: rgba(255,154,0,.15); border-color: var(--accent); color: var(--accent); }

.reset-btn {
  align-self: flex-start;
  background: none; border: none;
  color: var(--text-dim); font-size: 12px; font-weight: 600;
  cursor: pointer; padding: 0; text-decoration: underline;
  transition: color .2s;
}
.reset-btn:hover { color: var(--accent); }

/* ── Count ────────────────────────────────────── */
.results-count {
  font-size: 13px; color: var(--text-dim);
  margin-bottom: 20px; min-height: 20px;
}
.results-count strong { color: var(--text); }

/* ── Loader row ───────────────────────────────── */
.loader-row {
  display: flex; justify-content: center; padding: 48px 0;
}
.spinner {
  width: 32px; height: 32px;
  border: 2.5px solid var(--line);
  border-top-color: var(--accent);
  border-radius: 50%;
  animation: spin .8s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

.no-results {
  text-align: center; padding: 60px 20px;
  color: var(--text-dim); font-size: 15px;
}

/* ── Grid ─────────────────────────────────────── */
.strategies-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 20px;
}

.strategy-card {
  background: var(--bg-elevated); border: 1px solid var(--line);
  border-radius: 16px; overflow: hidden; cursor: pointer;
  transition: border-color .25s, transform .25s, box-shadow .25s;
}
@media (hover: hover) and (pointer: fine) {
  .strategy-card:hover {
    border-color: rgba(255,154,0,.5);
    transform: translateY(-4px);
    box-shadow: 0 8px 24px rgba(255,154,0,.12);
  }
}

.card-thumb {
  position: relative; aspect-ratio: 16/10; overflow: hidden;
  background: var(--bg-elevated-2, #25272b);
}
.card-img { width: 100%; height: 100%; object-fit: cover; display: block; }
.card-placeholder {
  width: 100%; height: 100%;
  display: flex; align-items: center; justify-content: center;
  font-size: 52px; font-weight: 900; color: rgba(255,154,0,.25);
}
.card-overlay {
  position: absolute; inset: 0;
  background: linear-gradient(to top, rgba(0,0,0,.65) 0%, transparent 55%);
}

.card-badges {
  position: absolute; top: 10px; left: 10px;
  display: flex; gap: 6px; z-index: 2;
}
.badge {
  padding: 3px 9px; border-radius: 6px;
  font-size: 10px; font-weight: 700;
  text-transform: uppercase; letter-spacing: .04em;
}
.badge-side  { background: rgba(0,0,0,.72); color: #fff; backdrop-filter: blur(4px); }
.badge-plant { background: rgba(0,0,0,.55); color: #fff; backdrop-filter: blur(4px); }
.badge-speed { background: var(--accent); color: #121212; }

.badge-access {
  position: absolute; bottom: 10px; right: 10px;
  padding: 3px 10px; border-radius: 99px;
  font-size: 10px; font-weight: 800; text-transform: uppercase; letter-spacing: .05em;
  z-index: 2;
}
.badge-access.free    { background: rgba(80,220,100,.2); color: #50dc64; border: 1px solid rgba(80,220,100,.4); }
.badge-access.premium { background: rgba(255,154,0,.2);  color: var(--accent); border: 1px solid rgba(255,154,0,.4); }

.fav-btn {
  position: absolute; top: 10px; right: 10px; z-index: 3;
  width: 30px; height: 30px; border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  background: rgba(0,0,0,0.5); backdrop-filter: blur(4px);
  border: 1px solid rgba(255,255,255,0.15); color: #fff;
  cursor: pointer; transition: color .15s, border-color .15s, background .15s;
}
.fav-btn:hover { border-color: var(--accent); }
.fav-btn.active { color: var(--accent); background: rgba(255,154,0,0.18); border-color: rgba(255,154,0,0.4); }

.card-body { padding: 16px 18px 20px; }
.card-body h3 {
  font-size: 16px; font-weight: 700;
  letter-spacing: -.01em; color: var(--text);
  margin-bottom: 10px; line-height: 1.35;
}
.card-meta { display: flex; align-items: center; gap: 10px; margin-bottom: 8px; }

.difficulty-group { display: flex; align-items: center; gap: 6px; }
.difficulty-label {
  font-size: 10px;
  font-weight: 600;
  color: var(--text-dim);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.meta-divider {
  width: 1px;
  height: 12px;
  background: var(--line);
  flex-shrink: 0;
}

.stars { display: flex; gap: 2px; }
.star { font-size: 13px; color: var(--line); }
.star.on { color: var(--accent); }

.win-rate { font-size: 12px; color: var(--text-dim); }

.card-tags { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 10px; }
.card-tag {
  padding: 2px 8px; border-radius: 4px;
  background: var(--bg); border: 1px solid var(--line);
  font-size: 11px; color: var(--text-dim);
}

.card-link { font-size: 13px; font-weight: 600; color: var(--accent); }
</style>