<template>
  <div class="tactics-player">
    <div class="tp-canvas">
      <img :src="imageUrl" alt="Strategy map" class="tp-image" @load="onImageLoad" ref="imgRef" />
      <svg class="tp-overlay" viewBox="0 0 100 100" preserveAspectRatio="none" ref="overlayRef">
        <!-- Landing markers, persisting once thrown. Just the point of
             impact: the translucent effect zone that used to sit under it
             was a fifth of the map wide for a smoke, which buried the map
             it was drawn on instead of telling you anything the landing
             point doesn't. The flight is the only animation now. -->
        <g v-for="(g, i) in trajectoryGrenades" :key="'land'+i">
          <ellipse
            v-if="grenadeState(g, currentTime) === 'landed'"
            :cx="landingPoint(g).x" :cy="landingPoint(g).y" :rx="rx(0.9)" ry="0.9"
            :fill="grenadeColor(g.grenade_type)" stroke="#111213" stroke-width="0.25"
          />
        </g>

        <!-- player paths already walked (trail) -->
        <polyline
          v-for="p in playerPaths" :key="'trail'+p.label"
          :points="trailPoints(p, currentTime)"
          fill="none" :stroke="p.color" stroke-width="0.5" stroke-opacity="0.55"
        />

        <!-- flying grenades -->
        <g v-for="(g, i) in trajectoryGrenades" :key="'fly'+i">
          <ellipse
            v-if="grenadeState(g, currentTime) === 'flying'"
            :cx="grenadeFlightPos(g, currentTime).x" :cy="grenadeFlightPos(g, currentTime).y"
            :rx="rx(1.1)" ry="1.1" :fill="grenadeColor(g.grenade_type)"
          />
        </g>

        <!-- player dots -->
        <g v-for="p in playerPaths" :key="'dot'+p.label" :transform="`translate(${positionAt(p.waypoints, currentTime).x},${positionAt(p.waypoints, currentTime).y})`">
          <ellipse :rx="rx(1.8)" ry="1.8" :fill="p.color" stroke="#111213" stroke-width="0.3" />
        </g>

        <!-- freehand drawings -->
        <polyline
          v-for="(d, di) in annotations.drawings" :key="'draw'+di"
          :points="d.points.map(pt => `${pt.x},${pt.y}`).join(' ')"
          fill="none" :stroke="d.color" stroke-width="0.7"
          stroke-linecap="round" stroke-linejoin="round"
        />

        <!-- text notes -->
        <g v-for="(n, ni) in annotations.notes" :key="'note'+ni">
          <ellipse :cx="n.x" :cy="n.y" :rx="rx(1.4)" ry="1.4" fill="#ffd23f" />
          <text v-if="n.text" :x="n.x" :y="n.y - 2.4" class="tp-note-text" text-anchor="middle">{{ n.text }}</text>
        </g>

        <!-- C4 marker — only from the second it's planted. A bomb sitting on
             the site from the start of the replay is wrong for every
             strategy that isn't already a post-plant. A marker with no time
             is one authored before the field existed, so it shows
             throughout, as it always did. -->
        <g
          v-if="annotations.bomb && (bombTime === null || currentTime >= bombTime)"
          :transform="`translate(${annotations.bomb.x},${annotations.bomb.y})`"
        >
          <ellipse :rx="rx(1.9)" ry="1.9" fill="#ff3b3b" />
          <text text-anchor="middle" dominant-baseline="central" class="tp-bomb-label">C4</text>
        </g>
      </svg>

      <div v-if="playerPaths.length" class="tp-legend">
        <span v-for="p in playerPaths" :key="'lg'+p.label" class="tp-legend-item">
          <span class="tp-legend-dot" :style="{ background: p.color }"></span>{{ p.label }}
        </span>
      </div>
    </div>

    <div class="tp-controls">
      <button type="button" class="tp-play-btn" @click="togglePlay" :aria-label="playing ? 'Pause' : 'Play'">
        <svg v-if="!playing" viewBox="0 0 20 20" width="16" height="16" fill="currentColor"><path d="M6 4l11 6-11 6z"/></svg>
        <svg v-else viewBox="0 0 20 20" width="16" height="16" fill="currentColor"><rect x="5" y="4" width="4" height="12"/><rect x="11" y="4" width="4" height="12"/></svg>
      </button>

      <div class="tp-scrub-wrap">
        <input
          type="range" class="tp-scrubber" min="0" :max="totalDuration" step="0.05"
          :value="currentTime" @input="onScrub"
        />
        <!-- One tick per event, positioned by time. pointer-events:none so
             they never steal a drag from the scrubber underneath. -->
        <div class="tp-marks" aria-hidden="true">
          <span
            v-for="(m, mi) in timelineMarkers" :key="'mark'+mi"
            class="tp-mark" :style="{ left: (m.t / totalDuration * 100) + '%', background: m.color }"
            :title="`${formatTime(m.t)} — ${m.label}`"
          ></span>
        </div>
      </div>

      <span class="tp-time mono">{{ formatTime(currentTime) }} / {{ formatTime(totalDuration) }}</span>

      <div class="tp-speed-group">
        <button
          v-for="s in [1, 2, 5]" :key="s" type="button"
          class="tp-speed-btn" :class="{ active: speed === s }"
          @click="speed = s"
        >{{ s }}×</button>
      </div>

      <button type="button" class="tp-export-btn" :disabled="exporting" @click="exportImage" aria-label="Export as image">
        <svg viewBox="0 0 20 20" width="15" height="15" fill="none">
          <path d="M10 3v10M6 9l4 4 4-4M4 16h12" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
        {{ exporting ? '…' : 'Export' }}
      </button>
    </div>
    <p v-if="exportError" class="tp-export-error">{{ exportError }}</p>
  </div>
</template>

<script setup>
import { ref, computed, onUnmounted, watch, nextTick } from 'vue'
import { grenadeColor } from '../utils/grenadeLabels'

const props = defineProps({
  imageUrl: { type: String, required: true },
  grenades: { type: Array, default: () => [] },
  playerPaths: { type: Array, default: () => [] },
  annotations: { type: Object, default: () => ({ drawings: [], notes: [], bomb: null }) },
})

// The overlay SVG uses viewBox="0 0 100 100" with preserveAspectRatio="none"
// so x/y percentages line up with the image regardless of its own aspect
// ratio — necessary for position, but it non-uniformly scales anything with
// a plain radius, squashing every circular marker into an oval on any
// non-square map. rx(r) compensates by widening/narrowing the x-radius so
// <ellipse :rx="rx(r)" :ry="r"> renders as a true circle in real pixels.
const imgRef = ref(null)
const imgAspect = ref(1)
function onImageLoad() {
  if (imgRef.value?.naturalWidth && imgRef.value?.naturalHeight) {
    imgAspect.value = imgRef.value.naturalWidth / imgRef.value.naturalHeight
  }
}
function rx(r) {
  return r / imgAspect.value
}
// The @load listener can miss an already-cached image — this catches that.
watch(() => props.imageUrl, () => {
  nextTick(() => { if (imgRef.value?.complete) onImageLoad() })
}, { immediate: true })

// ── Export current view as a PNG ──────────────────────────────────
const overlayRef = ref(null)
const exporting = ref(false)
const exportError = ref('')

function loadImage(src, crossOrigin) {
  return new Promise((resolve, reject) => {
    const img = new Image()
    if (crossOrigin) img.crossOrigin = crossOrigin
    img.onload = () => resolve(img)
    img.onerror = reject
    img.src = src
  })
}

async function exportImage() {
  if (exporting.value) return
  exporting.value = true
  exportError.value = ''
  try {
    const baseImg = await loadImage(props.imageUrl, 'anonymous')

    const canvas = document.createElement('canvas')
    canvas.width = baseImg.naturalWidth || 1280
    canvas.height = baseImg.naturalHeight || 720
    const ctx = canvas.getContext('2d')
    ctx.drawImage(baseImg, 0, 0, canvas.width, canvas.height)

    // Snapshot the overlay exactly as currently rendered (whatever point in
    // the playback the scrubber is at).
    const svgString = new XMLSerializer().serializeToString(overlayRef.value)
    const svgUrl = 'data:image/svg+xml;charset=utf-8,' + encodeURIComponent(svgString)
    const overlayImg = await loadImage(svgUrl)
    ctx.drawImage(overlayImg, 0, 0, canvas.width, canvas.height)

    const blob = await new Promise(resolve => canvas.toBlob(resolve, 'image/png'))
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'stratmaster-strategy.png'
    document.body.appendChild(a)
    a.click()
    a.remove()
    URL.revokeObjectURL(url)
  } catch (e) {
    // Most likely cause: the map image isn't same-origin (an admin pasted
    // an external URL instead of uploading it), which taints the canvas
    // and blocks reading it back out as a PNG.
    exportError.value = 'Could not export — this image must be hosted on StratMaster (uploaded, not linked) to export.'
  } finally {
    exporting.value = false
  }
}

// Only used for grenades authored before throw_at/lands_at existed, where
// the label is the single time we have and the flight length is a guess.
const FALLBACK_FLIGHT = 1.2
const TAIL_BUFFER = 2

const trajectoryGrenades = computed(() =>
  props.grenades.filter(g => flightPath(g).length >= 2)
)

function parseTiming(t) {
  if (!t) return 0
  const m = String(t).match(/^(\d+):(\d{1,2})$/)
  if (m) return parseInt(m[1], 10) * 60 + parseInt(m[2], 10)
  const n = parseFloat(t)
  return Number.isNaN(n) ? 0 : n
}

// The points a grenade travels through. An explicit trajectory can have any
// number of them, so a throw can bank off a wall; without one we fall back
// to the old two-point from_/to_ pair.
function flightPath(g) {
  if (Array.isArray(g.trajectory) && g.trajectory.length >= 2) return g.trajectory
  if (g.from_x != null && g.from_y != null && g.to_x != null && g.to_y != null) {
    return [{ x: g.from_x, y: g.from_y }, { x: g.to_x, y: g.to_y }]
  }
  return []
}

function throwTime(g) {
  return g.throw_at != null ? g.throw_at : parseTiming(g.timing)
}
function landTime(g) {
  // A lands_at that isn't actually after the throw would make the flight
  // instantaneous or run backwards — treat it as unset.
  if (g.lands_at != null && g.lands_at > throwTime(g)) return g.lands_at
  return throwTime(g) + FALLBACK_FLIGHT
}

const bombTime = computed(() => props.annotations?.bomb?.t ?? null)

const totalDuration = computed(() => {
  let max = 0
  for (const p of props.playerPaths) {
    for (const w of p.waypoints) max = Math.max(max, w.t)
  }
  for (const g of trajectoryGrenades.value) max = Math.max(max, landTime(g))
  if (bombTime.value != null) max = Math.max(max, bombTime.value)
  return Math.max(5, max + TAIL_BUFFER)
})

// Everything that happens at a specific second, for the ticks under the
// scrubber — the point is to see when things happen instead of reading a
// list and counting.
const timelineMarkers = computed(() => {
  const marks = []
  for (const g of trajectoryGrenades.value) {
    marks.push({ t: throwTime(g), color: grenadeColor(g.grenade_type), label: `${g.grenade_type} → ${g.target}` })
  }
  if (bombTime.value != null) {
    marks.push({ t: bombTime.value, color: '#ff3b3b', label: 'C4 planted' })
  }
  return marks.filter(m => m.t > 0 && m.t <= totalDuration.value)
})

function positionAt(waypoints, t) {
  if (!waypoints.length) return { x: 0, y: 0 }
  if (t <= waypoints[0].t) return { x: waypoints[0].x, y: waypoints[0].y }
  for (let i = 0; i < waypoints.length - 1; i++) {
    const a = waypoints[i], b = waypoints[i + 1]
    if (t >= a.t && t <= b.t) {
      const span = b.t - a.t
      const frac = span > 0 ? (t - a.t) / span : 0
      return { x: a.x + (b.x - a.x) * frac, y: a.y + (b.y - a.y) * frac }
    }
  }
  const last = waypoints[waypoints.length - 1]
  return { x: last.x, y: last.y }
}

function trailPoints(path, t) {
  const pts = path.waypoints.filter(w => w.t <= t).map(w => `${w.x},${w.y}`)
  const cur = positionAt(path.waypoints, t)
  pts.push(`${cur.x},${cur.y}`)
  return pts.join(' ')
}

function grenadeState(g, t) {
  if (t < throwTime(g)) return 'hidden'
  if (t < landTime(g)) return 'flying'
  return 'landed'
}

function landingPoint(g) {
  const path = flightPath(g)
  return path[path.length - 1] || { x: 0, y: 0 }
}

// Walks the flight path at a constant speed, so a throw that bounces spends
// proportionally longer on its longer legs instead of jumping between
// bends. A two-point path still arcs, which is what a direct throw looks
// like; a path with bends is drawn as straight legs, which is what a bounce
// actually is.
function grenadeFlightPos(g, t) {
  const path = flightPath(g)
  const start = throwTime(g)
  const frac = Math.min(1, Math.max(0, (t - start) / (landTime(g) - start)))

  if (path.length === 2) {
    const [a, b] = path
    const mx = (a.x + b.x) / 2
    const my = (a.y + b.y) / 2 - 14
    return {
      x: (1 - frac) ** 2 * a.x + 2 * (1 - frac) * frac * mx + frac ** 2 * b.x,
      y: (1 - frac) ** 2 * a.y + 2 * (1 - frac) * frac * my + frac ** 2 * b.y,
    }
  }

  const legs = []
  let total = 0
  for (let i = 0; i < path.length - 1; i++) {
    const len = Math.hypot(path[i + 1].x - path[i].x, path[i + 1].y - path[i].y)
    legs.push(len)
    total += len
  }
  if (total === 0) return path[0]

  let travelled = frac * total
  for (let i = 0; i < legs.length; i++) {
    if (travelled <= legs[i] || i === legs.length - 1) {
      const f = legs[i] > 0 ? Math.min(1, travelled / legs[i]) : 1
      return {
        x: path[i].x + (path[i + 1].x - path[i].x) * f,
        y: path[i].y + (path[i + 1].y - path[i].y) * f,
      }
    }
    travelled -= legs[i]
  }
  return path[path.length - 1]
}

function formatTime(t) {
  const s = Math.floor(t)
  return `0:${String(s).padStart(2, '0')}`
}

// ── Playback loop ──────────────────────────────────────
const currentTime = ref(0)
const playing = ref(false)
const speed = ref(1)
let rafId = null
let lastTs = null

const MAX_FRAME_DELTA = 0.1 // seconds — caps the jump after the tab was backgrounded/suspended

function tick(ts) {
  if (lastTs == null) lastTs = ts
  const dt = Math.min((ts - lastTs) / 1000, MAX_FRAME_DELTA)
  lastTs = ts
  currentTime.value = Math.min(totalDuration.value, currentTime.value + dt * speed.value)
  if (currentTime.value >= totalDuration.value) {
    playing.value = false
    lastTs = null
    return
  }
  rafId = requestAnimationFrame(tick)
}

function play() {
  if (currentTime.value >= totalDuration.value) currentTime.value = 0
  playing.value = true
  lastTs = null
  rafId = requestAnimationFrame(tick)
}
function pause() {
  playing.value = false
  if (rafId) cancelAnimationFrame(rafId)
}
function togglePlay() { playing.value ? pause() : play() }
function onScrub(event) {
  pause()
  currentTime.value = parseFloat(event.target.value)
}

onUnmounted(() => { if (rafId) cancelAnimationFrame(rafId) })
</script>

<style scoped>
.tactics-player { border-radius: 14px; overflow: hidden; border: 1px solid var(--line); }

.tp-canvas { position: relative; line-height: 0; }
.tp-image { width: 100%; height: auto; display: block; }
.tp-overlay { position: absolute; inset: 0; width: 100%; height: 100%; pointer-events: none; }
.tp-legend {
  position: absolute; top: 10px; left: 10px;
  display: flex; flex-direction: column; gap: 4px;
  background: rgba(0,0,0,0.55); backdrop-filter: blur(4px);
  border-radius: 8px; padding: 6px 10px;
}
.tp-legend-item { display: flex; align-items: center; gap: 6px; font-size: 11px; font-weight: 700; color: #fff; }
.tp-legend-dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }

.tp-note-text {
  font-size: 2.6px; font-weight: 700; fill: #ffd23f; font-family: inherit;
  paint-order: stroke; stroke: #14140f; stroke-width: 0.5px;
}
.tp-bomb-label { font-size: 1.6px; font-weight: 800; fill: #fff; font-family: inherit; }

.tp-controls {
  display: flex; align-items: center; gap: 12px;
  background: var(--bg-elevated); padding: 12px 16px;
}
.tp-play-btn {
  width: 34px; height: 34px; border-radius: 50%; flex-shrink: 0;
  display: flex; align-items: center; justify-content: center;
  background: var(--accent); color: #14140f; border: none; cursor: pointer;
  transition: transform .1s;
}
.tp-play-btn:active { transform: scale(0.92); }

.tp-scrubber {
  flex: 1; min-width: 60px;
  -webkit-appearance: none; appearance: none;
  height: 4px; border-radius: 99px; background: var(--line); outline: none;
  accent-color: var(--accent);
}
.tp-scrubber::-webkit-slider-thumb {
  -webkit-appearance: none; width: 13px; height: 13px; border-radius: 50%;
  background: var(--accent); cursor: pointer;
}

.tp-time { font-size: 11.5px; color: var(--text-dim); flex-shrink: 0; white-space: nowrap; }

.tp-speed-group { display: flex; gap: 3px; flex-shrink: 0; }
.tp-speed-btn {
  padding: 5px 9px; border-radius: 7px; background: var(--bg); border: 1px solid var(--line);
  color: var(--text-dim); font-size: 11px; font-weight: 700; cursor: pointer; transition: all .15s;
}
.tp-speed-btn.active { background: rgba(255,154,0,.14); border-color: var(--accent); color: var(--accent); }

.tp-export-btn {
  display: flex; align-items: center; gap: 5px; flex-shrink: 0;
  padding: 6px 11px; border-radius: 7px; background: var(--bg); border: 1px solid var(--line);
  color: var(--text-dim); font-size: 11px; font-weight: 700; cursor: pointer; transition: all .15s;
}
.tp-export-btn:hover:not(:disabled) { border-color: var(--accent); color: var(--accent); }
.tp-export-btn:disabled { opacity: .6; cursor: wait; }
.tp-export-error {
  font-size: 11.5px; color: var(--danger); font-weight: 600;
  background: var(--bg-elevated); padding: 8px 16px; margin: 0;
}

@media (max-width: 460px) {
  .tp-controls { flex-wrap: wrap; }
  .tp-scrubber { order: 3; flex-basis: 100%; }
}
.tp-scrub-wrap { position: relative; flex: 1; min-width: 80px; display: flex; align-items: center; }
.tp-scrub-wrap .tp-scrubber { flex: 1; }
.tp-marks { position: absolute; left: 0; right: 0; bottom: -1px; height: 6px; pointer-events: none; }
.tp-mark {
  position: absolute; top: 0; width: 2px; height: 6px; border-radius: 1px;
  transform: translateX(-1px);
}

</style>
