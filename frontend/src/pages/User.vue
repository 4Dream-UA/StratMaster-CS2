<template>
  <main class="user-page">
    <Header />

    <div class="wrap user-content" :class="{ 'user-content-wide': activeTab === 'board' || activeTab === 'cases' }">

      <!-- ── BREADCRUMB ─────────────────────────────────── -->
      <Breadcrumbs :items="[{ label: 'Home', to: '/' }, { label: 'Profile' }]" />

      <!-- ── PROFILE HEADER ───────────────────────────── -->
      <section class="profile-card">
        <div class="profile-row">
          <label class="avatar" :class="{ uploadable: isSubscribed || isLifetime }">
            <img v-if="user?.avatar_url" :src="user.avatar_url" alt="" class="avatar-img" />
            <span v-else>{{ initials }}</span>
            <span v-if="isSubscribed || isLifetime" class="avatar-edit-badge">{{ avatarUploading ? '…' : '✎' }}</span>
            <input v-if="isSubscribed || isLifetime" type="file" accept="image/jpeg,image/png,image/webp,image/gif" hidden @change="onAvatarChange" />
          </label>
          <div class="profile-info">
            <div v-if="!nicknameEditing" class="name-line">
              <h1>{{ user?.display_name || (user?.username ? '@' + user.username : 'Guest') }}</h1>
              <span v-if="user?.is_admin" class="admin-badge">ADMIN</span>
              <button type="button" class="nickname-edit-btn" @click="startEditNickname" aria-label="Edit nickname">✎</button>
            </div>
            <div v-else class="nickname-edit-row">
              <input v-model="nicknameDraft" type="text" maxlength="32" class="nickname-input" placeholder="Nickname" @keyup.enter="saveNickname" />
              <button class="mini-btn" :disabled="nicknameBusy" @click="saveNickname">{{ nicknameBusy ? '…' : 'Save' }}</button>
              <button class="mini-btn" @click="nicknameEditing = false">Cancel</button>
            </div>
            <span v-if="user?.display_name" class="username-sub">{{ user?.username ? '@' + user.username : '' }}</span>
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
          <span>
            Automatically renew Premium to keep uninterrupted access. You'll always get a reminder 24h before, either way.
            <template v-if="wallet?.auto_renew">
              Paying via <strong class="auto-renew-method-label">{{ methodLabel(wallet.auto_renew_method) }}</strong> —
              <button type="button" class="link-btn" @click="openAutoRenewModal">change</button>.
            </template>
          </span>
        </div>
        <label class="switch">
          <input type="checkbox" :checked="wallet?.auto_renew" @change="onAutoRenewToggle($event.target.checked)" />
          <span class="switch-track"><span class="switch-thumb"></span></span>
        </label>
      </section>

      <!-- ── WALLET CARD (bank-card styling, same functionality) ──── -->
      <section class="wallet-card">
        <div class="bank-card" :class="{ 'card-paying': topupPolling, 'card-success': cardFlash }">
          <div class="bank-card-sheen"></div>
          <div class="bank-card-row-top">
            <span class="bank-chip"><span></span><span></span><span></span></span>
            <span class="bank-brand">STRAT<b>MASTER</b></span>
          </div>

          <div class="bank-card-balance">
            <span class="wallet-label">Balance</span>
            <div class="wallet-balance-row">
              <span class="balance-num">{{ wallet?.balance_coins ?? 0 }}</span>
              <span class="coin-unit">MasterCoins</span>
            </div>
          </div>

          <div class="bank-card-row-bottom">
            <button type="button" class="bank-card-id" @click="copy(wallet?.wallet_id, 'wallet')">
              <span class="wallet-id-label">Wallet ID</span>
              <span class="wallet-id-val">{{ formattedWalletId }}</span>
              <span class="wallet-id-copy">{{ copiedField === 'wallet' ? 'Copied' : 'Copy' }}</span>
            </button>
            <span v-if="hasActiveDiscount" class="discount-chip">-25% active</span>
          </div>

          <!-- Contactless-tap payment animation while a top-up is in flight -->
          <div v-if="topupPolling" class="card-tap-ring"></div>
          <transition name="fade" :duration="250">
            <div v-if="cardFlash" class="card-success-badge">
              <svg viewBox="0 0 24 24" width="28" height="28" fill="none">
                <circle cx="12" cy="12" r="10" fill="var(--success)"/>
                <path d="M7.5 12.5l3 3 6-6.5" stroke="#0d1a10" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/>
              </svg>
            </div>
          </transition>
        </div>

        <button type="button" class="topup-toggle" @click="openTopupModal">
          <svg viewBox="0 0 20 20" width="15" height="15" fill="none">
            <path d="M10 4v12M4 10h12" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"/>
          </svg>
          Top Up MasterCoins
        </button>
      </section>

      <!-- ── HOTBAR ───────────────────────────────────── -->
      <nav class="hotbar">
        <template v-for="tab in TABS" :key="tab.key">
          <router-link v-if="tab.to" :to="tab.to" class="hotbar-btn">
            <span class="hotbar-icon" v-html="tab.icon"></span>
            <span class="hotbar-label">{{ tab.label }}</span>
          </router-link>
          <button
            v-else
            class="hotbar-btn"
            :class="{ active: activeTab === tab.key }"
            @click="toggleTab(tab.key)"
          >
            <span class="hotbar-icon" v-html="tab.icon"></span>
            <span class="hotbar-label">{{ tab.label }}</span>
          </button>
        </template>

        <router-link v-if="user?.is_admin" to="/admin" class="hotbar-btn admin-hotbar-btn">
          <span class="hotbar-icon" v-html="ICONS.admin"></span>
          <span class="hotbar-label">Admin</span>
        </router-link>
      </nav>

      <!-- ── PANEL ────────────────────────────────────── -->
      <!-- Explicit :duration bypasses waiting on the transitionend DOM event —
           if that never fires (backgrounded tab, reduced-motion, or just a
           fast double-click queuing a second transition mid-flight), Vue's
           out-in transition gets stuck showing the outgoing panel forever. -->
      <transition name="panel" mode="out-in" :duration="180">
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

          <div class="block-section">
            <h4>Blocked players</h4>
            <p class="panel-desc">Stop a specific player from sending you transfers, case gifts or sale offers.</p>
            <form class="block-form" @submit.prevent="blockPlayer">
              <input v-model="blockWalletId" type="text" placeholder="Wallet ID to block" class="p2p-input" autocomplete="off" spellcheck="false" :disabled="blockBusy" />
              <button type="submit" class="mini-btn" :disabled="blockBusy || !blockWalletId">Block</button>
            </form>
            <p v-if="blockError" class="panel-message error">{{ blockError }}</p>

            <div v-if="blockedList.length" class="blocked-list">
              <div v-for="b in blockedList" :key="b.wallet_id" class="blocked-row">
                <span>{{ b.username ? '@' + b.username : b.wallet_id }}</span>
                <button class="mini-btn danger" @click="unblockPlayer(b.wallet_id)">Unblock</button>
              </div>
            </div>
            <p v-else class="favorites-placeholder">No one blocked.</p>
          </div>
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

        <section v-else-if="activeTab === 'strategies'" key="strategies" class="panel-wrap panel-card">
          <div class="panel-header">
            <span class="panel-icon" v-html="ICONS.strategies"></span>
            <h3>My Strategies</h3>
          </div>
          <p class="panel-desc">Strategies you've starred — tap the star on any strategy page to pin it here.</p>

          <div v-if="favStrategiesLoading" class="favorites-placeholder">Loading…</div>
          <div v-else-if="!favStrategies.length" class="favorites-placeholder">
            No favorite strategies yet — tap the star on a strategy to pin it here.
          </div>
          <div v-else class="favorites-list">
            <router-link
              v-for="s in favStrategies" :key="s.id"
              :to="'/strategy/' + s.id" class="favorite-row"
            >
              <span class="favorite-row-name">{{ s.title }}</span>
              <span class="favorite-row-badge" :class="s.is_free ? 'free' : 'premium'">
                {{ s.is_free ? 'Free' : 'Premium' }}
              </span>
              <button
                type="button" class="favorite-row-remove"
                @click.prevent="unfavoriteStrategy(s.id)"
                aria-label="Remove from favorites"
              >✕</button>
            </router-link>
          </div>
        </section>

        <section v-else-if="activeTab === 'board'" key="board" class="panel-wrap">
          <BoardsPanel />
        </section>

        <section v-else-if="activeTab === 'cases'" key="cases" class="panel-wrap">
          <CasesPanel :initial-view="route.query.sub === 'offers' ? 'offers' : 'shop'" />
        </section>

        <p v-else key="hint" class="hotbar-hint">Tap an option above to get started.</p>
      </transition>

    </div>

    <Footer />

    <!-- ── TOP UP POPUP ─────────────────────────────────── -->
    <!-- Explicit :duration bypasses waiting on the transitionend DOM event —
         if that never fires (backgrounded tab, reduced-motion), Vue's
         <transition> gets stuck mid-leave forever: an invisible
         position:fixed;inset:0 backdrop keeps blocking every click. -->
    <transition name="fade" :duration="200">
      <div v-if="topupOpen" class="modal-backdrop" @click.self="closeTopupModal">
        <div class="modal">
          <button class="modal-close" @click="closeTopupModal">✕</button>

          <h3 class="modal-title">Top Up MasterCoins</h3>
          <p class="modal-price">${{ ((topupCoins || 0) * 0.01).toFixed(2) }}</p>

          <p class="modal-label">Amount</p>
          <input
            v-model.number="topupCoins" type="number" min="10" placeholder="Amount (min 10)"
            class="topup-amount-input" :disabled="topupBusy || topupPolling"
          />

          <p class="modal-label">Choose payment method</p>
          <div class="payment-options">
            <button class="payment-option selected" disabled>
              <span class="payment-icon">
                <svg viewBox="0 0 24 24" fill="none" width="18" height="18">
                  <path d="M7 5v14M11 5v14M6 8h9a3 3 0 010 6H6M6 13h10a3 3 0 010 6H6" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/>
                </svg>
              </span>
              <span class="payment-info">
                <span class="payment-name">Crypto</span>
                <span class="payment-sub">USDT / BTC / TON</span>
              </span>
              <span class="status-tag ready">Ready</span>
            </button>

            <button class="payment-option disabled" disabled>
              <span class="payment-icon">
                <svg viewBox="0 0 24 24" fill="none" width="18" height="18">
                  <rect x="3" y="6" width="18" height="12" rx="2" stroke="currentColor" stroke-width="1.6"/>
                  <path d="M3 10h18" stroke="currentColor" stroke-width="1.6"/>
                </svg>
              </span>
              <span class="payment-info">
                <span class="payment-name">Google Pay</span>
                <span class="payment-sub">One-tap checkout</span>
              </span>
              <span class="status-tag soon">Coming soon</span>
            </button>
          </div>

          <div class="pay-block">
            <button
              class="btn-primary pay-btn" :disabled="topupBusy || topupPolling || !topupCoins || topupCoins < 10"
              @click="buyCoins"
            >{{ topupPolling ? 'Waiting for payment…' : topupBusy ? 'Processing…' : `Pay $${((topupCoins || 0) * 0.01).toFixed(2)}` }}</button>
            <p v-if="topupMessage" class="pay-message" :class="{ success: topupSuccess }">{{ topupMessage }}</p>
          </div>
        </div>
      </div>
    </transition>

    <!-- ── AUTO-RENEW METHOD POPUP ──────────────────────── -->
    <transition name="fade" :duration="200">
      <div v-if="autoRenewModalOpen" class="modal-backdrop" @click.self="closeAutoRenewModal">
        <div class="modal">
          <button class="modal-close" @click="closeAutoRenewModal">✕</button>

          <h3 class="modal-title">Auto-Renew Method</h3>
          <p class="modal-footnote modal-intro">Pick how Premium should pay for itself when it's about to expire.</p>

          <p class="modal-label">Choose payment method</p>
          <div class="payment-options">
            <button
              class="payment-option" :class="{ selected: autoRenewMethodChoice === 'mastercoins' }"
              @click="autoRenewMethodChoice = 'mastercoins'"
            >
              <span class="payment-icon">
                <svg viewBox="0 0 24 24" fill="none" width="18" height="18">
                  <circle cx="12" cy="12" r="8" stroke="currentColor" stroke-width="1.6"/>
                  <path d="M12 8v8M9.5 9.8c0-.9 1-1.6 2.5-1.6s2.5.7 2.5 1.6c0 2-5 1-5 3 0 .9 1 1.6 2.5 1.6s2.5-.7 2.5-1.6" stroke="currentColor" stroke-width="1.3" stroke-linecap="round"/>
                </svg>
              </span>
              <span class="payment-info">
                <span class="payment-name">MasterCoins</span>
                <span class="payment-sub">Auto-charged from your balance</span>
              </span>
              <span class="status-tag ready">Ready</span>
            </button>

            <button
              class="payment-option" :class="{ selected: autoRenewMethodChoice === 'crypto' }"
              @click="autoRenewMethodChoice = 'crypto'"
            >
              <span class="payment-icon">
                <svg viewBox="0 0 24 24" fill="none" width="18" height="18">
                  <path d="M7 5v14M11 5v14M6 8h9a3 3 0 010 6H6M6 13h10a3 3 0 010 6H6" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/>
                </svg>
              </span>
              <span class="payment-info">
                <span class="payment-name">Crypto</span>
                <span class="payment-sub">We'll send a ready-to-pay link 24h before</span>
              </span>
              <span class="status-tag ready">Ready</span>
            </button>

            <button class="payment-option disabled" disabled>
              <span class="payment-icon">
                <svg viewBox="0 0 24 24" fill="none" width="18" height="18">
                  <rect x="3" y="6" width="18" height="12" rx="2" stroke="currentColor" stroke-width="1.6"/>
                  <path d="M3 10h18" stroke="currentColor" stroke-width="1.6"/>
                </svg>
              </span>
              <span class="payment-info">
                <span class="payment-name">Card</span>
                <span class="payment-sub">Saved-card auto-charge</span>
              </span>
              <span class="status-tag soon">Coming soon</span>
            </button>
          </div>

          <div class="pay-block">
            <button class="btn-primary pay-btn" :disabled="autoRenewSaving" @click="confirmAutoRenew">
              {{ autoRenewSaving ? 'Saving…' : 'Enable Auto-Renew' }}
            </button>
          </div>
        </div>
      </div>
    </transition>
  </main>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { storeToRefs } from 'pinia'
import { useUserStore } from '../store/user'
import { promoAPI } from '../api/promo'
import { subscriptionAPI } from '../api/subscription'
import { walletAPI } from '../api/wallet'
import { paymentsAPI } from '../api/payments'
import { favoritesAPI } from '../api/favorites'
import { authAPI } from '../api/auth'
import { forumAPI } from '../api/forum'
import Header from '../components/Header.vue'
import Footer from '../components/Footer.vue'
import Breadcrumbs from '../components/Breadcrumbs.vue'
import ReferralSection from '../components/ReferralSection.vue'
import BoardsPanel from '../components/BoardsPanel.vue'
import CasesPanel from '../components/CasesPanel.vue'

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()
const { user, wallet } = storeToRefs(userStore)

const copiedField = ref(null)

const promoCode = ref('')
const promoLoading = ref(false)
const promoMessage = ref('')
const promoSuccess = ref(false)

// Default open so the referral code-entry field is immediately visible —
// unless we were redirected here with a specific tab requested (e.g. from
// the old /my-strategies, /boards or /cases links).
const VALID_QUERY_TABS = ['strategies', 'board', 'cases']
const activeTab = ref(VALID_QUERY_TABS.includes(route.query.tab) ? route.query.tab : 'referral')
function toggleTab(key) {
  activeTab.value = activeTab.value === key ? null : key
  if (activeTab.value === 'favorites' && !favoritesLoaded.value) loadFavorites()
  if (activeTab.value === 'strategies' && !favStrategiesLoaded.value) loadFavStrategies()
  if (activeTab.value === 'p2p' && !blockedList.value.length) loadBlocked()
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

// ── Favorite strategies ──────────────────────────────────────────
const favStrategies = ref([])
const favStrategiesLoading = ref(false)
const favStrategiesLoaded = ref(false)

async function loadFavStrategies() {
  favStrategiesLoading.value = true
  try {
    favStrategies.value = await favoritesAPI.listStrategies()
    favStrategiesLoaded.value = true
  } catch (e) {
    console.warn('[User] could not load favorite strategies:', e.response?.data?.detail)
  } finally {
    favStrategiesLoading.value = false
  }
}

async function unfavoriteStrategy(strategyId) {
  favStrategies.value = favStrategies.value.filter(s => s.id !== strategyId)
  try {
    await favoritesAPI.removeStrategy(strategyId)
  } catch (e) {
    await loadFavStrategies() // out of sync — reload to recover the true state
  }
}

onMounted(() => {
  if (activeTab.value === 'strategies' && !favStrategiesLoaded.value) loadFavStrategies()
})

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

// Card-number-style grouping (XXXX XXXX XXXX XXXX) of the 16-char wallet
// ID — purely cosmetic, the copy button still copies the ungrouped value.
const formattedWalletId = computed(() => {
  const id = wallet.value?.wallet_id
  if (!id) return '—'
  return id.match(/.{1,4}/g)?.join(' ') ?? id
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

async function toggleAutoRenew(enabled, method = 'mastercoins') {
  try {
    const res = await subscriptionAPI.setAutoRenew(enabled, method)
    if (wallet.value) {
      wallet.value.auto_renew = res.auto_renew
      wallet.value.auto_renew_method = res.auto_renew_method
    }
  } catch (e) {
    console.warn('[User] could not update auto-renew:', e.response?.data?.detail)
  }
}

function methodLabel(method) {
  return method === 'crypto' ? 'Crypto' : 'MasterCoins'
}

function onAutoRenewToggle(checked) {
  if (!checked) {
    toggleAutoRenew(false, wallet.value?.auto_renew_method || 'mastercoins')
    return
  }
  openAutoRenewModal()
}

const autoRenewModalOpen = ref(false)
const autoRenewMethodChoice = ref('mastercoins')
const autoRenewSaving = ref(false)

function openAutoRenewModal() {
  autoRenewMethodChoice.value = wallet.value?.auto_renew_method || 'mastercoins'
  autoRenewModalOpen.value = true
}
function closeAutoRenewModal() {
  autoRenewModalOpen.value = false
}
async function confirmAutoRenew() {
  autoRenewSaving.value = true
  try {
    await toggleAutoRenew(true, autoRenewMethodChoice.value)
    autoRenewModalOpen.value = false
  } finally {
    autoRenewSaving.value = false
  }
}

// ── Top up MasterCoins with crypto ────────────────────────────────
const topupOpen = ref(false)
const topupCoins = ref(100)
const topupBusy = ref(false)
const topupPolling = ref(false)
const topupMessage = ref('')
const topupSuccess = ref(false)
const cardFlash = ref(false) // brief checkmark/glow flourish on the wallet card
let topupPollTimer = null

function stopTopupPolling() {
  if (topupPollTimer) { clearInterval(topupPollTimer); topupPollTimer = null }
  topupPolling.value = false
}

function openTopupModal() {
  topupCoins.value = 100
  topupMessage.value = ''
  topupSuccess.value = false
  topupOpen.value = true
}
function closeTopupModal() {
  stopTopupPolling()
  topupOpen.value = false
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
          cardFlash.value = true
          setTimeout(() => { cardFlash.value = false }, 2200)
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

// ── Trade blocking ────────────────────────────────
const blockedList = ref([])
const blockWalletId = ref('')
const blockBusy = ref(false)
const blockError = ref('')

async function loadBlocked() {
  try {
    blockedList.value = await walletAPI.listBlocked()
  } catch (e) {
    // Not critical to the page.
  }
}

async function blockPlayer() {
  if (!blockWalletId.value.trim() || blockBusy.value) return
  blockBusy.value = true
  blockError.value = ''
  try {
    await walletAPI.block(blockWalletId.value.trim())
    blockWalletId.value = ''
    await loadBlocked()
  } catch (e) {
    blockError.value = e.response?.data?.detail || 'Could not block that wallet ID.'
  } finally {
    blockBusy.value = false
  }
}

async function unblockPlayer(walletId) {
  await walletAPI.unblock(walletId)
  await loadBlocked()
}

// ── Avatar upload (premium only) ──────────────────────────────────
const avatarUploading = ref(false)

async function onAvatarChange(e) {
  const file = e.target.files[0]
  e.target.value = ''
  if (!file || avatarUploading.value) return

  avatarUploading.value = true
  try {
    const uploaded = await forumAPI.uploadImage(file)
    const updated = await authAPI.updateAvatar(uploaded.url)
    if (user.value) user.value.avatar_url = updated.avatar_url
  } catch (e) {
    console.warn('[User] avatar upload failed:', e.response?.data?.detail)
  } finally {
    avatarUploading.value = false
  }
}

// ── Nickname (open to everyone, not just premium) ──────────────────
const nicknameEditing = ref(false)
const nicknameDraft = ref('')
const nicknameBusy = ref(false)

function startEditNickname() {
  nicknameDraft.value = user.value?.display_name || ''
  nicknameEditing.value = true
}

async function saveNickname() {
  if (nicknameBusy.value) return
  nicknameBusy.value = true
  try {
    const updated = await authAPI.updateNickname(nicknameDraft.value.trim() || null)
    if (user.value) user.value.display_name = updated.display_name
    nicknameEditing.value = false
  } catch (e) {
    console.warn('[User] could not update nickname:', e.response?.data?.detail)
  } finally {
    nicknameBusy.value = false
  }
}

function copy(text, field) {
  if (!text) return
  navigator.clipboard.writeText(text).then(() => {
    copiedField.value = field
    setTimeout(() => { copiedField.value = null }, 1800)
  }).catch(() => {
    // Clipboard permission denied/unavailable — nothing useful to do beyond
    // not leaving an unhandled rejection; the user just sees "Copy" stay put.
  })
}

async function redeemPromo() {
  if (!promoCode.value) return
  promoLoading.value = true
  promoMessage.value = ''
  try {
    const res = await promoAPI.redeem(promoCode.value.trim())
    promoSuccess.value = true
    if (res.reward_type === 'premium') {
      promoMessage.value = res.is_lifetime ? 'Lifetime Premium activated!' : `+${res.premium_days} days of Premium activated!`
      if (wallet.value) {
        wallet.value.subscription_expires_at = res.new_subscription_expires_at
        wallet.value.is_lifetime = res.is_lifetime
      }
    } else if (res.reward_type === 'case') {
      promoMessage.value = `You received ${res.case_quantity}× ${res.case_name}! Check your Cases inventory.`
    } else {
      promoMessage.value = `+${res.coins_awarded} MasterCoins added!`
      if (wallet.value) wallet.value.balance_coins = res.new_balance
    }
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
  strategies: `<svg viewBox="0 0 24 24" fill="none" width="20" height="20">
    <path d="M12 3.5l2.82 5.71 6.3.92-4.56 4.44 1.08 6.27L12 17.77l-5.64 3.07 1.08-6.27-4.56-4.44 6.3-.92L12 3.5z" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round"/>
  </svg>`,
  board: `<svg viewBox="0 0 24 24" fill="none" width="20" height="20">
    <rect x="3.5" y="4.5" width="17" height="12" rx="1.4" stroke="currentColor" stroke-width="1.6"/>
    <path d="M8 20h8M12 16.5V20" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/>
    <path d="M7 12l3-3 2.5 2.5L17 7" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/>
  </svg>`,
  cases: `<svg viewBox="0 0 24 24" fill="none" width="20" height="20">
    <rect x="4" y="9" width="16" height="11" rx="1.4" stroke="currentColor" stroke-width="1.6"/>
    <path d="M4 13h16" stroke="currentColor" stroke-width="1.6"/>
    <path d="M9 9V7a3 3 0 016 0v2" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/>
  </svg>`,
  admin: `<svg viewBox="0 0 24 24" fill="none" width="20" height="20">
    <path d="M14.7 6.3a4 4 0 00-5.4 4.6L4 16.2V20h3.8l5.3-5.3a4 4 0 004.6-5.4l-2.6 2.6-2-2 2.6-2.6z"
          stroke="currentColor" stroke-width="1.6" stroke-linejoin="round" stroke-linecap="round"/>
  </svg>`,
}

const TABS = [
  { key: 'referral',   label: 'Referral',   icon: ICONS.referral },
  { key: 'promo',      label: 'Promo',      icon: ICONS.promo },
  { key: 'p2p',        label: 'P2P',        icon: ICONS.p2p },
  { key: 'favorites',  label: 'Maps',       icon: ICONS.favorites },
  { key: 'strategies', label: 'Strategies', icon: ICONS.strategies },
  { key: 'board',      label: 'My Board',   icon: ICONS.board },
  { key: 'cases',      label: 'Cases',      icon: ICONS.cases },
]
</script>

<style scoped>
.user-page { min-height: 100vh; background: var(--bg); }
.user-content { max-width: 640px; padding: 20px 16px 100px; transition: max-width .2s; }
.user-content-wide { max-width: 960px; }

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
  position: relative;
  width: 48px; height: 48px; border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  background: linear-gradient(135deg, var(--accent), var(--accent-2));
  color: #14140f; font-size: 19px; font-weight: 900;
  flex-shrink: 0; overflow: hidden;
}
.avatar-img { width: 100%; height: 100%; object-fit: cover; }
.avatar.uploadable { cursor: pointer; }
.avatar-edit-badge {
  position: absolute; bottom: -2px; right: -2px;
  width: 18px; height: 18px; border-radius: 50%;
  background: var(--bg-elevated); border: 2px solid var(--bg);
  color: var(--accent); font-size: 9px;
  display: flex; align-items: center; justify-content: center;
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

.nickname-edit-btn {
  flex-shrink: 0; background: none; border: none; color: var(--text-dim);
  cursor: pointer; font-size: 12px; padding: 2px 4px; border-radius: 6px;
  transition: color .15s, background .15s;
}
.nickname-edit-btn:hover { color: var(--accent); background: rgba(255,154,0,.1); }

.nickname-edit-row { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; }
.nickname-input {
  min-width: 0; flex: 1; background: var(--bg); border: 1px solid var(--line); border-radius: 8px;
  padding: 7px 10px; color: var(--text); font-size: 13.5px; font-family: inherit;
}
.nickname-input:focus { outline: none; border-color: var(--accent); }

.username-sub { font-size: 11.5px; color: var(--text-dim); margin-top: -3px; }

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
.auto-renew-method-label { color: var(--text); }
.link-btn {
  background: none; border: none; padding: 0; margin: 0;
  color: var(--accent); font-size: 12px; font-weight: 700;
  cursor: pointer; text-decoration: underline;
}
.modal-intro { text-align: left; margin: 0 0 4px; }

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
.wallet-card { margin-bottom: 16px; }

/* ── Bank-card-styled balance display ─────────────────────────
   Purely visual — same data (balance, wallet ID, discount, top-up)
   as before, just laid out like a physical card. */
.bank-card {
  position: relative; overflow: hidden;
  background: linear-gradient(135deg, #1a1710 0%, #2b2115 45%, #1a1710 100%);
  border: 1px solid rgba(255,154,0,.3);
  border-radius: 18px;
  padding: 20px 22px;
  box-shadow: 0 14px 34px -16px rgba(0,0,0,.65), inset 0 1px 0 rgba(255,255,255,.04);
  aspect-ratio: 1.586 / 1;
  display: flex; flex-direction: column; justify-content: space-between;
  transition: transform .4s ease, box-shadow .4s ease;
}
.bank-card-sheen {
  position: absolute; inset: 0; pointer-events: none;
  background: linear-gradient(115deg, transparent 30%, rgba(255,154,0,.14) 48%, transparent 62%);
}

/* Contactless-tap style animation while a top-up payment is being awaited */
.bank-card.card-paying {
  animation: cardTapPulse 1.7s ease-in-out infinite;
}
@keyframes cardTapPulse {
  0%, 100% { transform: perspective(700px) rotateX(0deg) rotateY(0deg) scale(1); }
  50% { transform: perspective(700px) rotateX(1.5deg) rotateY(-3deg) scale(1.012); }
}
.card-tap-ring {
  position: absolute; top: 18px; right: 20px; z-index: 2;
  width: 22px; height: 22px; border-radius: 50%;
  border: 2px solid rgba(255,154,0,.6);
  animation: cardTapRing 1.4s ease-out infinite;
}
@keyframes cardTapRing {
  0% { transform: scale(0.5); opacity: 1; }
  100% { transform: scale(2.2); opacity: 0; }
}

/* Success flourish once the invoice is confirmed paid */
.bank-card.card-success {
  animation: cardSuccessGlow 1s ease-out;
}
@keyframes cardSuccessGlow {
  0% { box-shadow: 0 0 0 0 rgba(80,220,100,.55), 0 14px 34px -16px rgba(0,0,0,.65); }
  60% { box-shadow: 0 0 0 22px rgba(80,220,100,0), 0 14px 34px -16px rgba(0,0,0,.65); }
  100% { box-shadow: 0 0 0 0 rgba(80,220,100,0), 0 14px 34px -16px rgba(0,0,0,.65); }
}
.card-success-badge {
  position: absolute; inset: 0; z-index: 3;
  display: flex; align-items: center; justify-content: center;
  background: rgba(10,10,8,.55); border-radius: 18px;
}

.bank-card-row-top { position: relative; z-index: 1; display: flex; align-items: center; justify-content: space-between; }
.bank-chip {
  width: 34px; height: 25px; border-radius: 5px; flex-shrink: 0;
  background: linear-gradient(155deg, #ffe2a3, #d9a441);
  display: flex; flex-direction: column; justify-content: center; gap: 3px; padding: 0 5px;
}
.bank-chip span { display: block; height: 1px; background: rgba(0,0,0,.35); }
.bank-brand { font-size: 11px; font-weight: 700; letter-spacing: .12em; color: rgba(255,255,255,.55); }
.bank-brand b { color: var(--accent); font-weight: 900; }

.bank-card-balance { position: relative; z-index: 1; }
.wallet-label {
  display: block;
  font-size: 10.5px; font-weight: 700; letter-spacing: .09em;
  text-transform: uppercase; color: rgba(255,255,255,.45);
  margin-bottom: 6px;
}
.wallet-balance-row { display: flex; align-items: baseline; gap: 8px; }
.balance-num {
  font-size: 32px; font-weight: 900; color: var(--accent);
  letter-spacing: -.02em; font-variant-numeric: tabular-nums;
}
.coin-unit { font-size: 12px; color: rgba(255,255,255,.45); font-weight: 600; }

.bank-card-row-bottom { position: relative; z-index: 1; display: flex; align-items: center; justify-content: space-between; gap: 10px; }
.bank-card-id {
  display: flex; flex-direction: column; align-items: flex-start; gap: 2px;
  background: none; border: none; cursor: pointer; padding: 0; min-width: 0; flex: 1;
}
.wallet-id-label {
  font-size: 9px; font-weight: 700; letter-spacing: .1em; text-transform: uppercase;
  color: rgba(255,255,255,.4);
}
.wallet-id-val {
  font-size: 14px; font-weight: 700; color: #fff; letter-spacing: .04em;
  font-variant-numeric: tabular-nums; font-family: 'Courier New', monospace;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 100%;
}
.bank-card-id .wallet-id-copy {
  font-size: 9.5px; font-weight: 700; color: var(--accent);
  text-transform: uppercase; letter-spacing: .04em;
}

.discount-chip {
  flex-shrink: 0;
  padding: 4px 11px; border-radius: 99px;
  background: rgba(80,220,100,0.16);
  border: 1px solid rgba(80,220,100,0.5);
  color: var(--success);
  font-size: 11px; font-weight: 700;
}

.topup-toggle {
  display: flex; align-items: center; justify-content: center; gap: 7px;
  width: 100%; margin-top: 14px;
  background: linear-gradient(160deg, #ffc266 0%, var(--accent) 48%, #cc7300 100%);
  color: #fff; text-shadow: 0 1px 2px rgba(0,0,0,.28);
  border: 1px solid rgba(255,255,255,.14);
  font-size: 13.5px; font-weight: 700; padding: 12px 16px; border-radius: 10px;
  letter-spacing: .01em;
  cursor: pointer; transition: transform .15s, box-shadow .15s, filter .15s;
  box-shadow: 0 6px 18px -8px rgba(255,154,0,.5), inset 0 1px 0 rgba(255,255,255,.22);
}
.topup-toggle:hover { transform: translateY(-1px); filter: brightness(1.05); box-shadow: 0 12px 26px -10px rgba(255,154,0,.55), inset 0 1px 0 rgba(255,255,255,.26); }
.topup-toggle:active { transform: translateY(0); filter: brightness(0.97); }

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

.block-section { margin-top: 24px; padding-top: 20px; border-top: 1px solid var(--line); }
.block-section h4 { font-size: 13.5px; font-weight: 800; color: var(--text); margin-bottom: 4px; }
.block-form { display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 10px; }
.block-form .p2p-input { flex: 1; min-width: 160px; }
.blocked-list { display: flex; flex-direction: column; gap: 6px; }
.blocked-row {
  display: flex; align-items: center; justify-content: space-between; gap: 10px;
  padding: 9px 12px; background: var(--bg); border: 1px solid var(--line); border-radius: 8px;
  font-size: 13px; color: var(--text);
}

.mini-btn {
  background: linear-gradient(160deg, var(--bg-elevated), var(--bg)); border: 1px solid var(--line); color: var(--text-dim);
  padding: 7px 13px; border-radius: 7px; font-size: 12px; font-weight: 700; cursor: pointer;
  box-shadow: 0 2px 6px rgba(0,0,0,.18);
  transition: border-color .15s, color .15s, transform .15s, box-shadow .15s; white-space: nowrap;
}
.mini-btn:hover:not(:disabled) { border-color: var(--accent); color: var(--accent); box-shadow: 0 4px 14px -4px rgba(255,154,0,.4); transform: translateY(-1px); }
.mini-btn:disabled { opacity: .5; cursor: not-allowed; }
.mini-btn.danger:hover { border-color: var(--danger); color: var(--danger); box-shadow: 0 4px 14px -4px rgba(235,75,75,.4); }

.favorites-placeholder {
  padding: 20px 0; text-align: center;
  font-size: 12px; color: var(--text-dim);
  border: 1px dashed var(--line); border-radius: 10px;
}

.favorites-list { display: flex; flex-direction: column; gap: 8px; }
.favorite-row {
  display: flex; align-items: center; justify-content: space-between; gap: 10px;
  padding: 12px 14px;
  background: var(--bg); border: 1px solid var(--line); border-radius: 10px;
  text-decoration: none; transition: border-color .15s;
}
.favorite-row:hover { border-color: var(--accent); }
.favorite-row-name { font-size: 13.5px; font-weight: 700; color: var(--text); flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.favorite-row-badge {
  flex-shrink: 0; padding: 2px 8px; border-radius: 99px;
  font-size: 10px; font-weight: 800; text-transform: uppercase; letter-spacing: .04em;
}
.favorite-row-badge.free { background: rgba(80,220,100,.14); color: var(--success); }
.favorite-row-badge.premium { background: rgba(255,154,0,.15); color: var(--accent); }
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

/* ── Top Up modal — same shell as the Pricing page's purchase popup ── */
.modal-backdrop {
  position: fixed; inset: 0; z-index: 500;
  background: rgba(0,0,0,0.6);
  display: flex; align-items: center; justify-content: center;
  padding: 20px; backdrop-filter: blur(4px); overflow-y: auto;
}
.modal {
  position: relative; width: 100%; max-width: 400px;
  background: var(--bg-elevated); border: 1px solid var(--line);
  border-radius: var(--radius-lg); padding: 32px 28px 26px; margin: auto;
}
.modal-close {
  position: absolute; top: 16px; right: 16px;
  width: 30px; height: 30px; border-radius: 8px;
  background: var(--bg); border: 1px solid var(--line);
  color: var(--text-dim); cursor: pointer;
  display: flex; align-items: center; justify-content: center;
  font-size: 13px; transition: border-color .15s, color .15s;
}
.modal-close:hover { border-color: var(--accent); color: var(--accent); }
.modal-title { font-size: 20px; font-weight: 800; color: var(--text); margin-bottom: 4px; }
.modal-price { font-size: 24px; font-weight: 900; color: var(--accent); margin-bottom: 4px; }
.modal-label {
  font-size: 11px; font-weight: 700; letter-spacing: .06em;
  text-transform: uppercase; color: var(--text-dim);
  margin-bottom: 12px; margin-top: 20px;
}
.topup-amount-input {
  width: 100%; padding: 11px 12px;
  background: var(--bg); border: 1px solid var(--line); border-radius: 9px;
  color: var(--text); font-size: 14px; font-family: inherit;
}
.topup-amount-input:focus { outline: none; border-color: var(--accent); }

.payment-options { display: flex; flex-direction: column; gap: 10px; margin-bottom: 6px; }
.payment-option {
  display: flex; align-items: center; gap: 12px; padding: 14px 16px;
  background: var(--bg); border: 1.5px solid var(--line); border-radius: 10px;
  cursor: pointer; transition: border-color .2s, background .2s;
  width: 100%; text-align: left;
}
.payment-option.selected { border-color: var(--accent); background: rgba(255,154,0,0.08); }
.payment-option.disabled { opacity: .5; cursor: not-allowed; }
.payment-icon {
  color: var(--text); width: 34px; height: 34px;
  display: flex; align-items: center; justify-content: center;
  background: var(--bg-elevated-2); border-radius: 8px; flex-shrink: 0;
}
.payment-info { display: flex; flex-direction: column; gap: 2px; flex: 1; text-align: left; min-width: 0; }
.payment-name { font-size: 14px; font-weight: 700; color: var(--text); }
.payment-sub { font-size: 11px; color: var(--text-dim); }
.status-tag {
  padding: 3px 8px; border-radius: 6px; font-size: 9px; font-weight: 700;
  text-transform: uppercase; letter-spacing: .04em; flex-shrink: 0;
}
.status-tag.soon { background: var(--bg-elevated-2); color: var(--text-dim); }
.status-tag.ready { background: rgba(80,220,100,0.15); color: var(--success); }

.pay-block { margin-top: 20px; }
.pay-btn { width: 100%; font-size: 14px; padding: 13px; }
.pay-btn:disabled { opacity: .7; cursor: not-allowed; }
.pay-message { margin-top: 10px; font-size: 12.5px; color: var(--text-dim); text-align: center; line-height: 1.5; }
.pay-message.success { color: var(--success); font-weight: 700; }

.fade-enter-active, .fade-leave-active { transition: opacity .2s; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>
