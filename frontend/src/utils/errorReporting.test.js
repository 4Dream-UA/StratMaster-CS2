import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { reportError } from './errorReporting'

describe('reportError', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn(() => Promise.resolve({ ok: true })))
    vi.useFakeTimers()
  })
  afterEach(() => {
    vi.unstubAllGlobals()
    vi.useRealTimers()
  })

  it('posts to /api/errors with the message and stack', () => {
    reportError('boom', 'at foo.js:1')
    expect(fetch).toHaveBeenCalledTimes(1)
    const [url, opts] = fetch.mock.calls[0]
    expect(url).toBe('/api/errors')
    const body = JSON.parse(opts.body)
    expect(body.message).toBe('boom')
    expect(body.stack).toBe('at foo.js:1')
  })

  it('suppresses a repeat of the same message within the cooldown window', () => {
    reportError('same error', 'stack')
    reportError('same error', 'stack')
    reportError('same error', 'stack')
    expect(fetch).toHaveBeenCalledTimes(1)
  })

  it('does not suppress a different message', () => {
    reportError('error A')
    reportError('error B')
    expect(fetch).toHaveBeenCalledTimes(2)
  })

  it('sends the same message again once the cooldown has passed', () => {
    reportError('flaky error')
    expect(fetch).toHaveBeenCalledTimes(1)

    vi.advanceTimersByTime(31_000)
    reportError('flaky error')
    expect(fetch).toHaveBeenCalledTimes(2)
  })
})
