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
          <div v-for="cat in categories" :key="cat.key" class="category-card-wrap">
            <button class="category-card" @click="openCategory(cat)">
              <span class="category-icon-badge"><LoungeIcon v-if="cat.key === 'lounge'" /><SupportIcon v-else /></span>
              <h3>{{ cat.name }}</h3>
              <p>{{ cat.description }}</p>
              <span class="category-arrow">→</span>
            </button>
            <button v-if="isAdmin" class="icon-btn small category-edit-btn" title="Edit category" @click="startEditCategory(cat)"><EditIcon :size="11" /></button>

            <div v-if="editingCategoryKey === cat.key" class="category-edit-form">
              <input v-model="categoryDraft.name" type="text" class="thread-input" placeholder="Name" />
              <input v-model="categoryDraft.description" type="text" class="thread-input" placeholder="Description" />
              <div class="form-actions">
                <button class="mini-btn" @click="saveCategory(cat)">Save</button>
                <button class="mini-btn" @click="editingCategoryKey = null">Cancel</button>
              </div>
            </div>
          </div>
        </div>
      </template>

      <!-- ═══ THREAD LIST ═══════════════════════ -->
      <template v-else-if="view === 'threads'">
        <section class="page-head row">
          <div>
            <span class="eyebrow">{{ activeCategory?.name }}</span>
            <h1>{{ activeCategory?.key === 'support' ? 'Support Tickets' : 'Threads' }}</h1>
          </div>
          <button class="btn-primary" @click="openNewThreadForm">
            {{ activeCategory?.key === 'support' ? '+ New Ticket' : '+ New Thread' }}
          </button>
        </section>

        <section v-if="newThreadOpen" class="form-card">
          <h3>{{ activeCategory?.key === 'support' ? 'New ticket' : 'New thread' }}</h3>
          <input
            v-model="newThreadTitle" type="text" class="thread-input"
            :placeholder="activeCategory?.key === 'support' ? 'What do you need help with?' : 'Title'"
          />
          <MarkdownComposer v-model="newThreadBody" placeholder="Write your message… supports **bold**, *italic*, `code` and images" />
          <div class="form-actions">
            <button class="btn-primary" :disabled="!newThreadTitle.trim() || !newThreadBody.trim() || posting" @click="submitNewThread">
              {{ posting ? 'Posting…' : (activeCategory?.key === 'support' ? 'Open Ticket' : 'Post Thread') }}
            </button>
            <button class="mini-btn" @click="newThreadOpen = false">Cancel</button>
          </div>
          <p v-if="errorMsg" class="err">{{ errorMsg }}</p>
        </section>

        <section class="list-card">
          <div v-if="loadingThreads" class="loading-row">Loading…</div>
          <div v-else-if="!threads.length" class="empty">
            {{ activeCategory?.key === 'support' ? 'No tickets yet — open one if you need help.' : 'No threads yet — start the first one.' }}
          </div>
          <div v-else class="thread-list">
            <ThreadRow
              v-for="t in pinnedThreads" :key="t.id" :thread="t"
              :can-pin="isAdmin" :can-modify="canModifyThread(t)"
              @open="openThread(t.id)" @toggle-pin="togglePin(t)" @remove="removeThreadRow(t)"
            />
            <div v-if="pinnedThreads.length && otherThreads.length" class="thread-divider"><span>Other threads</span></div>
            <ThreadRow
              v-for="t in otherThreads" :key="t.id" :thread="t"
              :can-pin="isAdmin" :can-modify="canModifyThread(t)"
              @open="openThread(t.id)" @toggle-pin="togglePin(t)" @remove="removeThreadRow(t)"
            />
          </div>
        </section>

        <Pagination :total="threadsTotal" :page="threadsPage" :page-size="PAGE_SIZE" @update:page="onThreadsPageChange" />
      </template>

      <!-- ═══ THREAD DETAIL ═══════════════════════ -->
      <template v-else-if="view === 'thread'">
        <section class="page-head">
          <span class="eyebrow">
            {{ activeCategory?.name }}
            <span v-if="activeThread?.is_pinned" class="pinned-tag"><PinIcon :size="10" /> Pinned</span>
            <span v-if="activeThread?.is_closed" class="closed-tag"><LockIcon :size="10" /> Closed</span>
          </span>

          <div v-if="!titleEditing" class="thread-title-row">
            <h1>{{ activeThread?.title }}</h1>
            <div class="thread-actions">
              <button class="icon-btn" :class="{ active: activeThread?.is_watching }" :title="activeThread?.is_watching ? 'Stop watching' : 'Watch for replies'" @click="toggleWatch"><WatchIcon /></button>
              <button class="icon-btn" title="Share" @click="openShare"><ShareIcon /></button>
              <template v-if="canModifyActiveThread">
                <button class="icon-btn" title="Edit title" @click="startEditTitle"><EditIcon /></button>
                <button v-if="isAdmin" class="icon-btn" :title="activeThread?.is_pinned ? 'Unpin' : 'Pin'" @click="toggleActiveThreadPin"><PinIcon /></button>
                <button v-if="isAdmin && activeCategory?.key === 'support'" class="icon-btn" :title="activeThread?.is_closed ? 'Reopen ticket' : 'Close ticket'" @click="toggleClose"><LockIcon /></button>
                <button class="icon-btn danger" title="Delete thread" @click="deleteActiveThread"><TrashIcon /></button>
              </template>
            </div>
          </div>
          <div v-else class="thread-title-edit">
            <input v-model="titleDraft" type="text" class="thread-input" />
            <button class="mini-btn" @click="saveTitle">Save</button>
            <button class="mini-btn" @click="titleEditing = false">Cancel</button>
          </div>

          <div v-if="shareOpen" class="share-box">
            <template v-if="activeThread?.share_token">
              <input type="text" readonly class="thread-input share-link-input" :value="shareLinkUrl" @click="$event.target.select()" />
              <button class="mini-btn" @click="copyShareLink">{{ shareLinkCopied ? 'Copied!' : 'Copy' }}</button>
              <button v-if="canModifyActiveThread" class="mini-btn danger" @click="revokeShare">Revoke</button>
            </template>
            <button v-else-if="canModifyActiveThread" class="mini-btn" :disabled="shareBusy" @click="generateShare">
              {{ shareBusy ? 'Generating…' : 'Generate share link' }}
            </button>
            <p v-else class="share-hint">Only the thread owner or an admin can generate a share link.</p>
          </div>
        </section>

        <div v-if="loadingThread" class="loading-row">Loading…</div>
        <template v-else-if="activeThread">
          <div class="post-list">
            <div
              v-for="p in activeThread.posts" :key="p.id" class="post-card"
              :class="{ mine: p.author_id === currentUserId, staff: p.author_is_admin }"
            >
              <div class="post-sidebar">
                <Avatar :username="p.author_username" :avatar-url="p.author_avatar_url" :is-admin="p.author_is_admin" :size="46" />
                <span class="post-username">{{ p.author_username ? '@' + p.author_username : 'Player' }}</span>
                <span class="post-role" :class="{ admin: p.author_is_admin }">{{ p.author_is_admin ? 'Admin' : 'Player' }}</span>
              </div>
              <div class="post-main">
                <div class="post-head">
                  <span class="post-time">{{ formatTime(p.created_at) }}</span>
                  <button v-if="!activeThread.is_closed || isAdmin" class="icon-btn small" title="Reply" @click="startReplyTo(p)"><ReplyIcon :size="11" /></button>
                  <button v-if="canModifyPost(p) && editingPostId !== p.id" class="icon-btn small" title="Edit" @click="startEditPost(p)"><EditIcon :size="11" /></button>
                </div>

                <div v-if="p.reply_to" class="post-quote">
                  <span class="post-quote-author">{{ p.reply_to.author_username ? '@' + p.reply_to.author_username : 'Player' }}</span>
                  {{ p.reply_to.body_snippet }}
                </div>

                <template v-if="editingPostId === p.id">
                  <MarkdownComposer v-model="editingPostBody" :rows="3" />
                  <div class="form-actions">
                    <button class="mini-btn" @click="saveEditPost">Save</button>
                    <button class="mini-btn" @click="editingPostId = null">Cancel</button>
                  </div>
                </template>
                <div v-else class="post-body" v-html="renderMarkdown(p.body)"></div>
              </div>
            </div>
          </div>

          <div v-if="!activeThread.is_closed || isAdmin" class="reply-box">
            <div v-if="replyingTo" class="replying-banner">
              Replying to <strong>{{ replyingTo.author_username ? '@' + replyingTo.author_username : 'Player' }}</strong>
              <button class="link-btn" @click="replyingTo = null">cancel</button>
            </div>
            <div class="reply-box-row">
              <Avatar :username="user?.username" :avatar-url="user?.avatar_url" :is-admin="isAdmin" :size="38" />
              <MarkdownComposer v-model="replyBody" :rows="3" placeholder="Write a reply…" />
            </div>
            <button class="btn-primary reply-btn" :disabled="!replyBody.trim() || posting" @click="submitReply">
              {{ posting ? 'Sending…' : 'Reply' }}
            </button>
            <p v-if="errorMsg" class="err">{{ errorMsg }}</p>
          </div>
          <p v-else class="closed-notice">This ticket is closed. An admin can reopen it if you still need help.</p>
        </template>
      </template>
    </div>

    <Footer />
  </main>
</template>

<script setup>
import { ref, computed, onMounted, h } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { storeToRefs } from 'pinia'
import { useUserStore } from '../store/user'
import { forumAPI } from '../api/forum'
import { renderMarkdown } from '../utils/markdown'
import { botDeepLink } from '../config'
import Header from '../components/Header.vue'
import Footer from '../components/Footer.vue'
import Pagination from '../components/Pagination.vue'
import MarkdownComposer from '../components/MarkdownComposer.vue'

const LoungeIcon = {
  render: () => h('svg', { viewBox: '0 0 24 24', width: 24, height: 24, fill: 'none' }, [
    h('path', { d: 'M4 8h14l-3.5-3.5M20 16H6l3.5 3.5', stroke: 'var(--accent)', 'stroke-width': 1.6, 'stroke-linecap': 'round', 'stroke-linejoin': 'round' }),
  ]),
}

// ── Small premium-styled utility icons (no emoji anywhere in the UI) ──
const PinIcon = {
  props: { size: { type: Number, default: 13 } },
  render() {
    return h('svg', { viewBox: '0 0 24 24', width: this.size, height: this.size, fill: 'none', style: { flexShrink: 0 } }, [
      h('path', { d: 'M9 4h6l-.7 5.6L18 13v2h-5.2L12 22l-.8-7H6v-2l3.7-3.4L9 4z', fill: 'currentColor' }),
    ])
  },
}
const TrashIcon = {
  props: { size: { type: Number, default: 13 } },
  render() {
    return h('svg', { viewBox: '0 0 24 24', width: this.size, height: this.size, fill: 'none', style: { flexShrink: 0 } }, [
      h('path', {
        d: 'M5 7h14M9 7V5a1 1 0 011-1h4a1 1 0 011 1v2m-8 0 1 13a1 1 0 001 1h6a1 1 0 001-1l1-13',
        stroke: 'currentColor', 'stroke-width': 1.6, 'stroke-linecap': 'round', 'stroke-linejoin': 'round',
      }),
      h('path', { d: 'M10 11v6M14 11v6', stroke: 'currentColor', 'stroke-width': 1.6, 'stroke-linecap': 'round' }),
    ])
  },
}
const EditIcon = {
  props: { size: { type: Number, default: 13 } },
  render() {
    return h('svg', { viewBox: '0 0 24 24', width: this.size, height: this.size, fill: 'none', style: { flexShrink: 0 } }, [
      h('path', {
        d: 'M16.5 3.5a2.1 2.1 0 013 3L7 19l-4 1 1-4L16.5 3.5z',
        stroke: 'currentColor', 'stroke-width': 1.6, 'stroke-linejoin': 'round', 'stroke-linecap': 'round',
      }),
    ])
  },
}
const StarIcon = {
  props: { size: { type: Number, default: 9 } },
  render() {
    return h('svg', { viewBox: '0 0 24 24', width: this.size, height: this.size, fill: 'currentColor', style: { flexShrink: 0 } }, [
      h('path', { d: 'M12 2.5l2.9 6 6.6.7-4.9 4.5 1.3 6.5L12 16.9l-5.9 3.3 1.3-6.5-4.9-4.5 6.6-.7L12 2.5z' }),
    ])
  },
}
const WatchIcon = {
  props: { size: { type: Number, default: 13 } },
  render() {
    return h('svg', { viewBox: '0 0 24 24', width: this.size, height: this.size, fill: 'none', style: { flexShrink: 0 } }, [
      h('path', { d: 'M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7-10-7-10-7z', stroke: 'currentColor', 'stroke-width': 1.6, 'stroke-linejoin': 'round' }),
      h('circle', { cx: 12, cy: 12, r: 3, stroke: 'currentColor', 'stroke-width': 1.6 }),
    ])
  },
}
const ShareIcon = {
  props: { size: { type: Number, default: 13 } },
  render() {
    return h('svg', { viewBox: '0 0 24 24', width: this.size, height: this.size, fill: 'none', style: { flexShrink: 0 } }, [
      h('circle', { cx: 18, cy: 5, r: 2.4, stroke: 'currentColor', 'stroke-width': 1.6 }),
      h('circle', { cx: 6, cy: 12, r: 2.4, stroke: 'currentColor', 'stroke-width': 1.6 }),
      h('circle', { cx: 18, cy: 19, r: 2.4, stroke: 'currentColor', 'stroke-width': 1.6 }),
      h('path', { d: 'M8.1 10.8l7.8-4.2M8.1 13.2l7.8 4.2', stroke: 'currentColor', 'stroke-width': 1.6, 'stroke-linecap': 'round' }),
    ])
  },
}
const LockIcon = {
  props: { size: { type: Number, default: 13 } },
  render() {
    return h('svg', { viewBox: '0 0 24 24', width: this.size, height: this.size, fill: 'none', style: { flexShrink: 0 } }, [
      h('rect', { x: 5, y: 11, width: 14, height: 9, rx: 2, stroke: 'currentColor', 'stroke-width': 1.6 }),
      h('path', { d: 'M8 11V8a4 4 0 018 0v3', stroke: 'currentColor', 'stroke-width': 1.6, 'stroke-linecap': 'round' }),
    ])
  },
}
const ReplyIcon = {
  props: { size: { type: Number, default: 13 } },
  render() {
    return h('svg', { viewBox: '0 0 24 24', width: this.size, height: this.size, fill: 'none', style: { flexShrink: 0 } }, [
      h('path', { d: 'M9 6L3 12l6 6M3 12h11a6 6 0 016 6v1', stroke: 'currentColor', 'stroke-width': 1.6, 'stroke-linecap': 'round', 'stroke-linejoin': 'round' }),
    ])
  },
}

const SupportIcon = {
  render: () => h('svg', { viewBox: '0 0 24 24', width: 24, height: 24, fill: 'none' }, [
    h('path', { d: 'M12 4a5 5 0 015 5c0 2.5-2 3.5-3 4.5s-1 1.5-1 2.5', stroke: 'var(--accent)', 'stroke-width': 1.6, 'stroke-linecap': 'round' }),
    h('circle', { cx: 12, cy: 19, r: 1.2, fill: 'var(--accent)' }),
  ]),
}

// Generated avatar — no photo storage on the backend, so every author gets
// a deterministic colored circle (hashed from their username) with their
// initial, plus a gold ring + star badge for admins.
function hashHue(str) {
  let hash = 0
  for (let i = 0; i < str.length; i++) hash = str.charCodeAt(i) + ((hash << 5) - hash)
  return Math.abs(hash) % 360
}
const Avatar = {
  props: {
    username: { type: String, default: null },
    avatarUrl: { type: String, default: null },
    isAdmin: { type: Boolean, default: false },
    size: { type: Number, default: 36 },
  },
  render() {
    const label = this.username || '?'
    const hue = hashHue(label)
    if (this.avatarUrl) {
      return h('div', {
        class: ['forum-avatar', { 'forum-avatar-admin': this.isAdmin }],
        style: { width: `${this.size}px`, height: `${this.size}px`, background: 'none' },
      }, [
        h('img', { src: this.avatarUrl, alt: '', class: 'forum-avatar-img' }),
        this.isAdmin ? h('span', { class: 'forum-avatar-badge' }, [h(StarIcon, { size: 8 })]) : null,
      ])
    }
    return h('div', {
      class: ['forum-avatar', { 'forum-avatar-admin': this.isAdmin }],
      style: {
        width: `${this.size}px`, height: `${this.size}px`,
        background: `linear-gradient(160deg, hsl(${hue},65%,48%), hsl(${hue},65%,30%))`,
        fontSize: `${Math.round(this.size * 0.42)}px`,
      },
    }, [
      h('span', label.charAt(0).toUpperCase()),
      this.isAdmin ? h('span', { class: 'forum-avatar-badge' }, [h(StarIcon, { size: 8 })]) : null,
    ])
  },
}

// One thread-list row — a separate render-function component (not a
// template partial) purely so the pin/delete icon buttons can
// event.stopPropagation() cleanly without fighting the row's own click.
const ThreadRow = {
  props: { thread: Object, canPin: Boolean, canModify: Boolean },
  emits: ['open', 'toggle-pin', 'remove'],
  render() {
    const t = this.thread
    const actions = []
    if (this.canPin) {
      actions.push(h('button', {
        class: 'icon-btn small', title: t.is_pinned ? 'Unpin' : 'Pin',
        onClick: (e) => { e.stopPropagation(); this.$emit('toggle-pin') },
      }, [h(PinIcon, { size: 11 })]))
    }
    if (this.canModify) {
      actions.push(h('button', {
        class: 'icon-btn small danger', title: 'Delete',
        onClick: (e) => { e.stopPropagation(); this.$emit('remove') },
      }, [h(TrashIcon, { size: 11 })]))
    }
    return h('button', { class: ['thread-row', { pinned: t.is_pinned, closed: t.is_closed }], onClick: () => this.$emit('open') }, [
      h(Avatar, { username: t.author_username, avatarUrl: t.author_avatar_url, isAdmin: t.author_is_admin, size: 38 }),
      h('div', { class: 'thread-row-main' }, [
        h('h4', [
          t.is_pinned ? h(PinIcon, { size: 11, class: 'pin-dot' }) : null,
          t.is_closed ? h(LockIcon, { size: 11, class: 'pin-dot' }) : null,
          t.title,
        ]),
        h('span', { class: 'thread-row-meta' },
          `${t.author_username ? '@' + t.author_username + ' · ' : ''}${t.post_count} ${t.post_count === 1 ? 'post' : 'posts'}`),
      ]),
      actions.length ? h('div', { class: 'thread-row-actions' }, actions) : null,
      h('span', { class: 'thread-row-arrow' }, '→'),
    ])
  },
}

const userStore = useUserStore()
const { user, wallet } = storeToRefs(userStore)
const currentUserId = computed(() => user.value?.id)
const isAdmin = computed(() => !!user.value?.is_admin)

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
const pinnedThreads = computed(() => threads.value.filter(t => t.is_pinned))
const otherThreads = computed(() => threads.value.filter(t => !t.is_pinned))

const newThreadOpen = ref(false)
const newThreadTitle = ref('')
const newThreadBody = ref('')

const activeThread = ref(null)
const loadingThread = ref(false)
const replyBody = ref('')
const posting = ref(false)
const errorMsg = ref('')

const titleEditing = ref(false)
const titleDraft = ref('')
const editingPostId = ref(null)
const editingPostBody = ref('')
const replyingTo = ref(null)

const shareOpen = ref(false)
const shareBusy = ref(false)
const shareLinkCopied = ref(false)
const shareLinkUrl = computed(() => activeThread.value?.share_token ? botDeepLink(`thread_${activeThread.value.share_token}`) : '')

const editingCategoryKey = ref(null)
const categoryDraft = ref({ name: '', description: '' })

const route = useRoute()
const router = useRouter()

const backLabel = computed(() => {
  if (view.value === 'thread') return 'Threads'
  if (view.value === 'threads') return 'Forum'
  return 'Home'
})

function onBack() {
  errorMsg.value = ''
  if (view.value === 'thread') { view.value = 'threads'; return }
  if (view.value === 'threads') { view.value = 'categories'; return }
  window.history.length > 1 ? window.history.back() : (window.location.href = '/')
}

function canModifyThread(t) {
  return isAdmin.value || t.author_id === currentUserId.value
}
function canModifyPost(p) {
  return isAdmin.value || p.author_id === currentUserId.value
}
const canModifyActiveThread = computed(() => activeThread.value && canModifyThread(activeThread.value))

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
  titleEditing.value = false
  editingPostId.value = null
  replyingTo.value = null
  shareOpen.value = false
  try {
    activeThread.value = await forumAPI.getThread(id)
  } finally {
    loadingThread.value = false
  }
}

function startReplyTo(post) {
  replyingTo.value = post
  window.scrollTo({ top: document.body.scrollHeight, behavior: 'smooth' })
}

async function submitReply() {
  if (!replyBody.value.trim() || !activeThread.value) return
  posting.value = true
  errorMsg.value = ''
  try {
    activeThread.value = await forumAPI.addPost(activeThread.value.id, replyBody.value.trim(), replyingTo.value?.id ?? null)
    replyBody.value = ''
    replyingTo.value = null
  } catch (e) {
    errorMsg.value = e.response?.data?.detail || 'Could not send the reply.'
  } finally {
    posting.value = false
  }
}

function startEditTitle() {
  titleDraft.value = activeThread.value.title
  titleEditing.value = true
}
async function saveTitle() {
  if (!titleDraft.value.trim()) return
  try {
    activeThread.value = await forumAPI.updateThread(activeThread.value.id, titleDraft.value.trim())
    titleEditing.value = false
  } catch (e) {
    errorMsg.value = e.response?.data?.detail || 'Could not update the title.'
  }
}

async function toggleActiveThreadPin() {
  activeThread.value = await forumAPI.pinThread(activeThread.value.id, !activeThread.value.is_pinned)
}

async function toggleClose() {
  activeThread.value = await forumAPI.closeThread(activeThread.value.id, !activeThread.value.is_closed)
}

async function toggleWatch() {
  const res = await forumAPI.toggleWatch(activeThread.value.id)
  activeThread.value.is_watching = res.is_watching
}

function openShare() {
  shareOpen.value = !shareOpen.value
  shareLinkCopied.value = false
}
async function generateShare() {
  shareBusy.value = true
  try {
    const res = await forumAPI.createShareLink(activeThread.value.id)
    activeThread.value.share_token = res.share_token
  } finally {
    shareBusy.value = false
  }
}
async function revokeShare() {
  await forumAPI.revokeShareLink(activeThread.value.id)
  activeThread.value.share_token = null
}
function copyShareLink() {
  navigator.clipboard.writeText(shareLinkUrl.value).then(() => {
    shareLinkCopied.value = true
    setTimeout(() => { shareLinkCopied.value = false }, 1800)
  }).catch(() => {})
}

function startEditCategory(cat) {
  editingCategoryKey.value = cat.key
  categoryDraft.value = { name: cat.name, description: cat.description }
}
async function saveCategory(cat) {
  if (!categoryDraft.value.name.trim() || !categoryDraft.value.description.trim()) return
  const updated = await forumAPI.updateCategory(cat.key, categoryDraft.value.name.trim(), categoryDraft.value.description.trim())
  Object.assign(cat, updated)
  editingCategoryKey.value = null
}

async function deleteActiveThread() {
  if (!confirm('Delete this thread? This can\'t be undone.')) return
  await forumAPI.deleteThread(activeThread.value.id)
  view.value = 'threads'
  await loadThreads(activeCategory.value.key)
}

async function togglePin(t) {
  const updated = await forumAPI.pinThread(t.id, !t.is_pinned)
  t.is_pinned = updated.is_pinned
}

async function removeThreadRow(t) {
  if (!confirm(`Delete "${t.title}"? This can't be undone.`)) return
  await forumAPI.deleteThread(t.id)
  await loadThreads(activeCategory.value.key)
}

function startEditPost(p) {
  editingPostId.value = p.id
  editingPostBody.value = p.body
}
async function saveEditPost() {
  if (!editingPostBody.value.trim()) return
  try {
    activeThread.value = await forumAPI.updatePost(editingPostId.value, editingPostBody.value.trim())
    editingPostId.value = null
  } catch (e) {
    errorMsg.value = e.response?.data?.detail || 'Could not update the post.'
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

  // Deep link from a Telegram notification (watch/reply) or a shared URL —
  // ?thread=<id> jumps straight to that thread instead of the category list.
  const threadId = route.query.thread
  if (threadId) {
    try {
      const thread = await forumAPI.getThread(threadId)
      activeCategory.value = categories.value.find(c => c.key === thread.category_key) || { key: thread.category_key, name: thread.category_key }
      activeThread.value = thread
      view.value = 'thread'
    } catch (e) {
      // Invalid/inaccessible thread id — fall through to the category list.
    }
    router.replace({ query: {} })
  }
})
</script>

<style scoped>
.forum-page { min-height: 100vh; background: var(--bg); }
.forum-content { max-width: 760px; padding: 32px 20px 140px; }

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
  display: flex; align-items: center; gap: 10px; font-size: 11px; font-weight: 800; letter-spacing: .08em;
  text-transform: uppercase; color: var(--accent); margin-bottom: 6px;
}
.pinned-tag {
  display: inline-flex; align-items: center; gap: 4px;
  font-size: 10px; font-weight: 800; letter-spacing: 0; text-transform: none;
  background: rgba(255,154,0,.14); color: var(--accent); padding: 2px 8px; border-radius: 99px;
}
.pin-dot { color: var(--accent); margin-right: 4px; vertical-align: -1px; }
.closed-tag {
  display: inline-flex; align-items: center; gap: 4px;
  font-size: 10px; font-weight: 800; letter-spacing: 0; text-transform: none;
  background: rgba(235,75,75,.12); color: var(--danger); padding: 2px 8px; border-radius: 99px;
}
.page-head h1 { font-size: clamp(22px, 4vw, 30px); font-weight: 900; color: var(--text); }

.share-box { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; margin-top: 12px; }
.share-link-input { flex: 1; min-width: 180px; margin-bottom: 0; }
.share-hint { font-size: 12px; color: var(--text-dim); margin-top: 10px; }

.loading-row, .empty { padding: 24px; text-align: center; color: var(--text-dim); font-size: 13px; }

/* ── Categories ─────────────────────────────── */
.category-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 16px; }
.category-card {
  position: relative;
  background: linear-gradient(160deg, rgba(255,154,0,0.05), var(--bg-elevated) 55%);
  border: 1px solid var(--line);
  border-radius: var(--radius-lg); padding: 24px; text-align: left;
  cursor: pointer; transition: border-color .2s, transform .2s;
}
.category-card:hover { border-color: rgba(255,154,0,.5); transform: translateY(-2px); }
.category-icon-badge {
  display: flex; align-items: center; justify-content: center;
  width: 46px; height: 46px; border-radius: 12px; margin-bottom: 12px;
  background: rgba(255,154,0,.12); border: 1px solid rgba(255,154,0,.25);
}
.category-card h3 { font-size: 16px; font-weight: 800; color: var(--text); margin-bottom: 6px; }
.category-card p { font-size: 12.5px; color: var(--text-dim); line-height: 1.5; }
.category-arrow { position: absolute; top: 22px; right: 22px; color: var(--text-dim); font-size: 16px; }

.category-card-wrap { position: relative; }
.category-card-wrap .category-card { width: 100%; }
.category-edit-btn { position: absolute; bottom: 12px; right: 12px; }
.category-edit-form {
  margin-top: 10px; background: var(--bg-elevated); border: 1px solid var(--line);
  border-radius: 12px; padding: 14px;
}
.category-edit-form .thread-input:last-of-type { margin-bottom: 0; }

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
  border-radius: 10px; padding: 14px 16px; cursor: pointer; transition: border-color .15s, background .15s;
}
.thread-row:hover { border-color: var(--accent); }
.thread-row.pinned { border-color: rgba(255,154,0,.35); background: rgba(255,154,0,.04); }
.thread-row.closed { opacity: .65; }
.thread-row-main { flex: 1; min-width: 0; }
.thread-row-main h4 {
  font-size: 13.5px; font-weight: 700; color: var(--text); margin-bottom: 4px;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.thread-row-meta { font-size: 11.5px; color: var(--text-dim); }
.thread-row-actions { display: flex; gap: 2px; flex-shrink: 0; }
.thread-row-arrow { color: var(--text-dim); flex-shrink: 0; }

.thread-divider {
  display: flex; align-items: center; gap: 10px; margin: 6px 0;
  font-size: 10.5px; font-weight: 800; letter-spacing: .06em; text-transform: uppercase; color: var(--text-dim);
}
.thread-divider::before, .thread-divider::after { content: ''; flex: 1; height: 1px; background: var(--line); }

.icon-btn {
  background: linear-gradient(160deg, var(--bg-elevated), var(--bg)); border: 1px solid var(--line); color: var(--text-dim);
  width: 30px; height: 30px; border-radius: 8px; font-size: 13px; cursor: pointer;
  display: flex; align-items: center; justify-content: center; flex-shrink: 0;
  box-shadow: 0 2px 6px rgba(0,0,0,.18);
  transition: border-color .15s, color .15s, transform .15s, box-shadow .15s;
}
.icon-btn:hover { border-color: var(--accent); color: var(--accent); box-shadow: 0 4px 14px -4px rgba(255,154,0,.4); transform: translateY(-1px); }
.icon-btn:active { transform: translateY(0); }
.icon-btn.danger:hover { border-color: var(--danger); color: var(--danger); box-shadow: 0 4px 14px -4px rgba(235,75,75,.4); }
.icon-btn.small { width: 26px; height: 26px; font-size: 11px; }
.icon-btn.active { border-color: var(--accent); color: var(--accent); background: rgba(255,154,0,.12); }

.thread-title-row { display: flex; align-items: center; justify-content: space-between; gap: 12px; flex-wrap: wrap; }
.thread-actions { display: flex; gap: 6px; flex-shrink: 0; }
.thread-title-edit { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.thread-title-edit .thread-input { flex: 1; min-width: 160px; margin-bottom: 0; }

.thread-input {
  width: 100%; padding: 10px 12px; margin-bottom: 10px;
  background: var(--bg); border: 1px solid var(--line); border-radius: 9px;
  color: var(--text); font-size: 13.5px; font-family: inherit; resize: vertical;
}
.thread-input:focus { outline: none; border-color: var(--accent); }

.form-actions { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; margin-top: 8px; }
.mini-btn {
  background: linear-gradient(160deg, var(--bg-elevated), var(--bg)); border: 1px solid var(--line); color: var(--text-dim);
  padding: 8px 14px; border-radius: 7px; font-size: 12.5px; font-weight: 700; cursor: pointer;
  box-shadow: 0 2px 6px rgba(0,0,0,.18);
  transition: border-color .15s, color .15s, transform .15s, box-shadow .15s;
}
.mini-btn:hover { border-color: var(--accent); color: var(--accent); box-shadow: 0 4px 14px -4px rgba(255,154,0,.4); transform: translateY(-1px); }
.mini-btn:active { transform: translateY(0); }
.mini-btn.danger:hover { border-color: var(--danger); color: var(--danger); box-shadow: 0 4px 14px -4px rgba(235,75,75,.4); }
.link-btn { background: none; border: none; color: var(--accent); font-size: 12px; font-weight: 700; cursor: pointer; text-decoration: underline; padding: 0; margin-left: 6px; }
.err { color: var(--danger); font-size: 12.5px; font-weight: 600; margin: 8px 0 0; width: 100%; }

/* ── Thread detail ─────────────────────────────── */
.post-list { display: flex; flex-direction: column; gap: 10px; margin-bottom: 16px; }
.post-card {
  display: flex; gap: 14px;
  background: var(--bg-elevated); border: 1px solid var(--line);
  border-radius: 12px; padding: 14px 16px;
}
.post-card.mine { border-color: rgba(255,154,0,.35); background: rgba(255,154,0,.05); }
.post-card.staff { border-left: 3px solid var(--accent); }

/* Forum-style left sidebar: avatar, username, role — arizona-rp layout */
.post-sidebar {
  display: flex; flex-direction: column; align-items: center; gap: 4px;
  width: 76px; flex-shrink: 0; text-align: center;
}
.post-username { font-size: 11px; font-weight: 700; color: var(--text); word-break: break-word; }
.post-role { font-size: 9.5px; font-weight: 800; letter-spacing: .04em; text-transform: uppercase; color: var(--text-dim); }
.post-role.admin { color: var(--accent); }

.post-main { flex: 1; min-width: 0; }
.post-head { display: flex; align-items: center; justify-content: flex-end; gap: 8px; margin-bottom: 6px; }
.post-time { font-size: 11px; color: var(--text-dim); margin-right: auto; }
.post-body { font-size: 13.5px; color: var(--text); line-height: 1.6; white-space: pre-wrap; }
.post-body :deep(.md-img) { max-width: 100%; border-radius: 8px; margin: 6px 0; display: block; }
.post-body :deep(a) { color: var(--accent); }
.post-body :deep(code) { background: var(--bg); padding: 1px 5px; border-radius: 4px; font-size: 12px; }

.post-quote {
  font-size: 12px; color: var(--text-dim); line-height: 1.5;
  background: var(--bg); border-left: 2px solid var(--accent);
  border-radius: 6px; padding: 6px 10px; margin-bottom: 8px;
}
.post-quote-author { color: var(--accent); font-weight: 700; margin-right: 4px; }

.closed-notice {
  font-size: 12.5px; color: var(--text-dim); text-align: center;
  background: var(--bg-elevated); border: 1px dashed var(--line);
  border-radius: var(--radius-lg); padding: 16px;
}

.reply-box {
  background: var(--bg-elevated); border: 1px solid var(--line);
  border-radius: var(--radius-lg); padding: 16px;
}
.replying-banner {
  display: flex; align-items: center; gap: 4px; font-size: 12px; color: var(--text-dim);
  background: var(--bg); border-radius: 8px; padding: 8px 12px; margin-bottom: 10px;
}
.reply-box-row { display: flex; gap: 12px; align-items: flex-start; }
.reply-box-row :deep(.md-composer) { flex: 1; min-width: 0; }
.reply-btn { width: 100%; padding: 11px; margin-top: 10px; }

/* ── Generated avatar ─────────────────────────────── */
.forum-avatar {
  position: relative; flex-shrink: 0; border-radius: 50%; overflow: hidden;
  display: flex; align-items: center; justify-content: center;
  color: #fff; font-weight: 800; text-shadow: 0 1px 2px rgba(0,0,0,.35);
  user-select: none;
}
.forum-avatar-img { width: 100%; height: 100%; object-fit: cover; }
.forum-avatar-admin { box-shadow: 0 0 0 2px var(--accent); }
.forum-avatar-badge {
  position: absolute; bottom: -2px; right: -2px;
  width: 16px; height: 16px; border-radius: 50%;
  background: var(--accent); color: #14140f;
  display: flex; align-items: center; justify-content: center;
  font-size: 9px; line-height: 1; border: 2px solid var(--bg-elevated);
}
</style>
