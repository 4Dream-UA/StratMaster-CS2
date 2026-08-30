<template>
  <div class="cases-panel">
    <div class="view-tabs">
      <button type="button" class="view-tab" :class="{ active: activeView === 'shop' }" @click="activeView = 'shop'">Shop</button>
      <button type="button" class="view-tab" :class="{ active: activeView === 'inventory' }" @click="switchToInventory">
        My Inventory <span v-if="totalOwned" class="tab-badge">{{ totalOwned }}</span>
      </button>
      <button type="button" class="view-tab" :class="{ active: activeView === 'offers' }" @click="switchToOffers">
        Offers <span v-if="incomingOffers.length + incomingVoucherOffers.length" class="tab-badge">{{ incomingOffers.length + incomingVoucherOffers.length }}</span>
      </button>
    </div>

    <div v-if="loading" class="loader-row"><div class="spinner"></div></div>
    <div v-else-if="!cases.length" class="empty">No cases available right now.</div>

    <!-- ═══ SHOP ═══════════════════════════════ -->
    <div v-else-if="activeView === 'shop'" class="case-grid">
      <div v-for="c in cases" :key="c.id" class="case-card" :style="{ '--case-accent': caseStyle(c.name).color }">
        <div class="case-icon"><PremiumIcon v-if="caseStyle(c.name).icon === 'crown'" :size="64" :color="caseStyle(c.name).color" /><CaseIcon v-else :color="caseStyle(c.name).color" /></div>
        <h3>{{ c.name }}</h3>
        <p class="case-cost"><CoinIcon :size="16" /> {{ c.cost_coins }} <span>MC</span></p>

        <div class="qty-picker">
          <button type="button" class="qty-btn" @click="setQty(c.id, qty(c.id) - 1)">−</button>
          <input type="number" class="qty-input" min="1" max="50" :value="qty(c.id)" @input="setQty(c.id, $event.target.valueAsNumber)" />
          <button type="button" class="qty-btn" @click="setQty(c.id, qty(c.id) + 1)">+</button>
        </div>
        <div class="qty-presets">
          <button
            v-for="n in [1, 3, 5, 9]" :key="n" type="button" class="qty-preset"
            :class="{ active: qty(c.id) === n }" @click="setQty(c.id, n)"
          >{{ n }}</button>
        </div>

        <button
          class="btn-primary buy-btn" :disabled="buying || (wallet?.balance_coins ?? 0) < c.cost_coins * qty(c.id)"
          @click="buyCase(c, qty(c.id))"
        >{{ buying ? 'Buying…' : `Buy ${qty(c.id)} for ${c.cost_coins * qty(c.id)} MC` }}</button>
        <p v-if="(wallet?.balance_coins ?? 0) < c.cost_coins * qty(c.id)" class="case-hint">Not enough MasterCoins</p>

        <button type="button" class="odds-toggle" @click="oddsOpenId = oddsOpenId === c.id ? null : c.id">
          {{ oddsOpenId === c.id ? 'Hide odds ▲' : 'View odds ▼' }}
        </button>
        <div v-if="oddsOpenId === c.id" class="odds-grid">
          <div
            v-for="(r, ri) in c.rewards" :key="ri" class="odds-tile"
            :style="{ borderColor: tierColor(r.tier).border, background: tierColor(r.tier).bg }"
          >
            <PremiumIcon v-if="isPremiumReward(r)" :size="16" :color="tierColor(r.tier).border" />
            <CoinIcon v-else :size="16" :color="tierColor(r.tier).border" />
            <span class="odds-tile-coins">{{ rewardLabel(r) }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- ═══ INVENTORY ═══════════════════════════════ -->
    <div v-else-if="activeView === 'inventory'" class="inventory-view">
      <div v-if="!inventory.length && !vouchers.length" class="empty">Your inventory is empty — buy a case in the Shop first.</div>

      <template v-if="inventory.length">
        <h3 class="inventory-heading">Cases</h3>
        <div class="item-grid">
          <button
            v-for="inv in inventory" :key="inv.case_id" type="button" class="item-tile"
            :style="{ '--case-accent': caseStyle(inv.case_name).color }"
            @click="openInventoryPopup(inv)"
          >
            <PremiumIcon v-if="caseStyle(inv.case_name).icon === 'crown'" :size="36" :color="caseStyle(inv.case_name).color" />
            <CaseIcon v-else :size="36" :color="caseStyle(inv.case_name).color" />
            <span class="item-tile-name">{{ inv.case_name }}</span>
            <span class="item-tile-count">×{{ inv.count }}</span>
          </button>
        </div>
      </template>

      <template v-if="vouchers.length">
        <h3 class="inventory-heading">Premium</h3>
        <div class="item-grid">
          <button
            v-for="v in vouchers" :key="v.id" type="button" class="item-tile"
            style="--case-accent: #4b69ff" @click="openVoucherPopup(v)"
          >
            <PremiumIcon :size="36" color="#4b69ff" />
            <span class="item-tile-name">{{ formatDays(v.days) }}</span>
            <span class="item-tile-count">Premium</span>
          </button>
        </div>
      </template>
    </div>

    <!-- ═══ OFFERS ═══════════════════════════════ -->
    <div v-else class="offers-view">
      <h3 class="offers-heading">Incoming</h3>
      <div v-if="!incomingOffers.length && !incomingVoucherOffers.length" class="empty">No incoming offers.</div>
      <div v-else class="offers-list">
        <div v-for="o in incomingOffers" :key="o.id" class="offer-row">
          <CaseIcon :size="40" :color="caseStyle(o.case_name).color" />
          <div class="offer-info">
            <span class="offer-title">{{ o.offer_type === 'gift' ? 'Gift' : 'Sale offer' }}: {{ o.quantity }}× {{ o.case_name }}</span>
            <span class="offer-sub">
              From {{ o.sender_username ? '@' + o.sender_username : o.sender_wallet_id }}
              <template v-if="o.offer_type === 'sale'"> — {{ o.price_coins }} MC</template>
            </span>
          </div>
          <div class="offer-actions">
            <button class="mini-btn" :disabled="offerBusyId === o.id" @click="respondToOffer(o, 'accept')">Accept</button>
            <button class="mini-btn danger" :disabled="offerBusyId === o.id" @click="respondToOffer(o, 'decline')">Decline</button>
          </div>
        </div>
        <div v-for="o in incomingVoucherOffers" :key="o.id" class="offer-row">
          <PremiumIcon :size="40" color="#4b69ff" />
          <div class="offer-info">
            <span class="offer-title">Sale offer: {{ formatDays(o.days) }} Premium</span>
            <span class="offer-sub">
              From {{ o.sender_username ? '@' + o.sender_username : o.sender_wallet_id }} — {{ o.price_coins }} MC
            </span>
          </div>
          <div class="offer-actions">
            <button class="mini-btn" :disabled="offerBusyId === o.id" @click="respondToVoucherOffer(o, 'accept')">Accept</button>
            <button class="mini-btn danger" :disabled="offerBusyId === o.id" @click="respondToVoucherOffer(o, 'decline')">Decline</button>
          </div>
        </div>
      </div>

      <h3 class="offers-heading">Outgoing</h3>
      <div v-if="!outgoingOffers.length && !outgoingVoucherOffers.length" class="empty">No outgoing offers.</div>
      <div v-else class="offers-list">
        <div v-for="o in outgoingOffers" :key="o.id" class="offer-row">
          <CaseIcon :size="40" :color="caseStyle(o.case_name).color" />
          <div class="offer-info">
            <span class="offer-title">{{ o.offer_type === 'gift' ? 'Gift' : 'Sale offer' }}: {{ o.quantity }}× {{ o.case_name }}</span>
            <span class="offer-sub">
              To {{ o.receiver_username ? '@' + o.receiver_username : o.receiver_wallet_id }}
              <template v-if="o.offer_type === 'sale'"> — {{ o.price_coins }} MC</template>
            </span>
          </div>
          <div class="offer-actions">
            <button class="mini-btn danger" :disabled="offerBusyId === o.id" @click="respondToOffer(o, 'cancel')">Cancel</button>
          </div>
        </div>
        <div v-for="o in outgoingVoucherOffers" :key="o.id" class="offer-row">
          <PremiumIcon :size="40" color="#4b69ff" />
          <div class="offer-info">
            <span class="offer-title">Sale offer: {{ formatDays(o.days) }} Premium</span>
            <span class="offer-sub">
              To {{ o.receiver_username ? '@' + o.receiver_username : o.receiver_wallet_id }} — {{ o.price_coins }} MC
            </span>
          </div>
          <div class="offer-actions">
            <button class="mini-btn danger" :disabled="offerBusyId === o.id" @click="respondToVoucherOffer(o, 'cancel')">Cancel</button>
          </div>
        </div>
      </div>
    </div>

    <!-- ── PRE-OPEN POPUP (inventory case item, not-yet-started) ────── -->
    <!-- No <transition> — see the reveal popup below for why. -->
      <div v-if="preOpenInv" class="modal-backdrop" @click.self="closePreOpen">
        <div class="modal preopen-modal">
          <button class="modal-close" @click="closePreOpen">✕</button>
          <div class="preopen-icon" :style="{ '--case-accent': caseStyle(preOpenInv.case_name).color }">
            <PremiumIcon v-if="caseStyle(preOpenInv.case_name).icon === 'crown'" :size="52" :color="caseStyle(preOpenInv.case_name).color" />
            <CaseIcon v-else :size="52" :color="caseStyle(preOpenInv.case_name).color" />
          </div>
          <h3 class="preopen-title">{{ preOpenInv.case_name }}</h3>
          <p class="inventory-line">You own <strong>{{ preOpenInv.count }}</strong></p>

          <div class="open-row">
            <button
              v-for="q in [1, 3, 5]" :key="q" class="grey-btn open-btn"
              :disabled="opening || preOpenInv.count < q"
              @click="startOpenFromPopup(q)"
            >{{ opening ? '…' : `Open ×${q}` }}</button>
          </div>

          <button type="button" class="odds-toggle" @click="sendFormOpenId = sendFormOpenId === preOpenInv.case_id ? null : preOpenInv.case_id">
            {{ sendFormOpenId === preOpenInv.case_id ? 'Hide gift/sell ▲' : 'Gift or sell ▼' }}
          </button>
          <div v-if="sendFormOpenId === preOpenInv.case_id" class="send-form">
            <div class="send-mode-toggle">
              <button type="button" class="qty-preset" :class="{ active: sendMode === 'gift' }" @click="sendMode = 'gift'">Gift</button>
              <button type="button" class="qty-preset" :class="{ active: sendMode === 'sale' }" @click="sendMode = 'sale'">Sell</button>
            </div>
            <input v-model="sendWalletId" type="text" placeholder="Recipient Wallet ID" class="qty-input send-input" />
            <input v-model.number="sendQuantity" type="number" min="1" :max="preOpenInv.count" placeholder="Qty" class="qty-input send-input-small" />
            <input v-if="sendMode === 'sale'" v-model.number="sendPrice" type="number" min="1" placeholder="Price MC" class="qty-input send-input-small" />
            <button class="mini-btn" :disabled="sendBusy" @click="submitSend(preOpenInv)">{{ sendBusy ? '…' : (sendMode === 'gift' ? 'Send Gift' : 'Send Offer') }}</button>
            <p v-if="sendError" class="case-hint">{{ sendError }}</p>
          </div>

          <button
            v-if="historyFor(preOpenInv.case_id).length" type="button" class="odds-toggle"
            @click="historyOpenId = historyOpenId === preOpenInv.case_id ? null : preOpenInv.case_id"
          >
            {{ historyOpenId === preOpenInv.case_id ? 'Hide recent openings ▲' : 'Recent openings ▼' }}
          </button>
          <div v-if="historyOpenId === preOpenInv.case_id" class="history-list">
            <div v-for="h in historyFor(preOpenInv.case_id)" :key="h.id" class="history-row">
              <span class="history-time">{{ formatHistoryTime(h.created_at) }}</span>
              <span class="history-amounts">
                <span class="spent">-{{ h.coins_spent }} MC</span>
                <span v-if="h.premium_days_won != null" class="won">+{{ formatDays(h.premium_days_won) }} Premium</span>
                <span v-else class="won">+{{ h.coins_won }} MC</span>
              </span>
            </div>
          </div>
        </div>
      </div>

    <!-- ── VOUCHER POPUP ─────────────────────────────────── -->
      <div v-if="voucherPopup" class="modal-backdrop" @click.self="closeVoucherPopup">
        <div class="modal preopen-modal">
          <button class="modal-close" @click="closeVoucherPopup">✕</button>
          <div class="preopen-icon" style="--case-accent: #4b69ff"><PremiumIcon :size="52" color="#4b69ff" /></div>
          <h3 class="preopen-title">{{ formatDays(voucherPopup.days) }} Premium</h3>
          <p class="inventory-line">Stacks on top of any active Premium you already have.</p>

          <button class="btn-primary reveal-btn" :disabled="voucherBusy" @click="doActivateVoucher">
            {{ voucherBusy ? 'Activating…' : 'Activate' }}
          </button>
          <p v-if="voucherActivateMessage" class="case-hint" :class="{ success: voucherActivateMessage === 'Activated!' }">{{ voucherActivateMessage }}</p>

          <button type="button" class="odds-toggle" @click="voucherSendOpen = !voucherSendOpen">
            {{ voucherSendOpen ? 'Hide gift/sell ▲' : 'Gift or sell ▼' }}
          </button>
          <div v-if="voucherSendOpen" class="send-form">
            <div class="send-mode-toggle">
              <button type="button" class="qty-preset" :class="{ active: voucherSendMode === 'gift' }" @click="voucherSendMode = 'gift'">Gift</button>
              <button type="button" class="qty-preset" :class="{ active: voucherSendMode === 'sale' }" @click="voucherSendMode = 'sale'">Sell</button>
            </div>
            <input v-model="voucherSendWalletId" type="text" placeholder="Recipient Wallet ID" class="qty-input send-input" />
            <input v-if="voucherSendMode === 'sale'" v-model.number="voucherSendPrice" type="number" min="1" placeholder="Price MC" class="qty-input send-input-small" />
            <button class="mini-btn" :disabled="voucherSendBusy" @click="submitVoucherSend">{{ voucherSendBusy ? '…' : (voucherSendMode === 'gift' ? 'Send Gift' : 'Send Offer') }}</button>
            <p v-if="voucherSendError" class="case-hint">{{ voucherSendError }}</p>
          </div>
        </div>
      </div>

    <!-- ── REVEAL POPUP ─────────────────────────────────── -->
    <!-- No <transition> here on purpose — an explicit :duration doesn't
         reliably save it: a Vue <transition> can still get stuck mid-leave
         forever (backgrounded tab, reduced-motion, a fast double-toggle),
         leaving this fixed position:fixed;inset:0 backdrop rendered
         invisibly and silently blocking every click on the page
         underneath it until reload — right after the core case-opening flow. -->
      <div v-if="revealOpen" class="modal-backdrop" @click.self="revealDone && closeReveal()">
        <div class="modal reveal-modal" :class="{ multi: revealReels.length > 1 }">
          <button v-if="revealDone" class="modal-close" @click="closeReveal">✕</button>

          <div
            v-for="(reel, ri) in revealReels" :key="ri" class="carousel-wrap"
            :ref="(el) => { if (el) carouselWrapRefs[ri] = el }"
          >
            <div class="carousel-center-line"></div>
            <div class="carousel-strip" :class="{ animating: reel.animating }" :style="{ transform: `translateX(${reel.offset}px)` }">
              <div
                v-for="(tile, i) in reel.items" :key="i" class="case-tile"
                :class="{ won: revealDone && i === WINNING_INDEX }"
                :style="{ borderColor: tierColor(tile.tier).border, background: tierColor(tile.tier).bg }"
              >
                <PremiumIcon v-if="isPremiumReward(tile)" :size="20" :color="tierColor(tile.tier).border" />
                <CoinIcon v-else :size="20" :color="tierColor(tile.tier).border" />
                <span>{{ rewardLabel(tile) }}</span>
              </div>
            </div>
          </div>

          <template v-if="revealDone">
            <p v-if="revealTotalWon > 0" class="reveal-amount"><CoinIcon :size="24" /> +{{ revealTotalWon }} <span>MC</span></p>
            <p v-if="revealPremiumDaysWon > 0" class="reveal-amount"><PremiumIcon :size="24" /> +{{ formatDays(revealPremiumDaysWon) }} <span>Premium</span></p>
            <p v-if="!revealTotalWon && !revealPremiumDaysWon" class="reveal-amount reveal-amount-empty">Better luck next time</p>
            <p class="reveal-sub">{{ revealReels.length > 1 ? 'Total added to your account' : 'Added to your account' }}</p>
            <button class="btn-primary reveal-btn" @click="closeReveal">Nice!</button>
          </template>
          <p v-else class="reveal-sub">Opening…</p>
        </div>
      </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, nextTick, watch } from 'vue'
import { storeToRefs } from 'pinia'
import { useUserStore } from '../store/user'
import { casesAPI } from '../api/cases'

const props = defineProps({
  initialView: { type: String, default: 'shop' }, // 'shop' | 'inventory' | 'offers'
})

const userStore = useUserStore()
const { wallet } = storeToRefs(userStore)

const cases = ref([])
const loading = ref(true)
const buying = ref(false)
const opening = ref(false)
const oddsOpenId = ref(null)
const historyOpenId = ref(null)
const history = ref([])
const inventory = ref([]) // [{ case_id, case_name, count }]
const vouchers = ref([]) // [{ id, days, created_at }]
const activeView = ref(props.initialView === 'inventory' || props.initialView === 'offers' ? props.initialView : 'shop')
// Shop/Inventory/Offers is internal state, not a route change, so
// vue-router's scrollBehavior never runs for it — without this, switching
// views can leave the page scrolled well past the new (possibly shorter)
// content, stranding the reader down near the footer.
watch(activeView, () => window.scrollTo({ top: 0, behavior: 'auto' }))

function caseById(id) {
  return cases.value.find(c => c.id === id)
}

function switchToInventory() {
  activeView.value = 'inventory'
  loadInventory()
  loadVouchers()
}
function switchToOffers() {
  activeView.value = 'offers'
  loadOffers()
}

// ── Inventory item popups — tapping a case or voucher item opens a popup
// showing the not-yet-started state (qty picker for cases, activate/gift/
// sell for vouchers) instead of acting immediately. ─────────────────────
const preOpenInv = ref(null)
function openInventoryPopup(inv) {
  sendFormOpenId.value = null
  historyOpenId.value = null
  preOpenInv.value = inv
}
function closePreOpen() {
  preOpenInv.value = null
}
async function startOpenFromPopup(q) {
  const inv = preOpenInv.value
  closePreOpen()
  await openCases(caseById(inv.case_id), q)
}

const voucherPopup = ref(null)
const voucherBusy = ref(false)
const voucherSendOpen = ref(false)
const voucherSendMode = ref('gift') // 'gift' | 'sale'
const voucherSendWalletId = ref('')
const voucherSendPrice = ref(null)
const voucherSendBusy = ref(false)
const voucherSendError = ref('')
const voucherActivateMessage = ref('')

function openVoucherPopup(v) {
  voucherSendOpen.value = false
  voucherSendWalletId.value = ''
  voucherSendPrice.value = null
  voucherSendError.value = ''
  voucherActivateMessage.value = ''
  voucherPopup.value = v
}
function closeVoucherPopup() {
  voucherPopup.value = null
}
async function doActivateVoucher() {
  if (!voucherPopup.value || voucherBusy.value) return
  voucherBusy.value = true
  try {
    const res = await casesAPI.activateVoucher(voucherPopup.value.id)
    if (wallet.value) wallet.value.subscription_expires_at = res.premium_expires_at
    voucherActivateMessage.value = 'Activated!'
    await loadVouchers()
    setTimeout(closeVoucherPopup, 900)
  } catch (e) {
    voucherActivateMessage.value = e.response?.data?.detail || 'Could not activate that voucher.'
  } finally {
    voucherBusy.value = false
  }
}
async function submitVoucherSend() {
  if (!voucherPopup.value || !voucherSendWalletId.value.trim() || voucherSendBusy.value) return
  if (voucherSendMode.value === 'sale' && !voucherSendPrice.value) { voucherSendError.value = 'Enter a price.'; return }

  voucherSendBusy.value = true
  voucherSendError.value = ''
  try {
    if (voucherSendMode.value === 'gift') {
      await casesAPI.giftVoucher(voucherPopup.value.id, voucherSendWalletId.value.trim())
    } else {
      await casesAPI.sellVoucher(voucherPopup.value.id, voucherSendWalletId.value.trim(), voucherSendPrice.value)
    }
    closeVoucherPopup()
    await loadVouchers()
  } catch (e) {
    voucherSendError.value = e.response?.data?.detail || 'Could not send that offer.'
  } finally {
    voucherSendBusy.value = false
  }
}

// ── Gift / sell (P2P case offers) ──────────────────────────────
const sendFormOpenId = ref(null)
const sendMode = ref('gift') // 'gift' | 'sale'
const sendWalletId = ref('')
const sendQuantity = ref(1)
const sendPrice = ref(null)
const sendBusy = ref(false)
const sendError = ref('')

const incomingOffers = ref([])
const outgoingOffers = ref([])
const incomingVoucherOffers = ref([])
const outgoingVoucherOffers = ref([])
const offerBusyId = ref(null)

async function loadOffers() {
  try {
    const [incoming, outgoing, incomingV, outgoingV] = await Promise.all([
      casesAPI.listOffers('incoming'),
      casesAPI.listOffers('outgoing'),
      casesAPI.listVoucherOffers('incoming'),
      casesAPI.listVoucherOffers('outgoing'),
    ])
    incomingOffers.value = incoming
    outgoingOffers.value = outgoing
    incomingVoucherOffers.value = incomingV
    outgoingVoucherOffers.value = outgoingV
  } catch (e) {
    // Not critical to the page.
  }
}

async function respondToVoucherOffer(offer, action) {
  offerBusyId.value = offer.id
  try {
    if (action === 'accept') await casesAPI.acceptVoucherOffer(offer.id)
    else if (action === 'decline') await casesAPI.declineVoucherOffer(offer.id)
    else await casesAPI.cancelVoucherOffer(offer.id)
    await Promise.all([loadOffers(), loadVouchers()])
  } catch (e) {
    console.warn('[Cases] voucher offer action failed:', e.response?.data?.detail)
  } finally {
    offerBusyId.value = null
  }
}

async function submitSend(inv) {
  if (!sendWalletId.value.trim() || sendBusy.value) return
  if (sendMode.value === 'sale' && !sendPrice.value) { sendError.value = 'Enter a price.'; return }

  sendBusy.value = true
  sendError.value = ''
  try {
    if (sendMode.value === 'gift') {
      await casesAPI.gift(sendWalletId.value.trim(), inv.case_id, sendQuantity.value || 1)
    } else {
      await casesAPI.sell(sendWalletId.value.trim(), inv.case_id, sendQuantity.value || 1, sendPrice.value)
    }
    sendFormOpenId.value = null
    sendWalletId.value = ''
    sendQuantity.value = 1
    sendPrice.value = null
    await loadInventory()
  } catch (e) {
    sendError.value = e.response?.data?.detail || 'Could not send that offer.'
  } finally {
    sendBusy.value = false
  }
}

async function respondToOffer(offer, action) {
  offerBusyId.value = offer.id
  try {
    if (action === 'accept') await casesAPI.acceptOffer(offer.id)
    else if (action === 'decline') await casesAPI.declineOffer(offer.id)
    else await casesAPI.cancelOffer(offer.id)
    await Promise.all([loadOffers(), loadInventory()])
  } catch (e) {
    console.warn('[Cases] offer action failed:', e.response?.data?.detail)
  } finally {
    offerBusyId.value = null
  }
}

const totalOwned = computed(() => inventory.value.reduce((sum, i) => sum + i.count, 0) + vouchers.value.length)

// Per-case buy quantity, defaulting to 1 — the quick-pick chips (1/3/5/9)
// and +/- stepper both write into this same map. Capped to match the
// backend's own limit (CaseBuyRequest.quantity, le=50).
const MAX_QTY = 50
const buyQty = ref({})
function qty(caseId) {
  return buyQty.value[caseId] ?? 1
}
function setQty(caseId, value) {
  const n = Math.max(1, Math.min(MAX_QTY, Math.round(value) || 1))
  buyQty.value[caseId] = n
}

function inventoryCount(caseId) {
  return inventory.value.find(i => i.case_id === caseId)?.count ?? 0
}

function historyFor(caseId) {
  return history.value.filter(h => h.case_id === caseId)
}
function formatHistoryTime(iso) {
  const d = new Date(iso)
  return d.toLocaleString(undefined, { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' })
}

// ── Per-case-type identity: icon + accent color, keyed off the case name
// (there's no dedicated "type" field on the case row — the name is the
// only stable thing to key off, and these three names are seeded/admin-
// managed, not user input). ──────────────────────────────────────────
const CASE_STYLES = {
  'Premium Case': { icon: 'crown', color: '#8847ff' },
  'Mega Master Coin Case': { icon: 'case', color: '#eb4b4b' },
  'MasterCoins Case': { icon: 'case', color: '#8847ff' },
}
function caseStyle(name) {
  return CASE_STYLES[name] || { icon: 'case', color: 'var(--accent)' }
}

// ── Rarity tiers, CS2-style: grey / blue / purple / red / legendary ──────
// Each reward now carries its own tier explicitly (set server-side) instead
// of being inferred from a coin-value range — that range differs per case
// (a Mega Case's "grey" tier is worth more than the base case's "purple"),
// and inference breaks entirely for premium-days rewards, which have no
// coin value at all.
const TIER_COLORS = {
  grey: { border: '#b0c3d9', bg: 'rgba(176,195,217,0.14)' },
  blue: { border: '#4b69ff', bg: 'rgba(75,105,255,0.14)' },
  purple: { border: '#8847ff', bg: 'rgba(136,71,255,0.14)' },
  red: { border: '#eb4b4b', bg: 'rgba(235,75,75,0.14)' },
  legendary: { border: '#ffd700', bg: 'rgba(255,215,0,0.16)' },
}
function tierColor(tier) {
  return TIER_COLORS[tier] || TIER_COLORS.grey
}

// Premium-day rewards render as "Nothing" / "7d" / "31d" / "3mo" style
// labels instead of a coin count.
function formatDays(days) {
  if (days === 0) return 'Nothing'
  if (days % 30 === 0) return `${days / 30}mo`
  return `${days}d`
}
function rewardLabel(r) {
  return r.premium_days != null ? formatDays(r.premium_days) : String(r.coins)
}
function isPremiumReward(r) {
  return r.premium_days != null
}
// The API's win result is just {coins, premium_days} — no tier, since tier
// is a display concept from the odds table, not part of the outcome. Match
// it back against the case's own reward pool to color the winning tile.
function findTier(rewardPool, result) {
  const match = rewardPool.find(r => (
    result.premium_days != null ? r.premium_days === result.premium_days : r.coins === result.coins && r.premium_days == null
  ))
  return match?.tier || 'grey'
}

// ── Case-opening carousel (CS2-style scroll-and-land reel) ────────
const CASE_TILE_WIDTH = 76
const CASE_TILE_GAP = 8
const CASE_TILE_PITCH = CASE_TILE_WIDTH + CASE_TILE_GAP
const STRIP_LENGTH = 55
const WINNING_INDEX = 48
const SPIN_DURATION_MS = 4200

function buildStrip(rewardPool, winningReward) {
  const items = []
  for (let i = 0; i < STRIP_LENGTH; i++) {
    if (i === WINNING_INDEX) {
      items.push(winningReward)
    } else {
      items.push(rewardPool[Math.floor(Math.random() * rewardPool.length)])
    }
  }
  return items
}

// One entry per case opened in this batch — each is its own independent
// reel (x1 is just the single-reel case of this).
const revealOpen = ref(false)
const revealDone = ref(false)
const revealReels = ref([]) // [{ items, offset, animating }]
const revealTotalWon = ref(0)
const revealPremiumDaysWon = ref(0)
const carouselWrapRefs = ref([])
const errorMsg = ref('')

async function loadCases() {
  loading.value = true
  try {
    cases.value = await casesAPI.list()
  } finally {
    loading.value = false
  }
}

async function loadInventory() {
  try {
    inventory.value = await casesAPI.inventory()
  } catch (e) {
    // Not critical to the page.
  }
}

async function loadVouchers() {
  try {
    vouchers.value = await casesAPI.vouchers()
  } catch (e) {
    // Not critical to the page.
  }
}

async function loadHistory() {
  try {
    history.value = await casesAPI.history()
  } catch (e) {
    // Not critical to the page.
  }
}

async function buyCase(c, quantity) {
  if (buying.value) return
  if ((wallet.value?.balance_coins ?? 0) < c.cost_coins * quantity) return

  buying.value = true
  errorMsg.value = ''
  try {
    const res = await casesAPI.buy(c.id, quantity)
    if (wallet.value) wallet.value.balance_coins = res.new_balance
    await loadInventory()
    activeView.value = 'inventory'
  } catch (e) {
    errorMsg.value = e.response?.data?.detail || 'Could not buy the case — please try again.'
  } finally {
    buying.value = false
  }
}

async function openCases(c, quantity) {
  if (opening.value || !c) return
  if (inventoryCount(c.id) < quantity) return

  opening.value = true
  errorMsg.value = ''
  revealDone.value = false
  carouselWrapRefs.value = []
  revealReels.value = Array.from({ length: quantity }, () => ({ items: [], offset: 0, animating: false }))
  revealOpen.value = true

  try {
    const res = await casesAPI.openInventory(c.id, quantity)
    if (wallet.value) wallet.value.balance_coins = res.new_balance
    revealTotalWon.value = res.total_won
    revealPremiumDaysWon.value = res.rewards.reduce((sum, r) => sum + (r.premium_days || 0), 0)
    revealReels.value = res.rewards.map(reward => {
      const withTier = { ...reward, tier: findTier(c.rewards, reward) }
      return { items: buildStrip(c.rewards, withTier), offset: 0, animating: false }
    })
    await Promise.all([loadInventory(), loadVouchers()])

    // Two steps: one to mount each strip at offset 0 with no transition, a
    // second (a hair later, not on the same tick) so the browser paints
    // that resting frame before we flip on the transition and jump to the
    // target — otherwise the very first frame can get folded into the
    // animated one and skip the spin. A short setTimeout does this more
    // reliably than requestAnimationFrame: rAF callbacks are suspended
    // entirely while a tab isn't actively compositing (backgrounded, some
    // embedded WebViews), which would leave the strip stuck at rest forever.
    await nextTick()
    setTimeout(() => {
      revealReels.value.forEach((reel, i) => {
        const containerWidth = carouselWrapRefs.value[i]?.clientWidth ?? 300
        const jitter = (Math.random() - 0.5) * (CASE_TILE_WIDTH - 24)
        const target = -(WINNING_INDEX * CASE_TILE_PITCH + CASE_TILE_WIDTH / 2 - containerWidth / 2) + jitter
        reel.animating = true
        reel.offset = target
      })
    }, 30)

    // A timer, not transitionend, drives the reveal — for the same reason
    // the modal-close fix doesn't wait on that event either: it can simply
    // never fire (backgrounded tab, reduced motion), hanging the reveal.
    setTimeout(() => {
      revealDone.value = true
      opening.value = false
    }, SPIN_DURATION_MS)

    await loadHistory()
  } catch (e) {
    revealOpen.value = false
    opening.value = false
    errorMsg.value = e.response?.data?.detail || 'Could not open — please try again.'
  }
}

function closeReveal() {
  revealOpen.value = false
}

onMounted(async () => {
  await loadCases()
  await loadInventory()
  await loadVouchers()
  loadHistory()
  loadOffers()
})
</script>

<script>
import { h } from 'vue'

// ── Custom icons (no emoji) ─────────────────────────────────────
const CoinIcon = {
  props: { size: { type: Number, default: 18 }, color: { type: String, default: 'currentColor' } },
  render() {
    return h('svg', { viewBox: '0 0 24 24', width: this.size, height: this.size, fill: 'none', style: { flexShrink: 0 } }, [
      h('circle', { cx: 12, cy: 12, r: 8, stroke: this.color, 'stroke-width': 1.6 }),
      h('path', {
        d: 'M12 8v8M9.5 9.8c0-.9 1-1.6 2.5-1.6s2.5.7 2.5 1.6c0 2-5 1-5 3 0 .9 1 1.6 2.5 1.6s2.5-.7 2.5-1.6',
        stroke: this.color, 'stroke-width': 1.3, 'stroke-linecap': 'round',
      }),
    ])
  },
}

// Premium: a small crown, for premium-days case rewards (no coin value).
const PremiumIcon = {
  props: { size: { type: Number, default: 18 }, color: { type: String, default: 'currentColor' } },
  render() {
    return h('svg', { viewBox: '0 0 24 24', width: this.size, height: this.size, fill: 'none', style: { flexShrink: 0 } }, [
      h('path', {
        d: 'M4 18h16l-1.4-8-4.1 3.2L12 7l-2.5 6.2L5.4 10z',
        stroke: this.color, 'stroke-width': 1.5, 'stroke-linejoin': 'round', fill: 'none',
      }),
    ])
  },
}

// Case: a CS2-style metal crate — isometric box, diagonal hazard stripe
// across the lid, corner rivets and a MasterCoins badge.
let caseIconSeq = 0
// darken/lighten a #rrggbb hex by `amt` (-1..1) — used so each case color
// still gets a front/top gradient instead of a single flat fill.
function shade(hex, amt) {
  if (!hex.startsWith('#')) return hex // CSS var fallback — leave as-is, browser can't blend it here
  const n = parseInt(hex.slice(1), 16)
  const clamp = (v) => Math.max(0, Math.min(255, v))
  const r = clamp(((n >> 16) & 255) + Math.round(255 * amt))
  const g = clamp(((n >> 8) & 255) + Math.round(255 * amt))
  const b = clamp((n & 255) + Math.round(255 * amt))
  return `#${((1 << 24) + (r << 16) + (g << 8) + b).toString(16).slice(1)}`
}
const CaseIcon = {
  props: { size: { type: Number, default: 72 }, color: { type: String, default: 'var(--accent)' } },
  data() { return { uid: `ci${++caseIconSeq}` } },
  render() {
    const id = this.uid
    const base = this.color
    const dark = base.startsWith('#') ? shade(base, -0.35) : '#c46b00'
    const light = base.startsWith('#') ? shade(base, 0.45) : '#ffcf80'
    return h('svg', { viewBox: '0 0 48 48', width: this.size, height: this.size, fill: 'none' }, [
      h('defs', {}, [
        h('linearGradient', { id: `${id}-front`, x1: '0', y1: '0', x2: '0', y2: '1' }, [
          h('stop', { offset: '0', 'stop-color': base }),
          h('stop', { offset: '1', 'stop-color': dark }),
        ]),
        h('linearGradient', { id: `${id}-top`, x1: '0', y1: '0', x2: '1', y2: '1' }, [
          h('stop', { offset: '0', 'stop-color': light }),
          h('stop', { offset: '1', 'stop-color': base }),
        ]),
        h('clipPath', { id: `${id}-clip` }, [
          h('rect', { x: 8, y: 15, width: 28, height: 26, rx: 2 }),
        ]),
      ]),

      h('polygon', { points: '36,15 42,7 42,33 36,41', fill: dark }),
      h('polygon', { points: '8,15 14,7 42,7 36,15', fill: `url(#${id}-top)` }),
      h('rect', { x: 8, y: 15, width: 28, height: 26, rx: 2, fill: `url(#${id}-front)` }),

      h('g', { 'clip-path': `url(#${id}-clip)`, opacity: 0.5 }, [
        h('rect', { x: -4, y: 16, width: 50, height: 4, fill: '#14140f', transform: 'rotate(-28 20 28)' }),
        h('rect', { x: -4, y: 26, width: 50, height: 4, fill: '#14140f', transform: 'rotate(-28 20 28)' }),
      ]),

      h('circle', { cx: 11, cy: 18, r: 1.3, fill: 'rgba(0,0,0,.4)' }),
      h('circle', { cx: 33, cy: 18, r: 1.3, fill: 'rgba(0,0,0,.4)' }),
      h('circle', { cx: 11, cy: 38, r: 1.3, fill: 'rgba(0,0,0,.4)' }),
      h('circle', { cx: 33, cy: 38, r: 1.3, fill: 'rgba(0,0,0,.4)' }),

      h('g', { transform: 'translate(22,29) scale(0.94) translate(-12,-12)' }, [
        h('circle', { cx: 12, cy: 12, r: 8, fill: `url(#${id}-top)`, stroke: '#14140f', 'stroke-width': 1.7 }),
        h('path', {
          d: 'M12 8v8M9.5 9.8c0-.9 1-1.6 2.5-1.6s2.5.7 2.5 1.6c0 2-5 1-5 3 0 .9 1 1.6 2.5 1.6s2.5-.7 2.5-1.6',
          stroke: '#14140f', 'stroke-width': 1.5, 'stroke-linecap': 'round', fill: 'none',
        }),
      ]),
    ])
  },
}

export default { components: { CoinIcon, CaseIcon, PremiumIcon } }
</script>

<style scoped>
.cases-panel { max-width: 900px; }

.view-tabs {
  display: flex; justify-content: center; gap: 8px; margin-bottom: 24px; flex-wrap: wrap;
}
.view-tab {
  display: flex; align-items: center; gap: 7px;
  padding: 10px 22px; border-radius: 99px;
  background: var(--bg-elevated); border: 1.5px solid var(--line);
  color: var(--text-dim); font-size: 13px; font-weight: 700; cursor: pointer;
  transition: all .15s;
}
.view-tab:hover { border-color: rgba(255,154,0,.5); color: var(--text); }
.view-tab.active { background: rgba(255,154,0,.12); border-color: var(--accent); color: var(--accent); }
.tab-badge {
  background: var(--accent); color: #14140f; font-size: 10.5px; font-weight: 900;
  padding: 1px 7px; border-radius: 99px;
}

.loader-row { display: flex; justify-content: center; padding: 60px 0; }
.spinner {
  width: 32px; height: 32px; border: 2.5px solid var(--line);
  border-top-color: var(--accent); border-radius: 50%; animation: spin .8s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }
.empty { text-align: center; padding: 40px 20px; color: var(--text-dim); font-size: 14px; }

.case-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); gap: 16px; }
.case-card {
  --case-accent: var(--accent);
  background: linear-gradient(160deg, color-mix(in srgb, var(--case-accent) 10%, transparent), var(--bg-elevated) 60%);
  border: 1px solid color-mix(in srgb, var(--case-accent) 35%, transparent); border-radius: var(--radius-lg);
  padding: 22px 18px; text-align: center;
}
.case-icon { display: flex; justify-content: center; margin-bottom: 10px; }
.case-card h3 { font-size: 15px; font-weight: 800; color: var(--text); margin-bottom: 6px; }
.case-cost {
  display: flex; align-items: center; justify-content: center; gap: 6px;
  font-size: 20px; font-weight: 900; color: var(--accent); margin-bottom: 14px;
}
.case-cost span { font-size: 12px; font-weight: 700; color: var(--text-dim); }

.mini-btn {
  background: linear-gradient(160deg, var(--bg-elevated), var(--bg)); border: 1px solid var(--line); color: var(--text-dim);
  border-radius: 8px; font-weight: 700; cursor: pointer;
  box-shadow: 0 2px 6px rgba(0,0,0,.18);
  transition: border-color .15s, color .15s, transform .15s, box-shadow .15s;
}
.mini-btn:hover:not(:disabled) { border-color: var(--accent); color: var(--accent); box-shadow: 0 4px 14px -4px rgba(255,154,0,.4); transform: translateY(-1px); }
.mini-btn:active:not(:disabled) { transform: translateY(0); }

.qty-picker { display: flex; align-items: stretch; justify-content: center; gap: 6px; margin-bottom: 8px; }
.qty-btn {
  width: 34px; border-radius: 8px; background: var(--bg); border: 1px solid var(--line);
  color: var(--text-dim); font-size: 16px; font-weight: 700; cursor: pointer;
  transition: border-color .15s, color .15s;
}
.qty-btn:hover { border-color: var(--accent); color: var(--accent); }
.qty-input {
  width: 60px; text-align: center; background: var(--bg); border: 1px solid var(--line);
  border-radius: 8px; color: var(--text); font-size: 14px; font-weight: 800;
  -moz-appearance: textfield;
}
.qty-input::-webkit-outer-spin-button, .qty-input::-webkit-inner-spin-button { -webkit-appearance: none; margin: 0; }
.qty-input:focus { outline: none; border-color: var(--accent); }

.qty-presets { display: flex; justify-content: center; gap: 6px; margin-bottom: 14px; }
.qty-preset {
  padding: 4px 11px; border-radius: 99px; background: var(--bg); border: 1px solid var(--line);
  color: var(--text-dim); font-size: 11.5px; font-weight: 700; cursor: pointer;
  transition: all .15s;
}
.qty-preset:hover { border-color: var(--accent); color: var(--accent); }
.qty-preset.active { background: rgba(255,154,0,.14); border-color: var(--accent); color: var(--accent); }

.buy-btn { width: 100%; padding: 12px; font-size: 12.5px; }
.buy-btn:disabled { opacity: .5; cursor: not-allowed; }
.case-hint { font-size: 11px; color: var(--danger); margin-top: 6px; }
.case-hint.success { color: var(--success); }

.inventory-line { font-size: 12px; color: var(--text-dim); margin: 12px 0 8px; }
.inventory-line strong { color: var(--text); font-weight: 800; }

/* ── Inventory: items, not an inline action list — tapping one opens a
   popup (pre-open case picker, or the voucher activate/gift/sell panel)
   instead of acting immediately. ── */
.inventory-heading {
  font-size: 12px; font-weight: 800; color: var(--text-dim); text-transform: uppercase;
  letter-spacing: .05em; margin: 20px 0 12px;
}
.inventory-heading:first-child { margin-top: 0; }
.item-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(120px, 1fr)); gap: 12px; }
.item-tile {
  --case-accent: var(--accent);
  display: flex; flex-direction: column; align-items: center; gap: 6px;
  background: linear-gradient(160deg, color-mix(in srgb, var(--case-accent) 8%, transparent), var(--bg-elevated) 60%);
  border: 1px solid color-mix(in srgb, var(--case-accent) 30%, transparent); border-radius: var(--radius-md);
  padding: 16px 10px; cursor: pointer; transition: border-color .15s, transform .15s;
  font-family: inherit;
}
.item-tile:hover { border-color: var(--case-accent); transform: translateY(-2px); }
.item-tile-name { font-size: 12px; font-weight: 800; color: var(--text); text-align: center; line-height: 1.3; }
.item-tile-count { font-size: 11px; font-weight: 700; color: var(--case-accent); }

.open-row { display: flex; gap: 6px; flex-wrap: wrap; }
.open-btn { flex: 1; min-width: 70px; padding: 10px 6px; font-size: 12px; }
.open-btn:disabled { opacity: .4; cursor: not-allowed; }
/* Grey, not accent-colored — this is a neutral "pick a quantity" choice,
   not a call to action like Buy/Pay. */
.grey-btn {
  background: linear-gradient(160deg, var(--bg-elevated), var(--bg)); border: 1px solid var(--line); color: var(--text);
  border-radius: 8px; font-weight: 700; cursor: pointer;
  transition: border-color .15s, color .15s;
}
.grey-btn:hover:not(:disabled) { border-color: var(--case-accent, var(--accent)); color: var(--case-accent, var(--accent)); }
.grey-btn:disabled { opacity: .4; cursor: not-allowed; }

.preopen-modal { text-align: center; padding-top: 28px; }
.preopen-icon { --case-accent: var(--accent); display: flex; justify-content: center; margin-bottom: 10px; }
.preopen-title { font-size: 16px; font-weight: 800; color: var(--text); margin-bottom: 4px; }

.odds-toggle {
  display: block; width: 100%; margin-top: 14px;
  background: none; border: none; color: var(--text-dim);
  font-size: 11.5px; font-weight: 700; cursor: pointer; text-decoration: underline;
}
.odds-toggle:hover { color: var(--accent); }

.odds-grid {
  display: grid; grid-template-columns: repeat(auto-fill, minmax(60px, 1fr)); gap: 8px;
  margin-top: 14px;
}
.odds-tile {
  display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 3px;
  aspect-ratio: 1; border-radius: 8px; border: 1.5px solid;
}
.odds-tile-coins { font-size: 13px; font-weight: 800; color: var(--text); }

.history-list { display: flex; flex-direction: column; gap: 6px; margin-top: 14px; text-align: left; }
.history-row {
  display: flex; align-items: center; justify-content: space-between; gap: 8px;
  padding: 9px 12px; background: var(--bg); border-radius: 8px; font-size: 12.5px;
}
.history-time { color: var(--text-dim); font-size: 11px; white-space: nowrap; }
.history-amounts { display: flex; gap: 8px; font-weight: 700; font-variant-numeric: tabular-nums; white-space: nowrap; }
.spent { color: var(--danger); }
.won { color: var(--success); }

/* ── Gift / sell form ─────────────────────────────── */
.send-form {
  margin-top: 14px; padding: 12px; background: var(--bg); border-radius: 10px;
  display: flex; flex-wrap: wrap; gap: 8px; align-items: center; justify-content: center;
}
.send-mode-toggle { display: flex; gap: 6px; width: 100%; justify-content: center; }
.send-input { width: auto; flex: 1; min-width: 140px; }
.send-input-small { width: 64px; }

.mini-btn.danger:hover:not(:disabled) { border-color: var(--danger); color: var(--danger); box-shadow: 0 4px 14px -4px rgba(235,75,75,.4); }
.mini-btn:disabled { opacity: .5; cursor: not-allowed; }

/* ── Offers ─────────────────────────────── */
.offers-view { max-width: 640px; margin: 0 auto; }
.offers-heading { font-size: 13px; font-weight: 800; color: var(--text); margin: 24px 0 12px; text-transform: uppercase; letter-spacing: .04em; }
.offers-heading:first-child { margin-top: 0; }
.offers-list { display: flex; flex-direction: column; gap: 8px; }
.offer-row {
  display: flex; align-items: center; gap: 12px;
  background: var(--bg-elevated); border: 1px solid var(--line); border-radius: 12px; padding: 12px 16px;
}
.offer-info { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 2px; }
.offer-title { font-size: 13px; font-weight: 700; color: var(--text); }
.offer-sub { font-size: 11.5px; color: var(--text-dim); }
.offer-actions { display: flex; gap: 6px; flex-shrink: 0; }

/* ── Reveal modal ─────────────────────────────── */
.modal-backdrop {
  position: fixed; inset: 0; z-index: 500;
  background: rgba(0,0,0,0.65); display: flex; align-items: center; justify-content: center;
  padding: 20px; backdrop-filter: blur(4px); overflow-y: auto;
}
.reveal-modal {
  position: relative; width: 100%; max-width: 400px;
  background: var(--bg-elevated); border: 1px solid var(--line);
  border-radius: var(--radius-lg); padding: 24px 16px 28px; text-align: center;
}
.reveal-modal.multi { max-width: 420px; }
.modal-close {
  position: absolute; top: 12px; right: 12px;
  width: 30px; height: 30px; border-radius: 8px;
  background: var(--bg); border: 1px solid var(--line);
  color: var(--text-dim); cursor: pointer;
  display: flex; align-items: center; justify-content: center; font-size: 13px;
}

/* ── Carousel reel ─────────────────────────────── */
.carousel-wrap {
  position: relative; overflow: hidden; height: 100px;
  margin: 8px 0 20px; border-radius: 12px;
  background: var(--bg); border: 1px solid var(--line);
  -webkit-mask-image: linear-gradient(90deg, transparent 0%, #000 12%, #000 88%, transparent 100%);
  mask-image: linear-gradient(90deg, transparent 0%, #000 12%, #000 88%, transparent 100%);
}
.carousel-center-line {
  position: absolute; left: 50%; top: 0; bottom: 0; width: 2px;
  background: var(--accent); transform: translateX(-1px); z-index: 2;
  box-shadow: 0 0 10px var(--accent);
}
.carousel-strip {
  display: flex; gap: 8px; padding: 8px 0; height: 100%;
  transform: translateX(0);
}
.carousel-strip.animating { transition: transform 4.2s cubic-bezier(0.09, 0, 0.03, 1); }

.case-tile {
  flex-shrink: 0; width: 76px; height: 84px; border-radius: 8px;
  display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 4px;
  border: 1.5px solid; font-weight: 800; font-size: 13px; color: var(--text);
  transition: box-shadow .2s;
}
.case-tile.won { box-shadow: 0 0 0 2px var(--accent), 0 0 16px rgba(255,154,0,.5); }

.reveal-amount {
  display: flex; align-items: center; justify-content: center; gap: 8px;
  font-size: 26px; font-weight: 900; color: var(--accent);
}
.reveal-amount + .reveal-amount { margin-top: 6px; }
.reveal-amount span { font-size: 15px; color: var(--text-dim); font-weight: 700; }
.reveal-amount-empty { font-size: 16px; color: var(--text-dim); font-weight: 700; }
.reveal-sub { font-size: 12.5px; color: var(--text-dim); margin-top: 4px; margin-bottom: 18px; }
.reveal-btn { width: 100%; padding: 12px; }

.fade-enter-active, .fade-leave-active { transition: opacity .2s; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>
