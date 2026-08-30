<template>
  <main class="legal-page">
    <Header />

    <div class="wrap legal-content">
      <Breadcrumbs :items="[{ label: 'Home', to: '/' }, { label: doc === 'privacy' ? 'Privacy Policy' : 'Terms of Service' }]" />

      <nav class="legal-tabs">
        <router-link to="/terms" class="legal-tab" :class="{ active: doc === 'terms' }">Terms of Service</router-link>
        <router-link to="/privacy" class="legal-tab" :class="{ active: doc === 'privacy' }">Privacy Policy</router-link>
      </nav>

      <!-- ═══ TERMS OF SERVICE ═══════════════════════ -->
      <article v-if="doc === 'terms'" class="legal-doc">
        <h1>Terms of Service</h1>
        <p class="legal-updated">Last updated: August 31, 2026</p>

        <p>These terms govern your use of StratMaster CS2 (the "Service"), a Telegram Mini App offering CS2 strategy content, a virtual currency (MasterCoins), a community forum, and related features. By opening or using the Service you agree to these terms.</p>

        <h2>1. Eligibility</h2>
        <p>You must meet the age of majority in your jurisdiction to purchase MasterCoins or open cases. If you're old enough to use Telegram under its own terms but not old enough to make purchases where you live, you may still browse strategy content but must not buy or spend MasterCoins.</p>

        <h2>2. MasterCoins</h2>
        <p>MasterCoins are a virtual currency usable only inside the Service. They have no cash value, cannot be redeemed for real money outside the Service, and are not a financial instrument, security, or investment of any kind. We may adjust prices, rewards, or the ways MasterCoins can be earned or spent at any time.</p>

        <h2>3. Cases and random rewards</h2>
        <p>Cases are opened for a random reward from a published pool. The odds for every case are shown in-app before purchase ("View odds") and don't change based on anything about you personally. Reward tables are tuned toward an average return of roughly 80% of what's spent on cases overall — that's a long-run target across all players and all cases combined, not a guarantee for any single case or any single player, and short-term results will vary. Cases are entertainment, not an investment; don't spend more than you're comfortable not getting back.</p>

        <h2>4. Payments and refunds</h2>
        <p><strong>All purchases are final. We do not offer refunds</strong> for MasterCoins, cases, subscription time, or anything else bought through the Service, including after a case has been opened, a voucher activated, or a subscription period has begun — regardless of the outcome of any random reward. This applies to crypto payments and any other payment method we offer. If you believe a purchase failed to deliver what was paid for due to a technical error on our end (for example, a payment that was charged but never credited), contact Support and we'll investigate on a case-by-case basis — this is a goodwill exception, not a right to a refund for remorse, changed your mind, or dissatisfaction with a random outcome.</p>

        <h2>5. Premium subscription</h2>
        <p>Premium unlocks additional features (tactics boards, forum access, and others as described in-app) for the purchased duration. Auto-renew, when enabled, charges automatically at the end of the current period using your chosen method; you can turn it off any time before renewal from your profile.</p>

        <h2>6. Trading between players</h2>
        <p>Cases, premium vouchers, and MasterCoins can be gifted or sold to other players through the Service's own trading tools. We're not a party to these trades and don't guarantee any player will complete one — sale offers require the buyer's explicit acceptance and payment before anything changes hands.</p>

        <h2>7. Forum and community conduct</h2>
        <p>Don't post anything illegal, harassing, hateful, or that infringes someone else's rights. Don't spam, impersonate others, or attempt to manipulate the case-reward system or the referral program. We can remove content, close threads, or suspend accounts that violate this — see our moderation tools (post editing history, soft-deletion, and reporting) for how this is enforced in practice.</p>

        <h2>8. Account actions</h2>
        <p>We may suspend or ban an account for violating these terms, attempting to exploit the Service, or fraudulent payment activity. Banned or trade-banned accounts don't get their MasterCoins balance refunded (see Section 4).</p>

        <h2>9. No warranty</h2>
        <p>The Service is provided "as is." We don't guarantee it will be uninterrupted, error-free, or that strategy content is accurate for every matchup or patch. Use tactics and strategies at your own judgment.</p>

        <h2>10. Changes to these terms</h2>
        <p>We may update these terms as the Service evolves. Material changes will be reflected here with an updated date; continued use after a change means you accept the update.</p>

        <h2>11. Contact</h2>
        <p>Questions about these terms can be sent through the Support ticket category in the <router-link to="/forum">forum</router-link> or via our <a href="https://t.me/+xyLN_GYPgvI5YWUy">Telegram contact</a>.</p>
      </article>

      <!-- ═══ PRIVACY POLICY ═══════════════════════ -->
      <article v-else class="legal-doc">
        <h1>Privacy Policy</h1>
        <p class="legal-updated">Last updated: August 31, 2026</p>

        <p>This explains what data StratMaster CS2 collects, why, and how it's handled. Using the Service means you're okay with the practices described here.</p>

        <h2>1. What we collect</h2>
        <ul>
          <li><strong>From Telegram:</strong> your Telegram ID, username, first/last name, and language, provided automatically when you open the Mini App.</li>
          <li><strong>Account data you provide:</strong> a display name and avatar (optional), and any wallet/payment identifiers needed to process a purchase.</li>
          <li><strong>Optional profile info:</strong> if you choose to fill it in, your public profile can include a location, Telegram/Discord/Steam/Instagram/WhatsApp/Twitch/Faceit handle, or similar — filling a field in is the only way it's ever shown to other players.</li>
          <li><strong>Activity data:</strong> transactions (purchases, transfers, case openings), forum posts and reactions, favorites, and similar in-app actions, so the Service can function (balances, history, moderation tools).</li>
          <li><strong>Technical data:</strong> basic request logs (IP address, timestamps) kept briefly for security and abuse prevention (including the rate limits described in these docs).</li>
        </ul>

        <h2>2. What we don't collect</h2>
        <p>We don't request your phone number, government ID, or payment card details — crypto payments are handled by a third-party payment processor that never shares your wallet's private keys or full transaction history with us, only payment confirmation.</p>

        <h2>3. How we use it</h2>
        <p>To run the Service: authenticate you, process purchases, display your balance and inventory, show your posts and reactions to other players, send you Telegram notifications you've opted into (replies, mentions, offers), and moderate content. We don't sell your data to third parties or use it for advertising.</p>

        <h2>4. Who can see what</h2>
        <p>Your Telegram username is visible to other players on forum posts unless you turn on "Hide my username" in Settings — admins can always see it regardless, for moderation. Optional profile info is visible to anyone who taps your avatar, if you've filled it in. Wallet IDs (not your Telegram identity) are visible to counterparties in a P2P trade you initiate.</p>

        <h2>5. Data retention</h2>
        <p>We keep account and activity data for as long as your account exists, plus a reasonable period after for legal, accounting, and anti-fraud purposes (transaction records in particular). Soft-deleted forum posts are retained until an admin permanently erases them or the thread is deleted.</p>

        <h2>6. Your choices</h2>
        <p>You can update or clear your display name, avatar, and optional profile info at any time from your profile. You can hide your username from the forum. To request deletion of your account and associated personal data, contact Support (a Support ticket in the forum, or our Telegram contact below) — we'll action it unless we're required to retain specific records (e.g. transaction history) for legal reasons.</p>

        <h2>7. Storage and security</h2>
        <p>Data is stored on servers we operate or contract with, with reasonable technical safeguards. No system is perfectly secure; we can't guarantee absolute protection against every possible breach, but we don't store payment credentials ourselves and limit what we collect to what the Service actually needs.</p>

        <h2>8. Children</h2>
        <p>The Service isn't directed at children under the age required to use Telegram itself, and purchases additionally require the age of majority in your jurisdiction (see Terms of Service, Section 1).</p>

        <h2>9. Changes to this policy</h2>
        <p>We may update this policy as the Service changes. Material changes will be reflected here with an updated date.</p>

        <h2>10. Contact</h2>
        <p>Privacy questions or data requests can be sent through the Support ticket category in the <router-link to="/forum">forum</router-link> or via our <a href="https://t.me/+xyLN_GYPgvI5YWUy">Telegram contact</a>.</p>
      </article>
    </div>

    <Footer />
  </main>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import Header from '../components/Header.vue'
import Footer from '../components/Footer.vue'
import Breadcrumbs from '../components/Breadcrumbs.vue'

const route = useRoute()
const doc = computed(() => (route.path === '/privacy' ? 'privacy' : 'terms'))
</script>

<style scoped>
.legal-page { min-height: 100vh; background: var(--bg); }
.legal-content { max-width: 760px; padding: 32px 20px 120px; }

.legal-tabs { display: flex; gap: 8px; margin-bottom: 28px; flex-wrap: wrap; }
.legal-tab {
  padding: 9px 18px; border-radius: 99px;
  background: var(--bg-elevated); border: 1.5px solid var(--line);
  color: var(--text-dim); font-size: 13px; font-weight: 700; text-decoration: none;
  transition: all .15s;
}
.legal-tab:hover { border-color: rgba(255,154,0,.5); color: var(--text); }
.legal-tab.active { background: rgba(255,154,0,.12); border-color: var(--accent); color: var(--accent); }

.legal-doc h1 { font-size: clamp(24px, 4.5vw, 32px); font-weight: 900; color: var(--text); margin-bottom: 6px; }
.legal-updated { font-size: 12px; color: var(--text-dim); margin-bottom: 24px; }
.legal-doc > p { font-size: 13.5px; color: var(--text-dim); line-height: 1.7; margin-bottom: 20px; }
.legal-doc h2 {
  font-size: 15px; font-weight: 800; color: var(--text);
  margin: 28px 0 10px; padding-top: 20px; border-top: 1px solid var(--line);
}
.legal-doc h2:first-of-type { border-top: none; padding-top: 0; margin-top: 8px; }
.legal-doc p, .legal-doc li { font-size: 13.5px; color: var(--text-dim); line-height: 1.7; }
.legal-doc ul { margin: 0 0 20px; padding-left: 20px; display: flex; flex-direction: column; gap: 8px; }
.legal-doc strong { color: var(--text); }
.legal-doc a { color: var(--accent); text-decoration: none; }
.legal-doc a:hover { text-decoration: underline; }
</style>
