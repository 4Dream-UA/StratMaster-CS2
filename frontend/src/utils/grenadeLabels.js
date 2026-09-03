// "HE" is a bare CS2 jargon abbreviation (High Explosive / frag grenade) —
// every other grenade type reads as a plain word, so this is the one spot
// that actually needs spelling out for anyone not already fluent in CS2
// terminology. The stored value stays "HE" (matches GrenadeTypeEnum); only
// the label shown to people changes.
export const GRENADE_TYPE_LABELS = {
  Smoke: 'Smoke',
  Flashbang: 'Flashbang',
  Molotov: 'Molotov',
  HE: 'HE Grenade',
  Decoy: 'Decoy',
}

export function grenadeTypeLabel(type) {
  return GRENADE_TYPE_LABELS[type] || type
}

// Shared between TacticsEditor (placing) and TacticsPlayer (replaying) so
// the two never drift apart — same color whichever screen you're looking at.
export const GRENADE_COLORS = {
  Smoke: '#c7c9cf', Flashbang: '#ffe98a', Molotov: '#ff6b3d', HE: '#ff9a00', Decoy: '#7fa8ff',
}
export function grenadeColor(type) {
  return GRENADE_COLORS[type] || '#ff9a00'
}

// Number inputs hand back '' when emptied, and clearing a trajectory leaves
// an empty array — the API wants null for "not set" and rejects a
// trajectory shorter than two points outright. Both editors run their
// grenades through this before saving so an emptied field is a no-op
// instead of a 422.
function orNull(v) {
  return v === '' || v === undefined || Number.isNaN(v) ? null : v
}

export function normalizeGrenades(grenades) {
  return grenades.map(g => ({
    ...g,
    throw_at: orNull(g.throw_at),
    lands_at: orNull(g.lands_at),
    effect_radius: orNull(g.effect_radius),
    trajectory: Array.isArray(g.trajectory) && g.trajectory.length >= 2
      ? g.trajectory.map(pt => ({ x: pt.x, y: pt.y }))
      : null,
  }))
}
