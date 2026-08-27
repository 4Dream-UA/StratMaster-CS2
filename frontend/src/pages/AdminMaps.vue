<template>
  <main class="admin-page">
    <Header />

    <div class="wrap admin-content">
      <button class="back-btn" @click="router.push('/admin')">
        <svg viewBox="0 0 16 16" fill="none" width="14" height="14">
          <path d="M10 3L5 8l5 5" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
        Admin Panel
      </button>

      <section class="page-head">
        <span class="eyebrow">Content</span>
        <h1>Maps</h1>
      </section>

      <!-- ── Add map ─────────────────────────── -->
      <section class="form-card">
        <h3>Add a map</h3>
        <div class="form-grid">
          <label class="field">
            <span>Name</span>
            <input v-model="form.name" type="text" placeholder="e.g. Anubis" />
          </label>
          <label class="field">
            <span>Cover image</span>
            <ImageUploadField v-model="form.cover_image_url" placeholder="https://… or upload" />
          </label>
        </div>
        <div class="form-actions">
          <button class="btn-primary" :disabled="!form.name || saving" @click="createMap">
            {{ saving ? 'Saving…' : 'Add Map' }}
          </button>
          <p v-if="errorMsg" class="err">{{ errorMsg }}</p>
        </div>
      </section>

      <!-- ── List ────────────────────────────── -->
      <div class="admin-search-wrap">
        <input v-model="search" type="text" class="admin-search" placeholder="Search maps by name…" />
        <button v-if="search" class="search-clear" @click="search = ''">✕</button>
      </div>

      <section class="list-card">
        <div v-if="loading" class="loading-row">Loading…</div>
        <table v-else class="admin-table">
          <thead>
            <tr><th>Name</th><th>Cover</th><th>Status</th><th></th></tr>
          </thead>
          <tbody>
            <tr v-for="m in maps" :key="m.id">
              <td>{{ m.name }}</td>
              <td class="dim">{{ m.cover_image_url || '—' }}</td>
              <td>
                <span class="status-pill" :class="m.is_active ? 'on' : 'off'">
                  {{ m.is_active ? 'Active' : 'Hidden' }}
                </span>
              </td>
              <td class="actions">
                <button class="mini-btn" @click="toggleActive(m)">
                  {{ m.is_active ? 'Hide' : 'Activate' }}
                </button>
              </td>
            </tr>
            <tr v-if="!maps.length">
              <td colspan="4" class="empty">No maps found.</td>
            </tr>
          </tbody>
        </table>
      </section>

      <Pagination :total="total" :page="page" :page-size="PAGE_SIZE" @update:page="onPageChange" />
    </div>

    <Footer />
  </main>
</template>

<script setup>
import { ref, reactive, watch, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { storeToRefs } from 'pinia'
import { useUserStore } from '../store/user'
import { adminAPI } from '../api/admin'
import Header from '../components/Header.vue'
import Footer from '../components/Footer.vue'
import Pagination from '../components/Pagination.vue'
import ImageUploadField from '../components/ImageUploadField.vue'

const router = useRouter()
const { user } = storeToRefs(useUserStore())
const maps = ref([])
const loading = ref(true)
const saving = ref(false)
const errorMsg = ref('')

const PAGE_SIZE = 5
const page = ref(1)
const total = ref(0)
const search = ref('')

const form = reactive({ name: '', cover_image_url: '' })

async function load() {
  loading.value = true
  const res = await adminAPI.getMaps({ limit: PAGE_SIZE, offset: (page.value - 1) * PAGE_SIZE, search: search.value || undefined })
  maps.value = res.maps
  total.value = res.total
  loading.value = false
}

function onPageChange(p) {
  page.value = p
  load()
}

let searchTimer = null
watch(search, () => {
  clearTimeout(searchTimer)
  searchTimer = setTimeout(() => { page.value = 1; load() }, 350)
})

async function createMap() {
  if (!form.name.trim()) return
  saving.value = true
  errorMsg.value = ''
  try {
    await adminAPI.createMap({
      name: form.name.trim(),
      cover_image_url: form.cover_image_url.trim() || null,
    })
    form.name = ''
    form.cover_image_url = ''
    await load()
  } catch (e) {
    errorMsg.value = e.response?.data?.detail || 'Could not create map.'
  } finally {
    saving.value = false
  }
}

async function toggleActive(map) {
  map.is_active = !map.is_active
  try {
    await adminAPI.updateMap(map.id, { is_active: map.is_active })
  } catch (e) {
    map.is_active = !map.is_active // revert on failure
  }
}

onMounted(() => {
  if (!user.value?.is_admin) { router.replace('/user'); return }
  load()
})
</script>

<style scoped>
.admin-page { min-height: 100vh; background: var(--bg); }
.admin-content { max-width: 880px; padding: 32px 20px 120px; }

.back-btn {
  display: inline-flex; align-items: center; gap: 6px;
  background: var(--bg-elevated); border: 1px solid var(--line);
  color: var(--text-dim); padding: 8px 16px; border-radius: 8px;
  font-size: 13px; font-weight: 600; cursor: pointer;
  transition: border-color .2s, color .2s; margin-bottom: 28px;
}
.back-btn:hover { border-color: var(--accent); color: var(--accent); }

.page-head { margin-bottom: 24px; }
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

.form-card, .list-card {
  background: var(--bg-elevated); border: 1px solid var(--line);
  border-radius: var(--radius-lg); padding: 22px; margin-bottom: 20px;
}
.form-card h3 { font-size: 15px; font-weight: 700; margin-bottom: 16px; }

.form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; margin-bottom: 16px; }
.field { display: flex; flex-direction: column; gap: 6px; }
.field span { font-size: 11px; font-weight: 700; color: var(--text-dim); text-transform: uppercase; letter-spacing: .04em; }
.field input, .field select, .field textarea {
  background: var(--bg); border: 1px solid var(--line); border-radius: 9px;
  padding: 10px 12px; color: var(--text); font-size: 13.5px; font-family: inherit;
}
.field input:focus, .field select:focus, .field textarea:focus { outline: none; border-color: var(--accent); }

.form-actions { display: flex; align-items: center; gap: 14px; }
.err { color: var(--danger); font-size: 12.5px; font-weight: 600; margin: 0; }

.loading-row, .empty { padding: 24px; text-align: center; color: var(--text-dim); font-size: 13px; }

.admin-table { width: 100%; border-collapse: collapse; font-size: 13.5px; }
.admin-table th {
  text-align: left; font-size: 11px; font-weight: 700; text-transform: uppercase;
  letter-spacing: .04em; color: var(--text-dim); padding: 0 10px 10px;
}
.admin-table td { padding: 12px 10px; border-top: 1px solid var(--line); }
.admin-table td.dim { color: var(--text-dim); font-size: 12.5px; max-width: 240px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.admin-table td.actions { text-align: right; }

.status-pill { padding: 3px 9px; border-radius: 99px; font-size: 11px; font-weight: 700; }
.status-pill.on { background: rgba(80,220,100,.12); color: var(--success); }
.status-pill.off { background: var(--bg); color: var(--text-dim); border: 1px solid var(--line); }

.mini-btn {
  background: var(--bg); border: 1px solid var(--line); color: var(--text-dim);
  padding: 6px 12px; border-radius: 7px; font-size: 12px; font-weight: 700; cursor: pointer;
  transition: border-color .15s, color .15s;
}
.mini-btn:hover { border-color: var(--accent); color: var(--accent); }

@media (max-width: 560px) {
  .form-grid { grid-template-columns: 1fr; }
  .admin-table { display: block; overflow-x: auto; }
}
</style>
