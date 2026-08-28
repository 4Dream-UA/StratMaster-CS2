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
          <div class="case-icon">🎁</div>
          <h3>{{ c.name }}</h3>
          <p class="case-cost">{{ c.cost_coins }} <span>MC</span></p>

          <button
            class="btn-primary case-open-btn"
            :disabled="opening || (wallet?.balance_coins ?? 0) < c.cost_coins"
            @click="openCase(c)"
          >{{ opening ? 'Opening…' : 'Open Case' }}</button>
          <p v-if="(wallet?.balance_coins ?? 0) < c.cost_coins" class="case-hint">Not enough MasterCoins</p>

          <button type="button" class="odds-toggle" @click="oddsOpenId = oddsOpenId === c.id ? null : c.id">
            {{ oddsOpenId === c.id ? 'Hide odds ▲' : 'View odds ▼' }}
          </button>
          <table v-if="oddsOpenId === c.id" class="odds-table">
            <thead><tr><th>Reward</th><th>Chance</th></tr></thead>
            <tbody>
              <tr v-for="r in c.rewards" :key="r.coins">
                <td>{{ r.coins }} MC</td>
                <td>{{ r.chance_percent }}%</td>
              </tr>
            </tbody>
          </table>
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
      <div v-if="revealOpen" class="modal-backdrop" @click.self="revealSpinning || closeReveal()">
        <div class="modal reveal-modal">
          <button v-if="!revealSpinning" class="modal-close" @click="closeReveal">✕</button>

          <div class="reveal-box" :class="{ spinning: revealSpinning }">
            <span class="reveal-emoji">{{ revealSpinning ? '🎁' : '🪙' }}</span>
          </div>

          <template v-if="!revealSpinning">
            <p class="reveal-amount">+{{ revealResult }} <span>MC</span></p>
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
import { ref, onMounted } from 'vue'
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

const revealOpen = ref(false)
const revealSpinning = ref(false)
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
  revealResult.value = 0
  revealSpinning.value = true
  revealOpen.value = true

  try {
    const [res] = await Promise.all([
      casesAPI.open(c.id),
      new Promise(r => setTimeout(r, 1100)), // let the spin animation play out
    ])
    revealResult.value = res.reward_coins
    if (wallet.value) wallet.value.balance_coins = res.new_balance
    await loadHistory()
  } catch (e) {
    revealOpen.value = false
    errorMsg.value = e.response?.data?.detail || 'Could not open the case — please try again.'
  } finally {
    revealSpinning.value = false
    opening.value = false
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
.case-icon { font-size: 44px; margin-bottom: 10px; }
.case-card h3 { font-size: 16px; font-weight: 800; color: var(--text); margin-bottom: 6px; }
.case-cost { font-size: 22px; font-weight: 900; color: var(--accent); margin-bottom: 16px; }
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

.odds-table { width: 100%; margin-top: 12px; border-collapse: collapse; font-size: 12px; }
.odds-table th {
  text-align: left; color: var(--text-dim); font-weight: 700; text-transform: uppercase;
  letter-spacing: .04em; font-size: 10px; padding: 0 6px 6px;
}
.odds-table td { padding: 5px 6px; border-top: 1px solid var(--line); color: var(--text); }

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
  position: relative; width: 100%; max-width: 340px;
  background: var(--bg-elevated); border: 1px solid var(--line);
  border-radius: var(--radius-lg); padding: 40px 28px 28px; text-align: center;
}
.modal-close {
  position: absolute; top: 16px; right: 16px;
  width: 30px; height: 30px; border-radius: 8px;
  background: var(--bg); border: 1px solid var(--line);
  color: var(--text-dim); cursor: pointer;
  display: flex; align-items: center; justify-content: center; font-size: 13px;
}
.reveal-box { display: flex; justify-content: center; margin-bottom: 18px; }
.reveal-emoji { font-size: 64px; display: inline-block; }
.reveal-box.spinning .reveal-emoji { animation: reveal-spin 1.1s ease-in-out; }
@keyframes reveal-spin {
  0% { transform: scale(0.7) rotate(0deg); }
  50% { transform: scale(1.15) rotate(180deg); }
  100% { transform: scale(1) rotate(360deg); }
}
.reveal-amount { font-size: 30px; font-weight: 900; color: var(--accent); }
.reveal-amount span { font-size: 16px; color: var(--text-dim); font-weight: 700; }
.reveal-sub { font-size: 12.5px; color: var(--text-dim); margin-top: 4px; margin-bottom: 18px; }
.reveal-btn { width: 100%; padding: 12px; }

.fade-enter-active, .fade-leave-active { transition: opacity .2s; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>
