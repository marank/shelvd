/**
 * Bundle budgets, brotli-compressed like a browser would receive them:
 *   initial JS – what the first start loads: index.html's entry script plus its
 *                modulepreloads (the shell, router, sidebar …). Keeps startup fast.
 *   total JS   – every chunk, also those loaded later (pages, dialogs, the scanner).
 *   CSS        – all stylesheets.
 * Limits live in package.json under "sizeBudget" (kB). Run after `pnpm build-only`.
 */
import { readFileSync, readdirSync } from 'node:fs'
import { join } from 'node:path'
import { brotliCompressSync } from 'node:zlib'

const dist = new URL('../dist/', import.meta.url).pathname
const budget = JSON.parse(readFileSync(new URL('../package.json', import.meta.url))).sizeBudget

const size = (file) => brotliCompressSync(readFileSync(join(dist, file))).length / 1000
const sum = (files) => files.reduce((total, file) => total + size(file), 0)

const html = readFileSync(join(dist, 'index.html'), 'utf8')
const initial = [...html.matchAll(/<(?:script[^>]*src|link rel="modulepreload"[^>]*href)="\/([^"]+\.js)"/g)]
  .map((m) => m[1])
const assets = readdirSync(join(dist, 'assets'))
const all = (ext) => assets.filter((f) => f.endsWith(ext)).map((f) => `assets/${f}`)

const rows = [
  ['initial JS', sum(initial), budget.initialJs, `${initial.length} files`],
  ['total JS', sum(all('.js')), budget.totalJs, `${all('.js').length} files`],
  ['CSS', sum(all('.css')), budget.css, `${all('.css').length} files`],
]
let failed = false
for (const [name, kb, limit, files] of rows) {
  const ok = kb <= limit
  failed ||= !ok
  console.log(`${ok ? 'ok  ' : 'OVER'} ${name.padEnd(11)} ${kb.toFixed(1).padStart(6)} / ${limit} kB  (${files})`)
}
if (failed) {
  console.error('Bundle budget exceeded: shrink it, load it later, or raise the budget deliberately.')
  process.exit(1)
}
