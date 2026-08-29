<template>
  <main class="admin-page">
    <Header />

    <div class="wrap admin-content">
      <button class="back-btn" @click="router.push('/admin')">
        <svg viewBox="0 0 16 16" fill="none" width="14" height="14">
          <path d="M10 3L5 8l5 5" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
        Admin Panel
      </button>

      <section class="page-head">
        <span class="eyebrow">Economy</span>
        <h1>Transactions</h1>
      </section>

      <div class="filters-row">
        <div class="type-filter">
          <button
            v-for="opt in TYPE_OPTIONS" :key="opt.value ?? 'all'"
            class="type-chip" :class="{ active: typeFilter === opt.value }"
            @click="setTypeFilter(opt.value)"
          >{{ opt.label }}</button>
        </div>
        <input v-model="walletFilter" type="text" placeholder="Filter by Wallet ID…" class="wallet-search" @input="debouncedSearch" />
      </div>

      <section class="list-card">
        <div v-if="loading" class="loading-row">Loading…</div>
        <table v-else class="admin-table">
          <thead>
            <tr><th>Type</th><th>From</th><th>To</th><th>Amount</th><th>Date</th></tr>
          </thead>
          <tbody>
            <tr v-for="t in transactions" :key="t.id">
              <td><span class="type-pill" :class="t.transaction_type">{{ typeLabel(t.transaction_type) }}</span></td>
              <td class="mono">{{ t.sender_wallet_id ?? '— system —' }}</td>
              <td class="mono">{{ t.receiver_wallet_id }}</td>
              <td class="amount">{{ t.amount }} MC</td>
              <td class="dim">{{ formatDate(t.created_at) }}</td>
            </tr>
            <tr v-if="!transactions.length">
              <td colspan="5" class="empty">No transactions found.</td>
            </tr>
          </tbody>
        </table>

        <div v-if="total > transactions.length" class="load-more">
          <button class="mini-btn" @click="loadMore">Load more ({{ transactions.length }} / {{ total }})</button>
        </div>
      </section>
    </div>

    <Footer />
  </main>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { storeToRefs } from 'pinia'
import { useUserStore } from '../store/user'
import { adminAPI } from '../api/admin'
import Header from '../components/Header.vue'
import Footer from '../components/Footer.vue'

const router = useRouter()
const { user } = storeToRefs(useUserStore())

const transactions = ref([])
const total = ref(0)
const loading = ref(true)
const walletFilter = ref('')
const typeFilter = ref(null)
const LIMIT = 50

const TYPE_OPTIONS = [
  { value: null, label: 'All' },
  { value: 'p2p_transfer', label: 'P2P' },
  { value: 'subscription_buy', label: 'Subscriptions' },
  { value: 'referral_bonus', label: 'Referral' },
  { value: 'promo_code', label: 'Promo' },
  { value: 'crypto_deposit', label: 'Crypto' },
  { value: 'case_open', label: 'Cases' },
  { value: 'case_gift', label: 'Case Gifts' },
  { value: 'case_sale', label: 'Case Sales' },
]

function typeLabel(type) {
  return TYPE_OPTIONS.find(o => o.value === type)?.label ?? type
}

function formatDate(iso) {
  return new Date(iso).toLocaleString(undefined, {
    month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit',
  })
}

async function load(offset = 0, append = false) {
  loading.value = !append
  const res = await adminAPI.getTransactions({
    transaction_type: typeFilter.value || undefined,
    wallet_id: walletFilter.value || undefined,
    limit: LIMIT,
    offset,
  })
  transactions.value = append ? [...transactions.value, ...res.transactions] : res.transactions
  total.value = res.total
  loading.value = false
}

function loadMore() { load(transactions.value.length, true) }

function setTypeFilter(value) {
  typeFilter.value = value
  load(0, false)
}

let searchTimer = null
function debouncedSearch() {
  clearTimeout(searchTimer)
  searchTimer = setTimeout(() => load(0, false), 350)
}

onMounted(() => {
  if (!user.value?.is_admin) { router.replace('/user'); return }
  load()
})
</script>

<style scoped>
.admin-page { min-height: 100vh; background: var(--bg); }
.admin-content { max-width: 960px; padding: 32px 20px 120px; }

.back-btn {
  display: inline-flex; align-items: center; gap: 6px;
  background: var(--bg-elevated); border: 1px solid var(--line);
  color: var(--text-dim); padding: 8px 16px; border-radius: 8px;
  font-size: 13px; font-weight: 600; cursor: pointer;
  transition: border-color .2s, color .2s; margin-bottom: 28px;
}
.back-btn:hover { border-color: var(--accent); color: var(--accent); }

.page-head { margin-bottom: 20px; }
.eyebrow {
  display: block; font-size: 11px; font-weight: 800; letter-spacing: .08em;
  text-transform: uppercase; color: var(--accent); margin-bottom: 6px;
}
.page-head h1 { font-size: clamp(22px, 4vw, 30px); font-weight: 900; color: var(--text); }

.filters-row {
  display: flex; align-items: center; justify-content: space-between;
  gap: 12px; flex-wrap: wrap; margin-bottom: 16px;
}
.type-filter { display: flex; gap: 6px; flex-wrap: wrap; }
.type-chip {
  padding: 6px 13px; border-radius: 99px;
  background: var(--bg-elevated); border: 1.5px solid var(--line);
  color: var(--text-dim); font-size: 12px; font-weight: 700; cursor: pointer;
  transition: all .15s;
}
.type-chip.active { background: rgba(255,154,0,.12); border-color: var(--accent); color: var(--accent); }

.wallet-search {
  flex: 1; min-width: 180px; max-width: 260px;
  background: var(--bg-elevated); border: 1px solid var(--line);
  border-radius: 10px; padding: 9px 13px; color: var(--text); font-size: 13px;
}
.wallet-search:focus { outline: none; border-color: var(--accent); }

.list-card {
  background: var(--bg-elevated); border: 1px solid var(--line);
  border-radius: var(--radius-lg); padding: 22px;
}
.loading-row, .empty { padding: 24px; text-align: center; color: var(--text-dim); font-size: 13px; }

.admin-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.admin-table th {
  text-align: left; font-size: 11px; font-weight: 700; text-transform: uppercase;
  letter-spacing: .04em; color: var(--text-dim); padding: 0 10px 10px;
}
.admin-table td { padding: 11px 10px; border-top: 1px solid var(--line); }
.admin-table td.mono { font-variant-numeric: tabular-nums; font-size: 12px; }
.admin-table td.dim { color: var(--text-dim); font-size: 12px; white-space: nowrap; }
.admin-table td.amount { font-weight: 700; font-variant-numeric: tabular-nums; white-space: nowrap; }

.type-pill {
  padding: 3px 9px; border-radius: 99px; font-size: 10.5px; font-weight: 700;
  white-space: nowrap; background: var(--bg); border: 1px solid var(--line); color: var(--text-dim);
}
.type-pill.p2p_transfer { background: rgba(127,168,255,.12); border-color: rgba(127,168,255,.35); color: #7fa8ff; }
.type-pill.subscription_buy { background: rgba(255,154,0,.12); border-color: rgba(255,154,0,.35); color: var(--accent); }
.type-pill.referral_bonus { background: rgba(80,220,100,.12); border-color: rgba(80,220,100,.35); color: var(--success); }
.type-pill.promo_code { background: rgba(255,204,68,.12); border-color: rgba(255,204,68,.35); color: #ffcc44; }
.type-pill.case_open, .type-pill.case_gift, .type-pill.case_sale { background: rgba(136,71,255,.12); border-color: rgba(136,71,255,.35); color: #8847ff; }

.mini-btn {
  background: linear-gradient(160deg, var(--bg-elevated), var(--bg)); border: 1px solid var(--line); color: var(--text-dim);
  padding: 6px 12px; border-radius: 7px; font-size: 12px; font-weight: 700; cursor: pointer;
  box-shadow: 0 2px 6px rgba(0,0,0,.18);
  transition: border-color .15s, color .15s, transform .15s, box-shadow .15s;
}
.mini-btn:hover { border-color: var(--accent); color: var(--accent); box-shadow: 0 4px 14px -4px rgba(255,154,0,.4); transform: translateY(-1px); }
.mini-btn:active { transform: translateY(0); }

.load-more { text-align: center; padding-top: 18px; }

@media (max-width: 640px) {
  .admin-table { display: block; overflow-x: auto; }
}
</style>
