export const BOT_USERNAME = 'StratMasterCS2_bot'

// Every "share" link in the app must go through the bot, never straight to
// the site — Telegram only lets a Mini App open via a t.me link (this one
// triggers /start <payload>, which the bot answers with a page-specific
// "Open" button; see backend/app/bot/handlers/start.py).
export function botDeepLink(payload) {
  return `https://t.me/${BOT_USERNAME}?start=${payload}`
}
