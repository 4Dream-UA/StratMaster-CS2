<template>
  <section v-if="loaded" class="ref-card">

    <!-- ── Invite hero — always the main focus ───────────────── -->
    <div class="ref-hero">
      <span class="ref-eyebrow">Invite &amp; Earn</span>
      <h3 class="ref-title">
        Get <span class="accent">{{ stats.bonus_per_referral }} MasterCoins</span> for every friend
      </h3>
      <p class="ref-sub">
        They get <strong>{{ stats.referral_discount_percent }}% off</strong> their first purchase — everybody wins.
      </p>
    </div>

    <!-- ── Own code + share ───────────────────────────────────── -->
    <div class="ref-code-block">
      <button class="ref-code-display" @click="copyCode">
        <span class="ref-code-val">{{ stats.referral_code }}</span>
        <span class="ref-code-copy">{{ copied ? 'Copied!' : 'Tap to copy' }}</span>
      </button>
      <button class="btn-primary ref-share-btn" @click="shareCode">
        <svg viewBox="0 0 24 24" fill="none" width="16" height="16">
          <path d="M15 4l5 5-5 5M20 9H10a6 6 0 00-6 6v2" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
        Invite
      </button>
    </div>

    <div class="ref-stats-row">
      <div class="ref-stat"><b>{{ stats.referred_count }}</b><span>invited</span></div>
      <div class="ref-stat"><b>{{ stats.total_earned_coins }}</b><span>coins earned</span></div>
    </div>

    <!-- ── Redeem a friend's code — secondary, always visible if eligible ── -->
    <div v-if="stats.can_apply_code" class="ref-apply">
      <div class="ref-apply-label">Got a friend's code?</div>
      <form class="ref-form" @submit.prevent="submitCode">
        <input
          v-model="codeInput"
          type="text"
          placeholder="e.g. 8F3KZ1Q9WX2R"
          maxlength="32"
          autocomplete="off"
          spellcheck="false"
          :disabled="submitting"
          @input="errorMsg = ''"
        />
        <button type="submit" class="btn-secondary ref-submit" :disabled="submitting || !codeInput.trim()">
          {{ submitting ? '...' : 'Apply' }}
        </button>
      </form>
      <p v-if="errorMsg" class="ref-msg error">{{ errorMsg }}</p>
      <p v-if="justApplied" class="ref-msg success">
        Discount applied — enjoy {{ appliedResult.discount_percent }}% off for 24 hours!
      </p>
    </div>

    <p v-else-if="justApplied" class="ref-msg success ref-msg-standalone">
      Discount applied — enjoy {{ appliedResult.discount_percent }}% off for 24 hours!
    </p>

    <p v-else class="ref-used-note">You've already redeemed a referral code.</p>

  </section>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { referralAPI } from '../api/referral'
import { BOT_USERNAME } from '../config'

const loaded = ref(false)
const stats = ref(null)
const codeInput = ref('')
const submitting = ref(false)
const errorMsg = ref('')
const justApplied = ref(false)
const appliedResult = ref(null)
const copied = ref(false)

async function fetchStats() {
  stats.value = await referralAPI.getStats()
  loaded.value = true
}

async function submitCode() {
  const code = codeInput.value.trim()
  if (!code || submitting.value) return
  submitting.value = true
  errorMsg.value = ''
  try {
    appliedResult.value = await referralAPI.applyCode(code)
    justApplied.value = true
    codeInput.value = ''
    // Refresh so can_apply_code / already_used_code reflect the new state
    await fetchStats()
  } catch (err) {
    errorMsg.value = err?.response?.data?.detail || 'Could not apply this code. Check it and try again.'
  } finally {
    submitting.value = false
  }
}

function copyCode() {
  if (!stats.value?.referral_code) return
  navigator.clipboard?.writeText(stats.value.referral_code)
  copied.value = true
  setTimeout(() => { copied.value = false }, 1600)
}

function shareCode() {
  if (!stats.value?.referral_code) return
  const text = `Join StratMaster CS2 with my code \`${stats.value.referral_code}\` and get ${stats.value.referral_discount_percent}% off your first purchase!`
  const url = `t.me/${BOT_USERNAME}`

  // Native Telegram share sheet, if running inside the Mini App
  if (window.Telegram?.WebApp?.openTelegramLink) {
    const shareUrl = `https://t.me/share/url?url=${encodeURIComponent(url)}&text=${encodeURIComponent(text)}`
    window.Telegram.WebApp.openTelegramLink(shareUrl)
    return
  }
  // Native OS share sheet in a regular browser
  if (navigator.share) {
    navigator.share({ text, url }).catch(() => {})
    return
  }
  // Fallback — just copy
  navigator.clipboard?.writeText(text)
  copied.value = true
  setTimeout(() => { copied.value = false }, 1600)
}

onMounted(fetchStats)
</script>

<style scoped>
.ref-card {
  position: relative;
  background: linear-gradient(180deg, rgba(255,154,0,0.08), var(--bg-elevated) 55%);
  border: 1px solid rgba(255,154,0,0.35);
  border-radius: var(--radius-lg);
  padding: 22px 18px;
  overflow: hidden;
}
.ref-card::before {
  content: '';
  position: absolute;
  top: -60%; right: -20%;
  width: 240px; height: 240px;
  background: radial-gradient(circle, rgba(255,154,0,0.3), transparent 70%);
  pointer-events: none;
}

/* ── Hero ─────────────────────────────────────── */
.ref-hero { position: relative; margin-bottom: 20px; }
.ref-eyebrow {
  display: inline-block;
  font-size: 11px; font-weight: 800; text-transform: uppercase;
  letter-spacing: .08em; color: var(--accent);
  margin-bottom: 8px;
}
.ref-title {
  font-size: clamp(17px, 4vw, 20px); font-weight: 800;
  letter-spacing: -.01em; color: var(--text);
  line-height: 1.35; margin-bottom: 6px;
}
.accent { color: var(--accent); }
.ref-sub { font-size: 13px; color: var(--text-dim); line-height: 1.5; }
.ref-sub strong { color: var(--text); }

/* ── Code + share ─────────────────────────────── */
.ref-code-block {
  position: relative;
  display: flex; gap: 8px; margin-bottom: 16px;
}
.ref-code-display {
  flex: 1; min-width: 0;
  display: flex; flex-direction: column; align-items: flex-start; gap: 2px;
  background: var(--bg); border: 1.5px solid var(--line);
  border-radius: 12px; padding: 11px 14px;
  cursor: pointer; transition: border-color .2s;
}
.ref-code-display:hover { border-color: var(--accent); }
.ref-code-val {
  font-size: 15px; font-weight: 800; color: var(--text);
  letter-spacing: .05em; font-variant-numeric: tabular-nums;
}
.ref-code-copy { font-size: 10px; font-weight: 600; color: var(--accent); text-transform: uppercase; letter-spacing: .04em; }

.ref-share-btn {
  flex-shrink: 0;
  font-size: 13px; padding: 11px 14px;
  display: flex; align-items: center; gap: 5px;
}

/* ── Stats ────────────────────────────────────── */
.ref-stats-row {
  position: relative;
  display: flex; gap: 22px;
  padding-bottom: 18px;
  margin-bottom: 18px;
  border-bottom: 1px solid var(--line);
}
.ref-stat { display: flex; flex-direction: column; gap: 2px; }
.ref-stat b { font-size: 19px; font-weight: 800; color: var(--text); }
.ref-stat span { font-size: 10.5px; color: var(--text-dim); text-transform: uppercase; letter-spacing: .04em; }

/* ── Apply someone else's code ────────────────── */
.ref-apply { position: relative; }
.ref-apply-label {
  font-size: 12px; font-weight: 700; color: var(--text-dim);
  margin-bottom: 10px;
}
.ref-form { display: flex; gap: 8px; }
.ref-form input {
  flex: 1; min-width: 0;
  background: var(--bg); border: 1px solid var(--line);
  border-radius: 10px; padding: 11px 13px;
  color: var(--text); font-size: 13px; font-weight: 600;
  letter-spacing: .03em;
  transition: border-color .2s;
}
.ref-form input::placeholder { color: var(--text-dim); font-weight: 500; letter-spacing: 0; }
.ref-form input:focus { outline: none; border-color: var(--accent); }
.ref-submit { font-size: 13px; padding: 11px 18px; flex-shrink: 0; }
.ref-submit:disabled { opacity: .5; cursor: not-allowed; }

.ref-msg { margin-top: 10px; font-size: 12.5px; font-weight: 600; position: relative; }
.ref-msg.error { color: var(--danger); }
.ref-msg.success { color: var(--success); }
.ref-msg-standalone { margin-top: 0; }

.ref-used-note {
  position: relative;
  font-size: 12.5px; color: var(--text-dim);
}

@media (max-width: 400px) {
  .ref-code-block { flex-direction: column; }
  .ref-share-btn { justify-content: center; padding: 11px; }
}
</style>