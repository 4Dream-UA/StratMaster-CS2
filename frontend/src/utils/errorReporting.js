// Best-effort client-side error reporting to POST /api/errors — closes the
// "a production failure is invisible unless a player happens to report it"
// gap without needing an external service. Deliberately minimal: no retry
// queue, no batching, and a simple per-message cooldown so a tight error
// loop (e.g. a render error firing every frame) can't hammer the endpoint
// or drown out everything else in the admin view.

const recentlySent = new Map() // message -> timestamp
const COOLDOWN_MS = 30_000

function shouldSend(message) {
  const last = recentlySent.get(message)
  const now = Date.now()
  if (last && now - last < COOLDOWN_MS) return false
  recentlySent.set(message, now)
  return true
}

export function reportError(message, stack) {
  const text = String(message || 'Unknown error').slice(0, 2000)
  if (!shouldSend(text)) return

  const initData = window.Telegram?.WebApp?.initData
  const headers = { 'Content-Type': 'application/json' }
  if (initData) headers['X-Init-Data'] = initData

  fetch('/api/errors', {
    method: 'POST',
    headers,
    body: JSON.stringify({
      message: text,
      stack: stack ? String(stack).slice(0, 8000) : null,
      url: window.location.pathname,
    }),
  }).catch(() => {
    // The error-reporting call itself failing (offline, backend down) is
    // not something to report or retry — there's nowhere for that report
    // to go either.
  })
}

export function installGlobalErrorReporting(app) {
  app.config.errorHandler = (err, instance, info) => {
    reportError(`[Vue] ${err?.message || err}` + (info ? ` (${info})` : ''), err?.stack)
    // Also log to the console the way Vue's default handler would, so
    // local dev debugging isn't worse off for having this installed.
    console.error(err)
  }

  window.addEventListener('error', (event) => {
    reportError(event.message, event.error?.stack)
  })

  window.addEventListener('unhandledrejection', (event) => {
    const reason = event.reason
    reportError(
      `Unhandled promise rejection: ${reason?.message || reason}`,
      reason?.stack,
    )
  })
}
