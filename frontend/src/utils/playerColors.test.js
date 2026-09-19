import { describe, expect, it } from 'vitest'
import { badgeTextColor, distinctPlayerColors, playerBadge, PLAYER_PALETTE } from './playerColors'

describe('distinctPlayerColors', () => {
  it('keeps colours that are already distinct', () => {
    expect(distinctPlayerColors(['#111111', '#222222'])).toEqual(['#111111', '#222222'])
  })

  it('gives repeats an unused palette colour', () => {
    const out = distinctPlayerColors(['#ff9a00', '#ff9a00', '#FF9A00'])
    expect(out[0]).toBe('#ff9a00')
    expect(new Set(out.map(c => c.toLowerCase())).size).toBe(3)
    expect(out.slice(1).every(c => PLAYER_PALETTE.includes(c))).toBe(true)
  })

  it('fills in missing colours', () => {
    expect(distinctPlayerColors([null, ''])).toHaveLength(2)
    expect(distinctPlayerColors([null, ''])[0]).toBeTruthy()
  })
})

describe('playerBadge', () => {
  it('uses the number in the label', () => {
    expect(playerBadge('Player 3', 0)).toBe('3')
  })
  it('falls back to the initial, then the position', () => {
    expect(playerBadge('entry', 0)).toBe('E')
    expect(playerBadge('', 4)).toBe('5')
  })
})

describe('badgeTextColor', () => {
  it('is dark on light fills and white on dark ones', () => {
    expect(badgeTextColor('#ffd23f')).toBe('#101114')
    expect(badgeTextColor('#2a1a6e')).toBe('#ffffff')
  })
})
