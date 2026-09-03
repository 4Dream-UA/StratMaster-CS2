<template>
  <div class="boards-panel">
    <button v-if="mode === 'edit'" class="back-btn" @click="mode = 'list'">
      <svg viewBox="0 0 16 16" fill="none" width="14" height="14">
        <path d="M10 3L5 8l5 5" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
      </svg>
      My Boards
    </button>

    <!-- ═══ NOT PREMIUM ═══════════════════════ -->
    <section v-if="!hasActiveAccess" class="upsell-card">
      <span class="eyebrow">Premium feature</span>
      <h1>Your own tactics board</h1>
      <p>Sketch player paths and grenade lineups on any map, saved privately just for you — upgrade to Premium to unlock it.</p>
      <router-link to="/pricing" class="btn-primary">Get Premium Access</router-link>
    </section>

    <!-- ═══ LIST MODE ═══════════════════════ -->
    <template v-else-if="mode === 'list'">
      <section class="page-head row">
        <div>
          <span class="eyebrow">Premium</span>
          <h1>My Boards</h1>
        </div>
        <button class="btn-neutral" @click="openCreate">+ New Board</button>
      </section>

      <section class="list-card">
        <div v-if="loading" class="loading-row">Loading…</div>
        <div v-else-if="!boards.length" class="empty">No boards yet — create your first one.</div>
        <div v-else class="board-grid">
          <div v-for="b in boards" :key="b.id" class="board-card" @click="openEdit(b)">
            <img v-if="b.image_url" :src="b.image_url" alt="" class="board-card-thumb" loading="lazy" />
            <div class="board-card-foot">
              <div class="board-card-body">
                <h3>{{ b.title }}</h3>
              </div>
              <button class="mini-btn danger" @click.stop="remove(b)">Delete</button>
            </div>
          </div>
        </div>
      </section>

      <Pagination :total="total" :page="page" :page-size="PAGE_SIZE" @update:page="onPageChange" />

      <!-- ═══ SHARED WITH YOU ═══════════════ -->
      <section v-if="sharedTotal > 0" class="page-head" style="margin-top: 32px;">
        <span class="eyebrow">Invited</span>
        <h1>Shared With You</h1>
      </section>
      <section v-if="sharedTotal > 0" class="list-card">
        <div v-if="sharedLoading" class="loading-row">Loading…</div>
        <div v-else class="board-grid">
          <div v-for="b in sharedBoards" :key="b.id" class="board-card" @click="openEdit(b)">
            <img v-if="b.image_url" :src="b.image_url" alt="" class="board-card-thumb" loading="lazy" />
            <div class="board-card-foot">
              <div class="board-card-body">
                <h3>{{ b.title }}</h3>
              </div>
              <span class="shared-badge">Shared</span>
            </div>
          </div>
        </div>
      </section>
      <Pagination v-if="sharedTotal > 0" :total="sharedTotal" :page="sharedPage" :page-size="PAGE_SIZE" @update:page="onSharedPageChange" />
    </template>

    <!-- ═══ EDIT MODE ═══════════════════════ -->
    <template v-else>
      <section class="page-head">
        <span class="eyebrow">{{ editingId ? 'Edit' : 'Create' }}</span>
        <h1>{{ editingId ? 'Edit board' : 'New board' }}</h1>
      </section>

      <section class="form-card">
        <div class="form-grid">
          <label class="field wide">
            <span>Title</span>
            <input v-model="form.title" type="text" placeholder="e.g. My A Site Practice" />
          </label>
          <!-- Required. A board used to borrow whichever map you picked from
               the catalog, which meant no cover uploaded = nothing to draw
               on, and no way to use a callout map, a radar image or a
               screenshot of your own. -->
          <div class="field wide">
            <span>Map image <em class="req">required</em></span>
            <ImageUploadField v-model="form.image_url" variant="board" placeholder="Paste an image URL, or upload one" />
            <p class="field-hint">Any map picture works — a radar, a callout map, or a screenshot. This is what you'll draw on.</p>
          </div>
        </div>

        <!-- Grenades -->
        <div class="field">
          <span>Grenades</span>
          <div class="rows">
            <div v-for="(g, i) in form.grenades" :key="i" class="row grenade-row">
              <select v-model="g.grenade_type" class="row-select">
                <option v-for="t in GRENADE_TYPES" :key="t" :value="t">{{ grenadeTypeLabel(t) }}</option>
              </select>
              <input v-model="g.target" type="text" placeholder="Target (e.g. Window)" class="row-main" />
              <button type="button" class="row-remove" @click="form.grenades.splice(i, 1)">✕</button>
            </div>
          </div>
          <button type="button" class="mini-btn" @click="form.grenades.push({ grenade_type: 'Smoke', target: '', order: form.grenades.length, from_x: null, from_y: null, to_x: null, to_y: null, throw_at: null, lands_at: null, trajectory: null, effect_radius: null })">+ Add grenade</button>
        </div>

        <div v-if="!form.image_url" class="te-no-image">
          Add a map image above — that's the picture you'll place paths and grenades on.
        </div>
        <template v-else>
          <div class="preview-toggle-row">
            <button type="button" class="mini-btn" :class="{ active: previewMode }" @click="previewMode = !previewMode">
              {{ previewMode ? '✎ Back to editing' : '▶ Preview playback' }}
            </button>
          </div>
          <TacticsPlayer
            v-if="previewMode"
            :image-url="form.image_url"
            :grenades="form.grenades"
            :player-paths="form.paths"
            :annotations="form.annotations"
          />
          <TacticsEditor
            v-else
            :image-url="form.image_url"
            :grenades="form.grenades"
            :player-paths="form.paths"
            :annotations="form.annotations"
          />
        </template>

        <div class="form-actions">
          <button class="btn-neutral" :disabled="!canSave || saving" @click="save">
            {{ saving ? 'Saving…' : (editingId ? 'Save changes' : 'Create board') }}
          </button>
          <button class="mini-btn" @click="mode = 'list'">Cancel</button>
          <p v-if="errorMsg" class="err">{{ errorMsg }}</p>
        </div>
      </section>

      <!-- ═══ SHARE (owner only, board must already be saved) ═══ -->
      <section v-if="editingId && isOwnBoard" class="form-card share-card">
        <h3>Share this board</h3>

        <div class="share-block">
          <p class="share-label">Public view link</p>
          <p class="share-desc">Anyone with this link can view (read-only) — no account needed.</p>
          <div v-if="shareToken" class="share-row">
            <input type="text" readonly class="share-link-input" :value="shareLinkUrl" @click="$event.target.select()" />
            <button class="mini-btn" @click="copyShareLink">{{ shareLinkCopied ? 'Copied!' : 'Copy' }}</button>
            <button class="mini-btn danger" @click="revokeShare">Revoke</button>
          </div>
          <button v-else class="mini-btn" :disabled="shareBusy" @click="generateShare">
            {{ shareBusy ? 'Generating…' : 'Generate public link' }}
          </button>
        </div>

        <div class="share-block">
          <p class="share-label">Invite an editor</p>
          <p class="share-desc">Grant another player edit access by their Wallet ID.</p>
          <div class="share-row">
            <input v-model="collabWalletId" type="text" placeholder="Wallet ID" class="share-link-input" :disabled="collabBusy" />
            <button class="mini-btn" :disabled="!collabWalletId || collabBusy" @click="inviteCollaborator">
              {{ collabBusy ? '…' : 'Grant access' }}
            </button>
          </div>
          <p v-if="collabError" class="err">{{ collabError }}</p>

          <div v-if="collaborators.length" class="collab-list">
            <div v-for="c in collaborators" :key="c.id" class="collab-row">
              <span>{{ c.display_name || (c.username ? '@' + c.username : 'Player') }}</span>
              <button class="mini-btn danger" @click="removeCollaboratorRow(c)">Remove</button>
            </div>
          </div>
        </div>
      </section>
    </template>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, watch } from 'vue'
import { storeToRefs } from 'pinia'
import { useUserStore } from '../store/user'
import { boardsAPI } from '../api/boards'
import { botDeepLink } from '../config'
import Pagination from './Pagination.vue'
import TacticsEditor from './TacticsEditor.vue'
import TacticsPlayer from './TacticsPlayer.vue'
import ImageUploadField from './ImageUploadField.vue'
import { grenadeTypeLabel, normalizeGrenades } from '../utils/grenadeLabels'

const { user, wallet } = storeToRefs(useUserStore())

const hasActiveAccess = computed(() => {
  if (wallet.value?.is_lifetime) return true
  const exp = wallet.value?.subscription_expires_at
  return !!(exp && new Date(exp) > new Date())
})

const GRENADE_TYPES = ['Smoke', 'Flashbang', 'Molotov', 'HE', 'Decoy']

const mode = ref('list') // 'list' | 'edit'
// list<->edit is internal state, not a route change, so vue-router's
// scrollBehavior never runs for it — without this, leaving a tall editor
// for the (much shorter) list, or vice versa, can leave the page scrolled
// well past its new content, stranding the reader down near the footer.
watch(mode, () => window.scrollTo({ top: 0, behavior: 'auto' }))
const loading = ref(true)
const saving = ref(false)
const errorMsg = ref('')

const boards = ref([])
const editingId = ref(null)

const PAGE_SIZE = 5
const page = ref(1)
const total = ref(0)

const sharedBoards = ref([])
const sharedLoading = ref(false)
const sharedPage = ref(1)
const sharedTotal = ref(0)

const previewMode = ref(false)
const isOwnBoard = ref(true)
const shareToken = ref(null)
const shareLinkCopied = ref(false)
const shareBusy = ref(false)
const collaborators = ref([])
const collabWalletId = ref('')
const collabBusy = ref(false)
const collabError = ref('')

const shareLinkUrl = computed(() => shareToken.value ? botDeepLink(`board_${shareToken.value}`) : '')

function blankForm() {
  return { image_url: '', title: '', paths: [], grenades: [], annotations: { drawings: [], notes: [], bomb: null } }
}
const form = reactive(blankForm())
let pathKeySeq = 0

// A board can't be saved without a backdrop — there'd be nothing for its
// paths and grenades to sit on, and their coordinates are percentages of an
// image that wouldn't exist.
const canSave = computed(() => !!form.image_url.trim() && form.title.trim().length > 0)

async function loadBoards() {
  loading.value = true
  try {
    const res = await boardsAPI.list({ limit: PAGE_SIZE, offset: (page.value - 1) * PAGE_SIZE })
    boards.value = res.boards
    total.value = res.total
  } finally {
    loading.value = false
  }
}

function onPageChange(p) {
  page.value = p
  loadBoards()
}

async function loadSharedBoards() {
  sharedLoading.value = true
  try {
    const res = await boardsAPI.listSharedWithMe({ limit: PAGE_SIZE, offset: (sharedPage.value - 1) * PAGE_SIZE })
    sharedBoards.value = res.boards
    sharedTotal.value = res.total
  } finally {
    sharedLoading.value = false
  }
}

function onSharedPageChange(p) {
  sharedPage.value = p
  loadSharedBoards()
}

function openCreate() {
  Object.assign(form, blankForm())
  editingId.value = null
  errorMsg.value = ''
  previewMode.value = false
  isOwnBoard.value = true
  shareToken.value = null
  collaborators.value = []
  mode.value = 'edit'
}

async function openEdit(boardPreview) {
  // The list only returns previews (no paths/grenades) — fetch the full
  // board before populating the form.
  const board = await boardsAPI.get(boardPreview.id)
  Object.assign(form, {
    image_url: board.image_url || '',
    title: board.title,
    grenades: (board.grenades || []).map(g => ({
      grenade_type: g.grenade_type, target: g.target, order: g.order,
      from_x: g.from_x ?? null, from_y: g.from_y ?? null, to_x: g.to_x ?? null, to_y: g.to_y ?? null,
      throw_at: g.throw_at ?? null, lands_at: g.lands_at ?? null,
      trajectory: g.trajectory ? g.trajectory.map(pt => ({ x: pt.x, y: pt.y })) : null,
      effect_radius: g.effect_radius ?? null,
    })),
    paths: (board.paths || []).map(p => ({
      _key: ++pathKeySeq, label: p.label, color: p.color,
      waypoints: p.waypoints.map(w => ({ x: w.x, y: w.y, t: w.t })),
      order: p.order,
    })),
    annotations: board.annotations
      ? {
          drawings: (board.annotations.drawings || []).map(d => ({ points: d.points.map(pt => ({ ...pt })), color: d.color })),
          notes: (board.annotations.notes || []).map(n => ({ ...n })),
          bomb: board.annotations.bomb ? { ...board.annotations.bomb } : null,
        }
      : { drawings: [], notes: [], bomb: null },
  })
  editingId.value = board.id
  errorMsg.value = ''
  previewMode.value = false
  isOwnBoard.value = board.user_id === user.value?.id
  shareToken.value = board.share_token || null
  shareLinkCopied.value = false
  collabWalletId.value = ''
  collabError.value = ''
  collaborators.value = isOwnBoard.value ? await boardsAPI.listCollaborators(board.id) : []
  mode.value = 'edit'
}

async function generateShare() {
  shareBusy.value = true
  try {
    const res = await boardsAPI.createShareLink(editingId.value)
    shareToken.value = res.share_token
  } finally {
    shareBusy.value = false
  }
}

async function revokeShare() {
  await boardsAPI.revokeShareLink(editingId.value)
  shareToken.value = null
}

function copyShareLink() {
  navigator.clipboard?.writeText(shareLinkUrl.value)
  shareLinkCopied.value = true
  setTimeout(() => { shareLinkCopied.value = false }, 1800)
}

async function inviteCollaborator() {
  if (!collabWalletId.value.trim()) return
  collabBusy.value = true
  collabError.value = ''
  try {
    collaborators.value = await boardsAPI.addCollaborator(editingId.value, collabWalletId.value.trim())
    collabWalletId.value = ''
  } catch (e) {
    collabError.value = e.response?.data?.detail || 'Could not grant access.'
  } finally {
    collabBusy.value = false
  }
}

async function removeCollaboratorRow(collaborator) {
  collaborators.value = await boardsAPI.removeCollaborator(editingId.value, collaborator.id)
}

async function save() {
  if (!canSave.value) return
  saving.value = true
  errorMsg.value = ''
  try {
    const payload = {
      image_url: form.image_url.trim(),
      title: form.title.trim(),
      grenades: normalizeGrenades(form.grenades.filter(g => g.target?.trim())),
      paths: form.paths
        .filter(p => p.label?.trim() && p.waypoints.length >= 2)
        .map(({ _key, ...p }) => p),
      annotations: form.annotations,
    }
    if (editingId.value) {
      await boardsAPI.update(editingId.value, payload)
    } else {
      await boardsAPI.create(payload)
    }
    mode.value = 'list'
    await Promise.all([loadBoards(), loadSharedBoards()])
  } catch (e) {
    errorMsg.value = e.response?.data?.detail || 'Could not save board.'
  } finally {
    saving.value = false
  }
}

async function remove(board) {
  if (!confirm(`Delete "${board.title}"? This can't be undone.`)) return
  await boardsAPI.remove(board.id)
  if (boards.value.length === 1 && page.value > 1) page.value -= 1
  await loadBoards()
}

onMounted(async () => {
  if (!hasActiveAccess.value) return
  await loadBoards()
  await loadSharedBoards()
})
</script>

<style scoped>
.boards-panel { max-width: 880px; }

.back-btn {
  display: inline-flex; align-items: center; gap: 6px;
  background: var(--bg-elevated); border: 1px solid var(--line);
  color: var(--text-dim); padding: 8px 16px; border-radius: 8px;
  font-size: 13px; font-weight: 600; cursor: pointer;
  transition: border-color .2s, color .2s; margin-bottom: 20px;
}
.back-btn:hover { border-color: var(--accent); color: var(--accent); }

.upsell-card {
  background: linear-gradient(160deg, rgba(255,154,0,0.08), var(--bg-elevated) 60%);
  border: 1px solid rgba(255,154,0,0.3); border-radius: var(--radius-lg);
  padding: 32px 24px; text-align: center;
}
.upsell-card h1 { font-size: 24px; font-weight: 900; color: var(--text); margin: 8px 0 10px; }
.upsell-card p { font-size: 13.5px; color: var(--text-dim); max-width: 420px; margin: 0 auto 20px; line-height: 1.6; }
.upsell-card .btn-primary { text-decoration: none; display: inline-block; }

.page-head { margin-bottom: 20px; }
.page-head.row { display: flex; align-items: center; justify-content: space-between; gap: 14px; flex-wrap: wrap; }
.eyebrow {
  display: block; font-size: 11px; font-weight: 800; letter-spacing: .08em;
  text-transform: uppercase; color: var(--accent); margin-bottom: 6px;
}
.page-head h1 { font-size: clamp(20px, 4vw, 26px); font-weight: 900; color: var(--text); }

.list-card, .form-card {
  background: var(--bg-elevated); border: 1px solid var(--line);
  border-radius: var(--radius-lg); padding: 20px; margin-bottom: 18px;
}
/* TacticsEditor's canvas/tools split responds to how much width THIS
   card actually has, not the browser viewport — this card can sit next
   to a sticky sidebar (profile page) or fill the whole page (dedicated
   board editor), and a viewport-based breakpoint can't tell those apart,
   which is exactly what broke: at a viewport wide enough to trigger it
   but a card too narrow to fit it, the two-column layout still turned
   on and everything inside it got crushed. */
.form-card { container-type: inline-size; container-name: tactics-host; }
.loading-row, .empty { padding: 24px; text-align: center; color: var(--text-dim); font-size: 13px; }

.board-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 12px; }
/* Stacked, not a row: the card leads with the board's own map image now, so
   the title and the Delete/Shared control sit under it rather than being
   squeezed alongside a picture. */
.board-card {
  display: flex; flex-direction: column; align-items: stretch; gap: 10px;
  background: var(--bg); border: 1px solid var(--line); border-radius: 10px;
  padding: 12px; cursor: pointer; transition: border-color .15s;
}
.board-card:hover { border-color: var(--accent); }
.board-card-foot { display: flex; align-items: center; justify-content: space-between; gap: 10px; }
.board-card-body { min-width: 0; }
.board-card-body h3 {
  font-size: 14px; font-weight: 700; color: var(--text);
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.board-card-thumb {
  width: 100%; aspect-ratio: 16 / 9; object-fit: cover;
  border-radius: 8px; border: 1px solid var(--line);
  display: block; background: var(--bg-elevated);
}

.mini-btn {
  background: linear-gradient(160deg, var(--bg-elevated), var(--bg)); border: 1px solid var(--line); color: var(--text-dim);
  padding: 6px 12px; border-radius: 7px; font-size: 12px; font-weight: 700; cursor: pointer;
  box-shadow: 0 2px 6px rgba(0,0,0,.18);
  transition: border-color .15s, color .15s, transform .15s, box-shadow .15s; flex-shrink: 0;
}
.mini-btn:hover { border-color: var(--accent); color: var(--accent); box-shadow: 0 4px 14px -4px rgba(255,154,0,.4); transform: translateY(-1px); }
.mini-btn:active { transform: translateY(0); }
.mini-btn.danger:hover { border-color: var(--danger); color: var(--danger); }
.mini-btn.active { border-color: var(--accent); color: var(--accent); background: rgba(255,154,0,.1); }

.shared-badge {
  flex-shrink: 0; padding: 3px 9px; border-radius: 99px;
  background: rgba(255,154,0,.14); color: var(--accent);
  font-size: 10px; font-weight: 800; text-transform: uppercase; letter-spacing: .04em;
}

.preview-toggle-row { display: flex; justify-content: flex-end; margin-bottom: 10px; }

.share-card { margin-top: 18px; }
.share-card h3 { font-size: 15px; font-weight: 700; color: var(--text); margin-bottom: 16px; }
.share-block { margin-bottom: 20px; }
.share-block:last-child { margin-bottom: 0; }
.share-label { font-size: 12.5px; font-weight: 700; color: var(--text); margin-bottom: 2px; }
.share-desc { font-size: 12px; color: var(--text-dim); margin-bottom: 10px; }
.share-row { display: flex; gap: 8px; flex-wrap: wrap; align-items: center; }
.share-link-input {
  flex: 1; min-width: 160px;
  background: var(--bg); border: 1px solid var(--line); border-radius: 8px;
  padding: 9px 11px; color: var(--text); font-size: 12.5px; font-family: inherit;
}
.share-link-input:focus { outline: none; border-color: var(--accent); }

.collab-list { display: flex; flex-direction: column; gap: 6px; margin-top: 12px; }
.collab-row {
  display: flex; align-items: center; justify-content: space-between; gap: 10px;
  background: var(--bg); border: 1px solid var(--line); border-radius: 8px;
  padding: 8px 12px; font-size: 12.5px; color: var(--text);
}

.form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; margin-bottom: 16px; }
.field { display: flex; flex-direction: column; gap: 6px; margin-bottom: 16px; }
.field.wide { grid-column: 1 / -1; }
.field span { font-size: 11px; font-weight: 700; color: var(--text-dim); text-transform: uppercase; letter-spacing: .04em; }
.field input, .field select {
  background: var(--bg); border: 1px solid var(--line); border-radius: 9px;
  padding: 10px 12px; color: var(--text); font-size: 13.5px; font-family: inherit;
}
.field input:focus, .field select:focus { outline: none; border-color: var(--accent); }

.rows { display: flex; flex-direction: column; gap: 8px; margin-bottom: 10px; }
.row { display: flex; gap: 8px; align-items: center; }
.row input, .row select {
  background: var(--bg); border: 1px solid var(--line); border-radius: 8px;
  padding: 9px 11px; color: var(--text); font-size: 13px; font-family: inherit;
}
.row-main { flex: 1; min-width: 0; }
.row-select { width: 120px; flex-shrink: 0; }
.grenade-row { flex-wrap: wrap; }
.row-remove {
  background: none; border: none; color: var(--text-dim); cursor: pointer;
  font-size: 14px; padding: 4px 6px; flex-shrink: 0; transition: color .15s;
}
.row-remove:hover { color: var(--danger); }

.te-no-image {
  font-size: 12.5px; color: var(--text-dim); background: var(--bg);
  border: 1px dashed var(--line); border-radius: 12px; padding: 16px; margin-bottom: 20px;
}

.field .req {
  font-style: normal; font-size: 10px; font-weight: 800; letter-spacing: .05em;
  text-transform: uppercase; color: var(--accent); margin-left: 6px;
}
.field-hint { font-size: 11.5px; color: var(--text-dim); margin-top: 6px; line-height: 1.45; }

.form-actions { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }
.err { color: var(--danger); font-size: 12.5px; font-weight: 600; margin: 0; width: 100%; }

@media (max-width: 640px) {
  .form-grid { grid-template-columns: 1fr; }
}
</style>
