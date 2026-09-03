<template>
  <div class="tactics-editor">
    <div class="te-header">
      <h4>Tactical Animation <span class="te-optional">(optional)</span></h4>
      <p class="te-desc">Click on the map to place waypoints — powers the animated replay on the strategy page.</p>
    </div>

    <div v-if="!imageUrl" class="te-empty">Add an image above first — the animation is placed on top of it.</div>

    <template v-else>
      <div class="te-mode-toggle">
        <button type="button" class="te-mode-btn" :class="{ active: mode === 'paths' }" @click="setMode('paths')">
          <svg viewBox="0 0 20 20" fill="none" width="16" height="16"><circle cx="4" cy="16" r="2" fill="currentColor"/><circle cx="16" cy="4" r="2" fill="currentColor"/><path d="M4 16C4 10 10 10 10 10C10 10 16 10 16 4" stroke="currentColor" stroke-width="1.5" stroke-dasharray="2 2"/></svg>
          <span>Player Paths</span>
        </button>
        <button type="button" class="te-mode-btn" :class="{ active: mode === 'grenades' }" @click="setMode('grenades')">
          <svg viewBox="0 0 20 20" fill="none" width="16" height="16"><circle cx="10" cy="12" r="6" stroke="currentColor" stroke-width="1.5"/><path d="M10 6V3M8 3h4M13 5l1.5-1.5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>
          <span>Grenade Trajectories</span>
        </button>
        <button type="button" class="te-mode-btn" :class="{ active: mode === 'draw' }" @click="setMode('draw')">
          <svg viewBox="0 0 20 20" fill="none" width="16" height="16"><path d="M4 16l1-4L13 4l3 3-8 8-4 1z" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/></svg>
          <span>Draw</span>
        </button>
        <button type="button" class="te-mode-btn" :class="{ active: mode === 'notes' }" @click="setMode('notes')">
          <svg viewBox="0 0 20 20" fill="none" width="16" height="16"><path d="M4 3h12v10l-4 4H4V3z" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/><path d="M12 17v-4h4" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/></svg>
          <span>Notes</span>
        </button>
        <button type="button" class="te-mode-btn" :class="{ active: mode === 'bomb' }" @click="setMode('bomb')">
          <svg viewBox="0 0 20 20" fill="none" width="16" height="16"><circle cx="10" cy="12" r="6" stroke="currentColor" stroke-width="1.5"/><path d="M10 6V3M14 3l2-1" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>
          <span>C4</span>
        </button>
      </div>

      <p class="te-hint-drag">
        Drag a point to move it. Remove points from the list below — a click on the map
        always adds, so two lines can share a point.
      </p>

      <div class="te-canvas-wrap">
        <img
          :src="imageUrl" alt="" class="te-image" ref="imgRef" draggable="false"
          @click="onImageClick" @pointerdown="onImagePointerDown" @load="onImageLoad" @dragstart.prevent
        />
        <svg class="te-overlay" viewBox="0 0 100 100" preserveAspectRatio="none" :class="{ placing }">
          <!-- existing grenade trajectories -->
          <!-- A polyline, not a single line: a throw can bank off walls, so
               it has as many segments as it has points. Every point is its
               own draggable handle. -->
          <g v-for="(g, i) in grenades" :key="'g'+i">
            <polyline
              v-if="trajectoryOf(g).length >= 2"
              :points="pointsAttr(trajectoryOf(g))"
              fill="none" :stroke="i === activeGrenadeIdx ? '#ffcc44' : 'rgba(255,154,0,0.8)'"
              stroke-width="0.6" stroke-linejoin="round" marker-end="url(#te-arrow)"
            />
            <ellipse
              v-if="g.effect_radius && trajectoryOf(g).length >= 2"
              :cx="trajectoryOf(g)[trajectoryOf(g).length - 1].x"
              :cy="trajectoryOf(g)[trajectoryOf(g).length - 1].y"
              :rx="rx(g.effect_radius)" :ry="g.effect_radius"
              :fill="grenadeColor(g.grenade_type)" fill-opacity="0.16"
              :stroke="grenadeColor(g.grenade_type)" stroke-width="0.3"
              style="pointer-events: none"
            />
            <ellipse
              v-for="(pt, pi) in trajectoryOf(g)" :key="'gp'+pi"
              :cx="pt.x" :cy="pt.y"
              :rx="rx(pi === 0 ? 1.3 : 1.1)" :ry="pi === 0 ? 1.3 : 1.1"
              :fill="pi === 0 ? '#ff9a00' : pi === trajectoryOf(g).length - 1 ? grenadeColor(g.grenade_type) : '#ffcc44'"
              class="te-handle" @pointerdown="startGrenadeDrag($event, g, pi)"
            />
          </g>

          <!-- player paths -->
          <g v-for="p in playerPaths" :key="p._key">
            <polyline
              :points="pointsAttr(p.waypoints)"
              fill="none" :stroke="p.color" stroke-width="0.6" stroke-dasharray="1.6,1"
            />
            <g v-for="(w, wi) in p.waypoints" :key="wi">
              <ellipse
                :cx="w.x" :cy="w.y" :rx="rx(1.6)" ry="1.6" :fill="p.color"
                class="te-handle" @pointerdown="startWaypointDrag($event, p, wi)"
              />
              <text :x="w.x" :y="w.y" class="te-point-num" text-anchor="middle" dominant-baseline="central">{{ wi + 1 }}</text>
            </g>
          </g>

          <!-- freehand drawings -->
          <polyline
            v-for="(d, di) in annotations.drawings" :key="'draw'+di"
            :points="pointsAttr(d.points)" fill="none" :stroke="d.color" stroke-width="0.7"
            stroke-linecap="round" stroke-linejoin="round"
          />

          <!-- text notes -->
          <g v-for="(n, ni) in annotations.notes" :key="'note'+ni">
            <ellipse
              :cx="n.x" :cy="n.y" :rx="rx(1.4)" ry="1.4" fill="#ffd23f"
              class="te-handle" @pointerdown="startNoteDrag($event, n)"
            />
            <text :x="n.x" :y="n.y - 2.4" class="te-note-text" text-anchor="middle">{{ n.text || '…' }}</text>
          </g>

          <!-- C4 marker -->
          <g v-if="annotations.bomb" :transform="`translate(${annotations.bomb.x},${annotations.bomb.y})`">
            <ellipse :rx="rx(1.9)" ry="1.9" fill="#ff3b3b" class="te-handle" @pointerdown="startBombDrag($event)" />
            <text text-anchor="middle" dominant-baseline="central" class="te-bomb-label">C4</text>
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
        <div v-for="(g, i) in grenades" :key="i" class="te-path-card">
          <div class="te-path-head">
            <span class="te-grenade-label">{{ g.grenade_type ? grenadeTypeLabel(g.grenade_type) : 'Grenade' }} → {{ g.target || '?' }}</span>
            <button
              type="button" class="te-mini-btn" :class="{ active: activeGrenadeIdx === i }"
              @click="startGrenadePlacement(i)"
            >{{ activeGrenadeIdx === i ? 'Click the map…' : (trajectoryOf(g).length ? 'Add points' : 'Set trajectory') }}</button>
            <button v-if="trajectoryOf(g).length" type="button" class="te-mini-btn danger" @click="clearTrajectory(g)">Clear</button>
          </div>

          <!-- Two separate times, not one label plus a fixed 1.2s flight —
               a lineup that hangs in the air for three seconds and one that
               lands instantly are different calls. -->
          <div class="te-time-row">
            <label class="te-time-field">
              <span>Thrown at</span>
              <input v-model.number="g.throw_at" type="number" min="0" step="0.5" class="te-input" placeholder="sec" />
            </label>
            <label class="te-time-field">
              <span>Lands at</span>
              <input v-model.number="g.lands_at" type="number" min="0" step="0.5" class="te-input" placeholder="sec" />
            </label>
            <label class="te-time-field">
              <span>Arrival circle</span>
              <input v-model.number="g.effect_radius" type="number" min="0" max="40" step="0.5" class="te-input" placeholder="off" />
            </label>
          </div>
          <p class="te-hint">Leave the circle blank for none. It's drawn on the map as you type, so you can size it against the callouts.</p>
          <p v-if="badTiming(g)" class="te-warn">Lands before it's thrown — the replay will ignore this and use a default flight.</p>

          <div v-if="trajectoryOf(g).length" class="te-waypoints">
            <div v-for="(pt, pi) in trajectoryOf(g)" :key="pi" class="te-waypoint-row">
              <span class="te-waypoint-idx">{{ pi + 1 }}</span>
              <span class="te-waypoint-unit">
                {{ pi === 0 ? 'throw' : pi === trajectoryOf(g).length - 1 ? 'lands' : 'bounce' }}
              </span>
              <button type="button" class="te-waypoint-remove" @click="removeTrajectoryPoint(g, pi)">✕</button>
            </div>
          </div>
          <p v-else class="te-hint">No trajectory yet. Click "Set trajectory", then click the throw spot, any walls it banks off, and the landing spot.</p>
        </div>
      </div>

      <!-- ═══ PLAYER PATHS ═══ -->
      <div v-else-if="mode === 'paths'" class="te-panel">
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

      <!-- ═══ DRAW ═══ -->
      <div v-else-if="mode === 'draw'" class="te-panel">
        <p class="te-hint">Click and drag on the map to draw a line.</p>
        <label class="te-draw-color-row">
          <span>Line color</span>
          <input v-model="activeDrawColor" type="color" class="te-color" />
        </label>
        <p v-if="!annotations.drawings.length" class="te-hint">No lines yet.</p>
        <div v-for="(d, di) in annotations.drawings" :key="di" class="te-grenade-row">
          <span class="te-color-swatch" :style="{ background: d.color }"></span>
          <span class="te-grenade-label">Line {{ di + 1 }} ({{ d.points.length }} pts)</span>
          <button type="button" class="te-mini-btn danger" @click="removeDrawing(d)">Remove</button>
        </div>
      </div>

      <!-- ═══ NOTES ═══ -->
      <div v-else-if="mode === 'notes'" class="te-panel">
        <p class="te-hint">Click the map to drop a note. Drag to move it.</p>
        <p v-if="!annotations.notes.length" class="te-hint">No notes yet.</p>
        <div v-for="(n, ni) in annotations.notes" :key="ni" class="te-path-head">
          <input v-model="n.text" type="text" placeholder="Note text…" class="te-input te-path-label" />
          <button type="button" class="te-mini-btn danger" @click="annotations.notes.splice(ni, 1)">Remove</button>
        </div>
      </div>

      <!-- ═══ C4 ═══ -->
      <div v-else-if="mode === 'bomb'" class="te-panel">
        <p class="te-hint">Click the map to place the C4 marker — placing again just moves it.</p>
        <p v-if="!annotations.bomb" class="te-hint">Not placed yet.</p>
        <template v-else>
          <!-- Without a time the bomb sits on the site from second zero,
               which is wrong for anything that isn't already a post-plant. -->
          <label class="te-time-field te-bomb-time">
            <span>Planted at</span>
            <input v-model.number="annotations.bomb.t" type="number" min="0" step="0.5" class="te-input" placeholder="sec" />
          </label>
          <p class="te-hint">Leave blank and it shows for the whole replay.</p>
          <button type="button" class="te-mini-btn danger" @click="annotations.bomb = null">Remove C4 marker</button>
        </template>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onBeforeUnmount, watch, nextTick } from 'vue'
import { grenadeTypeLabel, grenadeColor } from '../utils/grenadeLabels'

const props = defineProps({
  imageUrl: { type: String, default: null },
  grenades: { type: Array, required: true }, // mutated in place (from_x/from_y/to_x/to_y)
  playerPaths: { type: Array, required: true }, // mutated in place
  // { drawings: [{points:[{x,y}], color}], notes: [{x,y,text}], bomb: {x,y}|null } — mutated in place
  annotations: { type: Object, default: () => ({ drawings: [], notes: [], bomb: null }) },
})

const mode = ref('paths')
const imgRef = ref(null)

// The overlay SVG uses viewBox="0 0 100 100" with preserveAspectRatio="none"
// so x/y percentages line up with the image regardless of its own aspect
// ratio — necessary for position, but it non-uniformly scales anything with
// a plain radius, squashing every circular marker into an oval on any
// non-square map. rx(r) compensates by widening/narrowing the x-radius so
// <ellipse :rx="rx(r)" :ry="r"> renders as a true circle in real pixels.
const imgAspect = ref(1)
function onImageLoad() {
  if (imgRef.value?.naturalWidth && imgRef.value?.naturalHeight) {
    imgAspect.value = imgRef.value.naturalWidth / imgRef.value.naturalHeight
  }
}
function rx(r) {
  return r / imgAspect.value
}
// The @load listener can miss an already-cached image (fires before Vue's
// handler is wired up in some browsers) — this catches that case whenever
// the image URL changes.
watch(() => props.imageUrl, () => {
  nextTick(() => { if (imgRef.value?.complete) onImageLoad() })
}, { immediate: true })

// While a placing mode is armed the handles are made click-through (see the
// .placing rule in the stylesheet), so the click reaches the image and adds
// a point wherever the pointer is — including exactly on top of a point that
// already exists.
const placing = computed(() =>
  mode.value === 'draw'
  || (mode.value === 'paths' && activePathKey.value !== null)
  || (mode.value === 'grenades' && activeGrenadeIdx.value >= 0)
)

function setMode(m) {
  mode.value = m
  activeGrenadeIdx.value = -1
  activePathKey.value = null
}

// ── Grenade trajectories ─────────────────────────────
const activeGrenadeIdx = ref(-1)

function hasTrajectory(g) {
  return trajectoryOf(g).length >= 2
}

// The points a grenade flies through. `trajectory` is the real store; the
// old from_/to_ pair is read as a two-point path so anything authored before
// bounces existed still shows and stays editable.
function trajectoryOf(g) {
  if (Array.isArray(g.trajectory) && g.trajectory.length) return g.trajectory
  if (g.from_x != null && g.from_y != null && g.to_x != null && g.to_y != null) {
    return [{ x: g.from_x, y: g.from_y }, { x: g.to_x, y: g.to_y }]
  }
  return []
}

// from_/to_ stay in sync with the ends of the trajectory: the strategy page's
// grenade list and anything else still reading the old pair keeps working.
function syncTrajectoryEnds(g) {
  const pts = Array.isArray(g.trajectory) ? g.trajectory : []
  if (pts.length >= 2) {
    g.from_x = pts[0].x; g.from_y = pts[0].y
    g.to_x = pts[pts.length - 1].x; g.to_y = pts[pts.length - 1].y
  } else {
    g.from_x = g.from_y = g.to_x = g.to_y = null
  }
}

function startGrenadePlacement(i) {
  const g = props.grenades[i]
  // Materialise a legacy from_/to_ pair into a real trajectory the first
  // time it's edited, so adding a bounce to an existing grenade works.
  if (!Array.isArray(g.trajectory) || !g.trajectory.length) {
    const existing = trajectoryOf(g)
    g.trajectory = existing.length ? existing.map(pt => ({ x: pt.x, y: pt.y })) : []
  }
  activeGrenadeIdx.value = activeGrenadeIdx.value === i ? -1 : i
}

function clearTrajectory(g) {
  g.trajectory = []
  syncTrajectoryEnds(g)
  activeGrenadeIdx.value = -1
}

function removeTrajectoryPoint(g, index) {
  if (!Array.isArray(g.trajectory)) g.trajectory = trajectoryOf(g).map(pt => ({ x: pt.x, y: pt.y }))
  g.trajectory.splice(index, 1)
  syncTrajectoryEnds(g)
}

function badTiming(g) {
  return g.throw_at != null && g.lands_at != null && g.lands_at <= g.throw_at
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

// ── Shared coordinate helper ──────────────────────────
// Returns null while the image hasn't actually rendered yet (e.g. a broken
// URL) — its rect collapses to 0×0, which would otherwise divide-by-zero
// into NaN waypoints.
function coordsFromEvent(event) {
  const rect = imgRef.value.getBoundingClientRect()
  if (!rect.width || !rect.height) return null
  const x = Math.round(((event.clientX - rect.left) / rect.width) * 1000) / 10
  const y = Math.round(((event.clientY - rect.top) / rect.height) * 1000) / 10
  return { x: Math.min(100, Math.max(0, x)), y: Math.min(100, Math.max(0, y)) }
}

// ── Drag-to-reposition / click-to-delete on existing points ──────────
const drag = ref(null) // { kind: 'waypoint', path, index } | { kind: 'grenade', grenade, end }
let dragMoved = false
let dragStartClient = null

function startWaypointDrag(event, path, index) {
  event.stopPropagation()
  drag.value = { kind: 'waypoint', path, index }
  dragMoved = false
  dragStartClient = { x: event.clientX, y: event.clientY }
  window.addEventListener('pointermove', onDragMove)
  window.addEventListener('pointerup', onDragEnd)
}

function startGrenadeDrag(event, grenade, index) {
  event.stopPropagation()
  drag.value = { kind: 'grenade', grenade, index }
  dragMoved = false
  dragStartClient = { x: event.clientX, y: event.clientY }
  window.addEventListener('pointermove', onDragMove)
  window.addEventListener('pointerup', onDragEnd)
}

function startNoteDrag(event, note) {
  event.stopPropagation()
  drag.value = { kind: 'note', note }
  dragMoved = false
  dragStartClient = { x: event.clientX, y: event.clientY }
  window.addEventListener('pointermove', onDragMove)
  window.addEventListener('pointerup', onDragEnd)
}

function startBombDrag(event) {
  event.stopPropagation()
  drag.value = { kind: 'bomb' }
  dragMoved = false
  dragStartClient = { x: event.clientX, y: event.clientY }
  window.addEventListener('pointermove', onDragMove)
  window.addEventListener('pointerup', onDragEnd)
}

function onDragMove(event) {
  if (!drag.value) return
  if (!dragMoved) {
    const dx = event.clientX - dragStartClient.x
    const dy = event.clientY - dragStartClient.y
    if (Math.hypot(dx, dy) > 3) dragMoved = true
  }
  if (!dragMoved) return

  const coords = coordsFromEvent(event)
  if (!coords) return
  const { x, y } = coords
  const d = drag.value
  if (d.kind === 'waypoint') {
    const wp = d.path.waypoints[d.index]
    wp.x = x
    wp.y = y
  } else if (d.kind === 'grenade') {
    if (!Array.isArray(d.grenade.trajectory) || !d.grenade.trajectory.length) {
      d.grenade.trajectory = trajectoryOf(d.grenade).map(pt => ({ x: pt.x, y: pt.y }))
    }
    const pt = d.grenade.trajectory[d.index]
    if (pt) { pt.x = x; pt.y = y }
    syncTrajectoryEnds(d.grenade)
  } else if (d.kind === 'note') {
    d.note.x = x
    d.note.y = y
  } else if (d.kind === 'bomb') {
    props.annotations.bomb.x = x
    props.annotations.bomb.y = y
  }
}

function onDragEnd() {
  window.removeEventListener('pointermove', onDragMove)
  window.removeEventListener('pointerup', onDragEnd)
  const d = drag.value
  drag.value = null
  if (!d) return

  // A click that didn't move used to delete whatever was under it. That
  // made it impossible to run two lines through one point — the click landed
  // on the existing handle and destroyed it — and cost people work every
  // time they mis-clicked. Removal now lives on explicit buttons in the
  // panels below, where it can't happen by accident.
}

onBeforeUnmount(() => {
  window.removeEventListener('pointermove', onDragMove)
  window.removeEventListener('pointerup', onDragEnd)
})

// ── Freehand drawing ───────────────────────────────────
const activeDrawColor = ref('#ff3b3b')
let activeDrawing = null

function onImagePointerDown(event) {
  if (mode.value !== 'draw') return
  const coords = coordsFromEvent(event)
  if (!coords) return
  props.annotations.drawings.push({ points: [coords], color: activeDrawColor.value })
  // Re-read the item back out of the reactive array instead of keeping the
  // plain object we just pushed — those are different references once
  // annotations is a reactive proxy, and mutating the plain one directly
  // (as this used to do) never triggers a re-render, so the line only
  // seemed to "appear" later instead of drawing live under the pointer.
  activeDrawing = props.annotations.drawings[props.annotations.drawings.length - 1]
  window.addEventListener('pointermove', onDrawMove)
  window.addEventListener('pointerup', onDrawEnd)
}
function onDrawMove(event) {
  if (!activeDrawing) return
  const coords = coordsFromEvent(event)
  if (!coords) return
  const last = activeDrawing.points[activeDrawing.points.length - 1]
  // Skip near-duplicate points so a slow drag doesn't bloat the array.
  if (Math.hypot(coords.x - last.x, coords.y - last.y) < 0.6) return
  activeDrawing.points.push(coords)
}
function onDrawEnd() {
  window.removeEventListener('pointermove', onDrawMove)
  window.removeEventListener('pointerup', onDrawEnd)
  if (activeDrawing && activeDrawing.points.length < 2) {
    // A tap with no real movement — discard rather than leave a 1-point dot.
    const idx = props.annotations.drawings.indexOf(activeDrawing)
    if (idx !== -1) props.annotations.drawings.splice(idx, 1)
  }
  activeDrawing = null
}
function removeDrawing(d) {
  const idx = props.annotations.drawings.indexOf(d)
  if (idx !== -1) props.annotations.drawings.splice(idx, 1)
}
function removeNote(n) {
  const idx = props.annotations.notes.indexOf(n)
  if (idx !== -1) props.annotations.notes.splice(idx, 1)
}

// ── Click on the image itself: add a new point ────────────────────────
function onImageClick(event) {
  const coords = coordsFromEvent(event)
  if (!coords) return
  const { x: clampedX, y: clampedY } = coords

  if (mode.value === 'notes') {
    props.annotations.notes.push({ x: clampedX, y: clampedY, text: '' })
    return
  }
  if (mode.value === 'bomb') {
    props.annotations.bomb = { x: clampedX, y: clampedY }
    return
  }

  if (mode.value === 'grenades' && activeGrenadeIdx.value !== -1) {
    const g = props.grenades[activeGrenadeIdx.value]
    // Every click appends another point, so a throw can bank off as many
    // walls as it needs. It used to take exactly two clicks and then close
    // itself, which made a bounce impossible to express.
    if (!Array.isArray(g.trajectory)) g.trajectory = []
    g.trajectory.push({ x: clampedX, y: clampedY })
    syncTrajectoryEnds(g)
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

.te-mode-toggle { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 12px; }
.te-mode-btn {
  display: inline-flex; align-items: center; gap: 6px;
  padding: 6px 13px; border-radius: 99px; background: var(--bg-elevated); border: 1.5px solid var(--line);
  color: var(--text-dim); font-size: 12px; font-weight: 700; cursor: pointer; transition: all .15s;
}
.te-mode-btn svg { flex-shrink: 0; }
.te-mode-btn.active { background: rgba(255,154,0,.12); border-color: var(--accent); color: var(--accent); }

.te-hint-drag { font-size: 11.5px; color: var(--text-dim); margin: -6px 0 10px; }

.te-canvas-wrap { position: relative; border-radius: 10px; overflow: hidden; margin-bottom: 14px; line-height: 0; }
/* touch-action: none on the drawable surface stops the browser's own
   pan/scroll gesture from hijacking a single-finger drag — without it,
   touch drawing/dragging on mobile just scrolls the page instead. */
/* draggable="false" + @dragstart.prevent stop the browser's native "drag
   this image" ghost-drag gesture — without both, a mouse-down-and-drag on
   desktop starts dragging the image itself instead of drawing, since the
   native image-drag gesture and our own pointer-drag drawing both listen
   to the same mousedown. Touch has no such native gesture, which is why
   this only ever showed up on desktop. */
.te-image {
  width: 100%; height: auto; display: block; cursor: crosshair; touch-action: none;
  -webkit-user-drag: none; user-drag: none;
}
.te-overlay { position: absolute; inset: 0; width: 100%; height: 100%; pointer-events: none; }
/* Handles must not swallow the click while a placing mode is armed —
   that is what let a new point be dropped on top of an existing one. */
.te-overlay.placing .te-time-row { display: flex; gap: 10px; flex-wrap: wrap; margin-top: 8px; }
.te-time-field { display: flex; align-items: center; gap: 6px; font-size: 11.5px; color: var(--text-dim); }
.te-time-field input { width: 68px; }
.te-bomb-time { margin: 8px 0; }
.te-warn { font-size: 11.5px; color: var(--danger); margin-top: 6px; }

.te-handle { pointer-events: none; }

.te-handle {
  pointer-events: all; cursor: grab; touch-action: none;
  /* Transparent stroke widens the hit area well past the visible dot —
     the SVG-drawn circles are far too small to tap accurately on mobile,
     but a visibly bigger dot would clutter the map. */
  stroke: transparent; stroke-width: 3.5;
}
.te-handle:active { cursor: grabbing; }
.te-point-num {
  pointer-events: none; font-size: 2.1px; font-weight: 700; fill: #14140f;
  font-family: inherit; user-select: none;
}
.te-note-text {
  pointer-events: none; font-size: 2.6px; font-weight: 700; fill: #ffd23f;
  font-family: inherit; user-select: none; paint-order: stroke;
  stroke: #14140f; stroke-width: 0.5px;
}
.te-bomb-label {
  pointer-events: none; font-size: 1.6px; font-weight: 800; fill: #fff;
  font-family: inherit; user-select: none;
}

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
  background: linear-gradient(160deg, var(--bg-elevated), var(--bg)); border: 1px solid var(--line); color: var(--text-dim);
  padding: 6px 12px; border-radius: 7px; font-size: 11.5px; font-weight: 700; cursor: pointer;
  box-shadow: 0 2px 6px rgba(0,0,0,.18);
  transition: border-color .15s, color .15s, transform .15s, box-shadow .15s; white-space: nowrap;
}
.te-mini-btn:hover { border-color: var(--accent); color: var(--accent); box-shadow: 0 4px 14px -4px rgba(255,154,0,.4); transform: translateY(-1px); }
.te-mini-btn:active { transform: translateY(0); }
.te-mini-btn.active { border-color: var(--accent); color: var(--accent); background: rgba(255,154,0,.1); }
.te-mini-btn.danger:hover { border-color: var(--danger); color: var(--danger); }

.te-waypoints { display: flex; flex-direction: column; gap: 5px; }
.te-waypoint-row { display: flex; align-items: center; gap: 8px; }
.te-waypoint-idx { font-size: 11px; color: var(--text-dim); width: 14px; flex-shrink: 0; }
.te-waypoint-t { width: 64px; flex-shrink: 0; }
.te-waypoint-unit { font-size: 11px; color: var(--text-dim); }
.te-waypoint-remove { background: none; border: none; color: var(--text-dim); cursor: pointer; font-size: 12px; margin-left: auto; }
.te-waypoint-remove:hover { color: var(--danger); }

.te-draw-color-row { display: flex; align-items: center; gap: 10px; font-size: 12.5px; color: var(--text-dim); }
.te-color-swatch { width: 14px; height: 14px; border-radius: 4px; flex-shrink: 0; border: 1px solid var(--line); }

/* ── Wide enough card: canvas and tools side by side instead of a long
   vertical stack — the map gets a fixed column, mode toggle/hint/panel
   sit in a sidebar next to it. Named grid areas let this reorder without
   touching the DOM (te-panel comes after te-canvas-wrap in markup but
   needs to render beside it, not below).
   A @container query, not @media — this responds to the actual width of
   the .form-card it's rendered in (see BoardsPanel.vue), not the browser
   viewport, since that card isn't always full-width (it can sit beside a
   sticky sidebar on the profile page). Threshold is the 420px canvas +
   24px gap + enough left over for the tools to not be cramped. */
@container tactics-host (min-width: 700px) {
  .tactics-editor {
    display: grid;
    grid-template-columns: 420px 1fr;
    grid-template-areas:
      "header header"
      "empty  empty"
      "canvas toggle"
      "canvas hint"
      "canvas panel";
    align-items: start;
    column-gap: 24px;
  }
  .te-header { grid-area: header; }
  .te-empty { grid-area: empty; }
  .te-mode-toggle {
    grid-area: toggle; flex-wrap: nowrap; margin-bottom: 0;
    display: grid; grid-template-columns: 1fr 1fr; gap: 8px;
  }
  .te-mode-btn { justify-content: flex-start; padding: 9px 14px; }
  .te-hint-drag { grid-area: hint; margin: 10px 0 0; }
  .te-canvas-wrap { grid-area: canvas; margin-bottom: 0; max-width: 420px; }
  .te-panel { grid-area: panel; margin-top: 12px; max-height: 480px; overflow-y: auto; padding-right: 4px; }
}
</style>
