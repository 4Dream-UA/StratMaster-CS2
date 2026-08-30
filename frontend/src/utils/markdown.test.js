import { describe, expect, it } from 'vitest'
import { renderMarkdown } from './markdown'

describe('renderMarkdown', () => {
  it('returns an empty string for falsy input', () => {
    expect(renderMarkdown('')).toBe('')
    expect(renderMarkdown(null)).toBe('')
    expect(renderMarkdown(undefined)).toBe('')
  })

  it('escapes raw HTML instead of letting it through', () => {
    const out = renderMarkdown('<script>alert(1)</script>')
    expect(out).not.toContain('<script>')
    expect(out).toContain('&lt;script&gt;')
  })

  it('never turns an unsafe URL into a live element, even via image/link syntax', () => {
    // isSafeUrl rejects it, so the markdown pass leaves the original text
    // untouched (inert, escaped plain text) instead of emitting a tag —
    // the substring "javascript:" surviving as plain text is fine, an
    // <img> or <a href> actually pointing at it would not be.
    const out = renderMarkdown('![x](javascript:alert(1))')
    expect(out).not.toContain('<img')
    expect(out).not.toMatch(/href=["']javascript:/)
  })

  it('renders a safe http(s) image as an <img>', () => {
    const out = renderMarkdown('![alt text](https://example.com/pic.png)')
    expect(out).toBe('<img src="https://example.com/pic.png" alt="alt text" class="md-img" loading="lazy">')
  })

  it('renders a same-origin /uploads/ image as an <img>', () => {
    const out = renderMarkdown('![x](/uploads/abc.png)')
    expect(out).toContain('<img src="/uploads/abc.png"')
  })

  it('rejects a javascript: URL for an image and leaves it as plain text', () => {
    const out = renderMarkdown('![x](javascript:alert(1))')
    expect(out).not.toContain('<img')
  })

  it('renders a safe http(s) link with target=_blank and rel=noopener', () => {
    const out = renderMarkdown('[click me](https://example.com)')
    expect(out).toBe('<a href="https://example.com" target="_blank" rel="noopener noreferrer">click me</a>')
  })

  it('rejects a javascript: URL for a link and leaves it as plain text', () => {
    const out = renderMarkdown('[click me](javascript:alert(1))')
    expect(out).not.toContain('<a ')
    expect(out).toContain('click me')
  })

  it('renders bold before italic so **x** is not eaten by the italic pass', () => {
    expect(renderMarkdown('**bold**')).toBe('<strong>bold</strong>')
    expect(renderMarkdown('*italic*')).toBe('<em>italic</em>')
    expect(renderMarkdown('**bold** and *italic*')).toBe('<strong>bold</strong> and <em>italic</em>')
  })

  it('renders inline code', () => {
    expect(renderMarkdown('`code`')).toBe('<code>code</code>')
  })

  it('renders an @mention as a highlighted span', () => {
    expect(renderMarkdown('hey @qa_admin check this')).toBe('hey <span class="md-mention">@qa_admin</span> check this')
  })

  it('does not treat a too-short handle as a mention', () => {
    // Matches the backend's own MENTION_RE (3-32 chars) so client-side
    // rendering and server-side notification matching agree on what
    // counts as a mention.
    expect(renderMarkdown('@ab')).toBe('@ab')
  })

  it('combines several transforms in one pass without cross-contamination', () => {
    const out = renderMarkdown('**@qa_admin** said `hi` — see [this](https://example.com)')
    expect(out).toBe(
      '<strong><span class="md-mention">@qa_admin</span></strong> said <code>hi</code> — see <a href="https://example.com" target="_blank" rel="noopener noreferrer">this</a>'
    )
  })
})
