<template>
  <div class="tactics-editor">
    <div class="te-header">
      <h4>Tactical Animation <span class="te-optional">(optional)</span></h4>
      <p class="te-desc">Click on the map to place waypoints — powers the animated replay on the strategy page.</p>
    </div>

    <div v-if="!imageUrl" class="te-empty">Add an image above first — the animation is placed on top of it.</div>

    <template v-else>
      <div class="te-mode-toggle">
        <button type="button" class="te-mode-btn" :class="{ active: mode === 'paths' }" @click="setMode('paths')">Player Paths</button>
        <button type="button" class="te-mode-btn" :class="{ active: mode === 'grenades' }" @click="setMode('grenades')">Grenade Trajectories</button>
      </div>

      <div class="te-canvas-wrap">
        <img :src="imageUrl" alt="" class="te-image" @click="onImageClick" ref="imgRef" />
        <svg class="te-overlay" viewBox="0 0 100 100" preserveAspectRatio="none">
          <!-- existing grenade trajectories -->
          <g v-for="(g, i) in grenades" :key="'g'+i">
            <line
              v-if="hasTrajectory(g)"
              :x1="g.from_x" :y1="g.from_y" :x2="g.to_x" :y2="g.to_y"
              :stroke="i === activeGrenadeIdx ? '#ffcc44' : 'rgba(255,154,0,0.8)'" stroke-width="0.6"
              marker-end="url(#te-arrow)"
            />
            <circle v-if="hasTrajectory(g)" :cx="g.from_x" :cy="g.from_y" r="1.1" fill="#ff9a00" />
          </g>
          <!-- pending grenade placement -->
          <circle v-if="pendingFrom" :cx="pendingFrom.x" :cy="pendingFrom.y" r="1.3" fill="#ffcc44" />

          <!-- player paths -->
          <g v-for="p in playerPaths" :key="p._key">
            <polyline
              :points="pointsAttr(p.waypoints)"
              fill="none" :stroke="p.color" stroke-width="0.6" stroke-dasharray="1.6,1"
            />
            <circle
              v-for="(w, wi) in p.waypoints" :key="wi"
              :cx="w.x" :cy="w.y" r="1" :fill="p.color"
            />
          </g>

          <defs>
            <marker id="te-arrow" markerWidth="6" markerHeight="6" refX="5" refY="3" orient="auto">
              <path d="M0,0 L6,3 L0,6 z" fill="#ffcc44" />
            </marker>
          </defs>
        </svg>
      </div>

      <!-- ═══ GRENADE TRAJECTORIES ═══ -->
      <div v-if="mode === 'grenades'" class="te-panel">
        <p v-if="!grenades.length" class="te-hint">Add a grenade card above first.</p>
        <div v-for="(g, i) in grenades" :key="i" class="te-grenade-row">
          <span class="te-grenade-label">{{ g.grenade_type ? grenadeTypeLabel(g.grenade_type) : 'Grenade' }} → {{ g.target || '?' }}</span>
          <span v-if="hasTrajectory(g)" class="te-grenade-status">placed</span>
          <button
            type="button" class="te-mini-btn"
            :class="{ active: activeGrenadeIdx === i }"
            @click="startGrenadePlacement(i)"
          >{{ activeGrenadeIdx === i ? (pendingFrom ? 'Click the landing spot…' : 'Click the throw spot…') : (hasTrajectory(g) ? 'Redo' : 'Set trajectory') }}</button>
          <button v-if="hasTrajectory(g)" type="button" class="te-mini-btn danger" @click="clearTrajectory(g)">Clear</button>
        </div>
      </div>

      <!-- ═══ PLAYER PATHS ═══ -->
      <div v-else class="te-panel">
        <div v-for="p in playerPaths" :key="p._key" class="te-path-card">
          <div class="te-path-head">
            <input v-model="p.label" type="text" placeholder="Label (e.g. Entry)" class="te-input te-path-label" />
            <input v-model="p.color" type="color" class="te-color" />
            <button
              type="button" class="te-mini-btn" :class="{ active: activePathKey === p._key }"
              @click="toggleAddingTo(p)"
            >{{ activePathKey === p._key ? 'Click to add points…' : 'Add points' }}</button>
            <button type="button" class="te-mini-btn danger" @click="removePath(p)">Remove</button>
          </div>
          <div v-if="p.waypoints.length" class="te-waypoints">
            <div v-for="(w, wi) in p.waypoints" :key="wi" class="te-waypoint-row">
              <span class="te-waypoint-idx">{{ wi + 1 }}</span>
              <input v-model.number="w.t" type="number" min="0" step="0.5" class="te-input te-waypoint-t" />
              <span class="te-waypoint-unit">sec</span>
              <button type="button" class="te-waypoint-remove" @click="p.waypoints.splice(wi, 1)">✕</button>
            </div>
          </div>
        </div>
        <button type="button" class="te-mini-btn" @click="addPath">+ Add player path</button>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { grenadeTypeLabel } from '../utils/grenadeLabels'

const props = defineProps({
  imageUrl: { type: String, default: null },
  grenades: { type: Array, required: true }, // mutated in place (from_x/from_y/to_x/to_y)
  playerPaths: { type: Array, required: true }, // mutated in place
})

const mode = ref('paths')
const imgRef = ref(null)

function setMode(m) {
  mode.value = m
  activeGrenadeIdx.value = -1
  pendingFrom.value = null
  activePathKey.value = null
}

// ── Grenade trajectories ─────────────────────────────
const activeGrenadeIdx = ref(-1)
const pendingFrom = ref(null)

function hasTrajectory(g) {
  return g.from_x != null && g.from_y != null && g.to_x != null && g.to_y != null
}
function startGrenadePlacement(i) {
  activeGrenadeIdx.value = i
  pendingFrom.value = null
}
function clearTrajectory(g) {
  g.from_x = g.from_y = g.to_x = g.to_y = null
}

// ── Player paths ──────────────────────────────────────
let pathKeySeq = 0
const activePathKey = ref(null)

function addPath() {
  const key = ++pathKeySeq
  props.playerPaths.push({ _key: key, label: `Player ${props.playerPaths.length + 1}`, color: '#ff9a00', waypoints: [], order: props.playerPaths.length })
  activePathKey.value = key
}
function removePath(p) {
  const idx = props.playerPaths.indexOf(p)
  if (idx !== -1) props.playerPaths.splice(idx, 1)
  if (activePathKey.value === p._key) activePathKey.value = null
}
function toggleAddingTo(p) {
  activePathKey.value = activePathKey.value === p._key ? null : p._key
}
function pointsAttr(waypoints) {
  return waypoints.map(w => `${w.x},${w.y}`).join(' ')
}

// ── Shared click handler ─────────────────────────────
function onImageClick(event) {
  const rect = imgRef.value.getBoundingClientRect()
  const x = Math.round(((event.clientX - rect.left) / rect.width) * 1000) / 10
  const y = Math.round(((event.clientY - rect.top) / rect.height) * 1000) / 10
  const clampedX = Math.min(100, Math.max(0, x))
  const clampedY = Math.min(100, Math.max(0, y))

  if (mode.value === 'grenades' && activeGrenadeIdx.value !== -1) {
    const g = props.grenades[activeGrenadeIdx.value]
    if (!pendingFrom.value) {
      pendingFrom.value = { x: clampedX, y: clampedY }
    } else {
      g.from_x = pendingFrom.value.x
      g.from_y = pendingFrom.value.y
      g.to_x = clampedX
      g.to_y = clampedY
      pendingFrom.value = null
      activeGrenadeIdx.value = -1
    }
    return
  }

  if (mode.value === 'paths' && activePathKey.value != null) {
    const path = props.playerPaths.find(p => p._key === activePathKey.value)
    if (!path) return
    const lastT = path.waypoints.length ? path.waypoints[path.waypoints.length - 1].t : 0
    path.waypoints.push({ x: clampedX, y: clampedY, t: path.waypoints.length ? lastT + 3 : 0 })
  }
}
</script>

<style scoped>
.tactics-editor {
  background: var(--bg); border: 1px dashed var(--line); border-radius: 12px;
  padding: 16px; margin-bottom: 20px;
}
.te-header { margin-bottom: 12px; }
.te-header h4 { font-size: 13.5px; font-weight: 700; color: var(--text); margin-bottom: 4px; }
.te-optional { color: var(--text-dim); font-weight: 500; }
.te-desc { font-size: 12px; color: var(--text-dim); }
.te-empty { font-size: 12.5px; color: var(--text-dim); padding: 12px 0; }

.te-mode-toggle { display: flex; gap: 6px; margin-bottom: 12px; }
.te-mode-btn {
  padding: 6px 13px; border-radius: 99px; background: var(--bg-elevated); border: 1.5px solid var(--line);
  color: var(--text-dim); font-size: 12px; font-weight: 700; cursor: pointer; transition: all .15s;
}
.te-mode-btn.active { background: rgba(255,154,0,.12); border-color: var(--accent); color: var(--accent); }

.te-canvas-wrap { position: relative; border-radius: 10px; overflow: hidden; margin-bottom: 14px; line-height: 0; }
.te-image { width: 100%; height: auto; display: block; cursor: crosshair; }
.te-overlay { position: absolute; inset: 0; width: 100%; height: 100%; pointer-events: none; }

.te-panel { display: flex; flex-direction: column; gap: 10px; }
.te-hint { font-size: 12px; color: var(--text-dim); }

.te-grenade-row {
  display: flex; align-items: center; gap: 8px; flex-wrap: wrap;
  padding: 8px 10px; background: var(--bg-elevated); border-radius: 8px; font-size: 12.5px;
}
.te-grenade-label { flex: 1; min-width: 120px; color: var(--text); }
.te-grenade-status { color: var(--success); font-size: 11px; font-weight: 700; text-transform: uppercase; }

.te-path-card { background: var(--bg-elevated); border-radius: 10px; padding: 10px 12px; }
.te-path-head { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; margin-bottom: 8px; }
.te-path-label { flex: 1; min-width: 100px; }
.te-color { width: 34px; height: 30px; padding: 2px; border-radius: 7px; border: 1px solid var(--line); background: var(--bg); cursor: pointer; }

.te-input {
  background: var(--bg); border: 1px solid var(--line); border-radius: 7px;
  padding: 7px 9px; color: var(--text); font-size: 12.5px; font-family: inherit;
}
.te-input:focus { outline: none; border-color: var(--accent); }

.te-mini-btn {
  background: var(--bg); border: 1px solid var(--line); color: var(--text-dim);
  padding: 6px 12px; border-radius: 7px; font-size: 11.5px; font-weight: 700; cursor: pointer;
  transition: border-color .15s, color .15s; white-space: nowrap;
}
.te-mini-btn:hover { border-color: var(--accent); color: var(--accent); }
.te-mini-btn.active { border-color: var(--accent); color: var(--accent); background: rgba(255,154,0,.1); }
.te-mini-btn.danger:hover { border-color: var(--danger); color: var(--danger); }

.te-waypoints { display: flex; flex-direction: column; gap: 5px; }
.te-waypoint-row { display: flex; align-items: center; gap: 8px; }
.te-waypoint-idx { font-size: 11px; color: var(--text-dim); width: 14px; flex-shrink: 0; }
.te-waypoint-t { width: 64px; flex-shrink: 0; }
.te-waypoint-unit { font-size: 11px; color: var(--text-dim); }
.te-waypoint-remove { background: none; border: none; color: var(--text-dim); cursor: pointer; font-size: 12px; margin-left: auto; }
.te-waypoint-remove:hover { color: var(--danger); }
</style>
