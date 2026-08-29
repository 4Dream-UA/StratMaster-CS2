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
// the two never drift apart — same color, same effect-zone size, whichever
// screen you're looking at.
export const GRENADE_COLORS = {
  Smoke: '#c7c9cf', Flashbang: '#ffe98a', Molotov: '#ff6b3d', HE: '#ff9a00', Decoy: '#7fa8ff',
}
export function grenadeColor(type) {
  return GRENADE_COLORS[type] || '#ff9a00'
}

// Effect-zone radius at the landing point, as a percent of the image —
// smoke/molotov cover real ground, flash/HE/decoy are tighter.
export const GRENADE_EFFECT_RADIUS = {
  Smoke: 9, Molotov: 7, HE: 4.5, Flashbang: 4, Decoy: 3,
}
export function grenadeEffectRadius(type) {
  return GRENADE_EFFECT_RADIUS[type] || 4
}
