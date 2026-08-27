<template>
  <main class="boards-page">
    <Header />

    <div class="wrap boards-content">
      <button class="back-btn" @click="mode === 'edit' ? (mode = 'list') : router.push('/user')">
        <svg viewBox="0 0 16 16" fill="none" width="14" height="14">
          <path d="M10 3L5 8l5 5" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
        {{ mode === 'edit' ? 'My Boards' : 'Profile' }}
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
          <button class="btn-primary" @click="openCreate">+ New Board</button>
        </section>

        <section class="list-card">
          <div v-if="loading" class="loading-row">Loading…</div>
          <div v-else-if="!boards.length" class="empty">No boards yet — create your first one.</div>
          <div v-else class="board-grid">
            <div v-for="b in boards" :key="b.id" class="board-card" @click="openEdit(b)">
              <div class="board-card-body">
                <h3>{{ b.title }}</h3>
                <p class="board-card-map">{{ mapName(b.map_id) }}</p>
              </div>
              <button class="mini-btn danger" @click.stop="remove(b)">Delete</button>
            </div>
          </div>
        </section>

        <Pagination :total="total" :page="page" :page-size="PAGE_SIZE" @update:page="onPageChange" />
      </template>

      <!-- ═══ EDIT MODE ═══════════════════════ -->
      <template v-else>
        <section class="page-head">
          <span class="eyebrow">{{ editingId ? 'Edit' : 'Create' }}</span>
          <h1>{{ editingId ? 'Edit board' : 'New board' }}</h1>
        </section>

        <section class="form-card">
          <div class="form-grid">
            <label class="field">
              <span>Map</span>
              <select v-model.number="form.map_id">
                <option v-for="m in maps" :key="m.id" :value="m.id">{{ m.name }}</option>
              </select>
            </label>
            <label class="field wide">
              <span>Title</span>
              <input v-model="form.title" type="text" placeholder="e.g. My A Site Practice" />
            </label>
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
            <button type="button" class="mini-btn" @click="form.grenades.push({ grenade_type: 'Smoke', target: '', order: form.grenades.length, from_x: null, from_y: null, to_x: null, to_y: null })">+ Add grenade</button>
          </div>

          <div v-if="!selectedMapImage" class="te-no-image">
            This map doesn't have a cover image yet — ask an admin to add one before you can place points on it.
          </div>
          <TacticsEditor
            v-else
            :image-url="selectedMapImage"
            :grenades="form.grenades"
            :player-paths="form.paths"
          />

          <div class="form-actions">
            <button class="btn-primary" :disabled="!canSave || saving" @click="save">
              {{ saving ? 'Saving…' : (editingId ? 'Save changes' : 'Create board') }}
            </button>
            <button class="mini-btn" @click="mode = 'list'">Cancel</button>
            <p v-if="errorMsg" class="err">{{ errorMsg }}</p>
          </div>
        </section>
      </template>
    </div>

    <Footer />
  </main>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { storeToRefs } from 'pinia'
import { useUserStore } from '../store/user'
import { boardsAPI } from '../api/boards'
import { strategiesAPI } from '../api/strategies'
import Header from '../components/Header.vue'
import Footer from '../components/Footer.vue'
import Pagination from '../components/Pagination.vue'
import TacticsEditor from '../components/TacticsEditor.vue'
import { grenadeTypeLabel } from '../utils/grenadeLabels'

const router = useRouter()
const { wallet } = storeToRefs(useUserStore())

const hasActiveAccess = computed(() => {
  if (wallet.value?.is_lifetime) return true
  const exp = wallet.value?.subscription_expires_at
  return !!(exp && new Date(exp) > new Date())
})

const GRENADE_TYPES = ['Smoke', 'Flashbang', 'Molotov', 'HE', 'Decoy']

const mode = ref('list') // 'list' | 'edit'
const loading = ref(true)
const saving = ref(false)
const errorMsg = ref('')

const maps = ref([])
const boards = ref([])
const editingId = ref(null)

const PAGE_SIZE = 5
const page = ref(1)
const total = ref(0)

function blankForm() {
  return { map_id: null, title: '', paths: [], grenades: [] }
}
const form = reactive(blankForm())
let pathKeySeq = 0

function mapName(id) {
  return maps.value.find(m => m.id === id)?.name ?? '—'
}

const selectedMapImage = computed(() => maps.value.find(m => m.id === form.map_id)?.cover_image_url || null)
const canSave = computed(() => form.map_id && form.title.trim().length > 0)

async function loadMaps() {
  const res = await strategiesAPI.getMaps({ limit: 100 })
  maps.value = res.maps
}

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

function openCreate() {
  Object.assign(form, blankForm())
  form.map_id = maps.value[0]?.id ?? null
  editingId.value = null
  errorMsg.value = ''
  mode.value = 'edit'
}

async function openEdit(boardPreview) {
  // The list only returns previews (no paths/grenades) — fetch the full
  // board before populating the form.
  const board = await boardsAPI.get(boardPreview.id)
  Object.assign(form, {
    map_id: board.map_id,
    title: board.title,
    grenades: (board.grenades || []).map(g => ({
      grenade_type: g.grenade_type, target: g.target, order: g.order,
      from_x: g.from_x ?? null, from_y: g.from_y ?? null, to_x: g.to_x ?? null, to_y: g.to_y ?? null,
    })),
    paths: (board.paths || []).map(p => ({
      _key: ++pathKeySeq, label: p.label, color: p.color,
      waypoints: p.waypoints.map(w => ({ x: w.x, y: w.y, t: w.t })),
      order: p.order,
    })),
  })
  editingId.value = board.id
  errorMsg.value = ''
  mode.value = 'edit'
}

async function save() {
  if (!canSave.value) return
  saving.value = true
  errorMsg.value = ''
  try {
    const payload = {
      map_id: form.map_id,
      title: form.title.trim(),
      grenades: form.grenades.filter(g => g.target?.trim()),
      paths: form.paths
        .filter(p => p.label?.trim() && p.waypoints.length >= 2)
        .map(({ _key, ...p }) => p),
    }
    if (editingId.value) {
      await boardsAPI.update(editingId.value, payload)
    } else {
      await boardsAPI.create(payload)
    }
    mode.value = 'list'
    await loadBoards()
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
  await loadMaps()
  await loadBoards()
})
</script>

<style scoped>
.boards-page { min-height: 100vh; background: var(--bg); }
.boards-content { max-width: 880px; padding: 32px 20px 140px; }

.back-btn {
  display: inline-flex; align-items: center; gap: 6px;
  background: var(--bg-elevated); border: 1px solid var(--line);
  color: var(--text-dim); padding: 8px 16px; border-radius: 8px;
  font-size: 13px; font-weight: 600; cursor: pointer;
  transition: border-color .2s, color .2s; margin-bottom: 28px;
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

.page-head { margin-bottom: 24px; }
.page-head.row { display: flex; align-items: center; justify-content: space-between; gap: 14px; flex-wrap: wrap; }
.eyebrow {
  display: block; font-size: 11px; font-weight: 800; letter-spacing: .08em;
  text-transform: uppercase; color: var(--accent); margin-bottom: 6px;
}
.page-head h1 { font-size: clamp(22px, 4vw, 30px); font-weight: 900; color: var(--text); }

.list-card, .form-card {
  background: var(--bg-elevated); border: 1px solid var(--line);
  border-radius: var(--radius-lg); padding: 22px; margin-bottom: 20px;
}
.loading-row, .empty { padding: 24px; text-align: center; color: var(--text-dim); font-size: 13px; }

.board-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 12px; }
.board-card {
  display: flex; align-items: center; justify-content: space-between; gap: 10px;
  background: var(--bg); border: 1px solid var(--line); border-radius: 10px;
  padding: 14px 16px; cursor: pointer; transition: border-color .15s;
}
.board-card:hover { border-color: var(--accent); }
.board-card-body h3 { font-size: 14px; font-weight: 700; color: var(--text); margin-bottom: 3px; }
.board-card-map { font-size: 12px; color: var(--text-dim); }

.mini-btn {
  background: var(--bg); border: 1px solid var(--line); color: var(--text-dim);
  padding: 6px 12px; border-radius: 7px; font-size: 12px; font-weight: 700; cursor: pointer;
  transition: border-color .15s, color .15s; flex-shrink: 0;
}
.mini-btn:hover { border-color: var(--accent); color: var(--accent); }
.mini-btn.danger:hover { border-color: var(--danger); color: var(--danger); }

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

.form-actions { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }
.err { color: var(--danger); font-size: 12.5px; font-weight: 600; margin: 0; width: 100%; }

@media (max-width: 640px) {
  .form-grid { grid-template-columns: 1fr; }
}
</style>
