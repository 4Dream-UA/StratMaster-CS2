// Five colours that stay apart from each other and from the map art —
// roughly the in-game teammate colours, so they read the way players expect.
export const PLAYER_PALETTE = ['#4da3ff', '#3ddc84', '#ffd23f', '#ff9a00', '#c77dff']

export function defaultPlayerColor(index) {
  return PLAYER_PALETTE[index % PLAYER_PALETTE.length]
}

// Every path used to default to the same orange, so most strategies ship
// with five identical dots. Keep an author's colour the first time it
// appears and hand repeats the next unused palette colour instead.
export function distinctPlayerColors(colors) {
  const seen = new Set()
  const taken = new Set(colors.map(c => (c || '').toLowerCase()))
  const spare = PLAYER_PALETTE.filter(c => !taken.has(c))
  return colors.map((c, i) => {
    const key = (c || '').toLowerCase()
    if (key && !seen.has(key)) {
      seen.add(key)
      return c
    }
    const next = spare.shift() || defaultPlayerColor(i)
    seen.add(next)
    return next
  })
}

// Dark text on light fills, white on dark ones, so the number stays legible
// whatever colour the author picked.
export function badgeTextColor(hex) {
  const m = /^#?([0-9a-f]{6})$/i.exec(hex || '')
  if (!m) return '#101114'
  const n = parseInt(m[1], 16)
  const r = (n >> 16) & 255, g = (n >> 8) & 255, b = n & 255
  return (0.299 * r + 0.587 * g + 0.114 * b) > 140 ? '#101114' : '#ffffff'
}

// "Player 3" → "3", "Entry" → "E"; falls back to the position in the list.
export function playerBadge(label, index) {
  const digits = /\d+/.exec(label || '')
  if (digits) return digits[0].slice(0, 2)
  const first = (label || '').trim()[0]
  return first ? first.toUpperCase() : String(index + 1)
}
