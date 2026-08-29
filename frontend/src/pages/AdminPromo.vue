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
        <span class="eyebrow">Growth</span>
        <h1>Promo Codes</h1>
      </section>

      <section class="form-card">
        <h3>Generate a code</h3>
        <div class="reward-type-toggle">
          <button
            v-for="rt in REWARD_TYPES" :key="rt.value" type="button"
            class="reward-type-btn" :class="{ active: form.reward_type === rt.value }"
            @click="form.reward_type = rt.value"
          >{{ rt.label }}</button>
        </div>
        <div class="form-grid">
          <label class="field">
            <span>Code (optional)</span>
            <input v-model="form.code" type="text" placeholder="Auto-generated if empty" />
          </label>

          <label v-if="form.reward_type === 'coins'" class="field">
            <span>Coin reward</span>
            <input v-model.number="form.coin_reward" type="number" min="1" placeholder="25" />
          </label>

          <label v-if="form.reward_type === 'premium'" class="field">
            <span>Premium days (0 = forever)</span>
            <input v-model.number="form.premium_days" type="number" min="0" placeholder="30" />
          </label>

          <template v-if="form.reward_type === 'case'">
            <label class="field">
              <span>Case</span>
              <select v-model="form.case_id">
                <option value="" disabled>Select a case…</option>
                <option v-for="c in cases" :key="c.id" :value="c.id">{{ c.name }}</option>
              </select>
            </label>
            <label class="field">
              <span>Quantity per redemption</span>
              <input v-model.number="form.case_quantity" type="number" min="1" placeholder="1" />
            </label>
          </template>

          <label class="field">
            <span>Activation limit</span>
            <input v-model.number="form.activations_limit" type="number" min="1" placeholder="100" />
          </label>
        </div>
        <div class="form-actions">
          <button class="btn-primary" :disabled="!canSubmit || saving" @click="createPromo">
            {{ saving ? 'Saving…' : 'Generate' }}
          </button>
          <p v-if="errorMsg" class="err">{{ errorMsg }}</p>
        </div>
      </section>

      <div class="admin-search-wrap">
        <input v-model="search" type="text" class="admin-search" placeholder="Search by code…" />
        <button v-if="search" class="search-clear" @click="search = ''">✕</button>
      </div>

      <section class="list-card">
        <div v-if="loading" class="loading-row">Loading…</div>
        <table v-else class="admin-table">
          <thead>
            <tr><th>Code</th><th>Reward</th><th>Used</th><th>Status</th><th></th></tr>
          </thead>
          <tbody>
            <tr v-for="p in promoCodes" :key="p.id">
              <td class="mono">{{ p.code }}</td>
              <td>{{ rewardLabel(p) }}</td>
              <td>{{ p.used_count }} / {{ p.activations_limit }}</td>
              <td>
                <span class="status-pill" :class="p.is_active ? 'on' : 'off'">
                  {{ p.is_active ? 'Active' : 'Disabled' }}
                </span>
              </td>
              <td class="actions">
                <button class="mini-btn" @click="toggle(p)">
                  {{ p.is_active ? 'Disable' : 'Enable' }}
                </button>
              </td>
            </tr>
            <tr v-if="!promoCodes.length">
              <td colspan="5" class="empty">No promo codes found.</td>
            </tr>
          </tbody>
        </table>
      </section>

      <Pagination :total="total" :page="page" :page-size="PAGE_SIZE" @update:page="onPageChange" />
    </div>

    <Footer />
  </main>
</template>

<script setup>
import { ref, reactive, computed, watch, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { storeToRefs } from 'pinia'
import { useUserStore } from '../store/user'
import { adminAPI } from '../api/admin'
import { casesAPI } from '../api/cases'
import Header from '../components/Header.vue'
import Footer from '../components/Footer.vue'
import Pagination from '../components/Pagination.vue'

const router = useRouter()
const { user } = storeToRefs(useUserStore())
const promoCodes = ref([])
const cases = ref([])
const loading = ref(true)
const saving = ref(false)
const errorMsg = ref('')

const PAGE_SIZE = 5
const page = ref(1)
const total = ref(0)
const search = ref('')

const REWARD_TYPES = [
  { value: 'coins', label: 'MasterCoins' },
  { value: 'premium', label: 'Premium' },
  { value: 'case', label: 'Case' },
]

const form = reactive({
  code: '', reward_type: 'coins',
  coin_reward: 25, premium_days: 30, case_id: '', case_quantity: 1,
  activations_limit: 100,
})

const canSubmit = computed(() => {
  if (form.reward_type === 'coins') return !!form.coin_reward
  if (form.reward_type === 'premium') return form.premium_days !== null && form.premium_days >= 0
  if (form.reward_type === 'case') return !!form.case_id && !!form.case_quantity
  return false
})

function rewardLabel(p) {
  if (p.reward_type === 'premium') return p.premium_days === 0 ? 'Lifetime Premium' : `${p.premium_days}d Premium`
  if (p.reward_type === 'case') return `${p.case_quantity}× ${p.case_name || 'Case'}`
  return `${p.coin_reward} MC`
}

async function load() {
  loading.value = true
  const res = await adminAPI.getPromoCodes({ limit: PAGE_SIZE, offset: (page.value - 1) * PAGE_SIZE, search: search.value || undefined })
  promoCodes.value = res.promo_codes
  total.value = res.total
  loading.value = false
}

function onPageChange(p) {
  page.value = p
  load()
}

let searchTimer = null
watch(search, () => {
  clearTimeout(searchTimer)
  searchTimer = setTimeout(() => { page.value = 1; load() }, 350)
})

async function createPromo() {
  if (!canSubmit.value) return
  saving.value = true
  errorMsg.value = ''
  try {
    await adminAPI.createPromoCode({
      code: form.code.trim() || null,
      reward_type: form.reward_type,
      coin_reward: form.reward_type === 'coins' ? form.coin_reward : 0,
      premium_days: form.reward_type === 'premium' ? form.premium_days : null,
      case_id: form.reward_type === 'case' ? form.case_id : null,
      case_quantity: form.case_quantity || 1,
      activations_limit: form.activations_limit || 100,
    })
    form.code = ''
    form.coin_reward = 25
    form.premium_days = 30
    form.case_id = ''
    form.case_quantity = 1
    form.activations_limit = 100
    await load()
  } catch (e) {
    errorMsg.value = e.response?.data?.detail || 'Could not create promo code.'
  } finally {
    saving.value = false
  }
}

async function toggle(promo) {
  const next = !promo.is_active
  promo.is_active = next
  try {
    await adminAPI.togglePromoCode(promo.id, next)
  } catch (e) {
    promo.is_active = !next
  }
}

onMounted(async () => {
  if (!user.value?.is_admin) { router.replace('/user'); return }
  load()
  cases.value = await casesAPI.list()
})
</script>

<style scoped>
.admin-page { min-height: 100vh; background: var(--bg); }
.admin-content { max-width: 880px; padding: 32px 20px 120px; }

.back-btn {
  display: inline-flex; align-items: center; gap: 6px;
  background: var(--bg-elevated); border: 1px solid var(--line);
  color: var(--text-dim); padding: 8px 16px; border-radius: 8px;
  font-size: 13px; font-weight: 600; cursor: pointer;
  transition: border-color .2s, color .2s; margin-bottom: 28px;
}
.back-btn:hover { border-color: var(--accent); color: var(--accent); }

.page-head { margin-bottom: 24px; }
.eyebrow {
  display: block; font-size: 11px; font-weight: 800; letter-spacing: .08em;
  text-transform: uppercase; color: var(--accent); margin-bottom: 6px;
}
.page-head h1 { font-size: clamp(22px, 4vw, 30px); font-weight: 900; color: var(--text); }

.form-card, .list-card {
  background: var(--bg-elevated); border: 1px solid var(--line);
  border-radius: var(--radius-lg); padding: 22px; margin-bottom: 20px;
}
.form-card h3 { font-size: 15px; font-weight: 700; margin-bottom: 16px; }

.reward-type-toggle { display: flex; gap: 8px; margin-bottom: 16px; }
.reward-type-btn {
  background: var(--bg); border: 1px solid var(--line); color: var(--text-dim);
  padding: 8px 16px; border-radius: 8px; font-size: 12.5px; font-weight: 700; cursor: pointer;
  transition: border-color .15s, color .15s;
}
.reward-type-btn.active { border-color: var(--accent); color: var(--accent); background: rgba(255,154,0,.1); }

.form-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 14px; margin-bottom: 16px; }
.field { display: flex; flex-direction: column; gap: 6px; }
.field span { font-size: 11px; font-weight: 700; color: var(--text-dim); text-transform: uppercase; letter-spacing: .04em; }
.field input, .field select {
  background: var(--bg); border: 1px solid var(--line); border-radius: 9px;
  padding: 10px 12px; color: var(--text); font-size: 13.5px; font-family: inherit;
}
.field input:focus, .field select:focus { outline: none; border-color: var(--accent); }

.form-actions { display: flex; align-items: center; gap: 14px; }
.err { color: var(--danger); font-size: 12.5px; font-weight: 600; margin: 0; }

.loading-row, .empty { padding: 24px; text-align: center; color: var(--text-dim); font-size: 13px; }

.admin-search-wrap { position: relative; margin-bottom: 16px; }
.admin-search {
  width: 100%; padding: 10px 36px 10px 14px;
  background: var(--bg-elevated); border: 1.5px solid var(--line);
  border-radius: 10px; font-size: 13.5px; font-family: inherit;
  color: var(--text); transition: border-color .2s;
}
.admin-search::placeholder { color: var(--text-dim); }
.admin-search:focus { outline: none; border-color: var(--accent); }
.admin-search-wrap .search-clear {
  position: absolute; right: 10px; top: 50%; transform: translateY(-50%);
  background: none; border: none; color: var(--text-dim); font-size: 13px; cursor: pointer; padding: 4px;
}
.admin-search-wrap .search-clear:hover { color: var(--text); }

.admin-table { width: 100%; border-collapse: collapse; font-size: 13.5px; }
.admin-table th {
  text-align: left; font-size: 11px; font-weight: 700; text-transform: uppercase;
  letter-spacing: .04em; color: var(--text-dim); padding: 0 10px 10px;
}
.admin-table td { padding: 12px 10px; border-top: 1px solid var(--line); }
.admin-table td.mono { font-weight: 700; letter-spacing: .03em; }
.admin-table td.actions { text-align: right; }

.status-pill { padding: 3px 9px; border-radius: 99px; font-size: 11px; font-weight: 700; }
.status-pill.on { background: rgba(80,220,100,.12); color: var(--success); }
.status-pill.off { background: var(--bg); color: var(--text-dim); border: 1px solid var(--line); }

.mini-btn {
  background: linear-gradient(160deg, var(--bg-elevated), var(--bg)); border: 1px solid var(--line); color: var(--text-dim);
  padding: 6px 12px; border-radius: 7px; font-size: 12px; font-weight: 700; cursor: pointer;
  box-shadow: 0 2px 6px rgba(0,0,0,.18);
  transition: border-color .15s, color .15s, transform .15s, box-shadow .15s;
}
.mini-btn:hover { border-color: var(--accent); color: var(--accent); box-shadow: 0 4px 14px -4px rgba(255,154,0,.4); transform: translateY(-1px); }
.mini-btn:active { transform: translateY(0); }

@media (max-width: 560px) {
  .form-grid { grid-template-columns: 1fr; }
  .admin-table { display: block; overflow-x: auto; }
}
</style>
