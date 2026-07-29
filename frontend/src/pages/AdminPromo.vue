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
        <div class="form-grid">
          <label class="field">
            <span>Code (optional)</span>
            <input v-model="form.code" type="text" placeholder="Auto-generated if empty" />
          </label>
          <label class="field">
            <span>Coin reward</span>
            <input v-model.number="form.coin_reward" type="number" min="1" placeholder="25" />
          </label>
          <label class="field">
            <span>Activation limit</span>
            <input v-model.number="form.activations_limit" type="number" min="1" placeholder="100" />
          </label>
        </div>
        <div class="form-actions">
          <button class="btn-primary" :disabled="!form.coin_reward || saving" @click="createPromo">
            {{ saving ? 'Saving…' : 'Generate' }}
          </button>
          <p v-if="errorMsg" class="err">{{ errorMsg }}</p>
        </div>
      </section>

      <section class="list-card">
        <div v-if="loading" class="loading-row">Loading…</div>
        <table v-else class="admin-table">
          <thead>
            <tr><th>Code</th><th>Reward</th><th>Used</th><th>Status</th><th></th></tr>
          </thead>
          <tbody>
            <tr v-for="p in promoCodes" :key="p.id">
              <td class="mono">{{ p.code }}</td>
              <td>{{ p.coin_reward }} MC</td>
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
          </tbody>
        </table>
      </section>
    </div>

    <Footer />
  </main>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { storeToRefs } from 'pinia'
import { useUserStore } from '../store/user'
import { adminAPI } from '../api/admin'
import Header from '../components/Header.vue'
import Footer from '../components/Footer.vue'

const router = useRouter()
const { user } = storeToRefs(useUserStore())
const promoCodes = ref([])
const loading = ref(true)
const saving = ref(false)
const errorMsg = ref('')

const form = reactive({ code: '', coin_reward: 25, activations_limit: 100 })

async function load() {
  loading.value = true
  promoCodes.value = await adminAPI.getPromoCodes()
  loading.value = false
}

async function createPromo() {
  if (!form.coin_reward) return
  saving.value = true
  errorMsg.value = ''
  try {
    await adminAPI.createPromoCode({
      code: form.code.trim() || null,
      coin_reward: form.coin_reward,
      activations_limit: form.activations_limit || 100,
    })
    form.code = ''
    form.coin_reward = 25
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

onMounted(() => {
  if (!user.value?.is_admin) { router.replace('/user'); return }
  load()
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

.form-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 14px; margin-bottom: 16px; }
.field { display: flex; flex-direction: column; gap: 6px; }
.field span { font-size: 11px; font-weight: 700; color: var(--text-dim); text-transform: uppercase; letter-spacing: .04em; }
.field input {
  background: var(--bg); border: 1px solid var(--line); border-radius: 9px;
  padding: 10px 12px; color: var(--text); font-size: 13.5px; font-family: inherit;
}
.field input:focus { outline: none; border-color: var(--accent); }

.form-actions { display: flex; align-items: center; gap: 14px; }
.err { color: var(--danger); font-size: 12.5px; font-weight: 600; margin: 0; }

.loading-row { padding: 24px; text-align: center; color: var(--text-dim); font-size: 13px; }

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
  background: var(--bg); border: 1px solid var(--line); color: var(--text-dim);
  padding: 6px 12px; border-radius: 7px; font-size: 12px; font-weight: 700; cursor: pointer;
  transition: border-color .15s, color .15s;
}
.mini-btn:hover { border-color: var(--accent); color: var(--accent); }

@media (max-width: 560px) {
  .form-grid { grid-template-columns: 1fr; }
  .admin-table { display: block; overflow-x: auto; }
}
</style>
