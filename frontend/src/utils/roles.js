// Turns a strategy's free-text roles into "who: what" rows.
//
// Authors nearly always write one line per player ("Player 1: goes Palace"),
// but often on a single line, so it also splits before each "Player N",
// "P2", "T3" or "Игрок 4". Returns [] unless every piece has that shape, in
// which case the page shows the text as written.
const SPLIT = /\n+|(?=(?:^|\s)(?:player|игрок|p|t|ct)\s*\d)/i
const ROW = /^([^:]{1,40}?)\s*:\s*(.+)$/s

export function parseRoles(text) {
  const raw = (text || '').trim()
  if (!raw) return []
  const rows = raw
    .split(new RegExp(SPLIT.source, 'gi'))
    .map(line => line.trim())
    .filter(Boolean)
    .map(line => {
      const m = ROW.exec(line)
      return m ? { who: m[1].trim(), what: m[2].trim() } : null
    })
  return rows.length >= 2 && rows.every(Boolean) ? rows : []
}
