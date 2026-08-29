<template>
  <main class="shared-board-page">
    <Header />

    <div class="wrap shared-board-content">
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
          <span class="eyebrow">Shared board</span>
          <h1>{{ board.title }}</h1>
          <p class="page-sub">{{ board.map_name }} — shared by a StratMaster player</p>
        </section>

        <div v-if="!board.map_cover_image_url" class="no-image">
          This board's map has no cover image set yet.
        </div>
        <TacticsPlayer
          v-else
          :image-url="board.map_cover_image_url"
          :grenades="board.grenades"
          :player-paths="board.paths"
          :annotations="board.annotations"
        />

        <div class="cta-row">
          <p>Want your own tactics board?</p>
          <router-link to="/pricing" class="btn-primary">Get Premium Access</router-link>
        </div>
      </template>
    </div>

    <Footer />
  </main>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { boardsAPI } from '../api/boards'
import Header from '../components/Header.vue'
import Footer from '../components/Footer.vue'
import TacticsPlayer from '../components/TacticsPlayer.vue'

const route = useRoute()
const board = ref(null)
const loading = ref(true)
const error = ref('')

onMounted(async () => {
  window.scrollTo({ top: 0, behavior: 'auto' })
  try {
    board.value = await boardsAPI.getShared(route.params.token)
  } catch (e) {
    error.value = e.response?.data?.detail || 'This share link is invalid or was revoked.'
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.shared-board-page { min-height: 100vh; background: var(--bg); }
.shared-board-content { padding: 28px 20px 100px; max-width: 900px; }

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
.page-header h1 { font-size: clamp(24px, 5vw, 36px); font-weight: 900; color: var(--text); line-height: 1.1; }
.page-sub { font-size: 13px; color: var(--text-dim); margin-top: 6px; }

.no-image {
  font-size: 13px; color: var(--text-dim); background: var(--bg-elevated);
  border: 1px dashed var(--line); border-radius: 12px; padding: 24px; text-align: center;
}

.cta-row {
  margin-top: 28px; display: flex; align-items: center; justify-content: space-between;
  gap: 14px; flex-wrap: wrap; background: var(--bg-elevated); border: 1px solid var(--line);
  border-radius: var(--radius-lg); padding: 18px 20px;
}
.cta-row p { font-size: 13.5px; color: var(--text-dim); }
.cta-row .btn-primary { text-decoration: none; }
</style>
