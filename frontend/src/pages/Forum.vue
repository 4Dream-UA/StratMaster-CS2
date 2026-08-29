<template>
  <main class="forum-page">
    <Header />

    <div class="wrap forum-content">
      <button class="back-btn" @click="onBack">
        <svg viewBox="0 0 16 16" fill="none" width="14" height="14">
          <path d="M10 3L5 8l5 5" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
        {{ backLabel }}
      </button>

      <!-- ═══ NOT PREMIUM ═══════════════════════ -->
      <section v-if="!hasActiveAccess" class="upsell-card">
        <span class="eyebrow">Premium feature</span>
        <h1>Player Forum</h1>
        <p>Talk with other premium players in the Lounge, or open a private ticket with the team — upgrade to unlock it.</p>
        <router-link to="/pricing" class="btn-primary">Get Premium Access</router-link>
      </section>

      <!-- ═══ CATEGORIES ═══════════════════════ -->
      <template v-else-if="view === 'categories'">
        <section class="page-head">
          <span class="eyebrow">Premium</span>
          <h1>Forum</h1>
        </section>

        <div v-if="loadingCategories" class="loading-row">Loading…</div>
        <div v-else class="category-grid">
          <button v-for="cat in categories" :key="cat.key" class="category-card" @click="openCategory(cat)">
            <span class="category-icon"><LoungeIcon v-if="cat.key === 'lounge'" /><SupportIcon v-else /></span>
            <h3>{{ cat.name }}</h3>
            <p>{{ cat.description }}</p>
          </button>
        </div>
      </template>

      <!-- ═══ THREAD LIST (Lounge, or Support-as-admin) ═══════════════════════ -->
      <template v-else-if="view === 'threads'">
        <section class="page-head row">
          <div>
            <span class="eyebrow">{{ activeCategory?.name }}</span>
            <h1>{{ activeCategory?.key === 'support' ? 'Support Tickets' : 'Threads' }}</h1>
          </div>
          <button v-if="activeCategory?.key === 'lounge'" class="btn-primary" @click="openNewThreadForm">+ New Thread</button>
        </section>

        <section v-if="newThreadOpen" class="form-card">
          <h3>New thread</h3>
          <input v-model="newThreadTitle" type="text" placeholder="Title" class="thread-input" />
          <textarea v-model="newThreadBody" rows="4" placeholder="What's on your mind?" class="thread-input"></textarea>
          <div class="form-actions">
            <button class="btn-primary" :disabled="!newThreadTitle.trim() || !newThreadBody.trim() || posting" @click="submitNewThread">
              {{ posting ? 'Posting…' : 'Post Thread' }}
            </button>
            <button class="mini-btn" @click="newThreadOpen = false">Cancel</button>
          </div>
          <p v-if="errorMsg" class="err">{{ errorMsg }}</p>
        </section>

        <section class="list-card">
          <div v-if="loadingThreads" class="loading-row">Loading…</div>
          <div v-else-if="!threads.length" class="empty">
            {{ activeCategory?.key === 'support' ? 'No tickets yet.' : 'No threads yet — start the first one.' }}
          </div>
          <div v-else class="thread-list">
            <button v-for="t in threads" :key="t.id" class="thread-row" @click="openThread(t.id)">
              <div class="thread-row-main">
                <h4>{{ activeCategory?.key === 'support' ? (t.author_username ? '@' + t.author_username : 'Ticket') : t.title }}</h4>
                <span class="thread-row-meta">{{ t.author_username ? '@' + t.author_username + ' · ' : '' }}{{ t.post_count }} {{ t.post_count === 1 ? 'post' : 'posts' }}</span>
              </div>
              <span class="thread-row-arrow">→</span>
            </button>
          </div>
        </section>

        <Pagination :total="threadsTotal" :page="threadsPage" :page-size="PAGE_SIZE" @update:page="onThreadsPageChange" />
      </template>

      <!-- ═══ THREAD DETAIL ═══════════════════════ -->
      <template v-else-if="view === 'thread'">
        <section class="page-head">
          <span class="eyebrow">{{ activeCategory?.name }}</span>
          <h1>{{ activeThread?.title }}</h1>
        </section>

        <div v-if="loadingThread" class="loading-row">Loading…</div>
        <template v-else-if="activeThread">
          <div class="post-list">
            <div v-for="p in activeThread.posts" :key="p.id" class="post-card" :class="{ mine: p.author_id === currentUserId }">
              <div class="post-head">
                <span class="post-author">{{ p.author_username ? '@' + p.author_username : 'Player' }}</span>
                <span class="post-time">{{ formatTime(p.created_at) }}</span>
              </div>
              <p class="post-body">{{ p.body }}</p>
            </div>
          </div>

          <div class="reply-box">
            <textarea v-model="replyBody" rows="3" placeholder="Write a reply…" class="thread-input"></textarea>
            <button class="btn-primary reply-btn" :disabled="!replyBody.trim() || posting" @click="submitReply">
              {{ posting ? 'Sending…' : 'Reply' }}
            </button>
            <p v-if="errorMsg" class="err">{{ errorMsg }}</p>
          </div>
        </template>
      </template>
    </div>

    <Footer />
  </main>
</template>

<script setup>
import { ref, computed, onMounted, h } from 'vue'
import { storeToRefs } from 'pinia'
import { useUserStore } from '../store/user'
import { forumAPI } from '../api/forum'
import Header from '../components/Header.vue'
import Footer from '../components/Footer.vue'
import Pagination from '../components/Pagination.vue'

const LoungeIcon = {
  render: () => h('svg', { viewBox: '0 0 24 24', width: 28, height: 28, fill: 'none' }, [
    h('path', { d: 'M4 8h14l-3.5-3.5M20 16H6l3.5 3.5', stroke: 'var(--accent)', 'stroke-width': 1.6, 'stroke-linecap': 'round', 'stroke-linejoin': 'round' }),
  ]),
}
const SupportIcon = {
  render: () => h('svg', { viewBox: '0 0 24 24', width: 28, height: 28, fill: 'none' }, [
    h('path', { d: 'M12 4a5 5 0 015 5c0 2.5-2 3.5-3 4.5s-1 1.5-1 2.5', stroke: 'var(--accent)', 'stroke-width': 1.6, 'stroke-linecap': 'round' }),
    h('circle', { cx: 12, cy: 19, r: 1.2, fill: 'var(--accent)' }),
  ]),
}

const userStore = useUserStore()
const { user, wallet } = storeToRefs(userStore)
const currentUserId = computed(() => user.value?.id)

const hasActiveAccess = computed(() => {
  if (wallet.value?.is_lifetime) return true
  const exp = wallet.value?.subscription_expires_at
  return !!(exp && new Date(exp) > new Date())
})

const view = ref('categories') // 'categories' | 'threads' | 'thread'
const categories = ref([])
const activeCategory = ref(null)
const loadingCategories = ref(true)

const threads = ref([])
const loadingThreads = ref(false)
const PAGE_SIZE = 5
const threadsPage = ref(1)
const threadsTotal = ref(0)

const newThreadOpen = ref(false)
const newThreadTitle = ref('')
const newThreadBody = ref('')

const activeThread = ref(null)
const loadingThread = ref(false)
const replyBody = ref('')
const posting = ref(false)
const errorMsg = ref('')

const backLabel = computed(() => {
  if (view.value === 'thread') return activeCategory.value?.key === 'support' ? 'Back' : 'Threads'
  if (view.value === 'threads') return 'Forum'
  return 'Home'
})

function onBack() {
  errorMsg.value = ''
  if (view.value === 'thread') {
    if (activeCategory.value?.key === 'support' && !isAdmin.value) {
      view.value = 'categories'
    } else {
      view.value = 'threads'
    }
    return
  }
  if (view.value === 'threads') {
    view.value = 'categories'
    return
  }
  window.history.length > 1 ? window.history.back() : (window.location.href = '/')
}

const isAdmin = computed(() => !!user.value?.is_admin)

async function loadCategories() {
  loadingCategories.value = true
  try {
    categories.value = await forumAPI.listCategories()
  } finally {
    loadingCategories.value = false
  }
}

async function loadThreads(key) {
  loadingThreads.value = true
  try {
    const res = await forumAPI.listThreads(key, { limit: PAGE_SIZE, offset: (threadsPage.value - 1) * PAGE_SIZE })
    threads.value = res.threads
    threadsTotal.value = res.total
  } finally {
    loadingThreads.value = false
  }
}

function onThreadsPageChange(p) {
  threadsPage.value = p
  loadThreads(activeCategory.value.key)
}

async function openCategory(cat) {
  activeCategory.value = cat
  errorMsg.value = ''
  threadsPage.value = 1
  newThreadOpen.value = false

  if (cat.key === 'support' && !isAdmin.value) {
    // Regular users only ever have one ticket — skip straight to it.
    loadingThread.value = true
    view.value = 'thread'
    try {
      const res = await forumAPI.listThreads('support')
      await openThread(res.threads[0].id)
    } finally {
      loadingThread.value = false
    }
    return
  }

  view.value = 'threads'
  await loadThreads(cat.key)
}

function openNewThreadForm() {
  newThreadTitle.value = ''
  newThreadBody.value = ''
  errorMsg.value = ''
  newThreadOpen.value = true
}

async function submitNewThread() {
  if (!newThreadTitle.value.trim() || !newThreadBody.value.trim()) return
  posting.value = true
  errorMsg.value = ''
  try {
    const thread = await forumAPI.createThread(activeCategory.value.key, newThreadTitle.value.trim(), newThreadBody.value.trim())
    newThreadOpen.value = false
    await loadThreads(activeCategory.value.key)
    await openThread(thread.id)
  } catch (e) {
    errorMsg.value = e.response?.data?.detail || 'Could not post the thread.'
  } finally {
    posting.value = false
  }
}

async function openThread(id) {
  errorMsg.value = ''
  loadingThread.value = true
  view.value = 'thread'
  try {
    activeThread.value = await forumAPI.getThread(id)
  } finally {
    loadingThread.value = false
  }
}

async function submitReply() {
  if (!replyBody.value.trim() || !activeThread.value) return
  posting.value = true
  errorMsg.value = ''
  try {
    activeThread.value = await forumAPI.addPost(activeThread.value.id, replyBody.value.trim())
    replyBody.value = ''
  } catch (e) {
    errorMsg.value = e.response?.data?.detail || 'Could not send the reply.'
  } finally {
    posting.value = false
  }
}

function formatTime(iso) {
  const d = new Date(iso)
  return d.toLocaleString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
}

onMounted(async () => {
  window.scrollTo({ top: 0, behavior: 'auto' })
  if (!hasActiveAccess.value) return
  await loadCategories()
})
</script>

<style scoped>
.forum-page { min-height: 100vh; background: var(--bg); }
.forum-content { max-width: 720px; padding: 32px 20px 140px; }

.back-btn {
  display: inline-flex; align-items: center; gap: 6px;
  background: var(--bg-elevated); border: 1px solid var(--line);
  color: var(--text-dim); padding: 8px 16px; border-radius: 8px;
  font-size: 13px; font-weight: 600; cursor: pointer;
  transition: border-color .2s, color .2s; margin-bottom: 28px;
}
.back-btn:hover { border-color: var(--accent); color: var(--accent); }

.upsell-card {
  background: linear-gradient(160deg, rgba(255,154,0,0.08), var(--bg-elevated) 60%);
  border: 1px solid rgba(255,154,0,0.3); border-radius: var(--radius-lg);
  padding: 32px 24px; text-align: center;
}
.upsell-card h1 { font-size: 24px; font-weight: 900; color: var(--text); margin: 8px 0 10px; }
.upsell-card p { font-size: 13.5px; color: var(--text-dim); max-width: 420px; margin: 0 auto 20px; line-height: 1.6; }
.upsell-card .btn-primary { text-decoration: none; display: inline-block; }

.page-head { margin-bottom: 24px; }
.page-head.row { display: flex; align-items: center; justify-content: space-between; gap: 14px; flex-wrap: wrap; }
.eyebrow {
  display: block; font-size: 11px; font-weight: 800; letter-spacing: .08em;
  text-transform: uppercase; color: var(--accent); margin-bottom: 6px;
}
.page-head h1 { font-size: clamp(22px, 4vw, 30px); font-weight: 900; color: var(--text); }

.loading-row, .empty { padding: 24px; text-align: center; color: var(--text-dim); font-size: 13px; }

/* ── Categories ─────────────────────────────── */
.category-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 16px; }
.category-card {
  background: var(--bg-elevated); border: 1px solid var(--line);
  border-radius: var(--radius-lg); padding: 24px; text-align: left;
  cursor: pointer; transition: border-color .2s, transform .2s;
}
.category-card:hover { border-color: rgba(255,154,0,.5); transform: translateY(-2px); }
.category-icon { display: block; margin-bottom: 10px; }
.category-card h3 { font-size: 16px; font-weight: 800; color: var(--text); margin-bottom: 6px; }
.category-card p { font-size: 12.5px; color: var(--text-dim); line-height: 1.5; }

/* ── Thread list ─────────────────────────────── */
.list-card, .form-card {
  background: var(--bg-elevated); border: 1px solid var(--line);
  border-radius: var(--radius-lg); padding: 20px; margin-bottom: 16px;
}
.form-card h3 { font-size: 14px; font-weight: 700; color: var(--text); margin-bottom: 12px; }
.thread-list { display: flex; flex-direction: column; gap: 8px; }
.thread-row {
  display: flex; align-items: center; justify-content: space-between; gap: 12px;
  width: 100%; text-align: left; background: var(--bg); border: 1px solid var(--line);
  border-radius: 10px; padding: 14px 16px; cursor: pointer; transition: border-color .15s;
}
.thread-row:hover { border-color: var(--accent); }
.thread-row-main h4 { font-size: 13.5px; font-weight: 700; color: var(--text); margin-bottom: 4px; }
.thread-row-meta { font-size: 11.5px; color: var(--text-dim); }
.thread-row-arrow { color: var(--text-dim); flex-shrink: 0; }

.thread-input {
  width: 100%; padding: 10px 12px; margin-bottom: 10px;
  background: var(--bg); border: 1px solid var(--line); border-radius: 9px;
  color: var(--text); font-size: 13.5px; font-family: inherit; resize: vertical;
}
.thread-input:focus { outline: none; border-color: var(--accent); }

.form-actions { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }
.mini-btn {
  background: var(--bg); border: 1px solid var(--line); color: var(--text-dim);
  padding: 8px 14px; border-radius: 7px; font-size: 12.5px; font-weight: 700; cursor: pointer;
  transition: border-color .15s, color .15s;
}
.mini-btn:hover { border-color: var(--accent); color: var(--accent); }
.err { color: var(--danger); font-size: 12.5px; font-weight: 600; margin: 8px 0 0; width: 100%; }

/* ── Thread detail ─────────────────────────────── */
.post-list { display: flex; flex-direction: column; gap: 10px; margin-bottom: 16px; }
.post-card {
  background: var(--bg-elevated); border: 1px solid var(--line);
  border-radius: 12px; padding: 14px 16px;
}
.post-card.mine { border-color: rgba(255,154,0,.35); background: rgba(255,154,0,.05); }
.post-head { display: flex; align-items: center; justify-content: space-between; gap: 10px; margin-bottom: 6px; }
.post-author { font-size: 12.5px; font-weight: 700; color: var(--accent); }
.post-time { font-size: 11px; color: var(--text-dim); }
.post-body { font-size: 13.5px; color: var(--text); line-height: 1.6; white-space: pre-wrap; }

.reply-box {
  background: var(--bg-elevated); border: 1px solid var(--line);
  border-radius: var(--radius-lg); padding: 16px;
}
.reply-btn { width: 100%; padding: 11px; }
</style>
