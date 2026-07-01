<template>
  <header class="header" :class="{ scrolled: isScrolled }">
    <div class="wrap header-inner">
      <div class="header-logo">
        <img src="../assets/logo.png" alt="StratMaster CS2" class="logo-img" />
      </div>
      <nav class="header-nav">
        <a href="#strategies">Maps</a>
        <a href="#strategies">Strategies</a>
        <a href="#pricing">Pricing</a>
        <a href="#referral">Referral</a>
      </nav>
      <div class="header-actions">
        <button class="header-user" aria-label="User account">
          <svg viewBox="0 0 24 24" width="18" height="18" fill="none">
            <circle cx="12" cy="8" r="3.5" stroke="currentColor" stroke-width="1.6"/>
            <path d="M4.5 20c1.4-4 5-6 7.5-6s6.1 2 7.5 6" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/>
          </svg>
        </button>
        <button class="btn-primary header-cta">Get Access</button>
      </div>
    </div>
  </header>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
const isScrolled = ref(false)
const onScroll = () => { isScrolled.value = window.scrollY > 20 }
onMounted(() => window.addEventListener('scroll', onScroll))
onUnmounted(() => window.removeEventListener('scroll', onScroll))
</script>

<style scoped>
.header {
  position: sticky;
  top: 0;
  z-index: 200;
  padding: 14px 0;
  transition: background 0.3s, border-color 0.3s, backdrop-filter 0.3s;
  border-bottom: 1px solid transparent;
}
.header.scrolled {
  background: rgba(17,18,19,0.85);
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  border-color: var(--line);
}
.header-inner {
  display: flex;
  align-items: center;
  gap: 32px;
}
.header-logo { flex: 1; }
.logo-img { height: 36px; width: auto; object-fit: contain; }
.header-nav {
  display: flex;
  gap: 28px;
}
.header-nav a {
  color: var(--text-dim);
  text-decoration: none;
  font-size: 14px;
  font-weight: 600;
  letter-spacing: 0.02em;
  transition: color 0.2s;
}
.header-nav a:hover { color: var(--text); }
.header-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}
.header-user {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 38px;
  height: 38px;
  border-radius: 50%;
  border: 1px solid var(--line);
  background: transparent;
  color: var(--text-dim);
  cursor: pointer;
  transition: color 0.2s, border-color 0.2s, background 0.2s;
  flex-shrink: 0;
}
.header-user:hover {
  color: var(--text);
  border-color: var(--accent);
  background: rgba(255,154,0,0.08);
}
.header-cta {
  font-size: 13px;
  padding: 10px 22px;
}
@media (max-width: 520px) {
  .header-nav { display: none; }
}
</style>