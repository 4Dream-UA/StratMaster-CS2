<template>
  <main class="admin-page">
    <Header />

    <div class="wrap admin-content">
      <button class="back-btn" @click="mode === 'edit' ? (mode = 'list') : router.push('/admin')">
        <svg viewBox="0 0 16 16" fill="none" width="14" height="14">
          <path d="M10 3L5 8l5 5" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
        {{ mode === 'edit' ? 'Strategies' : 'Admin Panel' }}
      </button>

      <!-- ═══ LIST MODE ═══════════════════════ -->
      <template v-if="mode === 'list'">
        <section class="page-head row">
          <div>
            <span class="eyebrow">Content</span>
            <h1>Strategies</h1>
          </div>
          <button class="btn-primary" @click="openCreate">+ New Strategy</button>
        </section>

        <div class="admin-search-wrap">
          <input v-model="listSearch" type="text" class="admin-search" placeholder="Search strategies by title…" />
          <button v-if="listSearch" class="search-clear" @click="listSearch = ''">✕</button>
        </div>

        <section class="list-card">
          <div v-if="loading" class="loading-row">Loading…</div>
          <table v-else class="admin-table">
            <thead>
              <tr><th>Title</th><th>Map</th><th>Side / Plant</th><th>Access</th><th></th></tr>
            </thead>
            <tbody>
              <tr v-for="s in strategies" :key="s.id">
                <td>{{ s.title }}</td>
                <td class="dim">{{ mapName(s.map_id) }}</td>
                <td class="dim">{{ s.side === 'T_side' ? 'T' : 'CT' }} · Site {{ s.plant }}</td>
                <td>
                  <span class="status-pill" :class="s.is_free ? 'on' : 'premium'">
                    {{ s.is_free ? 'Free' : 'Premium' }}
                  </span>
                </td>
                <td class="actions">
                  <button class="mini-btn" @click="openEdit(s)">Edit</button>
                  <button class="mini-btn danger" @click="remove(s)">Delete</button>
                </td>
              </tr>
              <tr v-if="!strategies.length">
                <td colspan="5" class="empty">No strategies yet — create the first one.</td>
              </tr>
            </tbody>
          </table>
        </section>

        <Pagination :total="strategiesTotal" :page="listPage" :page-size="PAGE_SIZE" @update:page="onListPageChange" />
      </template>

      <!-- ═══ EDIT MODE ═══════════════════════ -->
      <template v-else>
        <section class="page-head">
          <span class="eyebrow">{{ editingId ? 'Edit' : 'Create' }}</span>
          <h1>{{ editingId ? 'Edit strategy' : 'New strategy' }}</h1>
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
              <input v-model="form.title" type="text" placeholder="e.g. A Split through Connector" />
            </label>
            <label class="field">
              <span>Side</span>
              <select v-model="form.side">
                <option value="T_side">Terrorist</option>
                <option value="CT_side">Counter-Terrorist</option>
              </select>
            </label>
            <label class="field">
              <span>Plant</span>
              <select v-model="form.plant">
                <option value="A">Site A</option>
                <option value="B">Site B</option>
              </select>
            </label>
            <label class="field">
              <span>Speed</span>
              <select v-model="form.speed">
                <option value="fast">Fast (&lt; 40s)</option>
                <option value="medium">Medium (40–120s)</option>
                <option value="slow">Slow (120s+)</option>
              </select>
            </label>
            <label class="field">
              <span>Difficulty (1–5)</span>
              <input v-model.number="form.difficulty_stars" type="number" min="1" max="5" />
            </label>
            <label class="field">
              <span>Success rate (%)</span>
              <input v-model.number="form.success_rate" type="number" min="1" max="100" />
            </label>
            <label class="field">
              <span>Author</span>
              <input v-model="form.author" type="text" placeholder="e.g. Team Spirit" />
            </label>
            <label class="field checkbox-field">
              <input v-model="form.is_free" type="checkbox" />
              <span>Free strategy (no subscription required)</span>
            </label>
          </div>

          <label class="field">
            <span>Roles &amp; notes</span>
            <textarea v-model="form.roles_description" rows="3" placeholder="Player 1: entry through connector…"></textarea>
          </label>
          <label class="field">
            <span>Timings</span>
            <textarea v-model="form.timings_description" rows="3" placeholder="00:10 — Rush mid&#10;00:50 — Plant A"></textarea>
          </label>

          <div class="field">
            <span>Buy types</span>
            <div class="tag-picker">
              <button
                v-for="t in buyTags" :key="t.id" type="button"
                class="tag-toggle" :class="{ active: form.buy_tag_ids.includes(t.id) }"
                @click="toggleBuyTag(t.id)"
              >{{ t.name }}</button>
            </div>
          </div>

          <!-- Images -->
          <div class="field">
            <span>Images (first = main map overview)</span>
            <div class="rows">
              <div v-for="(img, i) in form.images" :key="i" class="row">
                <ImageUploadField v-model="img.image_url" placeholder="Image URL or upload" />
                <input v-model.number="img.order" type="number" min="0" placeholder="Order" class="row-order" />
                <button type="button" class="row-remove" @click="form.images.splice(i, 1)">✕</button>
              </div>
            </div>
            <button type="button" class="mini-btn" @click="form.images.push({ image_url: '', order: form.images.length })">+ Add image</button>
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
                <input v-model="g.timing" type="text" placeholder="0:08" class="row-timing" />
                <input v-model="g.video_url" type="text" placeholder="Video/GIF URL" class="row-main" />
                <button type="button" class="row-remove" @click="form.grenades.splice(i, 1)">✕</button>
              </div>
            </div>
            <button type="button" class="mini-btn" @click="form.grenades.push({ grenade_type: 'Smoke', target: '', timing: '', video_url: '', order: form.grenades.length, from_x: null, from_y: null, to_x: null, to_y: null })">+ Add grenade</button>
          </div>

          <TacticsEditor
            :image-url="form.images[0]?.image_url || null"
            :grenades="form.grenades"
            :player-paths="form.player_paths"
            :annotations="form.annotations"
          />

          <div class="form-actions">
            <button class="btn-primary" :disabled="!canSave || saving" @click="save">
              {{ saving ? 'Saving…' : (editingId ? 'Save changes' : 'Create strategy') }}
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
import { ref, reactive, computed, watch, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { storeToRefs } from 'pinia'
import { useUserStore } from '../store/user'
import { adminAPI } from '../api/admin'
import { strategiesAPI } from '../api/strategies'
import Header from '../components/Header.vue'
import Footer from '../components/Footer.vue'
import Pagination from '../components/Pagination.vue'
import ImageUploadField from '../components/ImageUploadField.vue'
import TacticsEditor from '../components/TacticsEditor.vue'
import { grenadeTypeLabel } from '../utils/grenadeLabels'

const router = useRouter()
const { user } = storeToRefs(useUserStore())

const GRENADE_TYPES = ['Smoke', 'Flashbang', 'Molotov', 'HE', 'Decoy']

const mode = ref('list') // 'list' | 'edit'
const loading = ref(true)
const saving = ref(false)
const errorMsg = ref('')

const maps = ref([])
const buyTags = ref([])
const strategies = ref([])
const editingId = ref(null)

const PAGE_SIZE = 5
const listPage = ref(1)
const strategiesTotal = ref(0)
const listSearch = ref('')

function blankForm() {
  return {
    map_id: null,
    title: '',
    side: 'T_side',
    plant: 'A',
    speed: 'fast',
    difficulty_stars: 3,
    success_rate: 75,
    author: '',
    is_free: false,
    roles_description: '',
    timings_description: '',
    buy_tag_ids: [],
    images: [],
    grenades: [],
    player_paths: [],
    annotations: { drawings: [], notes: [], bomb: null },
  }
}
const form = reactive(blankForm())
let pathKeySeq = 0

function mapName(id) {
  return maps.value.find(m => m.id === id)?.name ?? '—'
}

function toggleBuyTag(id) {
  const idx = form.buy_tag_ids.indexOf(id)
  if (idx === -1) form.buy_tag_ids.push(id)
  else form.buy_tag_ids.splice(idx, 1)
}

const canSave = computed(() => form.map_id && form.title.trim().length > 0)

async function loadAll() {
  loading.value = true
  const [mapsRes, tagsRes, stratsRes] = await Promise.all([
    strategiesAPI.getMaps({ limit: 100 }),
    adminAPI.getBuyTags(),
    adminAPI.getStrategies({ limit: PAGE_SIZE, offset: (listPage.value - 1) * PAGE_SIZE, search: listSearch.value || undefined }),
  ])
  maps.value = mapsRes.maps
  buyTags.value = tagsRes
  strategies.value = stratsRes.strategies
  strategiesTotal.value = stratsRes.total
  loading.value = false
}

async function reloadStrategies() {
  const stratsRes = await adminAPI.getStrategies({
    limit: PAGE_SIZE, offset: (listPage.value - 1) * PAGE_SIZE, search: listSearch.value || undefined,
  })
  strategies.value = stratsRes.strategies
  strategiesTotal.value = stratsRes.total
}

function onListPageChange(p) {
  listPage.value = p
  reloadStrategies()
}

let listSearchTimer = null
watch(listSearch, () => {
  clearTimeout(listSearchTimer)
  listSearchTimer = setTimeout(() => { listPage.value = 1; reloadStrategies() }, 350)
})

function openCreate() {
  Object.assign(form, blankForm())
  form.map_id = maps.value[0]?.id ?? null
  editingId.value = null
  errorMsg.value = ''
  mode.value = 'edit'
}

function openEdit(strategy) {
  Object.assign(form, {
    map_id: strategy.map_id,
    title: strategy.title,
    side: strategy.side,
    plant: strategy.plant,
    speed: strategy.speed,
    difficulty_stars: strategy.difficulty_stars,
    success_rate: strategy.success_rate,
    author: strategy.author || '',
    is_free: strategy.is_free,
    roles_description: strategy.roles_description || '',
    timings_description: strategy.timings_description || '',
    buy_tag_ids: (strategy.buy_tags || []).map(t => t.id),
    images: (strategy.images || []).map(i => ({ image_url: i.image_url, order: i.order })),
    grenades: (strategy.grenades || []).map(g => ({
      grenade_type: g.grenade_type, target: g.target, timing: g.timing,
      video_url: g.video_url || '', order: g.order,
      from_x: g.from_x ?? null, from_y: g.from_y ?? null, to_x: g.to_x ?? null, to_y: g.to_y ?? null,
    })),
    player_paths: (strategy.player_paths || []).map(p => ({
      _key: ++pathKeySeq, label: p.label, color: p.color,
      waypoints: p.waypoints.map(w => ({ x: w.x, y: w.y, t: w.t })),
      order: p.order,
    })),
    annotations: strategy.annotations
      ? {
          drawings: (strategy.annotations.drawings || []).map(d => ({ points: d.points.map(pt => ({ ...pt })), color: d.color })),
          notes: (strategy.annotations.notes || []).map(n => ({ ...n })),
          bomb: strategy.annotations.bomb ? { ...strategy.annotations.bomb } : null,
        }
      : { drawings: [], notes: [], bomb: null },
  })
  editingId.value = strategy.id
  errorMsg.value = ''
  mode.value = 'edit'
}

async function save() {
  if (!canSave.value) return
  saving.value = true
  errorMsg.value = ''
  try {
    const payload = {
      ...form,
      author: form.author?.trim() || null,
      roles_description: form.roles_description?.trim() || null,
      timings_description: form.timings_description?.trim() || null,
      images: form.images.filter(i => i.image_url?.trim()),
      grenades: form.grenades.filter(g => g.target?.trim()),
      player_paths: form.player_paths
        .filter(p => p.label?.trim() && p.waypoints.length >= 2)
        .map(({ _key, ...p }) => p),
    }
    if (editingId.value) {
      await adminAPI.updateStrategy(editingId.value, payload)
    } else {
      await adminAPI.createStrategy(payload)
    }
    mode.value = 'list'
    await loadAll()
  } catch (e) {
    errorMsg.value = e.response?.data?.detail || 'Could not save strategy.'
  } finally {
    saving.value = false
  }
}

async function remove(strategy) {
  if (!confirm(`Delete "${strategy.title}"? This can't be undone.`)) return
  await adminAPI.deleteStrategy(strategy.id)
  // Deleting the last row on a page would strand you on an empty page.
  if (strategies.value.length === 1 && listPage.value > 1) listPage.value -= 1
  await reloadStrategies()
}

onMounted(() => {
  if (!user.value?.is_admin) { router.replace('/user'); return }
  loadAll()
})
</script>

<style scoped>
.admin-page { min-height: 100vh; background: var(--bg); }
.admin-content { max-width: 880px; padding: 32px 20px 140px; }

.back-btn {
  display: inline-flex; align-items: center; gap: 6px;
  background: var(--bg-elevated); border: 1px solid var(--line);
  color: var(--text-dim); padding: 8px 16px; border-radius: 8px;
  font-size: 13px; font-weight: 600; cursor: pointer;
  transition: border-color .2s, color .2s; margin-bottom: 28px;
}
.back-btn:hover { border-color: var(--accent); color: var(--accent); }

.page-head { margin-bottom: 24px; }
.page-head.row { display: flex; align-items: center; justify-content: space-between; gap: 14px; flex-wrap: wrap; }
.eyebrow {
  display: block; font-size: 11px; font-weight: 800; letter-spacing: .08em;
  text-transform: uppercase; color: var(--accent); margin-bottom: 6px;
}
.page-head h1 { font-size: clamp(22px, 4vw, 30px); font-weight: 900; color: var(--text); }

.admin-search-wrap { position: relative; margin-bottom: 16px; }
.admin-search {
  width: 100%; padding: 10px 36px 10px 14px;
  background: var(--bg-elevated); border: 1.5px solid var(--line);
  border-radius: 10px; font-size: 13.5px; font-family: inherit;
  color: var(--text); transition: border-color .2s;
}
.admin-search::placeholder { color: var(--text-dim); }
.admin-search:focus { outline: none; border-color: var(--accent); }
.admin-search-wrap .search-clear {
  position: absolute; right: 10px; top: 50%; transform: translateY(-50%);
  background: none; border: none; color: var(--text-dim); font-size: 13px; cursor: pointer; padding: 4px;
}
.admin-search-wrap .search-clear:hover { color: var(--text); }

.list-card, .form-card {
  background: var(--bg-elevated); border: 1px solid var(--line);
  border-radius: var(--radius-lg); padding: 22px; margin-bottom: 20px;
}
.loading-row, .empty { padding: 24px; text-align: center; color: var(--text-dim); font-size: 13px; }

.admin-table { width: 100%; border-collapse: collapse; font-size: 13.5px; }
.admin-table th {
  text-align: left; font-size: 11px; font-weight: 700; text-transform: uppercase;
  letter-spacing: .04em; color: var(--text-dim); padding: 0 10px 10px;
}
.admin-table td { padding: 12px 10px; border-top: 1px solid var(--line); }
.admin-table td.dim { color: var(--text-dim); font-size: 12.5px; }
.admin-table td.actions { text-align: right; display: flex; gap: 8px; justify-content: flex-end; }

.status-pill { padding: 3px 9px; border-radius: 99px; font-size: 11px; font-weight: 700; }
.status-pill.on { background: rgba(80,220,100,.12); color: var(--success); }
.status-pill.premium { background: rgba(255,154,0,.14); color: var(--accent); }

.mini-btn {
  background: var(--bg); border: 1px solid var(--line); color: var(--text-dim);
  padding: 6px 12px; border-radius: 7px; font-size: 12px; font-weight: 700; cursor: pointer;
  transition: border-color .15s, color .15s;
}
.mini-btn:hover { border-color: var(--accent); color: var(--accent); }
.mini-btn.danger:hover { border-color: var(--danger); color: var(--danger); }

/* ── Form ─────────────────────────────────── */
.form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; margin-bottom: 16px; }
.field { display: flex; flex-direction: column; gap: 6px; margin-bottom: 16px; }
.field.wide { grid-column: 1 / -1; }
.field span { font-size: 11px; font-weight: 700; color: var(--text-dim); text-transform: uppercase; letter-spacing: .04em; }
.field input, .field select, .field textarea {
  background: var(--bg); border: 1px solid var(--line); border-radius: 9px;
  padding: 10px 12px; color: var(--text); font-size: 13.5px; font-family: inherit;
}
.field input:focus, .field select:focus, .field textarea:focus { outline: none; border-color: var(--accent); }
.field textarea { resize: vertical; }

.checkbox-field { flex-direction: row; align-items: center; gap: 8px; }
.checkbox-field input { width: auto; }
.checkbox-field span { text-transform: none; font-size: 13px; font-weight: 600; color: var(--text); letter-spacing: 0; }

.tag-picker { display: flex; flex-wrap: wrap; gap: 8px; }
.tag-toggle {
  padding: 6px 13px; border-radius: 99px; background: var(--bg); border: 1.5px solid var(--line);
  color: var(--text-dim); font-size: 12px; font-weight: 700; cursor: pointer; transition: all .15s;
}
.tag-toggle.active { background: rgba(255,154,0,.12); border-color: var(--accent); color: var(--accent); }

.rows { display: flex; flex-direction: column; gap: 8px; margin-bottom: 10px; }
.row { display: flex; gap: 8px; align-items: center; }
.row input, .row select {
  background: var(--bg); border: 1px solid var(--line); border-radius: 8px;
  padding: 9px 11px; color: var(--text); font-size: 13px; font-family: inherit;
}
.row-main { flex: 1; min-width: 0; }
.row-order { width: 68px; }
.row-timing { width: 76px; }
.row-select { width: 120px; flex-shrink: 0; }
.grenade-row { flex-wrap: wrap; }
.row-remove {
  background: none; border: none; color: var(--text-dim); cursor: pointer;
  font-size: 14px; padding: 4px 6px; flex-shrink: 0; transition: color .15s;
}
.row-remove:hover { color: var(--danger); }

.form-actions { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }
.err { color: var(--danger); font-size: 12.5px; font-weight: 600; margin: 0; width: 100%; }

@media (max-width: 640px) {
  .form-grid { grid-template-columns: 1fr; }
  .admin-table { display: block; overflow-x: auto; }
}
</style>
