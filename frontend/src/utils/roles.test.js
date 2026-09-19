import { describe, expect, it } from 'vitest'
import { parseRoles } from './roles'

describe('parseRoles', () => {
  it('splits a one-line roles text into players', () => {
    expect(parseRoles('Player 1: goes Palace Player 2 & 3 & 4 : go Ramp Player 5: smokes A')).toEqual([
      { who: 'Player 1', what: 'goes Palace' },
      { who: 'Player 2 & 3 & 4', what: 'go Ramp' },
      { who: 'Player 5', what: 'smokes A' },
    ])
  })

  it('reads one role per line, times in the text included', () => {
    expect(parseRoles('Entry: flash in\nSupport: smoke at 1:40')).toEqual([
      { who: 'Entry', what: 'flash in' },
      { who: 'Support', what: 'smoke at 1:40' },
    ])
  })

  it('leaves prose alone', () => {
    expect(parseRoles('Everyone rushes B together.')).toEqual([])
    expect(parseRoles('')).toEqual([])
  })
})
