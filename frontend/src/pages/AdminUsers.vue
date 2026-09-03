<template>
  <main class="admin-page">
    <Header />

    <div class="wrap admin-content">
      <Breadcrumbs :items="[{ label: 'Home', to: '/' }, { label: 'Admin', to: '/admin' }, { label: 'Users' }]" />

      <section class="page-head">
        <span class="eyebrow">People</span>
        <h1>Users</h1>
      </section>

      <div class="search-wrap">
        <input v-model="search" type="text" placeholder="Search by name, wallet ID, Telegram ID or user ID…" @input="debouncedSearch" />
      </div>

      <section class="list-card">
        <div v-if="loading" class="loading-row">Loading…</div>
        <table v-else class="admin-table">
          <thead>
            <tr><th>User</th><th>Wallet</th><th>Balance</th><th>Subscription</th><th>Role</th><th></th></tr>
          </thead>
          <tbody>
            <tr v-for="u in users" :key="u.id" class="user-row" @click="openPlayer(u)">
              <td>
                <div class="user-name-cell">
                  <span class="user-nickname">{{ u.display_name || (u.username ? '@' + u.username : u.telegram_id) }}</span>
                  <span v-if="u.display_name" class="user-username-sub">{{ u.username ? '@' + u.username : u.telegram_id }}</span>
                </div>
              </td>
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
                <span v-if="u.is_banned" class="status-pill banned">Banned</span>
                <span v-if="u.is_trade_banned" class="status-pill off">No trades</span>
              </td>
              <td class="row-arrow">→</td>
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

    <!-- ── PLAYER DETAIL MODAL ─────────────────────────────── -->
    <!-- No <transition> here on purpose — see Pricing.vue's payment popup
         for why: even with an explicit :duration fallback, a Vue
         transition here can get stuck mid-leave (backgrounded tab,
         reduced-motion, a fast double-toggle), leaving this fixed
         full-screen backdrop rendered invisibly and silently blocking
         every click on the page underneath it until reload. -->
      <div v-if="selected" class="modal-backdrop" @click.self="closePlayer">
        <div class="modal player-modal">
          <button class="modal-close" @click="closePlayer">✕</button>

          <div class="player-head">
            <div class="player-avatar">
              <img v-if="selected.avatar_url" :src="selected.avatar_url" alt="" />
              <span v-else>{{ (selected.display_name || selected.username || '?').charAt(0).toUpperCase() }}</span>
            </div>
            <div>
              <h3 class="modal-title">{{ selected.display_name || (selected.username ? '@' + selected.username : selected.telegram_id) }}</h3>
              <p v-if="selected.display_name" class="player-username-sub">{{ selected.username ? '@' + selected.username : selected.telegram_id }}</p>
              <p class="player-wallet mono">{{ selected.wallet.wallet_id }} · {{ selected.wallet.balance_coins }} MC</p>
            </div>
          </div>

          <div class="player-status-row">
            <span class="status-pill" :class="selected.is_admin ? 'admin' : 'off'">{{ selected.is_admin ? 'Admin' : 'User' }}</span>
            <span class="status-pill" :class="isSubscribed(selected) ? 'on' : 'off'">
              {{ selected.wallet.is_lifetime ? 'Lifetime' : (isSubscribed(selected) ? 'Premium active' : 'No premium') }}
            </span>
            <span v-if="selected.is_banned" class="status-pill banned">Banned</span>
            <span v-if="selected.is_trade_banned" class="status-pill off">No trades</span>
          </div>

          <!-- Public profile info (support/verification reference) -->
          <div v-if="filledProfileInfo(selected).length" class="section">
            <p class="section-label">Public profile info</p>
            <div class="profile-info-list">
              <div v-for="f in filledProfileInfo(selected)" :key="f.key" class="profile-info-row">
                <span class="profile-info-key">{{ f.label }}</span>
                <span class="profile-info-val">{{ f.value }}</span>
              </div>
            </div>
          </div>

          <!-- Nickname -->
          <div class="section">
            <p class="section-label">Nickname</p>
            <div class="inline-form">
              <input v-model="nicknameDraft" type="text" maxlength="32" placeholder="No nickname set" class="inline-input" />
              <button class="mini-btn" :disabled="nicknameBusy" @click="saveNickname">{{ nicknameBusy ? '…' : 'Save' }}</button>
            </div>
          </div>

          <!-- Avatar -->
          <div class="section">
            <p class="section-label">Avatar</p>
            <div class="inline-form">
              <label class="mini-btn upload-label">
                {{ avatarBusy ? 'Uploading…' : 'Upload new' }}
                <input type="file" accept="image/jpeg,image/png,image/webp,image/gif" hidden :disabled="avatarBusy" @change="onAvatarFileChange" />
              </label>
              <button v-if="selected.avatar_url" class="mini-btn danger" :disabled="avatarBusy" @click="removeAvatar">Remove avatar</button>
            </div>
          </div>

          <!-- Grant coins -->
          <div class="section">
            <p class="section-label">Grant MasterCoins</p>
            <div class="inline-form">
              <input v-model.number="grantCoinsAmount" type="number" min="1" placeholder="Amount" class="inline-input inline-input-small" />
              <button class="mini-btn" :disabled="grantCoinsBusy || !grantCoinsAmount" @click="grantCoins">
                {{ grantCoinsBusy ? '…' : 'Grant' }}
              </button>
            </div>
          </div>

          <!-- Premium — absolute set, overwrites whatever time is left -->
          <div class="section">
            <p class="section-label">Set premium (overwrites current time left)</p>
            <div class="premium-form">
              <select v-model="premiumUnit" class="inline-select">
                <option value="forever">Forever</option>
                <option value="month">Months</option>
                <option value="hour">Hours</option>
                <option value="minute">Minutes</option>
              </select>
              <input
                v-if="premiumUnit !== 'forever'" v-model.number="premiumAmount" type="number" min="1"
                placeholder="Amount" class="inline-input inline-input-small"
              />
              <button class="mini-btn" :disabled="premiumBusy || (premiumUnit !== 'forever' && !premiumAmount)" @click="setPremium">
                {{ premiumBusy ? '…' : 'Set' }}
              </button>
            </div>
            <p class="section-hint">E.g. a user with a month left set to 1 minute ends up with exactly 1 minute.</p>
          </div>

          <!-- Role / trade / ban toggles -->
          <div class="section">
            <p class="section-label">Account controls</p>
            <div class="action-btn-row">
              <button class="mini-btn" :disabled="busyAction === 'admin'" @click="toggleAdmin(selected)">
                {{ selected.is_admin ? 'Revoke admin' : 'Make admin' }}
              </button>
              <button class="mini-btn" :disabled="busyAction === 'trade'" @click="toggleTradeBan(selected)">
                {{ selected.is_trade_banned ? 'Unban trades' : 'Ban trades' }}
              </button>
              <button class="mini-btn danger" :disabled="busyAction === 'ban'" @click="toggleBan(selected)">
                {{ selected.is_banned ? 'Unban' : 'Ban' }}
              </button>
            </div>
          </div>
        </div>
      </div>

    <Footer />
  </main>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { storeToRefs } from 'pinia'
import { useUserStore } from '../store/user'
import { adminAPI } from '../api/admin'
import Header from '../components/Header.vue'
import Footer from '../components/Footer.vue'
import Breadcrumbs from '../components/Breadcrumbs.vue'

const route = useRoute()
const router = useRouter()
const { user } = storeToRefs(useUserStore())
const users = ref([])
const total = ref(0)
const loading = ref(true)
const search = ref('')
const LIMIT = 50

function isSubscribed(u) {
  const exp = u.wallet?.subscription_expires_at
  return exp && new Date(exp) > new Date()
}

const PROFILE_FIELD_LABELS = {
  location: 'Location', telegram: 'Telegram', instagram: 'Instagram', discord: 'Discord',
  faceit: 'Faceit', steam: 'Steam', whatsapp: 'WhatsApp', twitch: 'Twitch',
}
function filledProfileInfo(u) {
  if (!u?.profile_info) return []
  return Object.entries(u.profile_info)
    .filter(([, v]) => v)
    .map(([key, value]) => ({ key, value, label: PROFILE_FIELD_LABELS[key] || key }))
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

// ── Player detail modal ──────────────────────────────────────────
const selected = ref(null)
const nicknameDraft = ref('')
const nicknameBusy = ref(false)
const avatarBusy = ref(false)
const premiumUnit = ref('month')
const premiumAmount = ref(1)
const premiumBusy = ref(false)
const grantCoinsAmount = ref(null)
const grantCoinsBusy = ref(false)
const busyAction = ref(null)

function openPlayer(u) {
  selected.value = u
  nicknameDraft.value = u.display_name || ''
  premiumUnit.value = 'month'
  premiumAmount.value = 1
  grantCoinsAmount.value = null
}
function closePlayer() { selected.value = null }

function patchSelected(updated) {
  Object.assign(selected.value, updated)
  const row = users.value.find(u => u.id === updated.id)
  if (row) Object.assign(row, updated)
}

async function saveNickname() {
  nicknameBusy.value = true
  try {
    const updated = await adminAPI.setUserNickname(selected.value.id, nicknameDraft.value.trim() || null)
    patchSelected(updated)
  } catch (e) {
    console.warn('[Admin] could not update nickname:', e.response?.data?.detail)
  } finally {
    nicknameBusy.value = false
  }
}

async function removeAvatar() {
  avatarBusy.value = true
  try {
    const updated = await adminAPI.clearUserAvatar(selected.value.id)
    patchSelected(updated)
  } catch (e) {
    console.warn('[Admin] could not clear avatar:', e.response?.data?.detail)
  } finally {
    avatarBusy.value = false
  }
}

async function onAvatarFileChange(e) {
  const file = e.target.files[0]
  e.target.value = ''
  if (!file || avatarBusy.value) return

  avatarBusy.value = true
  try {
    const uploaded = await adminAPI.uploadImage(file)
    const updated = await adminAPI.setUserAvatar(selected.value.id, uploaded.url)
    patchSelected(updated)
  } catch (e) {
    console.warn('[Admin] could not upload avatar:', e.response?.data?.detail)
  } finally {
    avatarBusy.value = false
  }
}

async function setPremium() {
  if (premiumUnit.value !== 'forever' && !premiumAmount.value) return
  premiumBusy.value = true
  try {
    const updated = await adminAPI.setUserPremium(selected.value.id, premiumUnit.value, premiumUnit.value === 'forever' ? null : premiumAmount.value)
    patchSelected(updated)
  } catch (e) {
    console.warn('[Admin] could not set premium:', e.response?.data?.detail)
  } finally {
    premiumBusy.value = false
  }
}

async function grantCoins() {
  if (!grantCoinsAmount.value) return
  grantCoinsBusy.value = true
  try {
    const updated = await adminAPI.grantUserCoins(selected.value.id, grantCoinsAmount.value)
    patchSelected(updated)
    grantCoinsAmount.value = null
  } catch (e) {
    console.warn('[Admin] could not grant coins:', e.response?.data?.detail)
  } finally {
    grantCoinsBusy.value = false
  }
}

async function toggleAdmin(u) {
  const next = !u.is_admin
  busyAction.value = 'admin'
  try {
    const updated = await adminAPI.setUserAdmin(u.id, next)
    patchSelected(updated)
  } catch (e) {
    console.warn('[Admin] could not update admin flag:', e.response?.data?.detail)
  } finally {
    busyAction.value = null
  }
}

async function toggleBan(u) {
  const next = !u.is_banned
  if (next && !confirm(`Ban ${u.username ? '@' + u.username : 'this user'}? They'll be locked out of the whole app.`)) return
  busyAction.value = 'ban'
  try {
    const updated = await adminAPI.setUserBanned(u.id, next)
    patchSelected(updated)
  } catch (e) {
    console.warn('[Admin] could not update ban flag:', e.response?.data?.detail)
  } finally {
    busyAction.value = null
  }
}

async function toggleTradeBan(u) {
  const next = !u.is_trade_banned
  busyAction.value = 'trade'
  try {
    const updated = await adminAPI.setUserTradeBanned(u.id, next)
    patchSelected(updated)
  } catch (e) {
    console.warn('[Admin] could not update trade-ban flag:', e.response?.data?.detail)
  } finally {
    busyAction.value = null
  }
}

onMounted(() => {
  if (!user.value?.is_admin) { router.replace('/user'); return }
  if (route.query.q) search.value = String(route.query.q)
  load()
})
</script>

<style scoped>
.admin-page { min-height: 100vh; background: var(--bg); }
.admin-content { max-width: 960px; padding: 32px 20px 120px; }

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

.user-row { cursor: pointer; transition: background .15s; }
.user-row:hover { background: rgba(255,154,0,.05); }
.user-name-cell { display: flex; flex-direction: column; gap: 1px; }
.user-nickname { font-weight: 700; color: var(--text); }
.user-username-sub { font-size: 11px; color: var(--text-dim); }
.row-arrow { color: var(--text-dim); text-align: right; }

.status-pill { padding: 3px 9px; border-radius: 99px; font-size: 11px; font-weight: 700; white-space: nowrap; }
.status-pill.on { background: rgba(80,220,100,.12); color: var(--success); }
.status-pill.off { background: var(--bg); color: var(--text-dim); border: 1px solid var(--line); }
.status-pill.admin { background: rgba(255,80,80,.12); color: var(--danger); }
.status-pill.banned { background: rgba(235,75,75,.18); color: var(--danger); border: 1px solid rgba(235,75,75,.4); margin-left: 4px; }

.mini-btn {
  background: linear-gradient(160deg, var(--bg-elevated), var(--bg)); border: 1px solid var(--line); color: var(--text-dim);
  padding: 6px 12px; border-radius: 7px; font-size: 12px; font-weight: 700; cursor: pointer;
  box-shadow: 0 2px 6px rgba(0,0,0,.18);
  transition: border-color .15s, color .15s, transform .15s, box-shadow .15s; white-space: nowrap;
}
.mini-btn:hover { border-color: var(--accent); color: var(--accent); box-shadow: 0 4px 14px -4px rgba(255,154,0,.4); transform: translateY(-1px); }
.mini-btn:active { transform: translateY(0); }
.mini-btn:disabled { opacity: .5; cursor: not-allowed; transform: none; }
.mini-btn.danger:hover { border-color: var(--danger); color: var(--danger); box-shadow: 0 4px 14px -4px rgba(235,75,75,.4); }

.load-more { text-align: center; padding-top: 18px; }
.action-btn-row { display: flex; gap: 6px; flex-wrap: wrap; }

@media (max-width: 640px) {
  .admin-table { display: block; overflow-x: auto; }
}

/* ── Player modal ─────────────────────────────── */
.modal-backdrop {
  position: fixed; inset: 0; z-index: 500;
  background: rgba(0,0,0,0.6);
  display: flex; align-items: center; justify-content: center;
  padding: 20px; backdrop-filter: blur(4px); overflow-y: auto;
}
.modal {
  position: relative; width: 100%; max-width: 420px;
  background: var(--bg-elevated); border: 1px solid var(--line);
  border-radius: var(--radius-lg); padding: 28px 24px 24px; margin: auto;
}
.modal-close {
  position: absolute; top: 16px; right: 16px;
  width: 30px; height: 30px; border-radius: 8px;
  background: var(--bg); border: 1px solid var(--line);
  color: var(--text-dim); cursor: pointer;
  display: flex; align-items: center; justify-content: center;
  font-size: 13px; transition: border-color .15s, color .15s;
}
.modal-close:hover { border-color: var(--accent); color: var(--accent); }
.modal-title { font-size: 18px; font-weight: 800; color: var(--text); }

.player-head { display: flex; align-items: center; gap: 14px; margin-bottom: 14px; padding-right: 30px; }
.player-avatar {
  flex-shrink: 0; width: 52px; height: 52px; border-radius: 50%; overflow: hidden;
  display: flex; align-items: center; justify-content: center;
  background: linear-gradient(160deg, rgba(255,154,0,.35), rgba(255,154,0,.1));
  color: var(--text); font-weight: 800; font-size: 20px;
}
.player-avatar img { width: 100%; height: 100%; object-fit: cover; }
.player-username-sub { font-size: 12px; color: var(--text-dim); margin-top: 1px; }
.player-wallet { font-size: 11.5px; color: var(--text-dim); margin-top: 4px; }

.player-status-row { display: flex; gap: 6px; flex-wrap: wrap; margin-bottom: 18px; }

.section { margin-top: 18px; padding-top: 18px; border-top: 1px solid var(--line); }
.section-label { font-size: 11px; font-weight: 700; letter-spacing: .04em; text-transform: uppercase; color: var(--text-dim); margin-bottom: 8px; }
.section-hint { font-size: 11px; color: var(--text-dim); margin-top: 6px; }

.inline-form, .premium-form { display: flex; gap: 8px; flex-wrap: wrap; }

.profile-info-list { display: flex; flex-direction: column; gap: 5px; }
.profile-info-row { display: flex; gap: 8px; font-size: 12.5px; }
.profile-info-key { color: var(--text-dim); width: 72px; flex-shrink: 0; }
.profile-info-val { color: var(--text); word-break: break-word; }
.inline-input, .inline-select {
  flex: 1; min-width: 120px; background: var(--bg); border: 1px solid var(--line); border-radius: 8px;
  padding: 8px 10px; color: var(--text); font-size: 13px; font-family: inherit;
}
.inline-input-small { flex: 0 0 90px; min-width: 90px; }
.inline-input:focus, .inline-select:focus { outline: none; border-color: var(--accent); }
</style>
