// A small, deliberately limited markdown renderer for forum posts.
// Safety model: escape all HTML first, THEN run markdown transforms that
// only ever emit tags we constructed ourselves — user input never becomes
// raw HTML. Links/images are further restricted to http(s) or our own
// /uploads/ path, so a javascript: URL (or anything else) just renders as
// plain (already-escaped) text instead of becoming a clickable element.

const ESCAPE_MAP = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }
function escapeHtml(str) {
  return str.replace(/[&<>"']/g, (c) => ESCAPE_MAP[c])
}

function isSafeUrl(url) {
  return /^(https?:\/\/|\/uploads\/)/i.test(url)
}

export function renderMarkdown(raw) {
  if (!raw) return ''
  let html = escapeHtml(raw)

  // Images: ![alt](url) — must come before the link pattern (same shape, leading `!`).
  html = html.replace(/!\[([^\]]*)\]\(([^)\s]+)\)/g, (match, alt, url) =>
    isSafeUrl(url) ? `<img src="${url}" alt="${alt}" class="md-img" loading="lazy">` : match
  )
  // Links: [text](url)
  html = html.replace(/\[([^\]]+)\]\(([^)\s]+)\)/g, (match, text, url) =>
    isSafeUrl(url) ? `<a href="${url}" target="_blank" rel="noopener noreferrer">${text}</a>` : match
  )
  // Bold, then italic (bold first so `**x**` doesn't get eaten by the italic pass first)
  html = html.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
  html = html.replace(/\*([^*]+)\*/g, '<em>$1</em>')
  // Inline code
  html = html.replace(/`([^`]+)`/g, '<code>$1</code>')

  return html
}
