/**
 * Descriptions from imports and metadata sources may contain simple HTML (lists, bold).
 * We rebuild it from scratch: only the tags below, never any attribute, text always
 * as text. Everything else is unwrapped (its text stays) or, for script-like tags, dropped.
 */

const ALLOWED = new Set([
  'b',
  'strong',
  'i',
  'em',
  'u',
  's',
  'br',
  'p',
  'ul',
  'ol',
  'li',
  'h3',
  'h4',
  'blockquote',
])
const DROPPED = new Set(['script', 'style', 'template', 'iframe', 'object', 'embed', 'noscript'])
const BLOCK = /\s*(<\/?(?:ul|ol|li|p|h3|h4|blockquote)\b[^>]*>)\s*/gi

function copy(from: Node, to: Node, doc: Document): void {
  for (const child of Array.from(from.childNodes)) {
    if (child.nodeType === Node.TEXT_NODE) {
      to.appendChild(doc.createTextNode(child.textContent ?? ''))
    } else if (child instanceof Element) {
      const tag = child.tagName.toLowerCase()
      if (DROPPED.has(tag)) continue
      if (ALLOWED.has(tag)) {
        const clean = doc.createElement(tag)
        copy(child, clean, doc)
        to.appendChild(clean)
      } else {
        copy(child, to, doc)
      }
    }
  }
}

/** Safe HTML for `v-html`. Line breaks in plain text are kept by `whitespace-pre-line`. */
export function richText(source: string): string {
  // Newlines around block tags would show up as empty lines under pre-line.
  const html = source.replace(BLOCK, '$1')
  const parsed = new DOMParser().parseFromString(html, 'text/html')
  const out = document.implementation.createHTMLDocument('')
  const root = out.createElement('div')
  copy(parsed.body, root, out)
  return root.innerHTML.trim()
}
