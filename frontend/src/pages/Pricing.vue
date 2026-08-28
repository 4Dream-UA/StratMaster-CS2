<template>
  <main class="pricing-page">
    <Header />

    <div class="wrap pricing-content">

      <button class="back-btn" @click="router.push('/')">
        <svg viewBox="0 0 16 16" fill="none" width="14" height="14">
          <path d="M10 3L5 8l5 5" stroke="currentColor" stroke-width="2"
                stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
        Home
      </button>

      <!-- ── HERO ─────────────────────────────────────── -->
      <section class="pricing-hero">
        <h1>Unlock <span class="accent">Premium</span> Strategies</h1>
        <p>Every plan gives full access to pro-level lineups, grenade timings and win-rate-tested executes.</p>
      </section>

      <!-- ── ACTIVE DISCOUNT BANNER ─────────────────────── -->
      <section v-if="hasActiveDiscount" class="discount-banner">
        <svg viewBox="0 0 24 24" fill="none" width="20" height="20">
          <path d="M11 4h6a1 1 0 011 1v6a1 1 0 01-.3.7l-8 8a1 1 0 01-1.4 0l-6-6a1 1 0 010-1.4l8-8A1 1 0 0111 4z" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round"/>
          <circle cx="15.5" cy="8.5" r="1.3" fill="currentColor"/>
        </svg>
        <span>Your referral discount is active — <strong>-{{ DISCOUNT_PERCENT }}%</strong> on any plan below.</span>
      </section>

      <!-- ── PLANS ────────────────────────────────────── -->
      <section class="plans-grid">

        <!-- Free -->
        <div class="plan-card" :class="{ 'is-current': currentTier === 'free' }">
          <span v-if="currentTier === 'free'" class="plan-tag current-tag">Current Plan</span>
          <div class="plan-head">
            <h3>Free</h3>
            <p class="plan-price"><span class="price-num">$0</span></p>
          </div>
          <ul class="plan-features">
            <li><Check /> Access to free strategies</li>
            <li><Check /> Basic grenade lineups</li>
            <li><Check /> Community Telegram</li>
            <li class="disabled"><Cross /> Premium strategy library</li>
            <li class="disabled"><Cross /> Timing screenshots</li>
            <li class="disabled"><Cross /> Priority updates</li>
          </ul>
          <button class="btn-secondary plan-btn" disabled>
            {{ currentTier === 'free' ? 'Current Plan' : 'Included' }}
          </button>
        </div>

        <!-- Premium -->
        <div class="plan-card featured" :class="{ 'is-current': currentTier === 'premium' }">
          <span v-if="currentTier === 'premium'" class="plan-tag current-tag">Current Plan</span>
          <span v-else class="plan-tag">Most Popular</span>
          <div class="plan-head">
            <h3>Premium</h3>
            <p v-if="currentTier === 'premium'" class="plan-status">
              Active — {{ daysRemaining }} day{{ daysRemaining === 1 ? '' : 's' }} left
            </p>
            <p class="plan-price">
              <span class="price-from">from</span>
              <template v-if="hasActiveDiscount">
                <span class="price-num-strike">${{ PREMIUM_DURATIONS[0].usd.toFixed(2) }}</span>
                <span class="price-num discounted">${{ discounted(PREMIUM_DURATIONS[0].usd).toFixed(2) }}</span>
              </template>
              <span v-else class="price-num">${{ PREMIUM_DURATIONS[0].usd.toFixed(2) }}</span>
              <span class="price-period">/month</span>
            </p>
          </div>
          <ul class="plan-features">
            <li><Check /> Everything in Free</li>
            <li><Check /> Full premium strategy library</li>
            <li><Check /> Grenade lineup videos</li>
            <li><Check /> Timing screenshots for every execute</li>
            <li><Check /> New strategies weekly</li>
            <li><Check /> Priority support</li>
          </ul>
          <button
            v-if="currentTier === 'lifetime'"
            class="btn-secondary plan-btn" disabled
          >Included in Lifetime</button>
          <button v-else class="btn-primary plan-btn" @click="openPayment('premium')">
            {{ currentTier === 'premium' ? 'Extend / Renew' : 'Get Premium' }}
          </button>
        </div>

        <!-- Lifetime -->
        <div class="plan-card" :class="{ 'is-current': currentTier === 'lifetime' }">
          <span v-if="currentTier === 'lifetime'" class="plan-tag current-tag">Current Plan</span>
          <span v-else class="plan-tag lifetime-tag">Best Value</span>
          <div class="plan-head">
            <h3>Lifetime</h3>
            <p class="plan-price">
              <template v-if="hasActiveDiscount">
                <span class="price-num-strike">${{ LIFETIME.usd.toFixed(2) }}</span>
                <span class="price-num discounted">${{ discounted(LIFETIME.usd).toFixed(2) }}</span>
              </template>
              <span v-else class="price-num">${{ LIFETIME.usd.toFixed(2) }}</span>
              <span class="price-period">once</span>
            </p>
          </div>
          <ul class="plan-features">
            <li><Check /> Everything in Premium</li>
            <li><Check /> Pay once, own forever</li>
            <li><Check /> All future maps &amp; updates</li>
            <li><Check /> Exclusive Discord role</li>
            <li><Check /> Early access to new features</li>
          </ul>
          <button class="btn-primary plan-btn" :disabled="currentTier === 'lifetime'" @click="openPayment('lifetime')">
            {{ currentTier === 'lifetime' ? 'Current Plan' : 'Get Lifetime' }}
          </button>
        </div>

      </section>

      <!-- ── MASTERCOINS NOTE ──────────────────────────── -->
      <section class="coins-note">
        <span class="coins-icon">
          <svg viewBox="0 0 24 24" fill="none" width="20" height="20">
            <circle cx="12" cy="12" r="8" stroke="currentColor" stroke-width="1.6"/>
            <path d="M12 8v8M9.5 9.8c0-.9 1-1.6 2.5-1.6s2.5.7 2.5 1.6c0 2-5 1-5 3 0 .9 1 1.6 2.5 1.6s2.5-.7 2.5-1.6" stroke="currentColor" stroke-width="1.3" stroke-linecap="round"/>
          </svg>
        </span>
        <p>
          Prefer to pay with <strong>MasterCoins</strong>? Earn them through referrals and promo codes,
          then use them for any plan right here — just pick MasterCoins as your payment method.
        </p>
      </section>

      <!-- ── FEATURE COMPARISON ────────────────────────── -->
      <section class="compare-section">
        <h2 class="section-title">Compare Plans</h2>

        <div class="compare-table">
          <div class="compare-row compare-head">
            <span class="compare-feature"></span>
            <span>Free</span>
            <span>Premium</span>
            <span>Lifetime</span>
          </div>

          <div v-for="row in COMPARE_ROWS" :key="row.label" class="compare-row">
            <span class="compare-feature">{{ row.label }}</span>
            <span><Check v-if="row.free" /><Cross v-else /></span>
            <span><Check v-if="row.premium" /><Cross v-else /></span>
            <span><Check v-if="row.lifetime" /><Cross v-else /></span>
          </div>
        </div>
      </section>

    </div>

    <Footer />

    <!-- ── PAYMENT POPUP ────────────────────────────────── -->
    <transition name="fade">
      <div v-if="popupOpen" class="modal-backdrop" @click.self="closePayment">
        <div class="modal">
          <button class="modal-close" @click="closePayment">✕</button>

          <h3 class="modal-title">{{ selectedPlanKey === 'premium' ? 'Premium' : 'Lifetime' }}</h3>

          <p class="modal-price">
            <template v-if="hasActiveDiscount">
              <span class="modal-price-strike">{{ formattedPrice(false) }}</span>
              <span class="modal-price-final">{{ formattedPrice(true) }}</span>
            </template>
            <template v-else>{{ formattedPrice(true) }}</template>
          </p>
          <p v-if="hasActiveDiscount" class="modal-discount-note">Referral discount applied — {{ DISCOUNT_PERCENT }}% off</p>

          <template v-if="selectedPlanKey === 'premium'">
            <p class="modal-label">Choose duration</p>
            <div class="duration-options">
              <button
                v-for="(d, i) in PREMIUM_DURATIONS" :key="d.months"
                class="duration-option"
                :class="{ active: i === selectedDurationIdx }"
                @click="selectedDurationIdx = i"
              >
                <span class="duration-label">{{ d.label }}</span>
                <span class="duration-price">{{ durationPriceLabel(d) }}</span>
              </button>
            </div>
          </template>

          <p class="modal-label">Choose payment method</p>

          <div class="payment-options">
            <button
              class="payment-option"
              :class="{ selected: selectedMethod === 'crypto' }"
              @click="selectMethod('crypto')"
            >
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

            <button
              class="payment-option"
              :class="{ selected: selectedMethod === 'mastercoins' }"
              @click="selectMethod('mastercoins')"
            >
              <span class="payment-icon">
                <svg viewBox="0 0 24 24" fill="none" width="18" height="18">
                  <circle cx="12" cy="12" r="8" stroke="currentColor" stroke-width="1.6"/>
                  <path d="M12 8v8M9.5 9.8c0-.9 1-1.6 2.5-1.6s2.5.7 2.5 1.6c0 2-5 1-5 3 0 .9 1 1.6 2.5 1.6s2.5-.7 2.5-1.6" stroke="currentColor" stroke-width="1.3" stroke-linecap="round"/>
                </svg>
              </span>
              <span class="payment-info">
                <span class="payment-name">MasterCoins</span>
                <span class="payment-sub">Use your balance</span>
              </span>
              <span class="status-tag ready">Ready</span>
            </button>
          </div>

          <!-- Pay button appears once a real method is chosen -->
          <transition name="fade" mode="out-in">
            <div v-if="selectedMethod" key="pay" class="pay-block">
              <button class="btn-primary pay-btn" :disabled="purchasing || paySuccess || cryptoPolling" @click="handlePayClick">
                {{ cryptoPolling ? 'Waiting for payment…' : purchasing ? 'Processing…' : paySuccess ? 'Unlocked' : `Pay ${formattedPrice(true)}` }}
              </button>
              <p v-if="payMessage" class="pay-message" :class="{ success: paySuccess }">{{ payMessage }}</p>
            </div>
            <p v-else key="hint" class="modal-footnote">Pick a payment method above to continue.</p>
          </transition>
        </div>
      </div>
    </transition>
  </main>
</template>

<script setup>
import { ref, computed, watch, onUnmounted, h } from 'vue'
import { useRouter } from 'vue-router'
import { storeToRefs } from 'pinia'
import { useUserStore } from '../store/user'
import { subscriptionAPI } from '../api/subscription'
import { paymentsAPI } from '../api/payments'
import Header from '../components/Header.vue'
import Footer from '../components/Footer.vue'

const router = useRouter()
const userStore = useUserStore()
const { wallet } = storeToRefs(userStore)

const DISCOUNT_PERCENT = 25

const hasActiveDiscount = computed(() => {
  const exp = wallet.value?.ref_discount_expires_at
  return exp && new Date(exp) > new Date()
})

const isSubscribed = computed(() => {
  const exp = wallet.value?.subscription_expires_at
  return exp && new Date(exp) > new Date()
})

// 'free' | 'premium' | 'lifetime' — drives which card shows "Current Plan"
const currentTier = computed(() => {
  if (wallet.value?.is_lifetime) return 'lifetime'
  if (isSubscribed.value) return 'premium'
  return 'free'
})

const daysRemaining = computed(() => {
  const exp = wallet.value?.subscription_expires_at
  if (!exp) return 0
  return Math.max(0, Math.ceil((new Date(exp) - new Date()) / 86400000))
})

function discounted(usd) {
  return usd * (1 - DISCOUNT_PERCENT / 100)
}
function discountedMc(mc) {
  return Math.round(mc * (1 - DISCOUNT_PERCENT / 100))
}

const PREMIUM_DURATIONS = [
  { months: 1,  usd: 0.99, mc: 99,  label: '1 Month' },
  { months: 3,  usd: 2.55, mc: 255, label: '3 Months' },
  { months: 6,  usd: 4.99, mc: 499, label: '6 Months' },
  { months: 12, usd: 9.99, mc: 999, label: '12 Months' },
]
const LIFETIME = { usd: 49.99, mc: 4999 }

const popupOpen = ref(false)
const selectedPlanKey = ref('') // 'premium' | 'lifetime'
const selectedDurationIdx = ref(0)
const selectedMethod = ref('mastercoins') // pre-selected on open, per spec
const payMessage = ref('')
const paySuccess = ref(false)
const purchasing = ref(false)

const cryptoPolling = ref(false)
let cryptoPollTimer = null

function stopCryptoPolling() {
  if (cryptoPollTimer) { clearInterval(cryptoPollTimer); cryptoPollTimer = null }
  cryptoPolling.value = false
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

function startCryptoPolling(invoiceId) {
  cryptoPolling.value = true
  cryptoPollTimer = setInterval(async () => {
    try {
      const res = await paymentsAPI.getCryptoInvoiceStatus(invoiceId)
      if (res.status === 'paid') {
        stopCryptoPolling()
        paySuccess.value = true
        payMessage.value = 'Payment received — enjoy your access!'
        await userStore.fetchMe()
      }
    } catch (e) {
      // transient network hiccup — keep polling, the interval will retry
    }
  }, 3000)
}

onUnmounted(stopCryptoPolling)

function durationPriceLabel(d) {
  if (selectedMethod.value === 'mastercoins') {
    const mc = hasActiveDiscount.value ? discountedMc(d.mc) : d.mc
    return `${mc} MC`
  }
  const usd = hasActiveDiscount.value ? discounted(d.usd) : d.usd
  return `$${usd.toFixed(2)}`
}

// Formatted current selection price. showFinal=true applies the discount (if any).
function formattedPrice(showFinal) {
  const isMc = selectedMethod.value === 'mastercoins'
  const base = selectedPlanKey.value === 'premium'
    ? PREMIUM_DURATIONS[selectedDurationIdx.value]
    : null
  const usd = base ? base.usd : LIFETIME.usd
  const mc  = base ? base.mc  : LIFETIME.mc

  if (isMc) {
    const val = showFinal && hasActiveDiscount.value ? discountedMc(mc) : mc
    return `${val} MC`
  }
  const val = showFinal && hasActiveDiscount.value ? discounted(usd) : usd
  return `$${val.toFixed(2)}`
}

function selectMethod(method) {
  stopCryptoPolling()
  selectedMethod.value = method
  payMessage.value = ''
  paySuccess.value = false
}

function openPayment(planKey) {
  stopCryptoPolling()
  selectedPlanKey.value = planKey
  selectedDurationIdx.value = 0
  selectedMethod.value = 'mastercoins' // default to the only live checkout path
  payMessage.value = ''
  paySuccess.value = false
  popupOpen.value = true
}
function closePayment() {
  stopCryptoPolling()
  popupOpen.value = false
}

async function handlePayClick() {
  if (selectedMethod.value === 'crypto') {
    if (purchasing.value || cryptoPolling.value) return
    purchasing.value = true
    payMessage.value = ''
    try {
      const months = selectedPlanKey.value === 'premium' ? PREMIUM_DURATIONS[selectedDurationIdx.value].months : null
      const invoice = await paymentsAPI.createCryptoInvoice({ plan: selectedPlanKey.value, months })
      openInvoiceLink(invoice.pay_url)
      startCryptoPolling(invoice.invoice_id)
      payMessage.value = 'Complete the payment in the window that just opened — this page updates automatically once it clears.'
    } catch (e) {
      payMessage.value = e.response?.data?.detail || 'Could not start checkout — please try again.'
    } finally {
      purchasing.value = false
    }
    return
  }

  if (purchasing.value) return
  purchasing.value = true
  payMessage.value = ''
  try {
    const months = selectedPlanKey.value === 'premium' ? PREMIUM_DURATIONS[selectedDurationIdx.value].months : null
    const res = await subscriptionAPI.purchase(selectedPlanKey.value, months)
    paySuccess.value = true
    payMessage.value = `Unlocked! ${res.coins_spent} MC spent — enjoy your ${selectedPlanKey.value === 'lifetime' ? 'lifetime' : 'premium'} access.`
    if (wallet.value) {
      wallet.value.balance_coins = res.new_balance
      wallet.value.subscription_expires_at = res.subscription_expires_at
    }
  } catch (e) {
    paySuccess.value = false
    payMessage.value = e.response?.data?.detail || 'Purchase failed — please try again.'
  } finally {
    purchasing.value = false
  }
}

// Reset the pay message whenever duration/method changes
watch(selectedDurationIdx, () => { stopCryptoPolling(); payMessage.value = ''; paySuccess.value = false })

const COMPARE_ROWS = [
  { label: 'Free strategies',              free: true,  premium: true,  lifetime: true },
  { label: 'Premium strategy library',     free: false, premium: true,  lifetime: true },
  { label: 'Grenade lineup videos',        free: false, premium: true,  lifetime: true },
  { label: 'Timing screenshots',           free: false, premium: true,  lifetime: true },
  { label: 'New strategies weekly',        free: false, premium: true,  lifetime: true },
  { label: 'Priority support',             free: false, premium: true,  lifetime: true },
  { label: 'Lifetime access',              free: false, premium: false, lifetime: true },
  { label: 'Exclusive Discord role',       free: false, premium: false, lifetime: true },
]

// Tiny inline check / cross icons as functional components
const Check = () => h('svg', { viewBox: '0 0 16 16', width: 14, height: 14, fill: 'none' }, [
  h('path', { d: 'M3 8.5l3.5 3.5L13 4.5', stroke: 'var(--success)', 'stroke-width': 2, 'stroke-linecap': 'round', 'stroke-linejoin': 'round' })
])
const Cross = () => h('svg', { viewBox: '0 0 16 16', width: 14, height: 14, fill: 'none' }, [
  h('path', { d: 'M4 4l8 8M12 4l-8 8', stroke: 'var(--text-dim)', 'stroke-width': 1.6, 'stroke-linecap': 'round' })
])
</script>

<style scoped>
.pricing-page { min-height: 100vh; background: var(--bg); }
.pricing-content { max-width: 1080px; padding: 32px 20px 120px; }

.back-btn {
  display: inline-flex; align-items: center; gap: 6px;
  background: var(--bg-elevated); border: 1px solid var(--line);
  color: var(--text-dim); padding: 8px 16px; border-radius: 8px;
  font-size: 13px; font-weight: 600; cursor: pointer;
  transition: border-color .2s, color .2s;
  margin-bottom: 36px;
}
.back-btn:hover { border-color: var(--accent); color: var(--accent); }

/* ── Hero ─────────────────────────────────────── */
.pricing-hero { text-align: center; margin-bottom: 28px; }
.pricing-hero h1 {
  font-size: clamp(28px, 6vw, 46px);
  font-weight: 900; letter-spacing: -.02em;
  color: var(--text); margin-bottom: 14px;
}
.pricing-hero p {
  font-size: 15px; color: var(--text-dim);
  max-width: 480px; margin: 0 auto; line-height: 1.6;
}
.accent { color: var(--accent); }

/* ── Discount banner ───────────────────────────── */
.discount-banner {
  display: flex; align-items: center; justify-content: center; gap: 10px;
  background: rgba(80,220,100,0.1); border: 1px solid rgba(80,220,100,0.35);
  border-radius: var(--radius-md); padding: 12px 18px;
  margin: 0 auto 32px; max-width: 620px;
  color: var(--success); font-size: 13.5px;
  text-align: center;
}
.discount-banner strong { font-weight: 800; }

/* ── Plans grid ───────────────────────────────── */
.plans-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: 20px;
  margin-bottom: 40px;
}

.plan-card {
  position: relative;
  background: var(--bg-elevated);
  border: 1px solid var(--line);
  border-radius: var(--radius-lg);
  padding: 28px 26px;
  display: flex; flex-direction: column;
  transition: border-color .2s, transform .2s;
}
.plan-card:hover { transform: translateY(-3px); }

.plan-card.featured {
  border-color: var(--accent);
  background: linear-gradient(180deg, rgba(255,154,0,0.06), var(--bg-elevated) 40%);
}

.plan-tag {
  position: absolute; top: -11px; left: 26px;
  padding: 4px 12px; border-radius: 99px;
  background: linear-gradient(90deg, var(--accent), var(--accent-2));
  color: #14140f; font-size: 11px; font-weight: 800;
  text-transform: uppercase; letter-spacing: .04em;
}
.plan-tag.lifetime-tag {
  background: var(--bg-elevated-2);
  color: var(--text); border: 1px solid var(--line);
}
.plan-tag.current-tag {
  background: var(--success); color: #0d1a10;
}
.plan-card.is-current { border-color: var(--success); }
.plan-status {
  font-size: 12.5px; font-weight: 700; color: var(--success);
  margin-top: -6px; margin-bottom: 10px;
}

.plan-head { margin-bottom: 20px; }
.plan-head h3 {
  font-size: 15px; font-weight: 700; color: var(--text-dim);
  text-transform: uppercase; letter-spacing: .06em; margin-bottom: 10px;
}
.plan-price { display: flex; align-items: baseline; gap: 6px; flex-wrap: wrap; }
.price-from { font-size: 12px; color: var(--text-dim); font-weight: 600; }
.price-num { font-size: 34px; font-weight: 900; color: var(--text); letter-spacing: -.02em; }
.price-num.discounted { color: var(--success); }
.price-num-strike {
  font-size: 17px; font-weight: 700; color: var(--text-dim);
  text-decoration: line-through; text-decoration-color: var(--danger);
}
.price-period { font-size: 13px; color: var(--text-dim); }

.plan-features {
  list-style: none;
  display: flex; flex-direction: column; gap: 12px;
  margin-bottom: 24px; flex: 1;
}
.plan-features li {
  display: flex; align-items: center; gap: 10px;
  font-size: 13.5px; color: var(--text);
}
.plan-features li.disabled { color: var(--text-dim); }
.plan-features li svg { flex-shrink: 0; }

.plan-btn { width: 100%; font-size: 14px; padding: 12px; }
.plan-btn:disabled { opacity: .5; cursor: not-allowed; }

/* ── MasterCoins note ─────────────────────────── */
.coins-note {
  display: flex; align-items: flex-start; gap: 12px;
  background: var(--bg-elevated); border: 1px solid var(--line);
  border-radius: var(--radius-md); padding: 18px 20px;
  margin-bottom: 56px;
}
.coins-icon { display: flex; color: var(--accent); flex-shrink: 0; margin-top: 2px; }
.coins-note p { font-size: 13px; color: var(--text-dim); line-height: 1.6; }
.coins-note strong { color: var(--text); }

/* ── Compare table ────────────────────────────── */
.section-title {
  font-size: 22px; font-weight: 800; letter-spacing: -.01em;
  color: var(--text); margin-bottom: 20px; text-align: center;
}

.compare-table {
  background: var(--bg-elevated); border: 1px solid var(--line);
  border-radius: var(--radius-lg); overflow: hidden;
}

.compare-row {
  display: grid;
  grid-template-columns: 2fr repeat(3, 1fr);
  align-items: center;
  padding: 14px 20px;
  border-bottom: 1px solid var(--line);
  gap: 8px;
}
.compare-row:last-child { border-bottom: none; }
.compare-row span:not(.compare-feature) {
  display: flex; justify-content: center;
}

.compare-head {
  background: var(--bg);
  font-size: 12px; font-weight: 700;
  text-transform: uppercase; letter-spacing: .05em;
  color: var(--text-dim);
}
.compare-head span:not(.compare-feature) { justify-content: center; }

.compare-feature { font-size: 13px; color: var(--text); }

/* ── Modal ─────────────────────────────────────── */
.modal-backdrop {
  position: fixed; inset: 0; z-index: 500;
  background: rgba(0,0,0,0.6);
  display: flex; align-items: center; justify-content: center;
  padding: 20px;
  backdrop-filter: blur(4px);
  overflow-y: auto;
}

.modal {
  position: relative;
  width: 100%; max-width: 400px;
  background: var(--bg-elevated);
  border: 1px solid var(--line);
  border-radius: var(--radius-lg);
  padding: 32px 28px 26px;
  margin: auto;
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

.modal-title {
  font-size: 20px; font-weight: 800; color: var(--text); margin-bottom: 4px;
}
.modal-price {
  display: flex; align-items: baseline; gap: 10px; flex-wrap: wrap;
  margin-bottom: 4px;
}
.modal-price-strike {
  font-size: 16px; font-weight: 700; color: var(--text-dim);
  text-decoration: line-through; text-decoration-color: var(--danger);
}
.modal-price-final,
.modal-price {
  font-size: 24px; font-weight: 900; color: var(--accent);
}
.modal-discount-note {
  font-size: 12px; font-weight: 600; color: var(--success);
  margin-bottom: 20px;
}
.modal-price + .modal-label { margin-top: 20px; }

.modal-label {
  font-size: 11px; font-weight: 700; letter-spacing: .06em;
  text-transform: uppercase; color: var(--text-dim); margin-bottom: 12px;
  margin-top: 20px;
}

.duration-options {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 8px;
  margin-bottom: 6px;
}
.duration-option {
  display: flex; flex-direction: column; align-items: center; gap: 4px;
  padding: 10px 8px;
  background: var(--bg); border: 1px solid var(--line);
  border-radius: 10px; cursor: pointer;
  transition: border-color .15s, background .15s;
}
.duration-option:hover { border-color: var(--accent); }
.duration-option.active {
  border-color: var(--accent);
  background: rgba(255,154,0,0.08);
}
.duration-label { font-size: 12px; font-weight: 700; color: var(--text); }
.duration-price { font-size: 13px; font-weight: 800; color: var(--accent); }

.payment-options { display: flex; flex-direction: column; gap: 10px; margin-bottom: 6px; }

.payment-option {
  display: flex; align-items: center; gap: 12px;
  padding: 14px 16px;
  background: var(--bg); border: 1.5px solid var(--line);
  border-radius: 10px; cursor: pointer;
  transition: border-color .2s, background .2s;
  width: 100%; text-align: left;
}
.payment-option:hover:not(.disabled) { border-color: rgba(255,154,0,0.5); }
.payment-option.selected {
  border-color: var(--accent);
  background: rgba(255,154,0,0.08);
}
.payment-option.disabled {
  opacity: .5; cursor: not-allowed;
}

.payment-icon {
  color: var(--text);
  width: 34px; height: 34px;
  display: flex; align-items: center; justify-content: center;
  background: var(--bg-elevated-2); border-radius: 8px; flex-shrink: 0;
}
.payment-info { display: flex; flex-direction: column; gap: 2px; flex: 1; text-align: left; min-width: 0; }
.payment-name { font-size: 14px; font-weight: 700; color: var(--text); }
.payment-sub { font-size: 11px; color: var(--text-dim); }

.status-tag {
  padding: 3px 8px; border-radius: 6px;
  font-size: 9px; font-weight: 700; text-transform: uppercase;
  letter-spacing: .04em; flex-shrink: 0;
}
.status-tag.soon { background: var(--bg-elevated-2); color: var(--text-dim); }
.status-tag.ready { background: rgba(80,220,100,0.15); color: var(--success); }

.pay-block { margin-top: 6px; }
.pay-btn { width: 100%; font-size: 14px; padding: 13px; }
.pay-message {
  margin-top: 10px; font-size: 12.5px; color: var(--text-dim);
  text-align: center; line-height: 1.5;
}
.pay-message.success { color: var(--success); font-weight: 700; }
.pay-btn:disabled { opacity: .7; cursor: not-allowed; }

.modal-footnote {
  font-size: 12px; color: var(--text-dim); text-align: center; line-height: 1.5;
  margin-top: 6px;
}

.fade-enter-active, .fade-leave-active { transition: opacity .2s; }
.fade-enter-from, .fade-leave-to { opacity: 0; }

/* ── Responsive ────────────────────────────────── */
@media (max-width: 640px) {
  .compare-row { grid-template-columns: 1.4fr repeat(3, 1fr); padding: 12px 14px; font-size: 12px; }
}
</style>