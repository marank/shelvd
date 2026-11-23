import { beforeEach, describe, expect, it, vi } from 'vitest'
import { nextTick } from 'vue'
import { useUiStore } from '@/stores/ui'
import { mockApi, renderComponent, settle } from '@/test/utils'
import AddItemDialog from '../components/AddItemDialog.vue'
import {
  $,
  $$,
  baseRoutes,
  candidate,
  click,
  item,
  LIB,
  lookup,
  ps5,
  release,
  submit,
  type,
} from './fixtures'

/** A phone: narrow and touch. */
function phone() {
  vi.stubGlobal('matchMedia', (query: string) => ({
    matches: query.includes('max-width') || query.includes('coarse'),
    media: query,
    addEventListener: () => {},
    removeEventListener: () => {},
  }))
}

async function open(autoAdd = true) {
  const ctx = await renderComponent(AddItemDialog, { url: '/', locale: 'en' })
  const ui = useUiStore()
  ui.scanAutoAdd = autoAdd
  ui.openAdd(LIB, 'scan')
  await settle()
  await vi.waitFor(() => expect($$('[data-testid="mobile-scan"]')).toHaveLength(1))
  return ctx
}

async function scan(code: string) {
  if (!$$('[data-testid="mobile-code"]').length) {
    click('[data-testid="open-code"]')
    await nextTick()
  }
  type('[data-testid="mobile-code"]', code)
  // Input passes its value on through a watcher: one tick later.
  await nextTick()
  submit('[data-testid="code-form"]')
  await settle()
}

const states = () => $$('[data-testid="queue-entry"]').map((e) => e.dataset.state)

beforeEach(phone)

describe('Scanning on a phone', () => {
  it('adds a known code right away with the round details, and undoes it', async () => {
    const known = release()
    const calls = mockApi({
      ...baseRoutes(),
      'GET /api/lookup/barcode/:code': lookup({ known: [known] }),
      'POST /api/libraries/:id/items': { status: 201, body: item(known, 'i-7') },
      'DELETE /api/libraries/:id/items/:item': { status: 204 },
    })
    await open()
    click('[data-testid="round-defaults"]')
    await settle()
    type('#item-location', 'loc-1')
    click('[data-testid="defaults-done"]')
    await settle()
    expect($('[data-testid="round-defaults"]').textContent).toContain('Living room / Shelf')

    await scan('0045496420055')
    expect(states()).toEqual(['added'])
    expect($('[data-testid="round-count"]').textContent).toContain('1 of 1')
    const created = calls.find((c) => c.method === 'POST' && c.path.endsWith('/items'))
    expect(created?.body).toMatchObject({ release_id: known.id, location_id: 'loc-1' })
    expect($$('[data-testid="scan-sheet"]')).toHaveLength(0)

    // The same code still in front of the camera is not added again …
    await scan('0045496420055')
    expect(states()).toEqual(['added'])

    // … and the entry can be undone.
    click('[data-testid="queue-entry"]')
    await settle()
    click('[data-testid="sheet-undo"]')
    await settle()
    expect(calls.some((c) => c.method === 'DELETE' && c.path.endsWith('/items/i-7'))).toBe(true)
    expect(states()).toEqual([])
  })

  it('asks first without auto-add, and adds another copy on request', async () => {
    const known = release()
    const calls = mockApi({
      ...baseRoutes(),
      'GET /api/lookup/barcode/:code': lookup({ known: [known] }),
      'POST /api/libraries/:id/items': { status: 201, body: item(known) },
    })
    await open(false)
    await scan('0045496420055')
    expect(states()).toEqual(['review'])
    expect($('[data-testid="scan-sheet"]').textContent).toContain(known.title)
    click('[data-testid="sheet-add"]')
    await settle()
    expect(states()).toEqual(['added'])

    click('[data-testid="queue-entry"]')
    await settle()
    click('[data-testid="sheet-again"]')
    await settle()
    expect(states()).toEqual(['added', 'added'])
    expect(calls.filter((c) => c.method === 'POST' && c.path.endsWith('/items'))).toHaveLength(2)
  })

  it('asks before adding a game the library has already', async () => {
    const known = release()
    const calls = mockApi({
      ...baseRoutes(),
      'GET /api/lookup/barcode/:code': lookup({ known: [known] }),
      'GET /api/libraries/:id/owned': [{ release_id: known.id, work_id: known.work_id, copies: 1 }],
      'POST /api/libraries/:id/items': { status: 201, body: item(known) },
    })
    await open()
    await scan('0045496420055')
    expect(states()).toEqual(['review'])
    expect($('[data-testid="sheet-duplicate"]').textContent).toContain('another copy?')
    expect($('[data-testid="scan-sheet"] [data-testid="owned-hint"]').textContent).toContain('1×')
    expect($('[data-testid="sheet-add"]').textContent).toContain('Another copy')
    expect(calls.some((c) => c.method === 'POST')).toBe(false)
    click('[data-testid="sheet-add"]')
    await settle()
    expect(states()).toEqual(['added'])
  })

  it('asks when a code added this round comes back later', async () => {
    const known = release()
    mockApi({
      ...baseRoutes(),
      'GET /api/lookup/barcode/:code': lookup({ known: [known] }),
      'POST /api/libraries/:id/items': { status: 201, body: item(known) },
    })
    await open()
    await scan('0045496420055')
    expect(states()).toEqual(['added'])
    const now = Date.now()
    vi.spyOn(Date, 'now').mockReturnValue(now + 5000)
    await scan('0045496420055')
    expect(states()).toEqual(['review', 'added'])
    expect($$('[data-testid="sheet-duplicate"]')).toHaveLength(1)
    vi.restoreAllMocks()
  })

  it('imports a candidate with the code, asking for the platform when the source has none', async () => {
    const imported = release({ id: 'r-new', title: 'Zelda' })
    const calls = mockApi({
      ...baseRoutes(),
      'GET /api/lookup/barcode/:code': lookup({}),
      'GET /api/catalog/releases': [],
      'GET /api/lookup/search': {
        query: 'zelda',
        platform_id: null,
        candidates: [candidate({ title: 'Zelda', platform_id: null, region: 'jp' })],
        errors: [],
      },
      'POST /api/lookup/import': { status: 201, body: imported },
      'POST /api/libraries/:id/items': { status: 201, body: item(imported) },
    })
    await open()
    await scan('4902370536485')
    expect(states()).toEqual(['unknown'])
    click('[data-testid="sheet-search"]')
    await settle()
    type('[data-testid="search-input"]', 'zelda')
    await vi.waitFor(() => expect($$('[data-testid="candidate-row"]')).toHaveLength(1))
    click('[data-testid="candidate-row"]')
    await settle()
    expect(states()).toEqual(['review'])
    expect(($('[data-testid="sheet-add"]') as HTMLButtonElement).disabled).toBe(true)
    type('#sheet-platform', ps5.id)
    await nextTick()
    click('[data-testid="sheet-add"]')
    await settle()
    expect(calls.find((c) => c.path === '/api/lookup/import')?.body).toMatchObject({
      platform_id: ps5.id,
      region: 'jp',
      barcode: '4902370536485',
    })
    expect(states()).toEqual(['added'])
  })

  it('puts a game that is not out yet on Upcoming', async () => {
    const coming = release({ is_released: false })
    const calls = mockApi({
      ...baseRoutes(),
      'GET /api/lookup/barcode/:code': lookup({ known: [coming] }),
      'POST /api/watchlist': { status: 201, body: { id: 't-1', release: coming } },
      'DELETE /api/watchlist/:id': { status: 204 },
    })
    await open()
    await scan('0045496420055')
    // Auto-add only goes into the library; this one asks.
    expect($('[data-testid="sheet-add"]').textContent).toContain('Upcoming')
    click('[data-testid="sheet-add"]')
    await settle()
    expect(calls.find((c) => c.path === '/api/watchlist')?.body).toMatchObject({
      release_id: coming.id,
      library_id: LIB,
    })
    expect(states()).toEqual(['tracked'])
    click('[data-testid="queue-entry"]')
    await settle()
    click('[data-testid="sheet-undo"]')
    await settle()
    expect(calls.some((c) => c.method === 'DELETE' && c.path === '/api/watchlist/t-1')).toBe(true)
  })

  it('asks to search or drop a code nothing was found for', async () => {
    const inCatalog = release({ id: 'r-cat', title: 'Disney Classic Games', barcodes: [] })
    const calls = mockApi({
      ...baseRoutes(false),
      'GET /api/lookup/barcode/:code': (_c: unknown, p: Record<string, string>) =>
        lookup({ code: p.code }),
      'GET /api/catalog/releases': [inCatalog],
      'POST /api/catalog/releases/:id/barcodes': { ...inCatalog, barcodes: ['3391892020175'] },
      'POST /api/libraries/:id/items': { status: 201, body: item(inCatalog) },
    })
    await open()
    await scan('2000000123455')
    expect($('[data-testid="sheet-unknown"]')).toBeTruthy()
    click('[data-testid="sheet-discard"]')
    await settle()
    expect(states()).toEqual([])

    await scan('3391892020175')
    click('[data-testid="sheet-later"]')
    await settle()
    expect(states()).toEqual(['unknown'])
    click('[data-testid="queue-entry"]')
    await settle()
    click('[data-testid="sheet-search"]')
    await settle()
    expect($('[data-testid="mobile-search"]').textContent).toContain('3391892020175')
    expect(($('[data-testid="search-input"]') as HTMLInputElement).value).toBe('')
    type('[data-testid="search-input"]', 'Disney Classic')
    await vi.waitFor(() => expect($$('[data-testid="release-row"]')).toHaveLength(1))
    click('[data-testid="release-row"]')
    await settle()
    // Back at the scanner with the picked game; one tap adds it and keeps the code.
    expect($('[data-testid="scan-sheet"]').textContent).toContain('Disney Classic Games')
    click('[data-testid="sheet-add"]')
    await settle()
    expect(calls.find((c) => c.path === '/api/catalog/releases/r-cat/barcodes')?.body).toEqual({
      code: '3391892020175',
    })
    expect(states()).toEqual(['added'])
  })

  it('retries a failed lookup and shows add errors in the sheet', async () => {
    let fail = true
    mockApi({
      ...baseRoutes(),
      'GET /api/lookup/barcode/:code': () =>
        fail ? { status: 502, body: { detail: 'Source down' } } : lookup({ known: [release()] }),
      'POST /api/libraries/:id/items': { status: 400, body: { detail: 'Library is full' } },
    })
    await open()
    await scan('0045496420055')
    expect(states()).toEqual(['failed'])
    expect($('[data-testid="scan-sheet"]').textContent).toContain('Source down')
    fail = false
    click('[data-testid="sheet-retry"]')
    await settle()
    // Auto-add failed: the choice stays open with the reason.
    expect(states()).toEqual(['review'])
    expect($('[data-testid="sheet-error"]').textContent).toContain('Library is full')
  })

  it('opens the full form for one copy and returns to the scanner', async () => {
    const known = release()
    const calls = mockApi({
      ...baseRoutes(),
      'GET /api/lookup/barcode/:code': lookup({ known: [known] }),
      'POST /api/libraries/:id/items': (call: { body: unknown }) => ({
        status: 201,
        body: { ...item(known, 'i-3'), ...(call.body as object) },
      }),
    })
    await open(false)
    await scan('0045496420055')
    click('[data-testid="sheet-details"]')
    await settle()
    type('#item-price', '19,99')
    await nextTick()
    submit('[data-testid="item-form"]')
    await settle()
    expect(calls.find((c) => c.path.endsWith('/items'))?.body).toMatchObject({
      purchase_price: '19.99',
    })
    expect(states()).toEqual(['added'])
    expect($$('[data-testid="item-form"]')).toHaveLength(0)
  })

  it('searches without a code, enters a game by hand and switches auto-add off', async () => {
    mockApi({
      ...baseRoutes(false),
      'GET /api/catalog/releases': [],
    })
    await open()
    click('[data-testid="round-defaults"]')
    await settle()
    click('[data-testid="auto-add"]')
    await settle()
    expect(useUiStore().scanAutoAdd).toBe(false)
    click('[data-testid="defaults-done"]')
    await settle()

    click('[data-testid="open-search"]')
    await settle()
    expect($$('[data-testid="search-barcode"]')).toHaveLength(0)
    click('[data-testid="search-back"]')
    await settle()
    click('[data-testid="open-search"]')
    await settle()
    type('[data-testid="search-input"]', 'halo')
    await vi.waitFor(() =>
      expect($$('[data-testid="mobile-search"] button').length).toBeGreaterThan(1),
    )
    const manual = $$('[data-testid="mobile-search"] button').find((b) =>
      b.textContent.includes('Enter it manually'),
    )!
    click(manual)
    await vi.waitFor(() => expect(useUiStore().addOpen).toBe(false))
  })

  it('shows problems in the sheet instead of a message', async () => {
    const inCatalog = release({ id: 'r-cat', title: 'Halo', barcodes: [] })
    mockApi({
      ...baseRoutes(false),
      'GET /api/lookup/barcode/:code': lookup({ code: '3391892020175' }),
      'GET /api/catalog/releases': [inCatalog],
      'POST /api/catalog/releases/:id/barcodes': {
        status: 409,
        body: { detail: 'This barcode already belongs to another release.' },
      },
      'POST /api/libraries/:id/items': { status: 201, body: item(inCatalog, 'i-5') },
      'DELETE /api/libraries/:id/items/:item': { status: 500, body: { detail: 'Server down' } },
    })
    await open()
    await scan('3391892020175')
    click('[data-testid="sheet-search"]')
    await settle()
    type('[data-testid="search-input"]', 'halo')
    await vi.waitFor(() => expect($$('[data-testid="release-row"]')).toHaveLength(1))
    click('[data-testid="release-row"]')
    await settle()
    click('[data-testid="sheet-add"]')
    await settle()
    // Added, but the sheet stays open and says why the code isn't remembered.
    expect(states()).toEqual(['added'])
    expect($('[data-testid="sheet-error"]').textContent).toContain('another release')
    expect($$('[data-sonner-toast]')).toHaveLength(0)

    click('[data-testid="sheet-undo"]')
    await settle()
    expect(states()).toEqual(['added'])
    expect($('[data-testid="sheet-error"]').textContent).toContain('Server down')
  })
})
