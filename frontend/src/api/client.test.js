import { describe, expect, it } from 'vitest'
import { normalizeErrorDetail } from './client'

describe('normalizeErrorDetail', () => {
  it('leaves a plain string detail untouched', () => {
    expect(normalizeErrorDetail('Not enough MasterCoins')).toBe('Not enough MasterCoins')
  })

  it('leaves undefined/null untouched', () => {
    expect(normalizeErrorDetail(undefined)).toBeUndefined()
    expect(normalizeErrorDetail(null)).toBeNull()
  })

  it('joins a FastAPI validation-error array into one readable string', () => {
    const detail = [
      { loc: ['body', 'amount'], msg: 'Input should be greater than 0', type: 'greater_than' },
      { loc: ['body', 'quantity'], msg: 'field required', type: 'missing' },
    ]
    expect(normalizeErrorDetail(detail)).toBe('Input should be greater than 0; field required')
  })

  it('falls back to a generic message for an empty array', () => {
    expect(normalizeErrorDetail([])).toBe('Invalid request.')
  })

  it('falls back to String(item) when an array entry has no msg', () => {
    expect(normalizeErrorDetail(['oops'])).toBe('oops')
  })

  it('unwraps a single object detail to its msg', () => {
    expect(normalizeErrorDetail({ msg: 'Something went wrong', type: 'value_error' })).toBe('Something went wrong')
  })

  it('falls back to a generic message for an object with no msg', () => {
    expect(normalizeErrorDetail({ type: 'value_error' })).toBe('Invalid request.')
  })
})
