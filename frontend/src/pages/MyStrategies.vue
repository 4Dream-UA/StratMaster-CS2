<template>
  <main class="my-strategies-page">
    <Header />

    <div class="wrap my-strategies-content">
      <section class="page-header">
        <button class="back-btn" @click="router.push('/')">
          <svg viewBox="0 0 16 16" fill="none" width="14" height="14">
            <path d="M10 3L5 8l5 5" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
          Home
        </button>
        <h1>My <span class="accent">Strategies</span></h1>
        <p class="page-sub">Strategies you've starred — tap the star on any strategy page to pin it here.</p>
      </section>

      <div v-if="isLoading" class="loader-row">
        <div class="spinner"></div>
      </div>

      <div v-else-if="!strategies.length" class="no-results">
        <p>No favorite strategies yet.</p>
        <router-link to="/#strategies" class="btn-primary empty-cta">Browse strategies</router-link>
      </div>

      <div v-else class="strategies-grid">
        <div
          v-for="s in strategies" :key="s.id" class="strategy-card"
          @click="router.push('/strategy/' + s.id)"
        >
          <div class="card-thumb">
            <img v-if="s.main_image_url" :src="s.main_image_url" :alt="s.title" class="card-img"/>
            <div v-else class="card-placeholder"><span>{{ s.title.charAt(0) }}</span></div>
            <div class="card-overlay"></div>
            <div class="card-badges">
              <span class="badge badge-side">{{ s.side === 'T_side' ? 'T' : 'CT' }}</span>
              <span class="badge badge-plant">{{ s.plant }}</span>
            </div>
            <span class="badge-access" :class="s.is_free ? 'free' : 'premium'">
              {{ s.is_free ? 'Free' : 'Premium' }}
            </span>
            <button
              type="button" class="unfav-btn"
              @click.stop="unfavorite(s.id)"
              aria-label="Remove from favorites"
            >
              <svg viewBox="0 0 20 20" fill="currentColor" width="15" height="15">
                <path d="M10 2.5l2.35 4.76 5.25.76-3.8 3.7.9 5.23L10 14.5l-4.7 2.45.9-5.23-3.8-3.7 5.25-.76z"/>
              </svg>
            </button>
          </div>

          <div class="card-body">
            <h3>{{ s.title }}</h3>
            <div class="card-meta">
              <span class="stars">
                <span v-for="i in 5" :key="i" class="star" :class="{ on: i <= s.difficulty_stars }">★</span>
              </span>
              <span class="meta-divider" aria-hidden="true"></span>
              <span class="win-rate">{{ s.success_rate }}% win rate</span>
            </div>
            <p class="card-link">View strategy →</p>
          </div>
        </div>
      </div>
    </div>

    <Footer />
  </main>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { favoritesAPI } from '../api/favorites'
import Header from '../components/Header.vue'
import Footer from '../components/Footer.vue'

const router = useRouter()
const strategies = ref([])
const isLoading = ref(true)

async function load() {
  isLoading.value = true
  try {
    strategies.value = await favoritesAPI.listStrategies()
  } catch (e) {
    console.error('[MyStrategies] failed to load:', e)
  } finally {
    isLoading.value = false
  }
}

async function unfavorite(id) {
  strategies.value = strategies.value.filter(s => s.id !== id)
  try {
    await favoritesAPI.removeStrategy(id)
  } catch (e) {
    await load() // out of sync — resync from the server
  }
}

onMounted(() => {
  window.scrollTo({ top: 0, behavior: 'auto' })
  load()
})
</script>

<style scoped>
.my-strategies-page { min-height: 100vh; background: var(--bg); }
.my-strategies-content { padding: 28px 20px 100px; }

.page-header { margin-bottom: 28px; }
.back-btn {
  display: inline-flex; align-items: center; gap: 6px;
  background: var(--bg-elevated); border: 1px solid var(--line);
  color: var(--text-dim); padding: 8px 16px; border-radius: 8px;
  font-size: 13px; font-weight: 600; cursor: pointer;
  transition: border-color .2s, color .2s; margin-bottom: 20px;
}
.back-btn:hover { border-color: var(--accent); color: var(--accent); }
.page-header h1 {
  font-size: clamp(28px, 6vw, 44px); font-weight: 900;
  letter-spacing: -.02em; line-height: 1.1; color: var(--text); margin-bottom: 8px;
}
.accent { color: var(--accent); }
.page-sub { font-size: 14px; color: var(--text-dim); }

.loader-row { display: flex; justify-content: center; padding: 60px 0; }
.spinner {
  width: 32px; height: 32px; border: 2.5px solid var(--line);
  border-top-color: var(--accent); border-radius: 50%; animation: spin .8s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

.no-results {
  text-align: center; padding: 60px 20px; color: var(--text-dim); font-size: 15px;
  display: flex; flex-direction: column; align-items: center; gap: 18px;
}
.empty-cta { text-decoration: none; }

.strategies-grid {
  display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 20px;
}
.strategy-card {
  background: var(--bg-elevated); border: 1px solid var(--line);
  border-radius: 16px; overflow: hidden; cursor: pointer;
  transition: border-color .25s, transform .25s, box-shadow .25s;
}
@media (hover: hover) and (pointer: fine) {
  .strategy-card:hover {
    border-color: rgba(255,154,0,.5); transform: translateY(-4px);
    box-shadow: 0 8px 24px rgba(255,154,0,.12);
  }
}

.card-thumb { position: relative; aspect-ratio: 16/10; overflow: hidden; background: var(--bg-elevated-2, #25272b); }
.card-img { width: 100%; height: 100%; object-fit: cover; display: block; }
.card-placeholder {
  width: 100%; height: 100%; display: flex; align-items: center; justify-content: center;
  font-size: 52px; font-weight: 900; color: rgba(255,154,0,.25);
}
.card-overlay { position: absolute; inset: 0; background: linear-gradient(to top, rgba(0,0,0,.65) 0%, transparent 55%); }

.card-badges { position: absolute; top: 10px; left: 10px; display: flex; gap: 6px; z-index: 2; }
.badge { padding: 3px 9px; border-radius: 6px; font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: .04em; }
.badge-side { background: rgba(0,0,0,.72); color: #fff; backdrop-filter: blur(4px); }
.badge-plant { background: rgba(0,0,0,.55); color: #fff; backdrop-filter: blur(4px); }

.badge-access {
  position: absolute; bottom: 10px; left: 10px;
  padding: 3px 10px; border-radius: 99px; font-size: 10px; font-weight: 800;
  text-transform: uppercase; letter-spacing: .05em; z-index: 2;
}
.badge-access.free { background: rgba(80,220,100,.2); color: #50dc64; border: 1px solid rgba(80,220,100,.4); }
.badge-access.premium { background: rgba(255,154,0,.2); color: var(--accent); border: 1px solid rgba(255,154,0,.4); }

.unfav-btn {
  position: absolute; top: 10px; right: 10px; z-index: 3;
  width: 30px; height: 30px; border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  background: rgba(255,154,0,.22); backdrop-filter: blur(4px);
  border: 1px solid rgba(255,154,0,.4); color: var(--accent);
  cursor: pointer; transition: background .15s, color .15s;
}
.unfav-btn:hover { background: rgba(255,80,80,.2); border-color: rgba(255,80,80,.4); color: var(--danger); }

.card-body { padding: 16px 18px 20px; }
.card-body h3 { font-size: 16px; font-weight: 700; letter-spacing: -.01em; color: var(--text); margin-bottom: 10px; line-height: 1.35; }
.card-meta { display: flex; align-items: center; gap: 10px; margin-bottom: 8px; }
.meta-divider { width: 1px; height: 12px; background: var(--line); flex-shrink: 0; }
.stars { display: flex; gap: 2px; }
.star { font-size: 13px; color: var(--line); }
.star.on { color: var(--accent); }
.win-rate { font-size: 12px; color: var(--text-dim); }
.card-link { font-size: 13px; font-weight: 600; color: var(--accent); }
</style>
