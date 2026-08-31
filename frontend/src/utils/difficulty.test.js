import { describe, expect, it } from 'vitest'
import { DIFFICULTY_LEVELS, difficultyKey, difficultyLabel, snapDifficulty } from './difficulty'

describe('difficulty', () => {
  it('maps the three canonical values to their own level', () => {
    expect(difficultyLabel(1)).toBe('Easy')
    expect(difficultyLabel(3)).toBe('Medium')
    expect(difficultyLabel(5)).toBe('Hard')
  })

  it('buckets the in-between legacy values sensibly', () => {
    expect(difficultyKey(2)).toBe('easy')
    expect(difficultyKey(4)).toBe('hard')
  })

  it('snaps any stored value onto a value the admin dropdown offers', () => {
    const offered = DIFFICULTY_LEVELS.map(l => l.value)
    for (const stars of [1, 2, 3, 4, 5]) {
      expect(offered).toContain(snapDifficulty(stars))
    }
    expect(snapDifficulty(2)).toBe(1)
    expect(snapDifficulty(4)).toBe(5)
  })

  it('never returns undefined for out-of-range input', () => {
    expect(difficultyLabel(0)).toBe('Easy')
    expect(difficultyLabel(99)).toBe('Hard')
  })
})
