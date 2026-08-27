<template>
  <header class="header" :class="{ scrolled: isScrolled, 'menu-open': isMenuOpen }">
    <div class="wrap header-inner">
      <router-link to="/" class="header-logo" aria-label="Go to home page">
        <img src="../assets/logo.png" alt="StratMaster CS2" class="logo-img" />
      </router-link>

      <nav class="header-nav">
        <a href="/#strategies" @click.prevent="goToSection('strategies')">Maps</a>
        <router-link to="/pricing">Pricing</router-link>
        <router-link to="/user">Referral</router-link>
      </nav>

      <div class="header-actions">
        <router-link to="/user" class="header-user" :class="{ 'is-admin': isAdmin }" aria-label="User account">
          <svg viewBox="0 0 24 24" width="18" height="18" fill="none">
            <circle cx="12" cy="8" r="3.5" stroke="currentColor" stroke-width="1.6"/>
            <path d="M4.5 20c1.4-4 5-6 7.5-6s6.1 2 7.5 6" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/>
          </svg>
          <span v-if="isAdmin" class="admin-dot"></span>
        </router-link>
        <router-link v-if="!hasActiveAccess" to="/pricing" class="btn-primary header-cta">Get Access</router-link>
      </div>

      <!-- ═══ MOBILE ══════════════════════════════ -->
      <button
        class="menu-toggle"
        :class="{ active: isMenuOpen }"
        aria-label="Toggle menu"
        :aria-expanded="isMenuOpen"
        @click="toggleMenu"
      >
        <span></span>
        <span></span>
        <span></span>
      </button>
    </div>

    <!-- Backdrop -->
    <transition name="fade">
      <div v-if="isMenuOpen" class="menu-backdrop" @click="closeMenu"></div>
    </transition>

    <!-- Dropdown panel -->
    <transition name="slide">
      <nav v-if="isMenuOpen" class="mobile-menu" aria-label="Mobile navigation">
        <a href="/#strategies" @click.prevent="goToSection('strategies')">Maps</a>
        <router-link to="/pricing" @click="closeMenu">Pricing</router-link>
        <router-link to="/user" @click="closeMenu">Referral</router-link>

        <div class="mobile-menu-divider"></div>

        <router-link to="/user" class="mobile-menu-user" @click="closeMenu">
          <svg viewBox="0 0 24 24" width="18" height="18" fill="none">
            <circle cx="12" cy="8" r="3.5" stroke="currentColor" stroke-width="1.6"/>
            <path d="M4.5 20c1.4-4 5-6 7.5-6s6.1 2 7.5 6" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/>
          </svg>
          Account
          <span v-if="isAdmin" class="admin-badge-inline">ADMIN</span>
        </router-link>

        <router-link v-if="isAdmin" to="/admin" class="mobile-menu-user admin-link" @click="closeMenu">
          <svg viewBox="0 0 24 24" width="18" height="18" fill="none">
            <path d="M14.7 6.3a4 4 0 00-5.4 4.6L4 16.2V20h3.8l5.3-5.3a4 4 0 004.6-5.4l-2.6 2.6-2-2 2.6-2.6z"
                  stroke="currentColor" stroke-width="1.6" stroke-linejoin="round" stroke-linecap="round"/>
          </svg>
          Admin Panel
        </router-link>
      </nav>
    </transition>
  </header>
</template>

<script setup>
import { ref, computed, nextTick, onMounted, onUnmounted, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { storeToRefs } from 'pinia'
import { useUserStore } from '../store/user'

const router = useRouter()
const route = useRoute()

const userStore = useUserStore()
const { user, wallet } = storeToRefs(userStore)
const isAdmin = computed(() => !!user.value?.is_admin)

const hasActiveAccess = computed(() => {
  if (wallet.value?.is_lifetime) return true
  const exp = wallet.value?.subscription_expires_at
  return !!(exp && new Date(exp) > new Date())
})

function scrollToSection(id, retries = 15) {
  const el = document.getElementById(id)
  if (el) {
    el.scrollIntoView({ behavior: 'smooth', block: 'start' })
  } else if (retries > 0) {
    setTimeout(() => scrollToSection(id, retries - 1), 60)
  }
}

function goToSection(id) {
  closeMenu()
  if (route.path !== '/') {
    router.push({ path: '/', hash: '#' + id }).then(() => {
      nextTick(() => scrollToSection(id))
    })
  } else {
    if (route.hash !== '#' + id) {
      router.replace({ path: '/', hash: '#' + id })
    }
    scrollToSection(id)
  }
}

const isScrolled = ref(false)
const onScroll = () => { isScrolled.value = window.scrollY > 20 }

const isMenuOpen = ref(false)
function toggleMenu() { isMenuOpen.value = !isMenuOpen.value }
function closeMenu()  { isMenuOpen.value = false }

// Lock page scroll while the mobile menu is open
watch(isMenuOpen, (open) => {
  document.body.style.overflow = open ? 'hidden' : ''
})

// Close on resize back to desktop, so it can't get stuck open
function onResize() {
  if (window.innerWidth > 720) isMenuOpen.value = false
}

onMounted(() => {
  window.addEventListener('scroll', onScroll)
  window.addEventListener('resize', onResize)
})
onUnmounted(() => {
  window.removeEventListener('scroll', onScroll)
  window.removeEventListener('resize', onResize)
  document.body.style.overflow = ''
})
</script>

<style scoped>
.header {
  position: sticky;
  top: 0;
  z-index: 200;
  padding: 8px 0;
  transition: background 0.3s, border-color 0.3s, backdrop-filter 0.3s;
  border-bottom: 1px solid transparent;
}
.logo-img {
  height: 48px;
  width: auto;
  object-fit: contain;
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
.header-logo {
  flex: 1;
  display: flex;
  align-items: center;
  width: fit-content;
  text-decoration: none;
}
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
  position: relative;
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
  text-decoration: none;
  transition: color 0.2s, border-color 0.2s, background 0.2s;
  flex-shrink: 0;
}
.header-user:hover {
  color: var(--text);
  border-color: var(--accent);
  background: rgba(255,154,0,0.08);
}
.header-user.is-admin {
  border-color: rgba(255,80,80,0.5);
  color: var(--danger);
}
.header-user.is-admin:hover {
  background: rgba(255,80,80,0.1);
}
.admin-dot {
  position: absolute; top: -2px; right: -2px;
  width: 9px; height: 9px; border-radius: 50%;
  background: var(--danger);
  border: 2px solid var(--bg);
}
.header-cta {
  font-size: 14px;
  font-weight: 800;
  padding: 12px 26px;
  border-radius: 12px;
  text-decoration: none;
}
/* Явно переопределяем hover: только подъём + тень, шрифт/цвет/жирность не трогаем */
.header-cta:hover {
  color: #111213;
  font-size: 14px;
  font-weight: 800;
  transform: translateY(-2px);
  box-shadow: 0 12px 28px -6px rgba(255,154,0,0.5);
}

/* ── Hamburger toggle ─────────────────────── */
.menu-toggle {
  display: none;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  gap: 5px;
  width: 38px;
  height: 38px;
  border-radius: 12px;
  border: 1px solid var(--line);
  background: transparent;
  cursor: pointer;
  flex-shrink: 0;
  transition: border-color 0.25s ease, background 0.25s ease;
}
.menu-toggle:hover { border-color: rgba(255,154,0,0.4); background: rgba(255,154,0,0.06); }
.menu-toggle.active { border-color: rgba(255,154,0,0.5); background: rgba(255,154,0,0.08); }
.menu-toggle span {
  display: block;
  width: 16px;
  height: 2px;
  border-radius: 2px;
  background: var(--text);
  transition: transform 0.3s cubic-bezier(0.25, 0.8, 0.4, 1), opacity 0.2s ease;
}
.menu-toggle.active span:nth-child(1) { transform: translateY(7px) rotate(40deg); }
.menu-toggle.active span:nth-child(2) { opacity: 0; }
.menu-toggle.active span:nth-child(3) { transform: translateY(-7px) rotate(-40deg); }

/* ── Mobile dropdown panel ────────────────── */
.menu-backdrop {
  position: fixed;
  inset: 0;
  top: 0;
  background: rgba(0,0,0,0.32);
  backdrop-filter: blur(2px);
  -webkit-backdrop-filter: blur(2px);
  z-index: 190;
}

.mobile-menu {
  position: absolute;
  top: calc(100% + 6px);
  left: 12px;
  right: 12px;
  z-index: 199;
  display: flex;
  flex-direction: column;
  gap: 3px;
  padding: 12px;
  background: rgba(24,25,29,0.97);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border: 1px solid var(--line);
  border-radius: 18px;
  box-shadow: 0 16px 40px -12px rgba(0,0,0,0.5);
}
.mobile-menu a {
  padding: 13px 16px;
  border-radius: 12px;
  color: var(--text);
  text-decoration: none;
  font-size: 15px;
  font-weight: 600;
  transition: background 0.2s;
}
.mobile-menu a:hover,
.mobile-menu a:active { background: var(--bg-elevated); }

.mobile-menu-divider {
  height: 1px;
  background: var(--line);
  margin: 6px 6px;
}

.mobile-menu-user {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 13px 16px;
  border-radius: 12px;
  border: none;
  background: transparent;
  color: var(--text-dim);
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  text-align: left;
  text-decoration: none;
  transition: background 0.2s, color 0.2s;
}
.mobile-menu-user:hover { background: var(--bg-elevated); color: var(--text); }
.mobile-menu-user.admin-link { color: var(--danger); }

.admin-badge-inline {
  margin-left: auto;
  padding: 2px 8px;
  border-radius: 6px;
  background: rgba(255,80,80,0.15);
  color: var(--danger);
  font-size: 9px;
  font-weight: 800;
  letter-spacing: .05em;
}

.mobile-menu-cta {
  margin-top: 8px;
  width: 100%;
  padding: 15px;
  font-size: 15px;
  border-radius: 14px;
  justify-content: center;
  text-decoration: none;
}

/* Transitions */
.fade-enter-active, .fade-leave-active { transition: opacity 0.25s ease; }
.fade-enter-from, .fade-leave-to { opacity: 0; }

.slide-enter-active, .slide-leave-active { transition: transform 0.3s cubic-bezier(0.25, 0.8, 0.4, 1), opacity 0.25s ease; }
.slide-enter-from, .slide-leave-to { transform: translateY(-10px) scale(0.98); opacity: 0; }

/* ── Breakpoint: collapse only nav links into hamburger — CTA & account stay visible ── */
@media (max-width: 720px) {
  .header-nav { display: none; }
  .menu-toggle { display: flex; }
  .header-inner { gap: 12px; }
  .header-cta { padding: 10px 18px; font-size: 13px; }
  .header-cta:hover { font-size: 13px; }
}

@media (max-width: 400px) {
  .header-user { display: none; }
  .logo-img { height: 36px; }
}
</style>