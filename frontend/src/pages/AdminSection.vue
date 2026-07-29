<template>
  <main class="section-page">
    <Header />

    <div class="wrap section-content">

      <button class="back-btn" @click="router.push('/admin')">
        <svg viewBox="0 0 16 16" fill="none" width="14" height="14">
          <path d="M10 3L5 8l5 5" stroke="currentColor" stroke-width="2"
                stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
        Admin Panel
      </button>

      <div class="placeholder-card">
        <span class="placeholder-icon" v-html="icon"></span>
        <h1>{{ title }}</h1>
        <p>This tool is under construction and will be available in the next release.</p>
      </div>

    </div>

    <Footer />
  </main>
</template>

<script setup>
import { computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { storeToRefs } from 'pinia'
import { useUserStore } from '../store/user'
import Header from '../components/Header.vue'
import Footer from '../components/Footer.vue'

const route  = useRoute()
const router = useRouter()
const userStore = useUserStore()
const { user } = storeToRefs(userStore)

const ICON_MAP = `<svg viewBox="0 0 24 24" fill="none" width="32" height="32"><path d="M9 4L4 6v14l5-2 6 2 5-2V4l-5 2-6-2z" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/><path d="M9 4v14M15 6v14" stroke="currentColor" stroke-width="1.5"/></svg>`
const ICON_TARGET = `<svg viewBox="0 0 24 24" fill="none" width="32" height="32"><circle cx="12" cy="12" r="8" stroke="currentColor" stroke-width="1.5"/><circle cx="12" cy="12" r="4.5" stroke="currentColor" stroke-width="1.5"/><circle cx="12" cy="12" r="1" fill="currentColor"/></svg>`
const ICON_USERS = `<svg viewBox="0 0 24 24" fill="none" width="32" height="32"><circle cx="9" cy="8" r="3" stroke="currentColor" stroke-width="1.5"/><path d="M3 20c0-3.3 2.7-6 6-6s6 2.7 6 6" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/><circle cx="17" cy="9" r="2.5" stroke="currentColor" stroke-width="1.3"/><path d="M15.5 14.2c2.5.4 4.5 2.6 4.5 5.3" stroke="currentColor" stroke-width="1.3" stroke-linecap="round"/></svg>`
const ICON_P2P = `<svg viewBox="0 0 24 24" fill="none" width="32" height="32"><rect x="2" y="7" width="20" height="12" rx="2" stroke="currentColor" stroke-width="1.5"/><circle cx="12" cy="13" r="3" stroke="currentColor" stroke-width="1.5"/><path d="M6 7V6a2 2 0 012-2h8a2 2 0 012 2v1" stroke="currentColor" stroke-width="1.3"/></svg>`
const ICON_TOOL = `<svg viewBox="0 0 24 24" fill="none" width="32" height="32"><path d="M14.7 6.3a4 4 0 00-5.4 4.6L4 16.2V20h3.8l5.3-5.3a4 4 0 004.6-5.4l-2.6 2.6-2-2 2.6-2.6z" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round" stroke-linecap="round"/></svg>`

const MAP = {
  maps:       { title: 'Work with Maps',       icon: ICON_MAP },
  strategies: { title: 'Work with Strategies',  icon: ICON_TARGET },
  users:      { title: 'Work with Users',       icon: ICON_USERS },
  p2p:        { title: 'Check P2P',             icon: ICON_P2P },
}

const key   = route.meta.sectionKey
const title = computed(() => MAP[key]?.title ?? 'Admin Tool')
const icon  = computed(() => MAP[key]?.icon ?? ICON_TOOL)

onMounted(() => {
  if (!user.value?.is_admin) router.replace('/user')
})
</script>

<style scoped>
.section-page { min-height: 100vh; background: var(--bg); }
.section-content { max-width: 760px; padding: 32px 20px 120px; }

.back-btn {
  display: inline-flex; align-items: center; gap: 6px;
  background: var(--bg-elevated); border: 1px solid var(--line);
  color: var(--text-dim); padding: 8px 16px; border-radius: 8px;
  font-size: 13px; font-weight: 600; cursor: pointer;
  transition: border-color .2s, color .2s;
  margin-bottom: 40px;
}
.back-btn:hover { border-color: var(--accent); color: var(--accent); }

.placeholder-card {
  text-align: center;
  padding: 64px 32px;
  background: var(--bg-elevated);
  border: 1px dashed var(--line);
  border-radius: var(--radius-lg);
}
.placeholder-icon {
  display: flex; justify-content: center;
  color: var(--text-dim);
  margin-bottom: 16px;
}
.placeholder-card h1 { font-size: 22px; font-weight: 800; color: var(--text); margin-bottom: 10px; }
.placeholder-card p { font-size: 14px; color: var(--text-dim); }
</style>