<template>
  <main class="cases-page">
    <Header />

    <div class="wrap cases-content">
      <section class="page-header">
        <h1>Open a <span class="accent">Case</span></h1>
        <p>Spend MasterCoins for a shot at winning more back.</p>
      </section>

      <div class="view-tabs">
        <button type="button" class="view-tab" :class="{ active: activeView === 'shop' }" @click="activeView = 'shop'">Shop</button>
        <button type="button" class="view-tab" :class="{ active: activeView === 'inventory' }" @click="activeView = 'inventory'">
          My Inventory <span v-if="totalOwned" class="tab-badge">{{ totalOwned }}</span>
        </button>
      </div>

      <div v-if="loading" class="loader-row"><div class="spinner"></div></div>
      <div v-else-if="!cases.length" class="empty">No cases available right now.</div>

      <!-- ═══ SHOP ═══════════════════════════════ -->
      <div v-else-if="activeView === 'shop'" class="case-grid">
        <div v-for="c in cases" :key="c.id" class="case-card">
          <div class="case-icon"><CaseIcon /></div>
          <h3>{{ c.name }}</h3>
          <p class="case-cost"><CoinIcon :size="16" /> {{ c.cost_coins }} <span>MC</span></p>

          <div class="qty-picker">
            <button type="button" class="qty-btn" @click="setQty(c.id, qty(c.id) - 1)">−</button>
            <input type="number" class="qty-input" min="1" max="99" :value="qty(c.id)" @input="setQty(c.id, $event.target.valueAsNumber)" />
            <button type="button" class="qty-btn" @click="setQty(c.id, qty(c.id) + 1)">+</button>
          </div>
          <div class="qty-presets">
            <button
              v-for="n in [1, 3, 5, 9]" :key="n" type="button" class="qty-preset"
              :class="{ active: qty(c.id) === n }" @click="setQty(c.id, n)"
            >{{ n }}</button>
          </div>

          <button
            class="btn-primary buy-btn" :disabled="buying || (wallet?.balance_coins ?? 0) < c.cost_coins * qty(c.id)"
            @click="buyCase(c, qty(c.id))"
          >{{ buying ? 'Buying…' : `Buy ${qty(c.id)} for ${c.cost_coins * qty(c.id)} MC` }}</button>
          <p v-if="(wallet?.balance_coins ?? 0) < c.cost_coins * qty(c.id)" class="case-hint">Not enough MasterCoins</p>

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

      <!-- ═══ INVENTORY ═══════════════════════════════ -->
      <div v-else class="case-grid">
        <div v-if="!inventory.length" class="empty">Your inventory is empty — buy a case in the Shop first.</div>
        <div v-for="inv in inventory" :key="inv.case_id" class="case-card">
          <div class="case-icon"><CaseIcon /></div>
          <h3>{{ inv.case_name }}</h3>
          <p class="inventory-line">You own <strong>{{ inv.count }}</strong></p>

          <div class="open-row">
            <button
              v-for="q in [1, 2, 5]" :key="q" class="btn-primary open-btn"
              :disabled="opening || inv.count < q"
              @click="openCases(caseById(inv.case_id), q)"
            >{{ opening ? '…' : `Open ×${q}` }}</button>
          </div>

          <button
            v-if="historyFor(inv.case_id).length" type="button" class="odds-toggle"
            @click="historyOpenId = historyOpenId === inv.case_id ? null : inv.case_id"
          >
            {{ historyOpenId === inv.case_id ? 'Hide recent openings ▲' : 'Recent openings ▼' }}
          </button>
          <div v-if="historyOpenId === inv.case_id" class="history-list">
            <div v-for="h in historyFor(inv.case_id)" :key="h.id" class="history-row">
              <span class="history-time">{{ formatHistoryTime(h.created_at) }}</span>
              <span class="history-amounts">
                <span class="spent">-{{ h.coins_spent }}</span>
                <span class="won">+{{ h.coins_won }} MC</span>
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <Footer />

    <!-- ── REVEAL POPUP ─────────────────────────────────── -->
    <!-- Explicit :duration bypasses waiting on the transitionend DOM event —
         if that never fires (backgrounded tab, reduced-motion), Vue's
         <transition> gets stuck mid-leave forever: an invisible
         position:fixed;inset:0 backdrop keeps blocking every click. -->
    <transition name="fade" :duration="200">
      <div v-if="revealOpen" class="modal-backdrop" @click.self="revealDone && closeReveal()">
        <div class="modal reveal-modal" :class="{ multi: revealReels.length > 1 }">
          <button v-if="revealDone" class="modal-close" @click="closeReveal">✕</button>

          <div
            v-for="(reel, ri) in revealReels" :key="ri" class="carousel-wrap"
            :ref="(el) => { if (el) carouselWrapRefs[ri] = el }"
          >
            <div class="carousel-center-line"></div>
            <div class="carousel-strip" :class="{ animating: reel.animating }" :style="{ transform: `translateX(${reel.offset}px)` }">
              <div
                v-for="(tile, i) in reel.items" :key="i" class="case-tile"
                :class="{ won: revealDone && i === WINNING_INDEX }"
                :style="{ borderColor: tierFor(tile.coins).border, background: tierFor(tile.coins).bg }"
              >
                <CoinIcon :size="20" :color="tierFor(tile.coins).border" />
                <span>{{ tile.coins }}</span>
              </div>
            </div>
          </div>

          <template v-if="revealDone">
            <p class="reveal-amount"><CoinIcon :size="24" /> +{{ revealTotalWon }} <span>MC</span></p>
            <p class="reveal-sub">{{ revealReels.length > 1 ? 'Total added to your balance' : 'Added to your balance' }}</p>
            <button class="btn-primary reveal-btn" @click="closeReveal">Nice!</button>
          </template>
          <p v-else class="reveal-sub">Opening…</p>
        </div>
      </div>
    </transition>
  </main>
</template>

<script setup>
import { ref, computed, onMounted, nextTick } from 'vue'
import { storeToRefs } from 'pinia'
import { useUserStore } from '../store/user'
import { casesAPI } from '../api/cases'
import Header from '../components/Header.vue'
import Footer from '../components/Footer.vue'

const userStore = useUserStore()
const { wallet } = storeToRefs(userStore)

const cases = ref([])
const loading = ref(true)
const buying = ref(false)
const opening = ref(false)
const oddsOpenId = ref(null)
const historyOpenId = ref(null)
const history = ref([])
const inventory = ref([]) // [{ case_id, case_name, count }]
const activeView = ref('shop') // 'shop' | 'inventory'

function caseById(id) {
  return cases.value.find(c => c.id === id)
}

const totalOwned = computed(() => inventory.value.reduce((sum, i) => sum + i.count, 0))

// Per-case buy quantity, defaulting to 1 — the quick-pick chips (1/3/5/9)
// and +/- stepper both write into this same map.
const buyQty = ref({})
function qty(caseId) {
  return buyQty.value[caseId] ?? 1
}
function setQty(caseId, value) {
  const n = Math.max(1, Math.min(99, Math.round(value) || 1))
  buyQty.value[caseId] = n
}

function inventoryCount(caseId) {
  return inventory.value.find(i => i.case_id === caseId)?.count ?? 0
}

function historyFor(caseId) {
  return history.value.filter(h => h.case_id === caseId)
}
function formatHistoryTime(iso) {
  const d = new Date(iso)
  return d.toLocaleString(undefined, { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' })
}

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

// One entry per case opened in this batch — each is its own independent
// reel (x1 is just the single-reel case of this).
const revealOpen = ref(false)
const revealDone = ref(false)
const revealReels = ref([]) // [{ items, offset, animating }]
const revealTotalWon = ref(0)
const carouselWrapRefs = ref([])
const errorMsg = ref('')

async function loadCases() {
  loading.value = true
  try {
    cases.value = await casesAPI.list()
  } finally {
    loading.value = false
  }
}

async function loadInventory() {
  try {
    inventory.value = await casesAPI.inventory()
  } catch (e) {
    // Not critical to the page.
  }
}

async function loadHistory() {
  try {
    history.value = await casesAPI.history()
  } catch (e) {
    // Not critical to the page.
  }
}

async function buyCase(c, quantity) {
  if (buying.value) return
  if ((wallet.value?.balance_coins ?? 0) < c.cost_coins * quantity) return

  buying.value = true
  errorMsg.value = ''
  try {
    const res = await casesAPI.buy(c.id, quantity)
    if (wallet.value) wallet.value.balance_coins = res.new_balance
    await loadInventory()
    activeView.value = 'inventory'
  } catch (e) {
    errorMsg.value = e.response?.data?.detail || 'Could not buy the case — please try again.'
  } finally {
    buying.value = false
  }
}

async function openCases(c, quantity) {
  if (opening.value || !c) return
  if (inventoryCount(c.id) < quantity) return

  opening.value = true
  errorMsg.value = ''
  revealDone.value = false
  carouselWrapRefs.value = []
  revealReels.value = Array.from({ length: quantity }, () => ({ items: [], offset: 0, animating: false }))
  revealOpen.value = true

  try {
    const res = await casesAPI.openInventory(c.id, quantity)
    if (wallet.value) wallet.value.balance_coins = res.new_balance
    revealTotalWon.value = res.total_won
    revealReels.value = res.rewards.map(coins => ({ items: buildStrip(c.rewards, coins), offset: 0, animating: false }))
    await loadInventory()

    // Two steps: one to mount each strip at offset 0 with no transition, a
    // second (a hair later, not on the same tick) so the browser paints
    // that resting frame before we flip on the transition and jump to the
    // target — otherwise the very first frame can get folded into the
    // animated one and skip the spin. A short setTimeout does this more
    // reliably than requestAnimationFrame: rAF callbacks are suspended
    // entirely while a tab isn't actively compositing (backgrounded, some
    // embedded WebViews), which would leave the strip stuck at rest forever.
    await nextTick()
    setTimeout(() => {
      revealReels.value.forEach((reel, i) => {
        const containerWidth = carouselWrapRefs.value[i]?.clientWidth ?? 300
        const jitter = (Math.random() - 0.5) * (CASE_TILE_WIDTH - 24)
        const target = -(WINNING_INDEX * CASE_TILE_PITCH + CASE_TILE_WIDTH / 2 - containerWidth / 2) + jitter
        reel.animating = true
        reel.offset = target
      })
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
    errorMsg.value = e.response?.data?.detail || 'Could not open — please try again.'
  }
}

function closeReveal() {
  revealOpen.value = false
}

onMounted(async () => {
  window.scrollTo({ top: 0, behavior: 'auto' })
  await loadCases()
  await loadInventory()
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

// Case: a CS2-style metal crate — isometric box, diagonal hazard stripe
// across the lid, corner rivets and a MasterCoins badge (the same coin
// glyph used everywhere else in the app) — built from plain shapes/
// gradients in the app's own accent color, no external art.
let caseIconSeq = 0
const CaseIcon = {
  props: { size: { type: Number, default: 72 } },
  data() { return { uid: `ci${++caseIconSeq}` } },
  render() {
    const id = this.uid
    return h('svg', { viewBox: '0 0 48 48', width: this.size, height: this.size, fill: 'none' }, [
      h('defs', {}, [
        h('linearGradient', { id: `${id}-front`, x1: '0', y1: '0', x2: '0', y2: '1' }, [
          h('stop', { offset: '0', 'stop-color': 'var(--accent)' }),
          h('stop', { offset: '1', 'stop-color': '#c46b00' }),
        ]),
        h('linearGradient', { id: `${id}-top`, x1: '0', y1: '0', x2: '1', y2: '1' }, [
          h('stop', { offset: '0', 'stop-color': '#ffcf80' }),
          h('stop', { offset: '1', 'stop-color': 'var(--accent)' }),
        ]),
        h('clipPath', { id: `${id}-clip` }, [
          h('rect', { x: 8, y: 15, width: 28, height: 26, rx: 2 }),
        ]),
      ]),

      // side face (depth)
      h('polygon', { points: '36,15 42,7 42,33 36,41', fill: '#8a4c00' }),
      // top face (lid)
      h('polygon', { points: '8,15 14,7 42,7 36,15', fill: `url(#${id}-top)` }),
      // front face
      h('rect', { x: 8, y: 15, width: 28, height: 26, rx: 2, fill: `url(#${id}-front)` }),

      // diagonal hazard stripes, clipped to the front face
      h('g', { 'clip-path': `url(#${id}-clip)`, opacity: 0.5 }, [
        h('rect', { x: -4, y: 16, width: 50, height: 4, fill: '#14140f', transform: 'rotate(-28 20 28)' }),
        h('rect', { x: -4, y: 26, width: 50, height: 4, fill: '#14140f', transform: 'rotate(-28 20 28)' }),
      ]),

      // corner rivets
      h('circle', { cx: 11, cy: 18, r: 1.3, fill: 'rgba(0,0,0,.4)' }),
      h('circle', { cx: 33, cy: 18, r: 1.3, fill: 'rgba(0,0,0,.4)' }),
      h('circle', { cx: 11, cy: 38, r: 1.3, fill: 'rgba(0,0,0,.4)' }),
      h('circle', { cx: 33, cy: 38, r: 1.3, fill: 'rgba(0,0,0,.4)' }),

      // MasterCoins badge — same circle+squiggle glyph as CoinIcon, dropped
      // onto the crate so it reads instantly as "coins inside", not a
      // generic loot box.
      h('g', { transform: 'translate(22,29) scale(0.94) translate(-12,-12)' }, [
        h('circle', { cx: 12, cy: 12, r: 8, fill: `url(#${id}-top)`, stroke: '#14140f', 'stroke-width': 1.7 }),
        h('path', {
          d: 'M12 8v8M9.5 9.8c0-.9 1-1.6 2.5-1.6s2.5.7 2.5 1.6c0 2-5 1-5 3 0 .9 1 1.6 2.5 1.6s2.5-.7 2.5-1.6',
          stroke: '#14140f', 'stroke-width': 1.5, 'stroke-linecap': 'round', fill: 'none',
        }),
      ]),
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

.view-tabs {
  display: flex; justify-content: center; gap: 8px; margin-bottom: 28px;
}
.view-tab {
  display: flex; align-items: center; gap: 7px;
  padding: 10px 22px; border-radius: 99px;
  background: var(--bg-elevated); border: 1.5px solid var(--line);
  color: var(--text-dim); font-size: 13px; font-weight: 700; cursor: pointer;
  transition: all .15s;
}
.view-tab:hover { border-color: rgba(255,154,0,.5); color: var(--text); }
.view-tab.active { background: rgba(255,154,0,.12); border-color: var(--accent); color: var(--accent); }
.tab-badge {
  background: var(--accent); color: #14140f; font-size: 10.5px; font-weight: 900;
  padding: 1px 7px; border-radius: 99px;
}

.loader-row { display: flex; justify-content: center; padding: 60px 0; }
.spinner {
  width: 32px; height: 32px; border: 2.5px solid var(--line);
  border-top-color: var(--accent); border-radius: 50%; animation: spin .8s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }
.empty { text-align: center; padding: 60px 20px; color: var(--text-dim); font-size: 14px; }

.case-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 20px; margin-bottom: 32px; }
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

.mini-btn {
  background: linear-gradient(160deg, var(--bg-elevated), var(--bg)); border: 1px solid var(--line); color: var(--text-dim);
  border-radius: 8px; font-weight: 700; cursor: pointer;
  box-shadow: 0 2px 6px rgba(0,0,0,.18);
  transition: border-color .15s, color .15s, transform .15s, box-shadow .15s;
}
.mini-btn:hover:not(:disabled) { border-color: var(--accent); color: var(--accent); box-shadow: 0 4px 14px -4px rgba(255,154,0,.4); transform: translateY(-1px); }
.mini-btn:active:not(:disabled) { transform: translateY(0); }

.qty-picker { display: flex; align-items: stretch; justify-content: center; gap: 6px; margin-bottom: 8px; }
.qty-btn {
  width: 34px; border-radius: 8px; background: var(--bg); border: 1px solid var(--line);
  color: var(--text-dim); font-size: 16px; font-weight: 700; cursor: pointer;
  transition: border-color .15s, color .15s;
}
.qty-btn:hover { border-color: var(--accent); color: var(--accent); }
.qty-input {
  width: 64px; text-align: center; background: var(--bg); border: 1px solid var(--line);
  border-radius: 8px; color: var(--text); font-size: 14px; font-weight: 800;
  -moz-appearance: textfield;
}
.qty-input::-webkit-outer-spin-button, .qty-input::-webkit-inner-spin-button { -webkit-appearance: none; margin: 0; }
.qty-input:focus { outline: none; border-color: var(--accent); }

.qty-presets { display: flex; justify-content: center; gap: 6px; margin-bottom: 14px; }
.qty-preset {
  padding: 4px 11px; border-radius: 99px; background: var(--bg); border: 1px solid var(--line);
  color: var(--text-dim); font-size: 11.5px; font-weight: 700; cursor: pointer;
  transition: all .15s;
}
.qty-preset:hover { border-color: var(--accent); color: var(--accent); }
.qty-preset.active { background: rgba(255,154,0,.14); border-color: var(--accent); color: var(--accent); }

.buy-btn { width: 100%; padding: 12px; font-size: 12.5px; }
.buy-btn:disabled { opacity: .5; cursor: not-allowed; }
.case-hint { font-size: 11px; color: var(--danger); margin-top: 6px; }

.inventory-line { font-size: 12px; color: var(--text-dim); margin: 14px 0 8px; }
.inventory-line strong { color: var(--text); font-weight: 800; }

.open-row { display: flex; gap: 6px; flex-wrap: wrap; }
.open-btn { flex: 1; min-width: 74px; padding: 10px 6px; font-size: 12px; }
.open-btn:disabled { opacity: .4; cursor: not-allowed; }

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

.history-list { display: flex; flex-direction: column; gap: 6px; margin-top: 14px; text-align: left; }
.history-row {
  display: flex; align-items: center; justify-content: space-between; gap: 8px;
  padding: 9px 12px; background: var(--bg); border-radius: 8px; font-size: 12.5px;
}
.history-time { color: var(--text-dim); font-size: 11px; white-space: nowrap; }
.history-amounts { display: flex; gap: 8px; font-weight: 700; font-variant-numeric: tabular-nums; white-space: nowrap; }
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
.reveal-modal.multi { max-width: 420px; }
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
