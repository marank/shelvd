import { describe, expect, it, vi } from 'vitest'
import { nextTick } from 'vue'
import { toast } from 'vue-sonner'
import { keys } from '@/features/library/composables/queryKeys'
import { useUiStore, type AddMode } from '@/stores/ui'
import { mockApi, pageText, renderApp, renderComponent, settle } from '@/test/utils'
import { layoutRoutes, makeLibrary } from '@/test/fixtures'
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

async function open(mode: AddMode, locale: 'de' | 'en' = 'en') {
  const ctx = await renderComponent(AddItemDialog, { url: '/', locale })
  useUiStore().openAdd(LIB, mode)
  await settle()
  return ctx
}

async function lookUp(code: string) {
  type('[data-testid="search-input"]', code)
  await nextTick()
  submit('[data-testid="search-form"]')
  await settle()
}

describe('AddItemDialog', () => {
  it('adds a known barcode and opens the new item in the explorer', async () => {
    const known = release()
    const calls = mockApi({
      ...baseRoutes(),
      'GET /api/lookup/barcode/:code': lookup({ known: [known] }),
      'POST /api/libraries/:id/items': (call: { body: unknown }) => ({
        status: 201,
        body: { ...item(known, 'i-9'), ...(call.body as object) },
      }),
    })
    const { router, queryClient } = await open('scan')
    const invalidate = vi.spyOn(queryClient, 'invalidateQueries')
    expect(pageText()).toContain('Add game')
    // No secure context in jsdom: the camera explains itself and points to the field.
    await vi.waitFor(() => expect($('[data-testid="camera-error"]').textContent).toContain('HTTPS'))

    await lookUp(' 0045496420055 ')
    expect(calls.find((c) => c.path.startsWith('/api/lookup/barcode'))?.path).toBe(
      '/api/lookup/barcode/0045496420055',
    )
    expect(pageText()).toContain('Already known for this barcode')
    click('[data-testid="release-row"]')
    await settle()

    expect($('[data-testid="chosen-release"]').textContent).toContain('Mario Kart 8 Deluxe')
    submit('[data-testid="item-form"]')
    await settle()

    const post = calls.find((c) => c.method === 'POST')!
    expect(post.path).toBe(`/api/libraries/${LIB}/items`)
    expect(post.body).toEqual({
      release_id: 'r-1',
      format: 'physical',
      status: 'owned',
      condition: null,
      completeness: null,
      play_status: null,
      location_id: null,
      owner_id: null,
      acquired_on: null,
      purchase_price: null,
      notes: '',
      title_override: '',
    })
    await vi.waitFor(() => expect(router.currentRoute.value.name).toBe('explorer'))
    expect(router.currentRoute.value.params.libraryId).toBe(LIB)
    expect(router.currentRoute.value.query.item).toBe('i-9')
    expect(useUiStore().addOpen).toBe(false)
    const invalidated = invalidate.mock.calls.map(
      (c) => (c[0] as { queryKey?: unknown } | undefined)?.queryKey,
    )
    expect(invalidated).toEqual(
      expect.arrayContaining([keys.items(LIB), keys.tree(LIB), keys.libraries]),
    )
  })

  it('says when the scanned game is in the library already', async () => {
    const known = release()
    const other = release({ id: 'r-other', title: 'Other edition' })
    mockApi({
      ...baseRoutes(),
      'GET /api/lookup/barcode/:code': lookup({ known: [known, other] }),
      'GET /api/libraries/:id/owned': [{ release_id: known.id, work_id: known.work_id, copies: 2 }],
    })
    await open('scan')
    await lookUp('0045496420055')
    const rows = $$('[data-testid="release-row"]')
    expect(rows[0]!.querySelector('[data-testid="owned-hint"]')?.textContent).toContain(
      'Already in this library (2×)',
    )
    // Same game, another release: said differently.
    expect(rows[1]!.querySelector('[data-testid="owned-hint"]')?.textContent).toContain(
      'in another release',
    )
    click('[data-testid="release-row"]')
    await settle()
    expect($('[data-testid="chosen-release"] [data-testid="owned-hint"]')).toBeTruthy()
  })

  it('imports a candidate with platform and region, then scans the next one', async () => {
    const imported = release({ id: 'r-2', title: 'Zelda', platform: ps5, region: 'jp' })
    const calls = mockApi({
      ...baseRoutes(),
      'GET /api/lookup/barcode/:code': lookup({
        code: '4902370550733',
      }),
      'GET /api/catalog/releases': [],
      'GET /api/lookup/search': {
        query: 'zelda',
        platform_id: null,
        candidates: [candidate({ platform_id: null, platform_name: 'Arcade', region: 'jp' })],
        errors: ['wikipedia'],
      },
      'POST /api/lookup/import': { status: 201, body: imported },
      'POST /api/libraries/:id/items': { status: 201, body: item(imported) },
    })
    await open('scan')
    await lookUp('4902370550733')
    type('[data-testid="search-input"]', 'zelda')
    await vi.waitFor(() => expect($$('[data-testid="candidate-row"]')).toHaveLength(1))
    expect(pageText()).toContain('Not reachable right now: wikipedia')
    click('[data-testid="candidate-row"]')
    await settle()

    expect(pageText()).toContain('The source lists “Arcade”')
    expect(($('[data-testid="import"]') as HTMLButtonElement).disabled).toBe(true)
    expect(($('#import-region') as HTMLSelectElement).value).toBe('jp')
    type('#import-platform', ps5.id)
    type('#import-region', 'asia')
    await nextTick()
    submit('[data-testid="candidate-confirm"]')
    await settle()
    expect(calls.find((c) => c.path === '/api/lookup/import')?.body).toEqual({
      provider: 'igdb',
      external_id: '42',
      platform_id: ps5.id,
      region: 'asia',
      barcode: '4902370550733',
    })

    // Fill a few details; location and owner stay for the next game.
    click('[data-testid="more-details"]')
    await settle()
    type('#item-location', 'loc-1')
    type('#item-owner', 'per-1')
    type('#item-condition', 'good')
    type('#item-completeness', 'complete')
    type('#item-play', 'finished')
    type('#item-format', 'digital')
    type('#item-status', 'sold')
    type('#item-acquired', '2026-10-31')
    type('#item-price', ' 19,99 ')
    type('#item-notes', ' gift ')
    await nextTick()
    click('[data-testid="add-next"]')
    await settle()
    const body = calls.find((c) => c.path.endsWith('/items'))?.body
    expect(body).toMatchObject({
      release_id: 'r-2',
      location_id: 'loc-1',
      owner_id: 'per-1',
      condition: 'good',
      completeness: 'complete',
      play_status: 'finished',
      format: 'digital',
      status: 'sold',
      acquired_on: '2026-10-31',
      purchase_price: '19.99',
      notes: 'gift',
    })

    // Still open, back on the scan tab with a fresh field and a counter.
    expect(useUiStore().addOpen).toBe(true)
    expect($('[data-testid="added-count"]').textContent).toContain('1 game added')
    expect(($('[data-testid="search-input"]') as HTMLInputElement).value).toBe('')
    // The last game's code doesn't stick to the next one picked in the search.
    expect(document.querySelector('[data-testid="search-barcode"]')).toBeNull()
    await lookUp('4902370550733')
    type('[data-testid="search-input"]', 'zelda')
    await vi.waitFor(() => expect($$('[data-testid="candidate-row"]')).toHaveLength(1))
    click('[data-testid="candidate-row"]')
    await settle()
    type('#import-platform', ps5.id)
    await nextTick()
    submit('[data-testid="candidate-confirm"]')
    await settle()
    // "More details" stays open during bulk entry.
    expect(($('#item-location') as HTMLSelectElement).value).toBe('loc-1')
    expect(($('#item-notes') as HTMLTextAreaElement).value).toBe('')
  })

  it('offers search and manual entry when nothing is found', async () => {
    const calls = mockApi({
      ...baseRoutes(),
      'GET /api/lookup/barcode/:code': lookup({
        code: '0000000000000',
      }),
      'GET /api/catalog/releases': [],
      'GET /api/lookup/search': { query: '', platform_id: null, candidates: [], errors: [] },
    })
    const { router } = await open('scan')
    await lookUp('0000000000000')
    expect(pageText()).toContain('No game known for this barcode yet.')

    expect(($('[data-testid="search-input"]') as HTMLInputElement).value).toBe('')
    type('[data-testid="search-input"]', 'Metroid Dread Switch')
    await vi.waitFor(() => expect(calls.some((c) => c.path === '/api/lookup/search')).toBe(true))
    expect(calls.find((c) => c.path === '/api/catalog/releases')?.query.get('q')).toBe(
      'Metroid Dread Switch',
    )
    await vi.waitFor(() => expect(pageText()).toContain('No online results.'))

    // Not listed: on to the form, with title and barcode.
    click('[data-testid="to-manual"]')
    await vi.waitFor(() => expect(router.currentRoute.value.name).toBe('release-new'))
    expect(router.currentRoute.value.query).toEqual({
      title: 'Metroid Dread Switch',
      barcode: '0000000000000',
    })
    expect(useUiStore().addOpen).toBe(false)
  })

  it('keeps a scanned code that found nothing for the game picked in the search', async () => {
    const inCatalog = release({ id: 'r-cat', title: 'Disney Classic Games', barcodes: [] })
    const imported = release({ id: 'r-new', title: 'Disney Classic Games Collection' })
    const calls = mockApi({
      ...baseRoutes(),
      'GET /api/lookup/barcode/:code': lookup({ code: '3391892020175' }),
      'GET /api/catalog/releases': [inCatalog],
      'GET /api/lookup/search': {
        query: 'disney',
        platform_id: null,
        candidates: [candidate({ title: 'Disney Classic Games Collection' })],
        errors: [],
      },
      'POST /api/lookup/import': { status: 201, body: imported },
      'POST /api/catalog/releases/:id/barcodes': { ...inCatalog, barcodes: ['3391892020175'] },
    })
    await open('scan')
    await lookUp('3391892020175')
    expect($('[data-testid="search-barcode"]').textContent).toContain('3391892020175')
    type('[data-testid="search-input"]', 'disney')
    await vi.waitFor(() => expect($$('[data-testid="candidate-row"]')).toHaveLength(1))

    // An online hit is imported with the code …
    click('[data-testid="candidate-row"]')
    await settle()
    expect($('[data-testid="candidate-confirm"]').textContent).toContain('3391892020175')
    type('#import-platform', ps5.id)
    submit('[data-testid="candidate-confirm"]')
    await settle()
    expect(calls.find((c) => c.path === '/api/lookup/import')?.body).toMatchObject({
      barcode: '3391892020175',
    })
    click(
      $$('[data-testid="item-form"] button[type="button"]').find((b) =>
        b.textContent.includes('Back'),
      )!,
    )
    await settle()

    // … a catalog entry gets it attached before the copy is added.
    click('[data-testid="release-row"]')
    await settle()
    const attach = calls.find((c) => c.path === '/api/catalog/releases/r-cat/barcodes')
    expect(attach?.body).toEqual({ code: '3391892020175' })
    expect($('[data-testid="chosen-release"]').textContent).toContain('Disney Classic Games')
  })

  it('still offers the catalog entry when attaching the code fails', async () => {
    const failed = vi.spyOn(toast, 'error')
    const inCatalog = release({ id: 'r-cat', title: 'Halo', barcodes: [] })
    mockApi({
      ...baseRoutes(false),
      'GET /api/lookup/barcode/:code': lookup({ code: '3391892020175' }),
      'GET /api/catalog/releases': [inCatalog],
      'POST /api/catalog/releases/:id/barcodes': {
        status: 409,
        body: { detail: 'This barcode already belongs to another release.' },
      },
    })
    await open('scan')
    await lookUp('3391892020175')
    type('[data-testid="search-input"]', 'halo')
    await vi.waitFor(() => expect($$('[data-testid="release-row"]')).toHaveLength(1))
    click('[data-testid="release-row"]')
    await settle()
    expect($('[data-testid="chosen-release"]').textContent).toContain('Halo')
    expect(failed).toHaveBeenCalledWith(expect.stringContaining('already belongs'))
  })

  it('shows lookup errors inline', async () => {
    mockApi({
      ...baseRoutes(),
      'GET /api/lookup/barcode/:code': {
        status: 400,
        body: { detail: 'This is not a valid EAN/UPC barcode.' },
      },
    })
    await open('scan')
    await lookUp('12345678')
    expect($('[data-testid="scan-error"]').textContent).toContain('not a valid EAN/UPC')
  })

  it('shows a generic message when the lookup fails without an API error', async () => {
    mockApi(baseRoutes())
    await open('scan')
    vi.stubGlobal(
      'fetch',
      vi.fn<() => Promise<Response>>(() => Promise.reject(new TypeError('offline'))),
    )
    await lookUp('12345678')
    expect($('[data-testid="scan-error"]').textContent).toContain('Something went wrong.')
  })

  it('ignores an empty code and toggles the camera', async () => {
    const calls = mockApi(baseRoutes())
    await open('scan')
    submit('[data-testid="search-form"]')
    await settle()
    expect(calls.some((c) => c.path.startsWith('/api/lookup/barcode'))).toBe(false)
    click('[data-testid="scan-toggle"]')
    await settle()
    expect($$('[data-testid="camera"]')).toHaveLength(0)
    click('[data-testid="scan-toggle"]')
    await settle()
    await vi.waitFor(() => expect($$('[data-testid="camera"]')).toHaveLength(1))
  })

  it('searches the catalog and online sources and picks results from both', async () => {
    const inCatalog = release({ id: 'r-cat', title: 'Mario Kart 8 Deluxe' })
    const imported = release({ id: 'r-new', title: 'Mario Kart Live' })
    const calls = mockApi({
      ...baseRoutes(),
      'GET /api/catalog/releases': [inCatalog],
      'GET /api/lookup/search': {
        query: 'mario',
        platform_id: null,
        candidates: [candidate({ title: 'Mario Kart Live', region: 'na' })],
        errors: ['igdb-slow'],
      },
      'POST /api/lookup/import': { status: 201, body: imported },
    })
    await open('search')
    expect(pageText()).toContain('Type at least two characters.')
    type('[data-testid="search-input"]', 'mario')
    type('[data-testid="search-platform"]', 'p-switch')
    await vi.waitFor(() => expect($$('[data-testid="candidate-row"]')).toHaveLength(1))
    expect($('[data-testid="catalog-section"]').textContent).toContain('Mario Kart 8 Deluxe')
    expect($('[data-testid="provider-section"]').textContent).toContain('Mario Kart Live')
    expect(pageText()).toContain('igdb-slow')
    const search = calls.filter((c) => c.path === '/api/lookup/search').at(-1)!
    expect(search.query.get('platform')).toBe('p-switch')
    expect($$('[data-testid="igdb-note"]')).toHaveLength(0)

    // Candidate: region falls back to the candidate's own.
    click('[data-testid="candidate-row"]')
    await settle()
    expect(($('#import-region') as HTMLSelectElement).value).toBe('na')
    expect(($('#import-platform') as HTMLSelectElement).value).toBe('p-switch')
    click($$('[data-testid="candidate-confirm"] button[type="button"]')[0]!)
    await settle()
    // Back keeps the search.
    expect(($('[data-testid="search-input"]') as HTMLInputElement).value).toBe('mario')

    click('[data-testid="release-row"]')
    await settle()
    expect($('[data-testid="chosen-release"]').textContent).toContain('Mario Kart 8 Deluxe')
    click(
      $$('[data-testid="item-form"] button[type="button"]').find((b) =>
        b.textContent.includes('Back'),
      )!,
    )
    await settle()
    expect($$('[data-testid="item-form"]')).toHaveLength(0)
  })

  it('explains that online search needs IGDB and searches only the catalog', async () => {
    const calls = mockApi({
      ...baseRoutes(false),
      'GET /api/catalog/releases': [],
    })
    const { router } = await open('search', 'de')
    expect($('[data-testid="igdb-note"]').textContent).toContain('IGDB-Zugangsdaten')
    expect($('[data-testid="igdb-note"] a').getAttribute('href')).toBe('/integrations')
    type('[data-testid="search-input"]', 'zelda')
    await vi.waitFor(() => expect(pageText()).toContain('Noch nicht im Katalog.'))
    expect(calls.some((c) => c.path === '/api/lookup/search')).toBe(false)
    expect($$('[data-testid="provider-section"]')).toHaveLength(0)

    // "Not listed?" → the form with the title.
    click($$('button').find((b) => b.textContent.includes('Selbst eintragen'))!)
    await vi.waitFor(() => expect(router.currentRoute.value.query.title).toBe('zelda'))
  })

  it('shows search errors per section', async () => {
    mockApi({
      ...baseRoutes(),
      'GET /api/catalog/releases': { status: 400, body: { detail: 'Catalog down' } },
      'GET /api/lookup/search': { status: 502, body: { detail: 'Source down' } },
    })
    await open('search')
    type('[data-testid="search-input"]', 'zelda')
    await vi.waitFor(() => expect(pageText()).toContain('Source down'))
    expect(pageText()).toContain('Catalog down')
  })

  it('shows import errors inline', async () => {
    mockApi({
      ...baseRoutes(),
      'GET /api/catalog/releases': [],
      'GET /api/lookup/search': {
        query: 'x',
        platform_id: null,
        candidates: [candidate({ region: 'mars' })],
        errors: [],
      },
      'POST /api/lookup/import': { status: 502, body: { detail: 'The source did not answer.' } },
    })
    await open('search')
    type('[data-testid="search-input"]', 'zelda')
    await vi.waitFor(() => expect($$('[data-testid="candidate-row"]')).toHaveLength(1))
    click('[data-testid="candidate-row"]')
    await settle()
    expect(($('#import-region') as HTMLSelectElement).value).toBe('pal')
    submit('[data-testid="candidate-confirm"]')
    await settle()
    expect($('[data-testid="import-error"]').textContent).toContain('did not answer')
  })

  it('opens with or without the camera and resets when opened again', async () => {
    mockApi(baseRoutes())
    await open('search')
    expect($$('[data-testid="camera"]')).toHaveLength(0)
    useUiStore().addOpen = false
    await settle()
    useUiStore().openAdd(LIB, 'scan')
    await settle()
    await vi.waitFor(() => expect($$('[data-testid="camera"]')).toHaveLength(1))
  })

  it('keeps the bar while a game is picked and returns to the results on typing', async () => {
    const inCatalog = release({ id: 'r-cat', title: 'Halo' })
    mockApi({ ...baseRoutes(false), 'GET /api/catalog/releases': [inCatalog] })
    await open('search')
    type('[data-testid="search-input"]', 'halo')
    await vi.waitFor(() => expect($$('[data-testid="release-row"]')).toHaveLength(1))
    click('[data-testid="release-row"]')
    await settle()
    expect($('[data-testid="chosen-release"]')).toBeTruthy()
    expect($$('[data-testid="search-input"]')).toHaveLength(1)
    expect($$('[data-testid="release-row"]')).toHaveLength(0)
    type('[data-testid="search-input"]', 'halo 2')
    await settle()
    expect($$('[data-testid="chosen-release"]')).toHaveLength(0)
  })

  it('takes article numbers and can drop a scanned code again', async () => {
    const calls = mockApi({
      ...baseRoutes(false),
      'GET /api/lookup/barcode/:code': lookup({ code: 'NTR-IPKD-NOE' }),
    })
    await open('search')
    type('[data-testid="search-input"]', 'NTR-IPKD-NOE')
    await nextTick()
    expect($('[data-testid="code-hint"]')).toBeTruthy()
    submit('[data-testid="search-form"]')
    await settle()
    expect(calls.some((c) => c.path === '/api/lookup/barcode/NTR-IPKD-NOE')).toBe(true)
    click('[data-testid="clear-barcode"]')
    await settle()
    expect($$('[data-testid="search-barcode"]')).toHaveLength(0)
  })

  it('copes with sparse provider data', async () => {
    const sparse = release({
      id: 'r-sparse',
      title: 'Obscure',
      publisher: null,
      year: null,
      edition: 'Limited',
    })
    mockApi({
      ...baseRoutes(),
      'GET /api/catalog/releases': [sparse],
      'GET /api/lookup/search': {
        query: 'x',
        platform_id: null,
        candidates: [
          candidate({
            platform_id: null,
            platform_name: '',
            year: null,
            publisher: '',
            summary: '',
            cover_url: '',
          }),
        ],
        errors: [],
      },
      'POST /api/lookup/import': { status: 201, body: sparse },
    })
    await open('search')
    type('[data-testid="search-input"]', 'obscure')
    await vi.waitFor(() => expect($$('[data-testid="candidate-row"]')).toHaveLength(1))
    expect($('[data-testid="candidate-row"]').textContent).toContain('Unknown')
    expect($('[data-testid="release-row"]').textContent).toContain('Limited')
    click('[data-testid="candidate-row"]')
    await settle()
    expect(pageText()).toContain('The source lists “—”')
    type('#import-platform', 'p-switch')
    await nextTick()
    submit('[data-testid="candidate-confirm"]')
    await settle()
    expect($('[data-testid="chosen-release"]').textContent).toContain('Limited')
  })

  it('keeps the latest lookup only', async () => {
    let release1!: () => void
    mockApi({
      ...baseRoutes(),
      'GET /api/lookup/barcode/:code': async (_call: unknown, params: Record<string, string>) => {
        if (params.code === '11111111') await new Promise<void>((r) => (release1 = r))
        return lookup({ code: params.code })
      },
    })
    vi.stubGlobal('matchMedia', (query: string) => ({
      matches: query.includes('coarse'),
      addEventListener: () => {},
      removeEventListener: () => {},
    }))
    await open('scan')
    // No keyboard popping up over the camera.
    expect(document.activeElement).not.toBe($('[data-testid="search-input"]'))
    type('[data-testid="search-input"]', '11111111')
    await nextTick()
    submit('[data-testid="search-form"]')
    await settle(1)
    await lookUp('22222222')
    release1()
    await settle()
    expect($('[data-testid="search-barcode"]').textContent).toContain('22222222')
    expect(($('[data-testid="search-input"]') as HTMLInputElement).value).toBe('')
  })
})

describe('AddItemDialog in the layout', () => {
  it('is loaded only once opened, then stays mounted', async () => {
    mockApi({ ...layoutRoutes(makeLibrary()), ...baseRoutes() })
    const { wrapper } = await renderApp('/l/lib-1')
    const dialog = () => wrapper.findComponent({ name: 'AddItemDialog' })
    expect(dialog().exists()).toBe(false)
    useUiStore().openAdd('lib-1', 'scan')
    await vi.waitFor(() => expect($$('[data-testid="search-input"]')).toHaveLength(1))
    useUiStore().addOpen = false
    await settle()
    expect(dialog().exists()).toBe(true)
    useUiStore().openAdd('lib-1', 'scan')
    await settle()
    expect($$('[data-testid="search-input"]')).toHaveLength(1)
  })
})
