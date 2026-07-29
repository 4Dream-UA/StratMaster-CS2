<template>
  <main class="admin-page">
    <Header />

    <div class="wrap admin-content">

      <button class="back-btn" @click="router.push('/user')">
        <svg viewBox="0 0 16 16" fill="none" width="14" height="14">
          <path d="M10 3L5 8l5 5" stroke="currentColor" stroke-width="2"
                stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
        Dashboard
      </button>

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
          <span class="stat-value">{{ stats?.transactions_count ?? '—' }}</span>
          <span class="stat-label">Transactions</span>
        </div>
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
const userStore = useUserStore()
const { user } = storeToRefs(userStore)

const stats = ref(null)

const ICON_MAP = `<svg viewBox="0 0 24 24" fill="none" width="22" height="22"><path d="M9 4L4 6v14l5-2 6 2 5-2V4l-5 2-6-2z" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round"/><path d="M9 4v14M15 6v14" stroke="currentColor" stroke-width="1.6"/></svg>`
const ICON_TARGET = `<svg viewBox="0 0 24 24" fill="none" width="22" height="22"><circle cx="12" cy="12" r="8" stroke="currentColor" stroke-width="1.6"/><circle cx="12" cy="12" r="4.5" stroke="currentColor" stroke-width="1.6"/><circle cx="12" cy="12" r="1" fill="currentColor"/></svg>`
const ICON_USERS = `<svg viewBox="0 0 24 24" fill="none" width="22" height="22"><circle cx="9" cy="8" r="3" stroke="currentColor" stroke-width="1.6"/><path d="M3 20c0-3.3 2.7-6 6-6s6 2.7 6 6" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/><circle cx="17" cy="9" r="2.5" stroke="currentColor" stroke-width="1.4"/><path d="M15.5 14.2c2.5.4 4.5 2.6 4.5 5.3" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/></svg>`
const ICON_P2P = `<svg viewBox="0 0 24 24" fill="none" width="22" height="22"><rect x="2" y="7" width="20" height="12" rx="2" stroke="currentColor" stroke-width="1.6"/><circle cx="12" cy="13" r="3" stroke="currentColor" stroke-width="1.6"/><path d="M6 7V6a2 2 0 012-2h8a2 2 0 012 2v1" stroke="currentColor" stroke-width="1.4"/></svg>`
const ICON_PROMO = `<svg viewBox="0 0 24 24" fill="none" width="22" height="22"><path d="M11 4h6a1 1 0 011 1v6a1 1 0 01-.3.7l-8 8a1 1 0 01-1.4 0l-6-6a1 1 0 010-1.4l8-8A1 1 0 0111 4z" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round"/><circle cx="15.5" cy="8.5" r="1.3" fill="currentColor"/></svg>`

const TILES = [
  { title: 'Work with Maps',      desc: 'Add, edit, or disable maps',            icon: ICON_MAP,   route: '/admin/maps' },
  { title: 'Work with Strategies',desc: 'Create and manage strategy content',    icon: ICON_TARGET,route: '/admin/strategies' },
  { title: 'Work with Users',     desc: 'View users, roles and subscriptions',   icon: ICON_USERS, route: '/admin/users' },
  { title: 'Promo Codes',         desc: 'Generate and manage MasterCoin codes',  icon: ICON_PROMO, route: '/admin/promo' },
  { title: 'Check P2P',           desc: 'Monitor coin transfers and payouts',    icon: ICON_P2P,   route: '/admin/p2p' },
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
  transition: border-color .2s, color .2s;
  margin-bottom: 28px;
}
.back-btn:hover { border-color: var(--accent); color: var(--accent); }

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
.stat-label { font-size: 11px; color: var(--text-dim); text-transform: uppercase; letter-spacing: .05em; }

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
</style>