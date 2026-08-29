<template>
  <main class="cases-page">
    <Header />

    <div class="wrap cases-content">
      <section class="page-header">
        <h1>Open a <span class="accent">Case</span></h1>
        <p>Spend MasterCoins for a shot at winning more back.</p>
      </section>

      <div v-if="loading" class="loader-row"><div class="spinner"></div></div>
      <div v-else-if="!cases.length" class="empty">No cases available right now.</div>

      <div v-else class="case-grid">
        <div v-for="c in cases" :key="c.id" class="case-card">
          <div class="case-icon"><CaseIcon /></div>
          <h3>{{ c.name }}</h3>
          <p class="case-cost"><CoinIcon :size="16" /> {{ c.cost_coins }} <span>MC</span></p>

          <button
            class="btn-primary case-open-btn"
            :disabled="opening || (wallet?.balance_coins ?? 0) < c.cost_coins"
            @click="openCase(c)"
          >{{ opening ? 'Opening…' : 'Open Case' }}</button>
          <p v-if="(wallet?.balance_coins ?? 0) < c.cost_coins" class="case-hint">Not enough MasterCoins</p>

          <button type="button" class="odds-toggle" @click="oddsOpenId = oddsOpenId === c.id ? null : c.id">
            {{ oddsOpenId === c.id ? 'Hide odds ▲' : 'View odds ▼' }}
          </button>
          <div v-if="oddsOpenId === c.id" class="odds-grid">
            <div
              v-for="r in c.rewards" :key="r.coins" class="odds-tile"
              :style="{ borderColor: tierFor(r.coins).border, background: tierFor(r.coins).bg }"
            >
              <CoinIcon :size="16" :color="tierFor(r.coins).border" />
              <span class="odds-tile-coins">{{ r.coins }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- ── History ──────────────────────────── -->
      <section v-if="history.length" class="history-card">
        <h3>Recent Openings</h3>
        <div class="history-list">
          <div v-for="h in history" :key="h.id" class="history-row">
            <span class="history-name">{{ h.case_name }}</span>
            <span class="history-amounts">
              <span class="spent">-{{ h.coins_spent }}</span>
              <span class="won">+{{ h.coins_won }} MC</span>
            </span>
          </div>
        </div>
      </section>
    </div>

    <Footer />

    <!-- ── REVEAL POPUP ─────────────────────────────────── -->
    <!-- Explicit :duration bypasses waiting on the transitionend DOM event —
         if that never fires (backgrounded tab, reduced-motion), Vue's
         <transition> gets stuck mid-leave forever: an invisible
         position:fixed;inset:0 backdrop keeps blocking every click. -->
    <transition name="fade" :duration="200">
      <div v-if="revealOpen" class="modal-backdrop" @click.self="revealDone && closeReveal()">
        <div class="modal reveal-modal">
          <button v-if="revealDone" class="modal-close" @click="closeReveal">✕</button>

          <div class="carousel-wrap" ref="carouselWrapRef">
            <div class="carousel-center-line"></div>
            <div class="carousel-strip" :class="{ animating: stripAnimating }" :style="{ transform: `translateX(${stripOffset}px)` }">
              <div
                v-for="(tile, i) in stripItems" :key="i" class="case-tile"
                :class="{ won: revealDone && i === WINNING_INDEX }"
                :style="{ borderColor: tierFor(tile.coins).border, background: tierFor(tile.coins).bg }"
              >
                <CoinIcon :size="20" :color="tierFor(tile.coins).border" />
                <span>{{ tile.coins }}</span>
              </div>
            </div>
          </div>

          <template v-if="revealDone">
            <p class="reveal-amount"><CoinIcon :size="24" /> +{{ revealResult }} <span>MC</span></p>
            <p class="reveal-sub">Added to your balance</p>
            <button class="btn-primary reveal-btn" @click="closeReveal">Nice!</button>
          </template>
          <p v-else class="reveal-sub">Opening…</p>
        </div>
      </div>
    </transition>
  </main>
</template>

<script setup>
import { ref, onMounted, nextTick } from 'vue'
import { storeToRefs } from 'pinia'
import { useUserStore } from '../store/user'
import { casesAPI } from '../api/cases'
import Header from '../components/Header.vue'
import Footer from '../components/Footer.vue'

const userStore = useUserStore()
const { wallet } = storeToRefs(userStore)

const cases = ref([])
const loading = ref(true)
const opening = ref(false)
const oddsOpenId = ref(null)
const history = ref([])

// ── Rarity tiers, CS2-style: grey / blue / purple / red ──────────
const RARITY_TIERS = [
  { max: 10,       border: '#b0c3d9', bg: 'rgba(176,195,217,0.14)' },
  { max: 49,       border: '#4b69ff', bg: 'rgba(75,105,255,0.14)' },
  { max: 100,      border: '#8847ff', bg: 'rgba(136,71,255,0.14)' },
  { max: Infinity, border: '#eb4b4b', bg: 'rgba(235,75,75,0.14)' },
]
function tierFor(coins) {
  return RARITY_TIERS.find(t => coins <= t.max)
}

// ── Case-opening carousel (CS2-style scroll-and-land reel) ────────
const CASE_TILE_WIDTH = 76
const CASE_TILE_GAP = 8
const CASE_TILE_PITCH = CASE_TILE_WIDTH + CASE_TILE_GAP
const STRIP_LENGTH = 55
const WINNING_INDEX = 48
const SPIN_DURATION_MS = 4200

const stripItems = ref([])
const stripOffset = ref(0)
const stripAnimating = ref(false)
const carouselWrapRef = ref(null)

function buildStrip(rewardPool, winningCoins) {
  const items = []
  for (let i = 0; i < STRIP_LENGTH; i++) {
    if (i === WINNING_INDEX) {
      items.push({ coins: winningCoins })
    } else {
      items.push({ coins: rewardPool[Math.floor(Math.random() * rewardPool.length)].coins })
    }
  }
  return items
}

const revealOpen = ref(false)
const revealDone = ref(false)
const revealResult = ref(0)
const errorMsg = ref('')

async function loadCases() {
  loading.value = true
  try {
    cases.value = await casesAPI.list()
  } finally {
    loading.value = false
  }
}

async function loadHistory() {
  try {
    history.value = await casesAPI.history()
  } catch (e) {
    // Not critical to the page.
  }
}

async function openCase(c) {
  if (opening.value) return
  if ((wallet.value?.balance_coins ?? 0) < c.cost_coins) return

  opening.value = true
  errorMsg.value = ''
  revealDone.value = false
  stripAnimating.value = false
  stripOffset.value = 0
  revealOpen.value = true

  try {
    const res = await casesAPI.open(c.id)
    if (wallet.value) wallet.value.balance_coins = res.new_balance

    stripItems.value = buildStrip(c.rewards, res.reward_coins)
    revealResult.value = res.reward_coins

    // Two steps: one to mount the strip at offset 0 with no transition, a
    // second (a hair later, not on the same tick) so the browser paints
    // that resting frame before we flip on the transition and jump to the
    // target — otherwise the very first frame can get folded into the
    // animated one and skip the spin. A short setTimeout does this more
    // reliably than requestAnimationFrame: rAF callbacks are suspended
    // entirely while a tab isn't actively compositing (backgrounded, some
    // embedded WebViews), which would leave the strip stuck at rest forever.
    await nextTick()
    setTimeout(() => {
      const containerWidth = carouselWrapRef.value?.clientWidth ?? 300
      const jitter = (Math.random() - 0.5) * (CASE_TILE_WIDTH - 24)
      const target = -(WINNING_INDEX * CASE_TILE_PITCH + CASE_TILE_WIDTH / 2 - containerWidth / 2) + jitter
      stripAnimating.value = true
      stripOffset.value = target
    }, 30)

    // A timer, not transitionend, drives the reveal — for the same reason
    // the modal-close fix doesn't wait on that event either: it can simply
    // never fire (backgrounded tab, reduced motion), hanging the reveal.
    setTimeout(() => {
      revealDone.value = true
      opening.value = false
    }, SPIN_DURATION_MS)

    await loadHistory()
  } catch (e) {
    revealOpen.value = false
    opening.value = false
    errorMsg.value = e.response?.data?.detail || 'Could not open the case — please try again.'
  }
}

function closeReveal() {
  revealOpen.value = false
}

onMounted(async () => {
  window.scrollTo({ top: 0, behavior: 'auto' })
  await loadCases()
  loadHistory()
})
</script>

<script>
import { h } from 'vue'

// ── Custom icons (no emoji) ─────────────────────────────────────
// Defined in a plain <script> block (not <script setup>) since a render
// function needs an options object — merges automatically with the
// <script setup> block above, same SFC.
// Coin: the same MasterCoins glyph used everywhere else in the app
// (Pricing/User payment icons), for one consistent icon language.
const CoinIcon = {
  props: { size: { type: Number, default: 18 }, color: { type: String, default: 'currentColor' } },
  render() {
    return h('svg', { viewBox: '0 0 24 24', width: this.size, height: this.size, fill: 'none', style: { flexShrink: 0 } }, [
      h('circle', { cx: 12, cy: 12, r: 8, stroke: this.color, 'stroke-width': 1.6 }),
      h('path', {
        d: 'M12 8v8M9.5 9.8c0-.9 1-1.6 2.5-1.6s2.5.7 2.5 1.6c0 2-5 1-5 3 0 .9 1 1.6 2.5 1.6s2.5-.7 2.5-1.6',
        stroke: this.color, 'stroke-width': 1.3, 'stroke-linecap': 'round',
      }),
    ])
  },
}

// Case: a stylized locked crate, built from plain shapes in the app's own
// accent color — no external art, no emoji.
const CaseIcon = {
  render() {
    return h('svg', { viewBox: '0 0 48 48', width: 48, height: 48, fill: 'none' }, [
      h('rect', { x: 6, y: 20, width: 36, height: 22, rx: 3, fill: 'var(--accent)' }),
      h('rect', { x: 6, y: 20, width: 36, height: 8, rx: 3, fill: 'rgba(255,255,255,.2)' }),
      h('rect', { x: 19, y: 10, width: 10, height: 14, rx: 2, stroke: 'var(--accent)', 'stroke-width': 2, fill: 'var(--bg-elevated)' }),
      h('circle', { cx: 24, cy: 31, r: 4, fill: 'rgba(0,0,0,.3)' }),
      h('rect', { x: 23, y: 29, width: 2, height: 4, rx: 1, fill: 'rgba(255,255,255,.55)' }),
    ])
  },
}

export default { components: { CoinIcon, CaseIcon } }
</script>

<style scoped>
.cases-page { min-height: 100vh; background: var(--bg); }
.cases-content { padding: 32px 20px 100px; max-width: 900px; }

.page-header { text-align: center; margin-bottom: 32px; }
.page-header h1 { font-size: clamp(26px, 5vw, 38px); font-weight: 900; color: var(--text); }
.accent { color: var(--accent); }
.page-header p { font-size: 13.5px; color: var(--text-dim); margin-top: 8px; }

.loader-row { display: flex; justify-content: center; padding: 60px 0; }
.spinner {
  width: 32px; height: 32px; border: 2.5px solid var(--line);
  border-top-color: var(--accent); border-radius: 50%; animation: spin .8s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }
.empty { text-align: center; padding: 60px 20px; color: var(--text-dim); font-size: 14px; }

.case-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(230px, 1fr)); gap: 20px; margin-bottom: 32px; }
.case-card {
  background: linear-gradient(160deg, rgba(255,154,0,0.07), var(--bg-elevated) 60%);
  border: 1px solid rgba(255,154,0,0.25); border-radius: var(--radius-lg);
  padding: 24px 20px; text-align: center;
}
.case-icon { display: flex; justify-content: center; margin-bottom: 10px; }
.case-card h3 { font-size: 16px; font-weight: 800; color: var(--text); margin-bottom: 6px; }
.case-cost {
  display: flex; align-items: center; justify-content: center; gap: 6px;
  font-size: 22px; font-weight: 900; color: var(--accent); margin-bottom: 16px;
}
.case-cost span { font-size: 13px; font-weight: 700; color: var(--text-dim); }

.case-open-btn { width: 100%; padding: 12px; font-size: 13.5px; }
.case-open-btn:disabled { opacity: .5; cursor: not-allowed; }
.case-hint { font-size: 11px; color: var(--danger); margin-top: 6px; }

.odds-toggle {
  display: block; width: 100%; margin-top: 14px;
  background: none; border: none; color: var(--text-dim);
  font-size: 11.5px; font-weight: 700; cursor: pointer; text-decoration: underline;
}
.odds-toggle:hover { color: var(--accent); }

.odds-grid {
  display: grid; grid-template-columns: repeat(auto-fill, minmax(64px, 1fr)); gap: 8px;
  margin-top: 14px;
}
.odds-tile {
  display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 3px;
  aspect-ratio: 1; border-radius: 8px; border: 1.5px solid;
}
.odds-tile-coins { font-size: 13px; font-weight: 800; color: var(--text); }

.history-card {
  background: var(--bg-elevated); border: 1px solid var(--line);
  border-radius: var(--radius-lg); padding: 20px;
}
.history-card h3 { font-size: 14px; font-weight: 800; color: var(--text); margin-bottom: 12px; }
.history-list { display: flex; flex-direction: column; gap: 6px; }
.history-row {
  display: flex; align-items: center; justify-content: space-between;
  padding: 9px 12px; background: var(--bg); border-radius: 8px; font-size: 12.5px;
}
.history-name { color: var(--text); font-weight: 600; }
.history-amounts { display: flex; gap: 8px; font-weight: 700; font-variant-numeric: tabular-nums; }
.spent { color: var(--danger); }
.won { color: var(--success); }

/* ── Reveal modal ─────────────────────────────── */
.modal-backdrop {
  position: fixed; inset: 0; z-index: 500;
  background: rgba(0,0,0,0.65); display: flex; align-items: center; justify-content: center;
  padding: 20px; backdrop-filter: blur(4px); overflow-y: auto;
}
.reveal-modal {
  position: relative; width: 100%; max-width: 400px;
  background: var(--bg-elevated); border: 1px solid var(--line);
  border-radius: var(--radius-lg); padding: 24px 16px 28px; text-align: center;
}
.modal-close {
  position: absolute; top: 12px; right: 12px;
  width: 30px; height: 30px; border-radius: 8px;
  background: var(--bg); border: 1px solid var(--line);
  color: var(--text-dim); cursor: pointer;
  display: flex; align-items: center; justify-content: center; font-size: 13px;
}

/* ── Carousel reel ─────────────────────────────── */
.carousel-wrap {
  position: relative; overflow: hidden; height: 100px;
  margin: 8px 0 20px; border-radius: 12px;
  background: var(--bg); border: 1px solid var(--line);
  -webkit-mask-image: linear-gradient(90deg, transparent 0%, #000 12%, #000 88%, transparent 100%);
  mask-image: linear-gradient(90deg, transparent 0%, #000 12%, #000 88%, transparent 100%);
}
.carousel-center-line {
  position: absolute; left: 50%; top: 0; bottom: 0; width: 2px;
  background: var(--accent); transform: translateX(-1px); z-index: 2;
  box-shadow: 0 0 10px var(--accent);
}
.carousel-strip {
  display: flex; gap: 8px; padding: 8px 0; height: 100%;
  transform: translateX(0);
}
.carousel-strip.animating { transition: transform 4.2s cubic-bezier(0.09, 0, 0.03, 1); }

.case-tile {
  flex-shrink: 0; width: 76px; height: 84px; border-radius: 8px;
  display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 4px;
  border: 1.5px solid; font-weight: 800; font-size: 13px; color: var(--text);
  transition: box-shadow .2s;
}
.case-tile.won { box-shadow: 0 0 0 2px var(--accent), 0 0 16px rgba(255,154,0,.5); }

.reveal-amount {
  display: flex; align-items: center; justify-content: center; gap: 8px;
  font-size: 26px; font-weight: 900; color: var(--accent);
}
.reveal-amount span { font-size: 15px; color: var(--text-dim); font-weight: 700; }
.reveal-sub { font-size: 12.5px; color: var(--text-dim); margin-top: 4px; margin-bottom: 18px; }
.reveal-btn { width: 100%; padding: 12px; }

.fade-enter-active, .fade-leave-active { transition: opacity .2s; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>
