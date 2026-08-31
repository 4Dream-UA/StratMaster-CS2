<template>
  <main class="admin-page">
    <Header />

    <div class="wrap admin-content">

      <Breadcrumbs :items="[{ label: 'Home', to: '/' }, { label: 'Admin' }]" />

      <section class="admin-header">
        <span class="admin-eyebrow">Admin Panel</span>
        <h1>Manage StratMaster</h1>
      </section>

      <!-- ── STATS STRIP ─────────────────────────────── -->
      <section class="stats-strip">
        <div class="stat-box">
          <span class="stat-value">{{ stats?.users_count ?? '—' }}</span>
          <span class="stat-label">Users</span>
        </div>
        <div class="stat-box">
          <span class="stat-value">{{ stats?.strategies_count ?? '—' }}</span>
          <span class="stat-label">Strategies</span>
        </div>
        <div class="stat-box">
          <span class="stat-value">{{ stats?.maps_count ?? '—' }}</span>
          <span class="stat-label">Maps</span>
        </div>
        <div class="stat-box">
          <span class="stat-value">{{ stats?.active_subscriptions_count ?? '—' }}</span>
          <span class="stat-label">Active Subs</span>
        </div>
        <div class="stat-box">
          <span class="stat-value">{{ stats?.transactions_count ?? '—' }}</span>
          <span class="stat-label">Transactions</span>
        </div>
        <!-- These used to dump you on the forum's category list with no hint
             of which thread the number referred to. They now open the queue
             that actually lists them. -->
        <button type="button" class="stat-box stat-box-link" @click="router.push('/admin/tickets')">
          <span class="stat-value" :class="{ warn: stats?.open_tickets_count > 0 }">{{ stats?.open_tickets_count ?? '—' }}</span>
          <span class="stat-label">Open Tickets</span>
        </button>
        <button type="button" class="stat-box stat-box-link" @click="router.push('/forum')">
          <span class="stat-value" :class="{ warn: stats?.pending_deleted_posts_count > 0 }">{{ stats?.pending_deleted_posts_count ?? '—' }}</span>
          <span class="stat-label">Deleted Posts</span>
        </button>
        <button type="button" class="stat-box stat-box-link" @click="router.push('/admin/reports')">
          <span class="stat-value" :class="{ warn: stats?.pending_reports_count > 0 }">{{ stats?.pending_reports_count ?? '—' }}</span>
          <span class="stat-label">Reports</span>
        </button>
        <button type="button" class="stat-box stat-box-link" @click="openErrors">
          <span class="stat-value" :class="{ warn: stats?.recent_errors_count > 0 }">{{ stats?.recent_errors_count ?? '—' }}</span>
          <span class="stat-label">Errors (24h)</span>
        </button>
      </section>

      <!-- ── TOOL TILES ───────────────────────────────── -->
      <section class="tiles-grid">
        <button
          v-for="tile in TILES" :key="tile.route"
          class="tile"
          @click="router.push(tile.route)"
        >
          <span class="tile-icon" v-html="tile.icon"></span>
          <span class="tile-title">{{ tile.title }}</span>
          <span class="tile-desc">{{ tile.desc }}</span>
          <span class="tile-arrow">→</span>
        </button>
      </section>

      <!-- ── AI SUPPORT ASSISTANT ─────────────────────────── -->
      <section class="settings-card">
        <div class="settings-head">
          <h3>AI Support Assistant</h3>
          <label class="switch">
            <input
              type="checkbox" :checked="aiEnabled" :disabled="!aiConfigured || savingAi"
              @change="setAiEnabled($event.target.checked)"
            />
            <span class="switch-track"><span class="switch-thumb"></span></span>
          </label>
        </div>
        <p class="settings-hint">
          Answers the first pass on new support tickets and marks its replies as automated. It stops
          as soon as an admin replies in a ticket, and never posts in the Lounge.
        </p>
        <p class="settings-hint" :class="aiConfigured ? 'ok' : 'warn'">
          <template v-if="aiConfigured">Model: <strong>{{ aiModel }}</strong></template>
          <template v-else>No API key configured on the server — set OPENAI_API_KEY to switch this on.</template>
        </p>
      </section>

      <!-- ── SITE SETTINGS ───────────────────────────────── -->
      <section class="settings-card">
        <h3>Site Logo</h3>
        <p class="settings-hint">Replaces the logo in the header and footer app-wide. Leave blank to use the default.</p>
        <div class="settings-row">
          <img v-if="logoUrl" :src="logoUrl" alt="" class="logo-preview" />
          <ImageUploadField v-model="logoUrlDraft" placeholder="Logo image URL" />
          <button class="mini-btn" :disabled="savingLogo" @click="saveLogo">{{ savingLogo ? 'Saving…' : 'Save' }}</button>
        </div>
      </section>

    </div>

    <!-- ── ERRORS POPUP ─────────────────────────────────── -->
      <div v-if="errorsOpen" class="modal-backdrop" @click.self="errorsOpen = false">
        <div class="modal errors-modal">
          <button class="modal-close" @click="errorsOpen = false">✕</button>
          <h3 class="modal-title">Recent errors</h3>
          <div v-if="errorsLoading" class="loading-row">Loading…</div>
          <div v-else class="errors-list">
            <div v-for="e in errorLogs" :key="e.id" class="error-row">
              <div class="error-row-head">
                <span class="error-source" :class="e.source">{{ e.source }}</span>
                <span class="error-time">{{ formatErrorTime(e.created_at) }}</span>
              </div>
              <p class="error-message">{{ e.message }}</p>
              <p v-if="e.url" class="error-url">{{ e.url }}</p>
              <details v-if="e.stack" class="error-stack-details">
                <summary>Stack trace</summary>
                <pre class="error-stack">{{ e.stack }}</pre>
              </details>
            </div>
            <p v-if="!errorLogs.length" class="empty">No errors logged.</p>
          </div>
        </div>
      </div>

    <Footer />
  </main>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { storeToRefs } from 'pinia'
import { useUserStore } from '../store/user'
import { useSettingsStore } from '../store/settings'
import { adminAPI } from '../api/admin'
import { settingsAPI } from '../api/settings'
import Header from '../components/Header.vue'
import Footer from '../components/Footer.vue'
import Breadcrumbs from '../components/Breadcrumbs.vue'
import ImageUploadField from '../components/ImageUploadField.vue'

const router = useRouter()
const userStore = useUserStore()
const { user } = storeToRefs(userStore)
const settingsStore = useSettingsStore()
const { logoUrl } = storeToRefs(settingsStore)

const stats = ref(null)
const logoUrlDraft = ref('')

const errorsOpen = ref(false)
const errorLogs = ref([])
const errorsLoading = ref(false)
async function openErrors() {
  errorsOpen.value = true
  errorsLoading.value = true
  try {
    errorLogs.value = await adminAPI.getErrors()
  } finally {
    errorsLoading.value = false
  }
}
function formatErrorTime(iso) {
  return new Date(iso).toLocaleString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
}
const savingLogo = ref(false)

async function saveLogo() {
  savingLogo.value = true
  try {
    const updated = await settingsAPI.update({ logo_url: logoUrlDraft.value.trim() || null })
    settingsStore.logoUrl = updated.logo_url
    applyAiSettings(updated)
  } finally {
    savingLogo.value = false
  }
}

// ── AI support assistant ──────────────────────────────────────────
// `configured` is the server having an API key at all; `enabled` is the
// admin switch. Both have to be true for it to say anything, and the two
// need telling apart — "off" is a choice, "no key" is a deployment gap.
const aiEnabled = ref(true)
const aiConfigured = ref(false)
const aiModel = ref('')
const savingAi = ref(false)

function applyAiSettings(data) {
  aiEnabled.value = data.ai_agent_enabled
  aiConfigured.value = data.ai_agent_configured
  aiModel.value = data.ai_agent_model
}

async function setAiEnabled(checked) {
  savingAi.value = true
  const previous = aiEnabled.value
  aiEnabled.value = checked
  try {
    applyAiSettings(await settingsAPI.update({ ai_agent_enabled: checked }))
  } catch (e) {
    aiEnabled.value = previous // put the switch back rather than lying about the state
  } finally {
    savingAi.value = false
  }
}

const ICON_MAP = `<svg viewBox="0 0 24 24" fill="none" width="22" height="22"><path d="M9 4L4 6v14l5-2 6 2 5-2V4l-5 2-6-2z" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round"/><path d="M9 4v14M15 6v14" stroke="currentColor" stroke-width="1.6"/></svg>`
const ICON_TARGET = `<svg viewBox="0 0 24 24" fill="none" width="22" height="22"><circle cx="12" cy="12" r="8" stroke="currentColor" stroke-width="1.6"/><circle cx="12" cy="12" r="4.5" stroke="currentColor" stroke-width="1.6"/><circle cx="12" cy="12" r="1" fill="currentColor"/></svg>`
const ICON_USERS = `<svg viewBox="0 0 24 24" fill="none" width="22" height="22"><circle cx="9" cy="8" r="3" stroke="currentColor" stroke-width="1.6"/><path d="M3 20c0-3.3 2.7-6 6-6s6 2.7 6 6" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/><circle cx="17" cy="9" r="2.5" stroke="currentColor" stroke-width="1.4"/><path d="M15.5 14.2c2.5.4 4.5 2.6 4.5 5.3" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/></svg>`
const ICON_P2P = `<svg viewBox="0 0 24 24" fill="none" width="22" height="22"><rect x="2" y="7" width="20" height="12" rx="2" stroke="currentColor" stroke-width="1.6"/><circle cx="12" cy="13" r="3" stroke="currentColor" stroke-width="1.6"/><path d="M6 7V6a2 2 0 012-2h8a2 2 0 012 2v1" stroke="currentColor" stroke-width="1.4"/></svg>`
const ICON_PROMO = `<svg viewBox="0 0 24 24" fill="none" width="22" height="22"><path d="M11 4h6a1 1 0 011 1v6a1 1 0 01-.3.7l-8 8a1 1 0 01-1.4 0l-6-6a1 1 0 010-1.4l8-8A1 1 0 0111 4z" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round"/><circle cx="15.5" cy="8.5" r="1.3" fill="currentColor"/></svg>`
const ICON_FLAG = `<svg viewBox="0 0 24 24" fill="none" width="22" height="22"><path d="M5 4v16M5 4h12l-2.2 3.8L17 12H5" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round"/></svg>`
const ICON_TICKET = `<svg viewBox="0 0 24 24" fill="none" width="22" height="22"><path d="M4 6h16v3.5a2.5 2.5 0 000 5V18H4v-3.5a2.5 2.5 0 000-5V6z" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round"/><path d="M12 8v2M12 13v3" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/></svg>`

const TILES = [
  { title: 'Work with Maps',      desc: 'Add, edit, or disable maps',            icon: ICON_MAP,   route: '/admin/maps' },
  { title: 'Work with Strategies',desc: 'Create and manage strategy content',    icon: ICON_TARGET,route: '/admin/strategies' },
  { title: 'Work with Users',     desc: 'View users, roles and subscriptions',   icon: ICON_USERS, route: '/admin/users' },
  { title: 'Reports',             desc: 'Every reported thread and message in one queue', icon: ICON_FLAG, route: '/admin/reports' },
  { title: 'Support Tickets',     desc: 'Open tickets and which ones need a reply', icon: ICON_TICKET, route: '/admin/tickets' },
  { title: 'Promo Codes',         desc: 'Generate and manage MasterCoin codes',  icon: ICON_PROMO, route: '/admin/promo' },
  { title: 'Check Transactions',  desc: 'Monitor coin transfers, purchases and payouts', icon: ICON_P2P, route: '/admin/transactions' },
]

onMounted(async () => {
  // Guard: redirect non-admins away
  if (!user.value?.is_admin) {
    router.replace('/user')
    return
  }
  try {
    stats.value = await adminAPI.getStats()
  } catch (e) {
    console.warn('[Admin] stats unavailable:', e)
  }
  await settingsStore.load()
  logoUrlDraft.value = logoUrl.value || ''
  try {
    applyAiSettings(await settingsAPI.get())
  } catch (e) {
    console.warn('[Admin] AI assistant settings unavailable:', e)
  }
})
</script>

<style scoped>
.admin-page { min-height: 100vh; background: var(--bg); }
.admin-content { max-width: 960px; padding: 32px 20px 120px; }

.admin-header { margin-bottom: 28px; }
.admin-eyebrow {
  display: inline-block;
  font-size: 11px; font-weight: 800; letter-spacing: .08em;
  text-transform: uppercase; color: var(--danger);
  margin-bottom: 8px;
}
.admin-header h1 {
  font-size: clamp(24px, 5vw, 34px); font-weight: 900;
  letter-spacing: -.02em; color: var(--text);
}

/* ── Stats strip ──────────────────────────────── */
.stats-strip {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
  gap: 12px;
  margin-bottom: 32px;
}
.stat-box {
  background: var(--bg-elevated); border: 1px solid var(--line);
  border-radius: var(--radius-md); padding: 18px;
  display: flex; flex-direction: column; gap: 4px;
}
.stat-value { font-size: 26px; font-weight: 900; color: var(--accent); }
.stat-value.warn { color: var(--danger); }
.stat-label { font-size: 11px; color: var(--text-dim); text-transform: uppercase; letter-spacing: .05em; }
.stat-box-link { cursor: pointer; text-align: left; transition: border-color .15s; }
.stat-box-link:hover { border-color: var(--accent); }

/* ── Tiles ─────────────────────────────────────── */
.tiles-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 16px;
}

.tile {
  position: relative;
  text-align: left;
  background: var(--bg-elevated);
  border: 1px solid var(--line);
  border-radius: var(--radius-lg);
  padding: 24px;
  cursor: pointer;
  transition: border-color .2s, transform .2s, box-shadow .2s;
  display: flex; flex-direction: column; gap: 6px;
}
.tile:hover {
  border-color: rgba(255,154,0,.5);
  transform: translateY(-3px);
  box-shadow: 0 8px 20px rgba(255,154,0,.1);
}

.tile-icon {
  display: flex; align-items: center;
  color: var(--accent);
  margin-bottom: 6px;
}
.tile-title { font-size: 15px; font-weight: 700; color: var(--text); }
.tile-desc { font-size: 12.5px; color: var(--text-dim); line-height: 1.5; }
.tile-arrow {
  position: absolute; top: 22px; right: 22px;
  color: var(--text-dim); font-size: 16px;
  transition: transform .2s, color .2s;
}
.tile:hover .tile-arrow { transform: translateX(3px); color: var(--accent); }

/* ── Site settings ─────────────────────────────── */
.settings-card {
  margin-top: 24px; background: var(--bg-elevated); border: 1px solid var(--line);
  border-radius: var(--radius-lg); padding: 22px;
}
.settings-card h3 { font-size: 15px; font-weight: 800; color: var(--text); margin-bottom: 4px; }
/* Same toggle as the profile page's — scoped styles don't cross files, so
   it's repeated here rather than shared through a component nobody else
   would use. */
.switch { position: relative; flex-shrink: 0; cursor: pointer; display: inline-flex; }
.switch input { position: absolute; opacity: 0; width: 0; height: 0; }
.switch-track {
  width: 44px; height: 26px; border-radius: 99px;
  background: var(--bg); border: 1px solid var(--line);
  display: inline-flex; align-items: center; padding: 2px;
  transition: background .2s, border-color .2s;
}
.switch-thumb {
  width: 20px; height: 20px; border-radius: 50%;
  background: var(--text-dim);
  transition: transform .2s, background .2s;
}
.switch input:checked + .switch-track { background: rgba(255,154,0,0.18); border-color: var(--accent); }
.switch input:checked + .switch-track .switch-thumb { transform: translateX(18px); background: var(--accent); }
.switch input:disabled + .switch-track { opacity: .45; cursor: not-allowed; }

.settings-head { display: flex; align-items: center; justify-content: space-between; gap: 14px; margin-bottom: 4px; }
.settings-head h3 { margin-bottom: 0; }
.settings-hint.ok { color: var(--text-dim); }
.settings-hint.warn { color: var(--accent); }
.settings-hint { font-size: 12.5px; color: var(--text-dim); margin-bottom: 14px; }
.settings-row { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.logo-preview {
  width: 40px; height: 40px; object-fit: contain; border-radius: 8px;
  background: var(--bg); border: 1px solid var(--line); flex-shrink: 0; padding: 4px;
}
.mini-btn {
  background: linear-gradient(160deg, var(--bg-elevated), var(--bg)); border: 1px solid var(--line); color: var(--text-dim);
  padding: 9px 16px; border-radius: 9px; font-size: 12.5px; font-weight: 700; cursor: pointer;
  box-shadow: 0 2px 6px rgba(0,0,0,.18);
  transition: border-color .15s, color .15s, transform .15s, box-shadow .15s; white-space: nowrap; flex-shrink: 0;
}
.mini-btn:hover:not(:disabled) { border-color: var(--accent); color: var(--accent); box-shadow: 0 4px 14px -4px rgba(255,154,0,.4); transform: translateY(-1px); }
.mini-btn:active:not(:disabled) { transform: translateY(0); }
.mini-btn:disabled { opacity: .6; cursor: wait; }

/* ── Errors popup ─────────────────────────────── */
.modal-backdrop {
  position: fixed; inset: 0; z-index: 500;
  background: rgba(0,0,0,0.6); display: flex; align-items: center; justify-content: center;
  padding: 20px; backdrop-filter: blur(4px); overflow-y: auto;
}
.modal {
  position: relative; width: 100%; max-width: 560px;
  background: var(--bg-elevated); border: 1px solid var(--line);
  border-radius: var(--radius-lg); padding: 28px 22px 22px; margin: auto;
}
.modal-close {
  position: absolute; top: 14px; right: 14px; width: 28px; height: 28px; border-radius: 8px;
  background: var(--bg); border: 1px solid var(--line); color: var(--text-dim); cursor: pointer;
  display: flex; align-items: center; justify-content: center; font-size: 12px;
}
.modal-close:hover { border-color: var(--accent); color: var(--accent); }
.modal-title { font-size: 17px; font-weight: 800; color: var(--text); margin-bottom: 16px; }

.errors-list { display: flex; flex-direction: column; gap: 10px; max-height: 60vh; overflow-y: auto; }
.error-row { background: var(--bg); border: 1px solid var(--line); border-radius: 10px; padding: 12px 14px; }
.error-row-head { display: flex; align-items: center; justify-content: space-between; gap: 10px; margin-bottom: 6px; }
.error-source {
  font-size: 10px; font-weight: 800; text-transform: uppercase; letter-spacing: .04em;
  padding: 2px 8px; border-radius: 99px; background: var(--bg-elevated); border: 1px solid var(--line); color: var(--text-dim);
}
.error-source.backend { background: rgba(235,75,75,.12); border-color: rgba(235,75,75,.35); color: var(--danger); }
.error-source.frontend { background: rgba(255,154,0,.12); border-color: rgba(255,154,0,.35); color: var(--accent); }
.error-time { font-size: 11px; color: var(--text-dim); white-space: nowrap; }
.error-message { font-size: 12.5px; color: var(--text); word-break: break-word; margin-bottom: 4px; }
.error-url { font-size: 11px; color: var(--text-dim); font-family: monospace; word-break: break-all; }
.error-stack-details { margin-top: 6px; }
.error-stack-details summary { font-size: 11px; color: var(--accent); cursor: pointer; }
.error-stack {
  font-size: 10.5px; color: var(--text-dim); white-space: pre-wrap; word-break: break-word;
  background: var(--bg-inset, var(--bg)); border-radius: 6px; padding: 8px; margin-top: 6px; max-height: 200px; overflow-y: auto;
}
</style>