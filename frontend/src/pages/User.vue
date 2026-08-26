<template>
  <main class="user-page">
    <Header />

    <div class="wrap user-content">

      <!-- ── BACK ─────────────────────────────────────── -->
      <button class="back-btn" @click="router.push('/')">
        <svg viewBox="0 0 16 16" fill="none" width="14" height="14">
          <path d="M10 3L5 8l5 5" stroke="currentColor" stroke-width="2"
                stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
        Home
      </button>

      <!-- ── PROFILE HEADER ───────────────────────────── -->
      <section class="profile-card">
        <div class="profile-row">
          <div class="avatar">{{ initials }}</div>
          <div class="profile-info">
            <div class="name-line">
              <h1>{{ user?.username ? '@' + user.username : 'Guest' }}</h1>
              <span v-if="user?.is_admin" class="admin-badge">ADMIN</span>
            </div>
            <span class="sub-pill" :class="isLifetime ? 'lifetime' : isSubscribed ? 'active' : 'inactive'">
              {{ isLifetime ? 'Lifetime access' : isSubscribed ? `Premium — ${remainingLabel} left` : 'No active subscription' }}
            </span>
          </div>
        </div>

        <router-link v-if="!user?.is_admin" to="/pricing" class="btn-primary upgrade-btn">
          {{ isLifetime ? 'View Plan' : isSubscribed ? 'Manage Plan' : 'Upgrade' }}
        </router-link>
      </section>

      <!-- ── EXPIRING SOON BANNER ──────────────────────── -->
      <section v-if="expiringSoon" class="expiry-banner">
        <div class="expiry-text">
          <strong>Your Premium expires in {{ remainingLabel }}.</strong>
          <span>Renew now to keep uninterrupted access — you'll get the same {{ wallet.last_plan_months || 1 }}-month plan.</span>
        </div>
        <button class="btn-primary expiry-renew-btn" :disabled="renewing" @click="renewNow">
          {{ renewing ? 'Renewing…' : 'Renew now' }}
        </button>
      </section>
      <p v-if="renewMessage" class="renew-message" :class="{ error: renewError }">{{ renewMessage }}</p>

      <!-- ── AUTO-RENEW ────────────────────────────────── -->
      <section v-if="isSubscribed && !isLifetime" class="auto-renew-card">
        <div class="auto-renew-text">
          <strong>Auto-renew</strong>
          <span>Automatically charge MasterCoins to keep Premium active. You'll always get a reminder 24h before, either way.</span>
        </div>
        <label class="switch">
          <input type="checkbox" :checked="wallet?.auto_renew" @change="toggleAutoRenew($event.target.checked)" />
          <span class="switch-track"><span class="switch-thumb"></span></span>
        </label>
      </section>

      <!-- ── WALLET CARD ──────────────────────────────── -->
      <section class="wallet-card">
        <div class="wallet-top">
          <span class="wallet-label">Balance</span>
          <div class="wallet-balance-row">
            <span class="balance-num">{{ wallet?.balance_coins ?? 0 }}</span>
            <span class="coin-unit">MasterCoins</span>
            <button type="button" class="topup-toggle" @click="topupOpen = !topupOpen">
              {{ topupOpen ? 'Cancel' : '+ Top up' }}
            </button>
          </div>
        </div>

        <div v-if="topupOpen" class="topup-form">
          <input
            v-model.number="topupCoins" type="number" min="10" placeholder="Amount (min 10)"
            class="topup-input" :disabled="topupBusy || topupPolling"
          />
          <span class="topup-usd">≈ ${{ ((topupCoins || 0) * 0.01).toFixed(2) }}</span>
          <button
            class="btn-primary topup-submit" :disabled="topupBusy || topupPolling || !topupCoins || topupCoins < 10"
            @click="buyCoins"
          >{{ topupPolling ? 'Waiting…' : topupBusy ? '...' : 'Pay with Crypto' }}</button>
        </div>
        <p v-if="topupMessage" class="panel-message" :class="topupSuccess ? 'success' : 'error'">{{ topupMessage }}</p>

        <div class="wallet-bottom">
          <div class="wallet-id-chip" @click="copy(wallet?.wallet_id, 'wallet')">
            <span class="wallet-id-label">WALLET ID:</span>
            <span class="wallet-id-val">{{ wallet?.wallet_id ?? '—' }}</span>
            <span class="wallet-id-copy">{{ copiedField === 'wallet' ? 'Copied' : 'Copy' }}</span>
          </div>
          <span v-if="hasActiveDiscount" class="discount-chip">-25% active</span>
        </div>
      </section>

      <!-- ── HOTBAR ───────────────────────────────────── -->
      <nav class="hotbar">
        <button
          v-for="tab in TABS" :key="tab.key"
          class="hotbar-btn"
          :class="{ active: activeTab === tab.key }"
          @click="toggleTab(tab.key)"
        >
          <span class="hotbar-icon" v-html="tab.icon"></span>
          <span class="hotbar-label">{{ tab.label }}</span>
        </button>

        <router-link v-if="user?.is_admin" to="/admin" class="hotbar-btn admin-hotbar-btn">
          <span class="hotbar-icon" v-html="ICONS.admin"></span>
          <span class="hotbar-label">Admin</span>
        </router-link>
      </nav>

      <!-- ── PANEL ────────────────────────────────────── -->
      <transition name="panel" mode="out-in">
        <section v-if="activeTab === 'referral'" key="referral" class="panel-wrap">
          <ReferralSection />
        </section>

        <section v-else-if="activeTab === 'promo'" key="promo" class="panel-wrap panel-card">
          <div class="panel-header">
            <span class="panel-icon" v-html="ICONS.promo"></span>
            <h3>Promo Code</h3>
          </div>
          <p class="panel-desc">Have a code? Redeem it for bonus MasterCoins.</p>
          <p class="panel-desc">Join our <a href="https://t.me/stratMasterCS2" class="panel-desc">Telegram</a> to enter the promo code giveaway!</p>

          <div class="promo-form">
            <input
              v-model="promoCode"
              type="text"
              placeholder="ENTER CODE"
              class="promo-input"
              @keyup.enter="redeemPromo"
              :disabled="promoLoading"
            />
            <button
              class="btn-primary promo-btn"
              :disabled="!promoCode || promoLoading"
              @click="redeemPromo"
            >
              {{ promoLoading ? '...' : 'Redeem' }}
            </button>
          </div>

          <p v-if="promoMessage" class="panel-message" :class="promoSuccess ? 'success' : 'error'">
            {{ promoMessage }}
          </p>
        </section>

        <section v-else-if="activeTab === 'p2p'" key="p2p" class="panel-wrap panel-card">
          <div class="panel-header">
            <span class="panel-icon" v-html="ICONS.p2p"></span>
            <h3>P2P Transfers</h3>
          </div>
          <p class="panel-desc">Send MasterCoins or gift a subscription directly to another player's Wallet ID.</p>

          <div class="p2p-mode-toggle">
            <button type="button" class="p2p-mode-btn" :class="{ active: p2pMode === 'coins' }" @click="switchP2pMode('coins')">Send Coins</button>
            <button type="button" class="p2p-mode-btn" :class="{ active: p2pMode === 'gift' }" @click="switchP2pMode('gift')">Gift Subscription</button>
          </div>

          <form v-if="p2pMode === 'coins'" class="p2p-form" @submit.prevent="sendCoins">
            <input v-model="p2pWalletId" type="text" placeholder="Recipient Wallet ID" class="p2p-input" autocomplete="off" spellcheck="false" :disabled="p2pLoading" />
            <input v-model.number="p2pAmount" type="number" min="1" placeholder="Amount" class="p2p-input p2p-input-amount" :disabled="p2pLoading" />
            <button type="submit" class="btn-primary p2p-submit" :disabled="p2pLoading || !p2pWalletId || !p2pAmount">
              {{ p2pLoading ? '...' : 'Send' }}
            </button>
          </form>

          <form v-else class="p2p-form p2p-form-gift" @submit.prevent="sendGift">
            <input v-model="p2pWalletId" type="text" placeholder="Recipient Wallet ID" class="p2p-input" autocomplete="off" spellcheck="false" :disabled="p2pLoading" />
            <select v-model="giftPlan" class="p2p-input p2p-select" :disabled="p2pLoading">
              <option value="premium-1">Premium — 1 Month (99 MC)</option>
              <option value="premium-3">Premium — 3 Months (255 MC)</option>
              <option value="premium-6">Premium — 6 Months (499 MC)</option>
              <option value="premium-12">Premium — 12 Months (999 MC)</option>
              <option value="lifetime">Lifetime (4999 MC)</option>
            </select>
            <button type="submit" class="btn-primary p2p-submit" :disabled="p2pLoading || !p2pWalletId">
              {{ p2pLoading ? '...' : 'Gift' }}
            </button>
          </form>

          <p v-if="p2pMessage" class="panel-message" :class="p2pSuccess ? 'success' : 'error'">{{ p2pMessage }}</p>
        </section>

        <section v-else-if="activeTab === 'favorites'" key="favorites" class="panel-wrap panel-card">
          <div class="panel-header">
            <span class="panel-icon" v-html="ICONS.favorites"></span>
            <h3>Favorite Maps</h3>
          </div>
          <p class="panel-desc">Pin your go-to maps for quicker access to their strategies.</p>

          <div v-if="favoritesLoading" class="favorites-placeholder">Loading…</div>
          <div v-else-if="!favoriteMaps.length" class="favorites-placeholder">
            No favorites yet — tap the star on a map's card to pin it here.
          </div>
          <div v-else class="favorites-list">
            <router-link
              v-for="m in favoriteMaps" :key="m.id"
              :to="'/map/' + m.id" class="favorite-row"
            >
              <span class="favorite-row-name">{{ m.name }}</span>
              <button
                type="button" class="favorite-row-remove"
                @click.prevent="unfavoriteMap(m.id)"
                aria-label="Remove from favorites"
              >✕</button>
            </router-link>
          </div>
        </section>

        <p v-else key="hint" class="hotbar-hint">Tap an option above to get started.</p>
      </transition>

    </div>

    <Footer />
  </main>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { storeToRefs } from 'pinia'
import { useUserStore } from '../store/user'
import { promoAPI } from '../api/promo'
import { subscriptionAPI } from '../api/subscription'
import { walletAPI } from '../api/wallet'
import { paymentsAPI } from '../api/payments'
import { favoritesAPI } from '../api/favorites'
import Header from '../components/Header.vue'
import Footer from '../components/Footer.vue'
import ReferralSection from '../components/ReferralSection.vue'

const router = useRouter()
const userStore = useUserStore()
const { user, wallet } = storeToRefs(userStore)

const copiedField = ref(null)

const promoCode = ref('')
const promoLoading = ref(false)
const promoMessage = ref('')
const promoSuccess = ref(false)

// Default open so the referral code-entry field is immediately visible
const activeTab = ref('referral')
function toggleTab(key) {
  activeTab.value = activeTab.value === key ? null : key
  if (activeTab.value === 'favorites' && !favoritesLoaded.value) loadFavorites()
}

// ── Favorite maps ──────────────────────────────────────────────
const favoriteMaps = ref([])
const favoritesLoading = ref(false)
const favoritesLoaded = ref(false)

async function loadFavorites() {
  favoritesLoading.value = true
  try {
    favoriteMaps.value = await favoritesAPI.list()
    favoritesLoaded.value = true
  } catch (e) {
    console.warn('[User] could not load favorites:', e.response?.data?.detail)
  } finally {
    favoritesLoading.value = false
  }
}

async function unfavoriteMap(mapId) {
  favoriteMaps.value = favoriteMaps.value.filter(m => m.id !== mapId)
  try {
    await favoritesAPI.remove(mapId)
  } catch (e) {
    await loadFavorites() // out of sync — reload to recover the true state
  }
}

const initials = computed(() => {
  const name = user.value?.username || 'G'
  return name.charAt(0).toUpperCase()
})

const isSubscribed = computed(() => {
  const exp = wallet.value?.subscription_expires_at
  return exp && new Date(exp) > new Date()
})

const isLifetime = computed(() => !!wallet.value?.is_lifetime)

const hoursRemaining = computed(() => {
  const exp = wallet.value?.subscription_expires_at
  if (!exp) return 0
  return Math.max(0, (new Date(exp) - new Date()) / 3600000)
})

const remainingLabel = computed(() => {
  const hours = hoursRemaining.value
  if (hours <= 0) return '0h'
  if (hours < 24) return `${Math.ceil(hours)}h`
  return `${Math.ceil(hours / 24)}d`
})

const expiringSoon = computed(() => isSubscribed.value && !isLifetime.value && hoursRemaining.value <= 24)

const hasActiveDiscount = computed(() => {
  const exp = wallet.value?.ref_discount_expires_at
  return exp && new Date(exp) > new Date()
})

const renewing = ref(false)
const renewMessage = ref('')
const renewError = ref(false)

async function renewNow() {
  if (renewing.value) return
  renewing.value = true
  renewMessage.value = ''
  try {
    const months = wallet.value?.last_plan_months || 1
    const res = await subscriptionAPI.purchase('premium', months)
    if (wallet.value) {
      wallet.value.balance_coins = res.new_balance
      wallet.value.subscription_expires_at = res.subscription_expires_at
    }
    renewError.value = false
    renewMessage.value = `Renewed! ${res.coins_spent} MC charged.`
  } catch (e) {
    renewError.value = true
    renewMessage.value = e.response?.data?.detail || 'Renewal failed — check your MasterCoins balance.'
  } finally {
    renewing.value = false
  }
}

async function toggleAutoRenew(enabled) {
  try {
    const res = await subscriptionAPI.setAutoRenew(enabled)
    if (wallet.value) wallet.value.auto_renew = res.auto_renew
  } catch (e) {
    console.warn('[User] could not update auto-renew:', e.response?.data?.detail)
  }
}

// ── Top up MasterCoins with crypto ────────────────────────────────
const topupOpen = ref(false)
const topupCoins = ref(100)
const topupBusy = ref(false)
const topupPolling = ref(false)
const topupMessage = ref('')
const topupSuccess = ref(false)
let topupPollTimer = null

function stopTopupPolling() {
  if (topupPollTimer) { clearInterval(topupPollTimer); topupPollTimer = null }
  topupPolling.value = false
}

function openInvoiceLink(url) {
  if (window.Telegram?.WebApp?.openTelegramLink && url.includes('t.me/')) {
    window.Telegram.WebApp.openTelegramLink(url)
  } else if (window.Telegram?.WebApp?.openLink) {
    window.Telegram.WebApp.openLink(url)
  } else {
    window.open(url, '_blank', 'noopener')
  }
}

async function buyCoins() {
  if (topupBusy.value || topupPolling.value || !topupCoins.value || topupCoins.value < 10) return
  topupBusy.value = true
  topupMessage.value = ''
  try {
    const invoice = await paymentsAPI.createCryptoInvoice({ coins: topupCoins.value })
    openInvoiceLink(invoice.pay_url)
    topupMessage.value = 'Complete the payment in the window that just opened — this updates automatically.'
    topupSuccess.value = false
    topupPolling.value = true
    topupPollTimer = setInterval(async () => {
      try {
        const res = await paymentsAPI.getCryptoInvoiceStatus(invoice.invoice_id)
        if (res.status === 'paid') {
          stopTopupPolling()
          topupSuccess.value = true
          topupMessage.value = `+${invoice.coins} MasterCoins added!`
          await userStore.fetchMe()
        }
      } catch (e) { /* transient — keep polling */ }
    }, 3000)
  } catch (e) {
    topupSuccess.value = false
    topupMessage.value = e.response?.data?.detail || 'Could not start checkout — please try again.'
  } finally {
    topupBusy.value = false
  }
}

onUnmounted(stopTopupPolling)

// ── P2P: send coins / gift subscription ──────────────────────────
const p2pMode = ref('coins') // 'coins' | 'gift'
const p2pWalletId = ref('')
const p2pAmount = ref(null)
const giftPlan = ref('premium-1')
const p2pLoading = ref(false)
const p2pMessage = ref('')
const p2pSuccess = ref(false)

function switchP2pMode(mode) {
  p2pMode.value = mode
  p2pMessage.value = ''
}

async function sendCoins() {
  if (!p2pWalletId.value || !p2pAmount.value || p2pLoading.value) return
  p2pLoading.value = true
  p2pMessage.value = ''
  try {
    const res = await walletAPI.transfer(p2pWalletId.value.trim(), p2pAmount.value)
    p2pSuccess.value = true
    p2pMessage.value = `Sent ${res.amount} MC to ${res.receiver_wallet_id}.`
    if (wallet.value) wallet.value.balance_coins = res.new_balance
    p2pWalletId.value = ''
    p2pAmount.value = null
  } catch (e) {
    p2pSuccess.value = false
    p2pMessage.value = e.response?.data?.detail || 'Transfer failed.'
  } finally {
    p2pLoading.value = false
  }
}

async function sendGift() {
  if (!p2pWalletId.value || p2pLoading.value) return
  p2pLoading.value = true
  p2pMessage.value = ''
  try {
    const isLifetimePlan = giftPlan.value === 'lifetime'
    const plan = isLifetimePlan ? 'lifetime' : 'premium'
    const months = isLifetimePlan ? null : Number(giftPlan.value.split('-')[1])
    const res = await walletAPI.giftSubscription(p2pWalletId.value.trim(), plan, months)
    p2pSuccess.value = true
    p2pMessage.value = `Gifted ${plan} to ${res.receiver_wallet_id} — ${res.coins_spent} MC spent.`
    if (wallet.value) wallet.value.balance_coins = res.new_balance
    p2pWalletId.value = ''
  } catch (e) {
    p2pSuccess.value = false
    p2pMessage.value = e.response?.data?.detail || 'Gift failed.'
  } finally {
    p2pLoading.value = false
  }
}

function copy(text, field) {
  if (!text) return
  navigator.clipboard.writeText(text).then(() => {
    copiedField.value = field
    setTimeout(() => { copiedField.value = null }, 1800)
  })
}

async function redeemPromo() {
  if (!promoCode.value) return
  promoLoading.value = true
  promoMessage.value = ''
  try {
    const res = await promoAPI.redeem(promoCode.value.trim())
    promoSuccess.value = true
    promoMessage.value = `+${res.coins_awarded} MasterCoins added!`
    if (wallet.value) wallet.value.balance_coins = res.new_balance
    promoCode.value = ''
  } catch (e) {
    promoSuccess.value = false
    promoMessage.value = e.response?.data?.detail || 'Invalid or expired code.'
  } finally {
    promoLoading.value = false
  }
}

// ── Icon set (inline SVG strings — no emoji) ─────────────────────
const ICONS = {
  referral: `<svg viewBox="0 0 24 24" fill="none" width="20" height="20" id="referral">
    <rect x="4" y="10" width="16" height="10" rx="1" stroke="currentColor" stroke-width="1.6"/>
    <path d="M4 10h16M12 10v10" stroke="currentColor" stroke-width="1.6"/>
    <path d="M12 10c0-2.5-2-5-4-5s-2 3 0 4c1 .5 3 1 4 1zM12 10c0-2.5 2-5 4-5s2 3 0 4c-1 .5-3 1-4 1z" stroke="currentColor" stroke-width="1.4" stroke-linejoin="round"/>
  </svg>`,
  promo: `<svg viewBox="0 0 24 24" fill="none" width="20" height="20">
    <path d="M11 4h6a1 1 0 011 1v6a1 1 0 01-.3.7l-8 8a1 1 0 01-1.4 0l-6-6a1 1 0 010-1.4l8-8A1 1 0 0111 4z" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round"/>
    <circle cx="15.5" cy="8.5" r="1.3" fill="currentColor"/>
  </svg>`,
  p2p: `<svg viewBox="0 0 24 24" fill="none" width="20" height="20">
    <path d="M4 8h14l-3.5-3.5M20 16H6l3.5 3.5" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/>
  </svg>`,
  favorites: `<svg viewBox="0 0 24 24" fill="none" width="20" height="20">
    <path d="M6.5 4h11a1 1 0 011 1v15l-6.5-4-6.5 4V5a1 1 0 011-1z" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round"/>
  </svg>`,
  admin: `<svg viewBox="0 0 24 24" fill="none" width="20" height="20">
    <path d="M14.7 6.3a4 4 0 00-5.4 4.6L4 16.2V20h3.8l5.3-5.3a4 4 0 004.6-5.4l-2.6 2.6-2-2 2.6-2.6z"
          stroke="currentColor" stroke-width="1.6" stroke-linejoin="round" stroke-linecap="round"/>
  </svg>`,
}

const TABS = [
  { key: 'referral',  label: 'Referral',  icon: ICONS.referral },
  { key: 'promo',     label: 'Promo',     icon: ICONS.promo },
  { key: 'p2p',       label: 'P2P',       icon: ICONS.p2p },
  { key: 'favorites', label: 'Maps',      icon: ICONS.favorites },
]
</script>

<style scoped>
.user-page { min-height: 100vh; background: var(--bg); }
.user-content { max-width: 640px; padding: 20px 16px 100px; }

/* ── Back ─────────────────────────────────────── */
.back-btn {
  display: inline-flex; align-items: center; gap: 6px;
  background: var(--bg-elevated); border: 1px solid var(--line);
  color: var(--text-dim); padding: 8px 14px; border-radius: 8px;
  font-size: 13px; font-weight: 600; cursor: pointer;
  transition: border-color .2s, color .2s;
  margin-bottom: 18px;
}
.back-btn:hover { border-color: var(--accent); color: var(--accent); }

/* ── Profile card ─────────────────────────────── */
.profile-card {
  background: var(--bg-elevated);
  border: 1px solid var(--line);
  border-radius: var(--radius-lg);
  padding: 18px;
  margin-bottom: 12px;
  display: flex; align-items: center; justify-content: space-between;
  gap: 12px; flex-wrap: wrap;
}

.profile-row { display: flex; align-items: center; gap: 12px; min-width: 0; flex: 1; }

.avatar {
  width: 48px; height: 48px; border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  background: linear-gradient(135deg, var(--accent), var(--accent-2));
  color: #14140f; font-size: 19px; font-weight: 900;
  flex-shrink: 0;
}

.profile-info { min-width: 0; display: flex; flex-direction: column; gap: 5px; }

.name-line { display: flex; align-items: center; gap: 8px; min-width: 0; }
.name-line h1 {
  font-size: 17px; font-weight: 800;
  letter-spacing: -.01em; color: var(--text);
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap; min-width: 0;
}
.admin-badge {
  flex-shrink: 0;
  padding: 2px 8px; border-radius: 6px;
  background: rgba(255,80,80,0.15);
  border: 1px solid rgba(255,80,80,0.4);
  color: var(--danger);
  font-size: 9px; font-weight: 800;
  letter-spacing: .06em; text-transform: uppercase;
}

.sub-pill {
  align-self: flex-start;
  font-size: 11.5px; font-weight: 600;
  padding: 2px 9px; border-radius: 99px;
}
.sub-pill.active { color: var(--success); background: rgba(80,220,100,0.1); }
.sub-pill.inactive { color: var(--text-dim); background: var(--bg); }
.sub-pill.lifetime { color: var(--accent); background: rgba(255,154,0,0.12); }

.upgrade-btn {
  flex-shrink: 0;
  text-decoration: none;
  font-size: 11.5px;
  font-weight: 700;
  padding: 7px 16px;
  white-space: nowrap;
  border-radius: 999px;
}

/* ── Expiring soon banner ─────────────────────── */
.expiry-banner {
  display: flex; align-items: center; justify-content: space-between;
  gap: 14px; flex-wrap: wrap;
  background: rgba(255,154,0,0.1); border: 1px solid rgba(255,154,0,0.35);
  border-radius: var(--radius-lg); padding: 16px 18px; margin-bottom: 12px;
}
.expiry-text { display: flex; flex-direction: column; gap: 3px; min-width: 0; }
.expiry-text strong { font-size: 13.5px; color: var(--text); }
.expiry-text span { font-size: 12px; color: var(--text-dim); }
.expiry-renew-btn { font-size: 12.5px; padding: 10px 18px; flex-shrink: 0; white-space: nowrap; }

.renew-message {
  font-size: 12.5px; font-weight: 600; color: var(--success);
  margin: -6px 0 12px;
}
.renew-message.error { color: var(--danger); }

/* ── Auto-renew ────────────────────────────────── */
.auto-renew-card {
  display: flex; align-items: center; justify-content: space-between;
  gap: 14px;
  background: var(--bg-elevated); border: 1px solid var(--line);
  border-radius: var(--radius-lg); padding: 16px 18px; margin-bottom: 12px;
}
.auto-renew-text { display: flex; flex-direction: column; gap: 3px; min-width: 0; }
.auto-renew-text strong { font-size: 13.5px; color: var(--text); }
.auto-renew-text span { font-size: 12px; color: var(--text-dim); }

.switch { position: relative; flex-shrink: 0; cursor: pointer; display: inline-flex; }
.switch input { position: absolute; opacity: 0; width: 0; height: 0; }
.switch-track {
  width: 44px; height: 26px; border-radius: 99px;
  background: var(--bg); border: 1px solid var(--line);
  display: inline-flex; align-items: center; padding: 2px;
  transition: background .2s, border-color .2s;
}
.switch-thumb {
  width: 20px; height: 20px; border-radius: 50%;
  background: var(--text-dim);
  transition: transform .2s, background .2s;
}
.switch input:checked + .switch-track {
  background: rgba(255,154,0,0.18); border-color: var(--accent);
}
.switch input:checked + .switch-track .switch-thumb {
  transform: translateX(18px); background: var(--accent);
}

/* ── Wallet card ──────────────────────────────── */
.wallet-card {
  background: linear-gradient(160deg, rgba(255,154,0,0.07), var(--bg-elevated) 60%);
  border: 1px solid rgba(255,154,0,0.25);
  border-radius: var(--radius-lg);
  padding: 20px;
  margin-bottom: 16px;
}

.wallet-top { margin-bottom: 16px; }
.wallet-label {
  display: block;
  font-size: 11px; font-weight: 700; letter-spacing: .07em;
  text-transform: uppercase; color: var(--text-dim);
  margin-bottom: 6px;
}
.wallet-balance-row { display: flex; align-items: baseline; gap: 8px; }
.balance-num {
  font-size: 32px; font-weight: 900; color: var(--accent);
  letter-spacing: -.02em; font-variant-numeric: tabular-nums;
}
.coin-unit { font-size: 12px; color: var(--text-dim); font-weight: 600; }

.topup-toggle {
  margin-left: auto;
  background: none; border: 1px solid var(--line); color: var(--accent);
  font-size: 11.5px; font-weight: 700; padding: 5px 11px; border-radius: 99px;
  cursor: pointer; transition: border-color .15s, background .15s;
}
.topup-toggle:hover { border-color: var(--accent); background: rgba(255,154,0,.08); }

.topup-form {
  display: flex; align-items: center; gap: 8px; flex-wrap: wrap;
  margin-top: 12px; padding-top: 12px; border-top: 1px solid var(--line);
}
.topup-input {
  flex: 1; min-width: 110px;
  padding: 10px 12px; background: var(--bg); border: 1px solid var(--line);
  border-radius: 9px; color: var(--text); font-size: 13px;
}
.topup-input:focus { outline: none; border-color: var(--accent); }
.topup-usd { font-size: 12px; color: var(--text-dim); flex-shrink: 0; }
.topup-submit { font-size: 12.5px; padding: 10px 16px; flex-shrink: 0; white-space: nowrap; }
.topup-submit:disabled { opacity: .5; cursor: not-allowed; }

.wallet-bottom {
  display: flex; align-items: center; gap: 10px; flex-wrap: wrap;
  padding-top: 14px; border-top: 1px solid var(--line);
}

.wallet-id-chip {
  display: flex; align-items: center; gap: 8px;
  background: var(--bg); border: 1px solid var(--line);
  border-radius: 10px; padding: 8px 12px;
  cursor: pointer; transition: border-color .15s;
  flex: 1; min-width: 0;
}
.wallet-id-chip:hover { border-color: var(--accent); }
.wallet-id-label {
  font-size: 10px; font-weight: 700; color: var(--text-dim);
  text-transform: uppercase; flex-shrink: 0;
}
.wallet-id-val {
  font-size: 13px; font-weight: 700; color: var(--text);
  font-variant-numeric: tabular-nums;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap; min-width: 0; flex: 1;
}
.wallet-id-copy {
  font-size: 10.5px; font-weight: 700; color: var(--accent);
  text-transform: uppercase; letter-spacing: .04em; flex-shrink: 0;
}

.discount-chip {
  flex-shrink: 0;
  padding: 4px 11px; border-radius: 99px;
  background: rgba(80,220,100,0.12);
  border: 1px solid rgba(80,220,100,0.4);
  color: var(--success);
  font-size: 11px; font-weight: 700;
}

/* ── Hotbar ───────────────────────────────────── */
.hotbar {
  display: flex; gap: 8px;
  overflow-x: auto;
  padding-bottom: 4px;
  margin-bottom: 14px;
  scrollbar-width: none;
}
.hotbar::-webkit-scrollbar { display: none; }

.hotbar-btn {
  display: flex; flex-direction: column; align-items: center; gap: 6px;
  flex: 1; min-width: 76px;
  padding: 12px 8px;
  background: var(--bg-elevated); border: 1.5px solid var(--line);
  border-radius: 14px; cursor: pointer;
  color: var(--text-dim);
  text-decoration: none;
  transition: border-color .18s, background .18s, color .18s, transform .1s;
}
.hotbar-btn:active { transform: scale(0.96); }
.hotbar-btn:hover { border-color: rgba(255,154,0,.4); color: var(--text); }
.hotbar-btn.active {
  border-color: var(--accent);
  background: rgba(255,154,0,0.1);
  color: var(--accent);
}
.hotbar-icon { display: flex; align-items: center; justify-content: center; }
.hotbar-label { font-size: 11px; font-weight: 700; letter-spacing: .01em; }

.admin-hotbar-btn { color: var(--danger); border-color: rgba(255,80,80,0.25); }
.admin-hotbar-btn:hover { border-color: rgba(255,80,80,0.5); color: var(--danger); }

/* ── Panel ────────────────────────────────────── */
.panel-wrap { min-height: 40px; }

.panel-card {
  background: var(--bg-elevated);
  border: 1px solid var(--line);
  border-radius: var(--radius-lg);
  padding: 20px;
}

.panel-header {
  display: flex; align-items: center; gap: 8px;
  margin-bottom: 10px;
}
.panel-icon { display: flex; color: var(--accent); flex-shrink: 0; }
.panel-header h3 { font-size: 15px; font-weight: 700; color: var(--text); flex: 1; }

.soon-badge {
  padding: 2px 9px; border-radius: 99px;
  background: var(--bg); border: 1px solid var(--line);
  color: var(--text-dim); font-size: 10px; font-weight: 700;
  text-transform: uppercase; letter-spacing: .05em;
}

.panel-desc { font-size: 13px; color: var(--text-dim); line-height: 1.6; margin-bottom: 16px; }

.promo-form { display: flex; gap: 8px; margin-bottom: 10px; }
.promo-input {
  flex: 1; min-width: 0;
  padding: 11px 12px;
  background: var(--bg); border: 1px solid var(--line);
  border-radius: 10px; color: var(--text);
  font-size: 13px; font-family: inherit;
  text-transform: uppercase; letter-spacing: .04em;
}
.promo-input:focus { outline: none; border-color: var(--accent); }
.promo-btn { font-size: 13px; padding: 11px 18px; flex-shrink: 0; }
.promo-btn:disabled { opacity: .5; cursor: not-allowed; }

.panel-message { font-size: 12px; font-weight: 600; }
.panel-message.success { color: var(--success); }
.panel-message.error { color: var(--danger); }

.p2p-mode-toggle {
  display: flex; gap: 6px;
  background: var(--bg); border: 1px solid var(--line);
  border-radius: 10px; padding: 4px; margin-bottom: 14px;
}
.p2p-mode-btn {
  flex: 1; padding: 8px 10px; border-radius: 7px;
  background: none; border: none; cursor: pointer;
  font-size: 12.5px; font-weight: 700; color: var(--text-dim);
  transition: background .15s, color .15s;
}
.p2p-mode-btn.active { background: var(--bg-elevated-2); color: var(--accent); }

.p2p-form { display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 10px; }
.p2p-input {
  flex: 1; min-width: 140px;
  padding: 11px 12px;
  background: var(--bg); border: 1px solid var(--line);
  border-radius: 10px; color: var(--text);
  font-size: 13px; font-family: inherit;
}
.p2p-input:focus { outline: none; border-color: var(--accent); }
.p2p-input-amount { flex: 0 1 110px; min-width: 90px; }
.p2p-select { flex-basis: 220px; }
.p2p-submit { font-size: 13px; padding: 11px 18px; flex-shrink: 0; }
.p2p-submit:disabled { opacity: .5; cursor: not-allowed; }

.favorites-placeholder {
  padding: 20px 0; text-align: center;
  font-size: 12px; color: var(--text-dim);
  border: 1px dashed var(--line); border-radius: 10px;
}

.favorites-list { display: flex; flex-direction: column; gap: 8px; }
.favorite-row {
  display: flex; align-items: center; justify-content: space-between;
  padding: 12px 14px;
  background: var(--bg); border: 1px solid var(--line); border-radius: 10px;
  text-decoration: none; transition: border-color .15s;
}
.favorite-row:hover { border-color: var(--accent); }
.favorite-row-name { font-size: 13.5px; font-weight: 700; color: var(--text); }
.favorite-row-remove {
  background: none; border: none; color: var(--text-dim); cursor: pointer;
  font-size: 13px; padding: 4px 6px; transition: color .15s;
}
.favorite-row-remove:hover { color: var(--danger); }

.hotbar-hint {
  text-align: center; font-size: 13px; color: var(--text-dim);
  padding: 24px 0;
}

/* Panel transition */
.panel-enter-active, .panel-leave-active { transition: opacity .18s, transform .18s; }
.panel-enter-from { opacity: 0; transform: translateY(6px); }
.panel-leave-to { opacity: 0; transform: translateY(-4px); }
</style>
