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
        <span class="eyebrow">People</span>
        <h1>Users</h1>
      </section>

      <div class="search-wrap">
        <input v-model="search" type="text" placeholder="Search by username or wallet ID…" @input="debouncedSearch" />
      </div>

      <section class="list-card">
        <div v-if="loading" class="loading-row">Loading…</div>
        <table v-else class="admin-table">
          <thead>
            <tr><th>User</th><th>Wallet</th><th>Balance</th><th>Subscription</th><th>Role</th><th></th></tr>
          </thead>
          <tbody>
            <tr v-for="u in users" :key="u.id">
              <td>{{ u.username ? '@' + u.username : u.telegram_id }}</td>
              <td class="mono">{{ u.wallet.wallet_id }}</td>
              <td>{{ u.wallet.balance_coins }} MC</td>
              <td>
                <span class="status-pill" :class="isSubscribed(u) ? 'on' : 'off'">
                  {{ u.wallet.is_lifetime ? 'Lifetime' : (isSubscribed(u) ? 'Active' : 'None') }}
                </span>
              </td>
              <td>
                <span class="status-pill" :class="u.is_admin ? 'admin' : 'off'">
                  {{ u.is_admin ? 'Admin' : 'User' }}
                </span>
              </td>
              <td class="actions">
                <div class="grant-row">
                  <input
                    type="number" min="0" max="120" class="grant-months-input"
                    v-model.number="grantMonths[u.id]" placeholder="mo."
                  />
                  <button class="mini-btn" :disabled="grantBusyId === u.id" @click="grantPremium(u)">
                    {{ grantBusyId === u.id ? '…' : ((grantMonths[u.id] ?? 0) === 0 ? 'Grant lifetime' : 'Grant') }}
                  </button>
                </div>
                <button class="mini-btn" @click="toggleAdmin(u)">
                  {{ u.is_admin ? 'Revoke admin' : 'Make admin' }}
                </button>
              </td>
            </tr>
            <tr v-if="!users.length">
              <td colspan="6" class="empty">No users found.</td>
            </tr>
          </tbody>
        </table>

        <div v-if="total > users.length" class="load-more">
          <button class="mini-btn" @click="loadMore">Load more ({{ users.length }} / {{ total }})</button>
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
const users = ref([])
const total = ref(0)
const loading = ref(true)
const search = ref('')
const LIMIT = 50
const grantMonths = ref({})
const grantBusyId = ref(null)

function isSubscribed(u) {
  const exp = u.wallet?.subscription_expires_at
  return exp && new Date(exp) > new Date()
}

async function load(offset = 0, append = false) {
  loading.value = !append
  const res = await adminAPI.getUsers({ search: search.value || undefined, limit: LIMIT, offset })
  users.value = append ? [...users.value, ...res.users] : res.users
  total.value = res.total
  loading.value = false
}

function loadMore() { load(users.value.length, true) }

let searchTimer = null
function debouncedSearch() {
  clearTimeout(searchTimer)
  searchTimer = setTimeout(() => load(0, false), 350)
}

async function grantPremium(u) {
  const months = grantMonths.value[u.id] ?? 0
  grantBusyId.value = u.id
  try {
    const updated = await adminAPI.grantSubscription(u.id, months)
    u.wallet = updated.wallet
    grantMonths.value[u.id] = null
  } catch (e) {
    console.warn('[Admin] could not grant subscription:', e.response?.data?.detail)
  } finally {
    grantBusyId.value = null
  }
}

async function toggleAdmin(user) {
  const next = !user.is_admin
  try {
    await adminAPI.setUserAdmin(user.id, next)
    user.is_admin = next
  } catch (e) {
    // e.g. trying to revoke your own admin access — server rejects it
    console.warn('[Admin] could not update admin flag:', e.response?.data?.detail)
  }
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

.search-wrap { margin-bottom: 16px; }
.search-wrap input {
  width: 100%; background: var(--bg-elevated); border: 1px solid var(--line);
  border-radius: 10px; padding: 11px 14px; color: var(--text); font-size: 13.5px;
}
.search-wrap input:focus { outline: none; border-color: var(--accent); }

.list-card {
  background: var(--bg-elevated); border: 1px solid var(--line);
  border-radius: var(--radius-lg); padding: 22px;
}
.loading-row, .empty { padding: 24px; text-align: center; color: var(--text-dim); font-size: 13px; }

.admin-table { width: 100%; border-collapse: collapse; font-size: 13.5px; }
.admin-table th {
  text-align: left; font-size: 11px; font-weight: 700; text-transform: uppercase;
  letter-spacing: .04em; color: var(--text-dim); padding: 0 10px 10px;
}
.admin-table td { padding: 12px 10px; border-top: 1px solid var(--line); }
.admin-table td.mono { font-variant-numeric: tabular-nums; font-size: 12.5px; color: var(--text-dim); }
.admin-table td.actions { text-align: right; }

.status-pill { padding: 3px 9px; border-radius: 99px; font-size: 11px; font-weight: 700; white-space: nowrap; }
.status-pill.on { background: rgba(80,220,100,.12); color: var(--success); }
.status-pill.off { background: var(--bg); color: var(--text-dim); border: 1px solid var(--line); }
.status-pill.admin { background: rgba(255,80,80,.12); color: var(--danger); }

.mini-btn {
  background: linear-gradient(160deg, var(--bg-elevated), var(--bg)); border: 1px solid var(--line); color: var(--text-dim);
  padding: 6px 12px; border-radius: 7px; font-size: 12px; font-weight: 700; cursor: pointer;
  box-shadow: 0 2px 6px rgba(0,0,0,.18);
  transition: border-color .15s, color .15s, transform .15s, box-shadow .15s; white-space: nowrap;
}
.mini-btn:hover { border-color: var(--accent); color: var(--accent); box-shadow: 0 4px 14px -4px rgba(255,154,0,.4); transform: translateY(-1px); }
.mini-btn:active { transform: translateY(0); }

.load-more { text-align: center; padding-top: 18px; }

.grant-row { display: flex; align-items: center; gap: 6px; margin-bottom: 6px; justify-content: flex-end; }
.grant-months-input {
  width: 52px; background: var(--bg); border: 1px solid var(--line); border-radius: 7px;
  padding: 6px 6px; color: var(--text); font-size: 12px; text-align: center;
}
.grant-months-input:focus { outline: none; border-color: var(--accent); }

@media (max-width: 640px) {
  .admin-table { display: block; overflow-x: auto; }
}
</style>
