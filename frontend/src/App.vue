<template>
  <div id="app">
    <div v-if="isPublicRoute">
      <router-view />
    </div>

    <div v-else-if="isLoading" class="splash">
      <div class="splash-logo">SM</div>
      <div class="splash-bar"><div class="splash-fill"></div></div>
    </div>

    <div v-else-if="error" class="error-screen">
      <span>⚠️ {{ error }}</span>
    </div>

    <router-view v-else />
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { storeToRefs } from 'pinia'
import { useUserStore } from './store/user'

const userStore = useUserStore()
const { isLoading, error } = storeToRefs(userStore)

// Terms/Privacy need to work as plain links outside Telegram entirely —
// a payment processor, an app-store reviewer, or a player who wants to
// read them before opening the Mini App can't do that if they're stuck
// behind the same "open this from the Telegram bot" gate as the rest of
// the app, which requires real Telegram initData to even render. Reads
// the raw URL rather than vue-router's resolved route: the router hasn't
// necessarily finished resolving the initial navigation yet at the point
// App.vue mounts, but the path in the address bar is available
// immediately, with no race.
const PUBLIC_PATHS = new Set(['/terms', '/privacy'])
const isPublicRoute = ref(PUBLIC_PATHS.has(window.location.pathname))

onMounted(async () => {
  if (isPublicRoute.value) return
  const urlParams = new URLSearchParams(window.location.search)
  const ref = urlParams.get('ref') || window?.Telegram?.WebApp?.initDataUnsafe?.start_param || null
  await userStore.initSession(ref)
})
</script>

<style scoped>
.splash {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  gap: 28px;
}
.splash-logo {
  font-size: 48px;
  font-weight: 900;
  letter-spacing: -2px;
  background: linear-gradient(90deg, var(--accent), var(--accent-2));
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
  animation: breathe 1.8s ease-in-out infinite;
}
@keyframes breathe {
  0%,100% { opacity:1; transform: scale(1); }
  50%      { opacity:.6; transform: scale(.95); }
}
.splash-bar {
  width: 140px;
  height: 3px;
  background: var(--line);
  border-radius: 99px;
  overflow: hidden;
}
.splash-fill {
  height: 100%;
  background: linear-gradient(90deg, var(--accent), var(--accent-2));
  border-radius: 99px;
  animation: load 1.4s ease-in-out infinite;
}
@keyframes load {
  0%   { width:0%;   margin-left:0; }
  50%  { width:70%;  margin-left:0; }
  100% { width:0%;   margin-left:100%; }
}

.error-screen {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  color: #ff5050;
  font-size: 16px;
  font-weight: 600;
  padding: 24px;
  text-align: center;
}
</style>