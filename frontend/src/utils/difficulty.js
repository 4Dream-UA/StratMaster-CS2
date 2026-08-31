// Difficulty is stored as a 1–5 integer (strategies.difficulty_stars) and
// shown as a word, not a star row — "★★★☆☆" makes a reader count pips to
// learn something a single word says outright, and five gradations were
// never distinguishable in practice anyway.
//
// The column keeps its 1–5 range so existing rows stay valid; the admin
// editor writes the three canonical values (1 / 3 / 5) and anything in
// between from before still lands in a sensible bucket.

export const DIFFICULTY_LEVELS = [
  { value: 1, key: 'easy', label: 'Easy' },
  { value: 3, key: 'medium', label: 'Medium' },
  { value: 5, key: 'hard', label: 'Hard' },
]

export function difficultyKey(stars) {
  if (stars >= 4) return 'hard'
  if (stars >= 3) return 'medium'
  return 'easy'
}

export function difficultyLabel(stars) {
  const key = difficultyKey(stars)
  return DIFFICULTY_LEVELS.find(l => l.key === key).label
}

// Snaps a stored 1–5 value onto the nearest of the three canonical ones, so
// a legacy 2 or 4 still selects an option in the admin dropdown instead of
// leaving it blank.
export function snapDifficulty(stars) {
  const key = difficultyKey(stars)
  return DIFFICULTY_LEVELS.find(l => l.key === key).value
}
