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
