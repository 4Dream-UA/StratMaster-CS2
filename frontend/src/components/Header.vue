<template>
  <header class="header" :class="{ scrolled: isScrolled, 'menu-open': isMenuOpen }">
    <div class="wrap header-inner">
      <router-link to="/" class="header-logo" aria-label="Go to home page">
        <img src="../assets/logo.png" alt="StratMaster CS2" class="logo-img" />
      </router-link>

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
        <a href="#strategies" @click="closeMenu">Maps</a>
        <a href="#strategies" @click="closeMenu">Strategies</a>
        <a href="#pricing" @click="closeMenu">Pricing</a>
        <a href="#referral" @click="closeMenu">Referral</a>

        <div class="mobile-menu-divider"></div>

        <button class="mobile-menu-user" @click="closeMenu">
          <svg viewBox="0 0 24 24" width="18" height="18" fill="none">
            <circle cx="12" cy="8" r="3.5" stroke="currentColor" stroke-width="1.6"/>
            <path d="M4.5 20c1.4-4 5-6 7.5-6s6.1 2 7.5 6" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/>
          </svg>
          Account
        </button>
        <button class="btn-primary mobile-menu-cta" @click="closeMenu">Get Access</button>
      </nav>
    </transition>
  </header>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch } from 'vue'

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

/* ── Hamburger toggle ─────────────────────── */
.menu-toggle {
  display: none;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  gap: 5px;
  width: 38px;
  height: 38px;
  border-radius: 8px;
  border: 1px solid var(--line);
  background: transparent;
  cursor: pointer;
  flex-shrink: 0;
  transition: border-color 0.2s, background 0.2s;
}
.menu-toggle:hover { border-color: var(--accent); background: rgba(255,154,0,0.08); }
.menu-toggle span {
  display: block;
  width: 16px;
  height: 2px;
  border-radius: 2px;
  background: var(--text);
  transition: transform 0.25s, opacity 0.25s;
}
.menu-toggle.active span:nth-child(1) { transform: translateY(7px) rotate(45deg); }
.menu-toggle.active span:nth-child(2) { opacity: 0; }
.menu-toggle.active span:nth-child(3) { transform: translateY(-7px) rotate(-45deg); }

/* ── Mobile dropdown panel ────────────────── */
.menu-backdrop {
  position: fixed;
  inset: 0;
  top: 0;
  background: rgba(0,0,0,0.45);
  z-index: 190;
}

.mobile-menu {
  position: absolute;
  top: 100%;
  left: 0;
  right: 0;
  z-index: 199;
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 14px;
  background: rgba(17,18,19,0.98);
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  border-bottom: 1px solid var(--line);
}
.mobile-menu a {
  padding: 13px 14px;
  border-radius: 8px;
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
  margin: 8px 4px;
}

.mobile-menu-user {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 13px 14px;
  border-radius: 8px;
  border: none;
  background: transparent;
  color: var(--text-dim);
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  text-align: left;
  transition: background 0.2s, color 0.2s;
}
.mobile-menu-user:hover { background: var(--bg-elevated); color: var(--text); }

.mobile-menu-cta {
  margin-top: 10px;
  width: 100%;
  padding: 14px;
  font-size: 15px;
}

/* Transitions */
.fade-enter-active, .fade-leave-active { transition: opacity 0.2s; }
.fade-enter-from, .fade-leave-to { opacity: 0; }

.slide-enter-active, .slide-leave-active { transition: transform 0.25s ease, opacity 0.2s ease; }
.slide-enter-from, .slide-leave-to { transform: translateY(-8px); opacity: 0; }

/* ── Breakpoint: collapse nav + actions into hamburger ── */
@media (max-width: 720px) {
  .header-nav,
  .header-actions { display: none; }
  .menu-toggle { display: flex; }
}
</style>