<template>
  <div class="tactics-player">
    <div class="tp-canvas">
      <img :src="imageUrl" alt="Strategy map" class="tp-image" />
      <svg class="tp-overlay" viewBox="0 0 100 100" preserveAspectRatio="none">
        <!-- landed grenade markers (persist once thrown) -->
        <g v-for="(g, i) in trajectoryGrenades" :key="'land'+i">
          <g v-if="grenadeState(g, currentTime) === 'landed'" :transform="`translate(${g.to_x},${g.to_y})`" class="tp-landed">
            <circle r="2.4" :fill="grenadeColor(g.grenade_type)" fill-opacity="0.18" :stroke="grenadeColor(g.grenade_type)" stroke-width="0.4" />
            <circle r="0.6" :fill="grenadeColor(g.grenade_type)" />
          </g>
        </g>

        <!-- player paths already walked (trail) -->
        <polyline
          v-for="p in playerPaths" :key="'trail'+p.label"
          :points="trailPoints(p, currentTime)"
          fill="none" :stroke="p.color" stroke-width="0.5" stroke-opacity="0.55"
        />

        <!-- flying grenades -->
        <g v-for="(g, i) in trajectoryGrenades" :key="'fly'+i">
          <circle
            v-if="grenadeState(g, currentTime) === 'flying'"
            :cx="grenadeFlightPos(g, currentTime).x" :cy="grenadeFlightPos(g, currentTime).y"
            r="1.1" :fill="grenadeColor(g.grenade_type)"
          />
        </g>

        <!-- player dots -->
        <g v-for="p in playerPaths" :key="'dot'+p.label" :transform="`translate(${positionAt(p.waypoints, currentTime).x},${positionAt(p.waypoints, currentTime).y})`">
          <circle r="1.8" :fill="p.color" stroke="#111213" stroke-width="0.3" />
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

      <input
        type="range" class="tp-scrubber" min="0" :max="totalDuration" step="0.05"
        :value="currentTime" @input="onScrub"
      />

      <span class="tp-time mono">{{ formatTime(currentTime) }} / {{ formatTime(totalDuration) }}</span>

      <div class="tp-speed-group">
        <button
          v-for="s in [1, 2, 5]" :key="s" type="button"
          class="tp-speed-btn" :class="{ active: speed === s }"
          @click="speed = s"
        >{{ s }}×</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onUnmounted } from 'vue'

const props = defineProps({
  imageUrl: { type: String, required: true },
  grenades: { type: Array, default: () => [] },
  playerPaths: { type: Array, default: () => [] },
})

const FLIGHT_DURATION = 1.2
const TAIL_BUFFER = 2

const GRENADE_COLORS = {
  Smoke: '#c7c9cf', Flashbang: '#ffe98a', Molotov: '#ff6b3d', HE: '#ff9a00', Decoy: '#7fa8ff',
}
function grenadeColor(type) {
  return GRENADE_COLORS[type] || '#ff9a00'
}

const trajectoryGrenades = computed(() =>
  props.grenades.filter(g => g.from_x != null && g.from_y != null && g.to_x != null && g.to_y != null)
)

function parseTiming(t) {
  if (!t) return 0
  const m = String(t).match(/^(\d+):(\d{1,2})$/)
  if (m) return parseInt(m[1], 10) * 60 + parseInt(m[2], 10)
  const n = parseFloat(t)
  return Number.isNaN(n) ? 0 : n
}

const totalDuration = computed(() => {
  let max = 0
  for (const p of props.playerPaths) {
    for (const w of p.waypoints) max = Math.max(max, w.t)
  }
  for (const g of trajectoryGrenades.value) {
    max = Math.max(max, parseTiming(g.timing) + FLIGHT_DURATION)
  }
  return Math.max(5, max + TAIL_BUFFER)
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
  const start = parseTiming(g.timing)
  if (t < start) return 'hidden'
  if (t < start + FLIGHT_DURATION) return 'flying'
  return 'landed'
}

function grenadeFlightPos(g, t) {
  const start = parseTiming(g.timing)
  const frac = Math.min(1, Math.max(0, (t - start) / FLIGHT_DURATION))
  const mx = (g.from_x + g.to_x) / 2
  const my = (g.from_y + g.to_y) / 2 - 14
  const x = (1 - frac) ** 2 * g.from_x + 2 * (1 - frac) * frac * mx + frac ** 2 * g.to_x
  const y = (1 - frac) ** 2 * g.from_y + 2 * (1 - frac) * frac * my + frac ** 2 * g.to_y
  return { x, y }
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

function tick(ts) {
  if (lastTs == null) lastTs = ts
  const dt = (ts - lastTs) / 1000
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
.tp-landed { animation: tp-pop .25s ease; }
@keyframes tp-pop { from { transform-origin: center; } }

.tp-legend {
  position: absolute; top: 10px; left: 10px;
  display: flex; flex-direction: column; gap: 4px;
  background: rgba(0,0,0,0.55); backdrop-filter: blur(4px);
  border-radius: 8px; padding: 6px 10px;
}
.tp-legend-item { display: flex; align-items: center; gap: 6px; font-size: 11px; font-weight: 700; color: #fff; }
.tp-legend-dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }

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

@media (max-width: 460px) {
  .tp-controls { flex-wrap: wrap; }
  .tp-scrubber { order: 3; flex-basis: 100%; }
}
</style>
