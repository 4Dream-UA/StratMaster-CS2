<template>
  <main class="shared-thread-page">
    <Header />

    <div class="wrap shared-thread-content">
      <div v-if="loading" class="loader-row">
        <div class="spinner"></div>
      </div>

      <div v-else-if="error" class="error-card">
        <h1>Link not found</h1>
        <p>{{ error }}</p>
        <router-link to="/" class="btn-primary">Go home</router-link>
      </div>

      <template v-else>
        <section class="page-header">
          <span class="eyebrow">Shared thread</span>
          <h1>{{ thread.title }}</h1>
        </section>

        <div class="post-list">
          <div v-for="p in thread.posts" :key="p.id" class="post-card" :class="{ staff: p.author_is_admin }">
            <div class="post-sidebar">
              <Avatar :username="p.author_username" :avatar-url="p.author_avatar_url" :is-admin="p.author_is_admin" :size="46" />
              <span class="post-username">{{ p.author_username ? '@' + p.author_username : 'Player' }}</span>
            </div>
            <div class="post-main">
              <div class="post-head"><span class="post-time">{{ formatTime(p.created_at) }}</span></div>
              <div class="post-body" v-html="renderMarkdown(p.body)"></div>
            </div>
          </div>
        </div>

        <div class="cta-row">
          <p>Want to join the conversation?</p>
          <router-link to="/pricing" class="btn-primary">Get Premium Access</router-link>
        </div>
      </template>
    </div>

    <Footer />
  </main>
</template>

<script setup>
import { ref, onMounted, h } from 'vue'
import { useRoute } from 'vue-router'
import { forumAPI } from '../api/forum'
import { renderMarkdown } from '../utils/markdown'
import Header from '../components/Header.vue'
import Footer from '../components/Footer.vue'

function hashHue(str) {
  let hash = 0
  for (let i = 0; i < str.length; i++) hash = str.charCodeAt(i) + ((hash << 5) - hash)
  return Math.abs(hash) % 360
}
const Avatar = {
  props: {
    username: { type: String, default: null }, avatarUrl: { type: String, default: null },
    isAdmin: { type: Boolean, default: false }, size: { type: Number, default: 36 },
  },
  render() {
    const label = this.username || '?'
    const hue = hashHue(label)
    if (this.avatarUrl) {
      return h('div', {
        class: ['thread-avatar', { 'thread-avatar-admin': this.isAdmin }],
        style: { width: `${this.size}px`, height: `${this.size}px`, background: 'none' },
      }, [h('img', { src: this.avatarUrl, alt: '', class: 'thread-avatar-img' })])
    }
    return h('div', {
      class: ['thread-avatar', { 'thread-avatar-admin': this.isAdmin }],
      style: {
        width: `${this.size}px`, height: `${this.size}px`,
        background: `linear-gradient(160deg, hsl(${hue},65%,48%), hsl(${hue},65%,30%))`,
        fontSize: `${Math.round(this.size * 0.42)}px`,
      },
    }, [h('span', label.charAt(0).toUpperCase())])
  },
}

const route = useRoute()
const thread = ref(null)
const loading = ref(true)
const error = ref('')

function formatTime(iso) {
  const d = new Date(iso)
  return d.toLocaleString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
}

onMounted(async () => {
  window.scrollTo({ top: 0, behavior: 'auto' })
  try {
    thread.value = await forumAPI.getShared(route.params.token)
  } catch (e) {
    error.value = e.response?.data?.detail || 'This share link is invalid or was revoked.'
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.shared-thread-page { min-height: 100vh; background: var(--bg); }
.shared-thread-content { padding: 28px 20px 100px; max-width: 760px; }

.loader-row { display: flex; justify-content: center; padding: 80px 0; }
.spinner {
  width: 32px; height: 32px; border: 2.5px solid var(--line);
  border-top-color: var(--accent); border-radius: 50%; animation: spin .8s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

.error-card { text-align: center; padding: 60px 20px; }
.error-card h1 { font-size: 22px; font-weight: 900; color: var(--text); margin-bottom: 8px; }
.error-card p { font-size: 13.5px; color: var(--text-dim); margin-bottom: 20px; }
.error-card .btn-primary { text-decoration: none; display: inline-block; }

.page-header { margin-bottom: 20px; }
.eyebrow {
  display: block; font-size: 11px; font-weight: 800; letter-spacing: .08em;
  text-transform: uppercase; color: var(--accent); margin-bottom: 6px;
}
.page-header h1 { font-size: clamp(22px, 4vw, 30px); font-weight: 900; color: var(--text); }

.post-list { display: flex; flex-direction: column; gap: 10px; margin-bottom: 16px; }
.post-card {
  display: flex; gap: 14px;
  background: var(--bg-elevated); border: 1px solid var(--line);
  border-radius: 12px; padding: 14px 16px;
}
.post-card.staff { border-left: 3px solid var(--accent); }
.post-sidebar { display: flex; flex-direction: column; align-items: center; gap: 4px; width: 76px; flex-shrink: 0; text-align: center; }
.post-username { font-size: 11px; font-weight: 700; color: var(--text); word-break: break-word; }
.post-main { flex: 1; min-width: 0; }
.post-head { margin-bottom: 6px; }
.post-time { font-size: 11px; color: var(--text-dim); }
.post-body { font-size: 13.5px; color: var(--text); line-height: 1.6; white-space: pre-wrap; }
.post-body :deep(.md-img) { max-width: 100%; border-radius: 8px; margin: 6px 0; display: block; }
.post-body :deep(a) { color: var(--accent); }
.post-body :deep(code) { background: var(--bg); padding: 1px 5px; border-radius: 4px; font-size: 12px; }

.thread-avatar {
  position: relative; flex-shrink: 0; border-radius: 50%; overflow: hidden;
  display: flex; align-items: center; justify-content: center;
  color: #fff; font-weight: 800; text-shadow: 0 1px 2px rgba(0,0,0,.35); user-select: none;
}
.thread-avatar-img { width: 100%; height: 100%; object-fit: cover; }
.thread-avatar-admin { box-shadow: 0 0 0 2px var(--accent); }

.cta-row {
  margin-top: 28px; display: flex; align-items: center; justify-content: space-between;
  gap: 14px; flex-wrap: wrap; background: var(--bg-elevated); border: 1px solid var(--line);
  border-radius: var(--radius-lg); padding: 18px 20px;
}
.cta-row p { font-size: 13.5px; color: var(--text-dim); }
.cta-row .btn-primary { text-decoration: none; }
</style>
