<template>
  <main class="admin-page">
    <Header />

    <div class="wrap admin-content">
      <Breadcrumbs :items="[{ label: 'Home', to: '/' }, { label: 'Admin', to: '/admin' }, { label: tab === 'reports' ? 'Reports' : 'Support' }]" />

      <section class="page-head">
        <span class="eyebrow">Moderation</span>
        <h1>{{ tab === 'reports' ? 'Reports' : 'Support Tickets' }}</h1>
      </section>

      <div class="view-tabs">
        <button type="button" class="view-tab" :class="{ active: tab === 'reports' }" @click="go('reports')">
          Reports <span v-if="reportsTotal" class="tab-badge">{{ reportsTotal }}</span>
        </button>
        <button type="button" class="view-tab" :class="{ active: tab === 'tickets' }" @click="go('tickets')">
          Support <span v-if="openTicketCount" class="tab-badge">{{ openTicketCount }}</span>
        </button>
      </div>

      <!-- ═══ REPORTS ═══════════════════════════ -->
      <template v-if="tab === 'reports'">
        <section class="list-card">
          <div v-if="loading" class="loading-row">Loading…</div>
          <div v-else-if="!reports.length" class="empty">Nothing reported — the queue is clear.</div>
          <div v-else class="queue-list">
            <!-- One card per reported item, not per report — Dismiss
                 resolves them all together, so grouping is what makes the
                 list match what the button does. -->
            <article v-for="r in reports" :key="r.target_kind + r.target_id" class="queue-row">
              <div class="queue-head">
                <span class="kind-pill" :class="r.target_kind">{{ r.target_kind === 'thread' ? 'Thread' : 'Message' }}</span>
                <span class="kind-pill muted">{{ r.category_key }}</span>
                <span v-if="r.reports.length > 1" class="kind-pill count">{{ r.reports.length }} reports</span>
                <span class="queue-time">{{ formatTime(r.last_reported_at) }}</span>
              </div>

              <p class="queue-title">{{ r.thread_title }}</p>
              <p class="queue-excerpt">{{ r.excerpt }}</p>

              <dl class="queue-meta">
                <div><dt>Posted by</dt><dd>{{ nameOf(r.author_display_name, r.author_username) }}</dd></div>
              </dl>

              <ul class="reason-list">
                <li v-for="(x, i) in r.reports" :key="i">
                  <span class="reason-who">{{ nameOf(x.reporter_display_name, x.reporter_username) }}</span>
                  <span class="reason-text">{{ x.reason || '(no reason given)' }}</span>
                  <span class="reason-time">{{ formatTime(x.created_at) }}</span>
                </li>
              </ul>

              <div class="queue-actions">
                <button class="mini-btn" @click="openInForum(r)">Open in forum →</button>
                <button class="mini-btn" :disabled="busyId === targetKey(r)" @click="dismiss(r)">
                  {{ busyId === targetKey(r) ? '…' : (r.reports.length > 1 ? `Dismiss all ${r.reports.length}` : 'Dismiss') }}
                </button>
              </div>
            </article>
          </div>
        </section>
        <Pagination :total="reportsTotal" :page="page" :page-size="PAGE_SIZE" @update:page="onPageChange" />
      </template>

      <!-- ═══ TICKETS ═══════════════════════════ -->
      <template v-else>
        <div class="filter-row">
          <button
            v-for="f in TICKET_FILTERS" :key="f.value" type="button" class="filter-chip"
            :class="{ active: ticketStatus === f.value }" @click="setTicketStatus(f.value)"
          >{{ f.label }}</button>
        </div>

        <section class="list-card">
          <div v-if="loading" class="loading-row">Loading…</div>
          <div v-else-if="!tickets.length" class="empty">No tickets here.</div>
          <table v-else class="admin-table">
            <thead>
              <tr><th>Ticket</th><th>Opened by</th><th>Messages</th><th>Status</th><th>Last activity</th><th></th></tr>
            </thead>
            <tbody>
              <tr v-for="t in tickets" :key="t.id" class="ticket-row" @click="openTicket(t)">
                <td class="ticket-title">{{ t.title }}</td>
                <td>{{ nameOf(t.author_display_name, t.author_username) }}</td>
                <td>{{ t.post_count }}</td>
                <td>
                  <span class="status-pill" :class="t.is_closed ? 'off' : 'on'">{{ t.is_closed ? 'Closed' : 'Open' }}</span>
                  <span v-if="t.awaiting_reply" class="status-pill waiting">Needs reply</span>
                </td>
                <td class="queue-time">{{ formatTime(t.updated_at) }}</td>
                <td class="row-arrow">→</td>
              </tr>
            </tbody>
          </table>
        </section>
        <Pagination :total="ticketsTotal" :page="page" :page-size="PAGE_SIZE" @update:page="onPageChange" />
      </template>
    </div>

    <Footer />
  </main>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { adminAPI } from '../api/admin'
import { forumAPI } from '../api/forum'
import Header from '../components/Header.vue'
import Footer from '../components/Footer.vue'
import Breadcrumbs from '../components/Breadcrumbs.vue'
import Pagination from '../components/Pagination.vue'

const route = useRoute()
const router = useRouter()

const PAGE_SIZE = 20
const TICKET_FILTERS = [
  { value: 'open', label: 'Open' },
  { value: 'closed', label: 'Closed' },
  { value: 'all', label: 'All' },
]

// One component, two routes — /admin/reports and /admin/tickets. They're
// the same job (a queue of things waiting on an admin) and share every
// helper, but they get their own URLs so the dashboard's stat boxes can
// link straight at either one.
const tab = computed(() => (route.path.endsWith('/tickets') ? 'tickets' : 'reports'))

const loading = ref(true)
const busyId = ref(null)
const page = ref(1)

const reports = ref([])
const reportsTotal = ref(0)
const tickets = ref([])
const ticketsTotal = ref(0)
const openTicketCount = ref(0)
const ticketStatus = ref('open')

function nameOf(displayName, username) {
  return displayName || (username ? '@' + username : 'Player')
}
function formatTime(iso) {
  return new Date(iso).toLocaleString(undefined, { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' })
}

async function load() {
  loading.value = true
  const params = { limit: PAGE_SIZE, offset: (page.value - 1) * PAGE_SIZE }
  try {
    if (tab.value === 'reports') {
      const res = await adminAPI.getReports(params)
      reports.value = res.reports
      reportsTotal.value = res.total
    } else {
      const res = await adminAPI.getTickets({ ...params, status: ticketStatus.value })
      tickets.value = res.tickets
      ticketsTotal.value = res.total
    }
  } finally {
    loading.value = false
  }
}

// The badge on the *other* tab, so an admin sitting on one queue can still
// see the other filling up.
async function loadCounts() {
  try {
    const [r, t] = await Promise.all([
      adminAPI.getReports({ limit: 1 }),
      adminAPI.getTickets({ limit: 1, status: 'open' }),
    ])
    reportsTotal.value = r.total
    openTicketCount.value = t.total
  } catch (e) {
    // Badges are decoration — never block the list on them.
  }
}

function go(next) {
  if (tab.value === next) return
  page.value = 1
  router.push(next === 'tickets' ? '/admin/tickets' : '/admin/reports')
}
function setTicketStatus(value) {
  ticketStatus.value = value
  page.value = 1
  load()
}
function onPageChange(next) {
  page.value = next
  load()
}

function openInForum(r) {
  // A thread report lands on the thread; a message report lands on the
  // message itself, which is often buried a long way down a busy thread.
  const query = { thread: r.thread_id }
  if (r.target_kind === 'post') query.post = r.target_id
  router.push({ path: '/forum', query })
}
function openTicket(t) {
  router.push({ path: '/forum', query: { thread: t.id } })
}

function targetKey(r) {
  return r.target_kind + r.target_id
}

async function dismiss(r) {
  busyId.value = targetKey(r)
  try {
    if (r.target_kind === 'thread') await forumAPI.dismissThreadReports(r.target_id)
    else await forumAPI.dismissPostReports(r.target_id)
    await load()
    await loadCounts()
  } finally {
    busyId.value = null
  }
}

watch(tab, () => { load(); loadCounts() })
onMounted(() => { load(); loadCounts() })
</script>

<style scoped>
.admin-page { min-height: 100vh; background: var(--bg); }
.admin-content { max-width: 960px; padding: 32px 20px 120px; }

.page-head { margin-bottom: 20px; }
.eyebrow { font-size: 11px; font-weight: 800; letter-spacing: .08em; color: var(--accent); text-transform: uppercase; }
.page-head h1 { font-size: 28px; font-weight: 900; color: var(--text); margin-top: 6px; }

.view-tabs { display: flex; gap: 8px; margin-bottom: 20px; flex-wrap: wrap; }
.view-tab {
  display: flex; align-items: center; gap: 7px;
  padding: 9px 20px; border-radius: 99px;
  background: var(--bg-elevated); border: 1.5px solid var(--line);
  color: var(--text-dim); font-size: 13px; font-weight: 700; cursor: pointer;
  transition: border-color .15s, color .15s;
}
.view-tab:hover { border-color: rgba(255,154,0,.5); color: var(--text); }
.view-tab.active { background: rgba(255,154,0,.12); border-color: var(--accent); color: var(--accent); }
.tab-badge { background: var(--accent); color: #14140f; font-size: 10.5px; font-weight: 900; padding: 1px 7px; border-radius: 99px; }

.filter-row { display: flex; gap: 6px; margin-bottom: 14px; flex-wrap: wrap; }
.filter-chip {
  padding: 5px 14px; border-radius: 99px; background: var(--bg); border: 1px solid var(--line);
  color: var(--text-dim); font-size: 11.5px; font-weight: 700; cursor: pointer;
}
.filter-chip.active { background: rgba(255,154,0,.14); border-color: var(--accent); color: var(--accent); }

.list-card {
  background: var(--bg-elevated); border: 1px solid var(--line);
  border-radius: var(--radius-lg); padding: 8px; overflow-x: auto;
}
.loading-row, .empty { padding: 40px 20px; text-align: center; color: var(--text-dim); font-size: 14px; }

/* ── Report cards ─────────────────────────── */
.queue-list { display: flex; flex-direction: column; gap: 8px; }
.queue-row { background: var(--bg); border: 1px solid var(--line); border-radius: 12px; padding: 16px 18px; }
.queue-head { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; margin-bottom: 10px; }
.kind-pill {
  font-size: 10.5px; font-weight: 800; text-transform: uppercase; letter-spacing: .05em;
  padding: 3px 10px; border-radius: 99px; border: 1px solid;
}
.kind-pill.post { color: var(--accent); border-color: color-mix(in srgb, var(--accent) 45%, transparent); }
.kind-pill.thread { color: #8847ff; border-color: rgba(136,71,255,.45); }
.kind-pill.muted { color: var(--text-dim); border-color: var(--line); }
.kind-pill.count { color: var(--danger); border-color: color-mix(in srgb, var(--danger) 45%, transparent); }
.queue-time { font-size: 11.5px; color: var(--text-dim); margin-left: auto; white-space: nowrap; }

.queue-title { font-size: 14px; font-weight: 800; color: var(--text); margin-bottom: 6px; }
.queue-excerpt {
  font-size: 13px; color: var(--text-dim); line-height: 1.5;
  padding: 10px 12px; background: var(--bg-elevated); border-radius: 8px;
  border-left: 2px solid var(--line); margin-bottom: 12px;
  white-space: pre-wrap; overflow-wrap: anywhere;
}

.queue-meta { display: flex; flex-wrap: wrap; gap: 8px 22px; margin-bottom: 12px; }
.queue-meta div { display: flex; flex-direction: column; gap: 2px; min-width: 0; }
.queue-meta dt { font-size: 10px; font-weight: 800; color: var(--text-dim); text-transform: uppercase; letter-spacing: .05em; }
.queue-meta dd { font-size: 12.5px; font-weight: 600; color: var(--text); overflow-wrap: anywhere; }

.reason-list { list-style: none; margin: 0 0 14px; padding: 0; display: flex; flex-direction: column; gap: 6px; }
.reason-list li {
  display: flex; align-items: baseline; gap: 10px; flex-wrap: wrap;
  font-size: 12.5px; padding: 7px 11px; background: var(--bg-elevated); border-radius: 8px;
}
.reason-who { font-weight: 800; color: var(--text); white-space: nowrap; }
.reason-text { color: var(--text-dim); flex: 1; min-width: 120px; overflow-wrap: anywhere; }
.reason-time { font-size: 11px; color: var(--text-dim); white-space: nowrap; }

.queue-actions { display: flex; gap: 8px; flex-wrap: wrap; }
.mini-btn {
  background: linear-gradient(160deg, var(--bg-elevated), var(--bg)); border: 1px solid var(--line);
  color: var(--text-dim); border-radius: 8px; padding: 7px 14px;
  font-size: 12px; font-weight: 700; cursor: pointer; font-family: inherit;
  transition: border-color .15s, color .15s;
}
.mini-btn:hover:not(:disabled) { border-color: var(--accent); color: var(--accent); }
.mini-btn:disabled { opacity: .5; cursor: not-allowed; }

/* ── Ticket table ─────────────────────────── */
.admin-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.admin-table th {
  text-align: left; padding: 12px 14px; font-size: 10.5px; font-weight: 800;
  text-transform: uppercase; letter-spacing: .05em; color: var(--text-dim);
  border-bottom: 1px solid var(--line); white-space: nowrap;
}
.admin-table td { padding: 13px 14px; color: var(--text); border-bottom: 1px solid var(--line); }
.admin-table tr:last-child td { border-bottom: none; }
.ticket-row { cursor: pointer; }
.ticket-row:hover td { background: var(--bg); }
.ticket-title { font-weight: 700; }
.row-arrow { color: var(--text-dim); text-align: right; }

.status-pill {
  display: inline-block; padding: 2px 10px; border-radius: 99px;
  font-size: 10.5px; font-weight: 800; border: 1px solid; white-space: nowrap;
}
.status-pill.on { color: var(--success); border-color: color-mix(in srgb, var(--success) 45%, transparent); }
.status-pill.off { color: var(--text-dim); border-color: var(--line); }
.status-pill.waiting { color: var(--accent); border-color: color-mix(in srgb, var(--accent) 45%, transparent); margin-left: 6px; }
</style>
