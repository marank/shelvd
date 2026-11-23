import { describe, expect, it, vi } from 'vitest'
import { api } from '@/api/client'
import { backTarget, splitList } from '@/features/works/composables/form'
import { layoutRoutes, makeLibrary, makeRelease, makeWork } from '@/test/fixtures'
import {
  mockApi,
  pageText,
  pickerChips as chips,
  pickTerm,
  renderApp,
  settle,
  type ApiCall,
} from '@/test/utils'

const release = makeRelease({ id: 'rel-1', work_id: 'work-1', title: 'MK8 DE', edition: 'Booster' })

function routes(extra: Record<string, unknown> = {}) {
  return {
    ...layoutRoutes(makeLibrary()),
    'GET /api/libraries/lib-1/tree': { total: 0, group_by: [], nodes: [] },
    'GET /api/catalog/works/work-1': makeWork(),
    'GET /api/catalog/releases/rel-1': release,
    'GET /api/libraries/lib-1/items': { count: 0, items: [] },
    'GET /api/watchlist': [],
    ...extra,
  }
}

async function type(selector: string, value: string) {
  const input = document.querySelector(selector) as HTMLInputElement
  input.value = value
  input.dispatchEvent(new Event('input'))
  await settle()
}

function key(selector: string, name: string) {
  const input = document.querySelector(selector) as HTMLInputElement
  input.dispatchEvent(new KeyboardEvent('keydown', { key: name, bubbles: true }))
}

async function submit() {
  await settle()
  document.querySelector('form')!.dispatchEvent(new Event('submit'))
  await settle()
}

describe('catalog edit pages', () => {
  it('helpers', () => {
    expect(splitList(' a, b ,,')).toEqual(['a', 'b'])
    expect(backTarget('/l/x')).toBe('/l/x')
    expect(backTarget('//evil.example')).toEqual({ name: 'home' })
    expect(backTarget(undefined)).toEqual({ name: 'home' })
  })

  it('edits the game, picking genres and series from suggestions', async () => {
    const calls = mockApi(
      routes({
        'PATCH /api/catalog/works/work-1': makeWork(),
        'GET /api/catalog/genres': (call: ApiCall) =>
          call.query.get('q') === 'Par' ? [{ id: 'genre-party', name: 'Party', uses: 3 }] : [],
        'GET /api/catalog/series': [{ id: 'series-mario', name: 'Mario', uses: 9 }],
      }),
    )
    const { router } = await renderApp('/works/work-1/edit?back=/works/work-1')
    await vi.waitFor(() => expect(document.querySelector('#w-title')).not.toBeNull())
    // The game's genres and developers show as chips.
    expect(chips('#w-genres')).toEqual(['Racing'])
    // An existing genre from the suggestions, and a new one ("create").
    await pickTerm('#w-genres', 'Par', 'Party')
    await pickTerm('#w-genres', 'Brand New', 'Create “Brand New”')
    expect(chips('#w-genres')).toEqual(['Racing', 'Party', 'Brand New'])
    // Backspace in the empty field removes the last chip; then pick another series.
    key('#w-series', 'Backspace')
    await settle()
    expect(chips('#w-series')).toEqual([])
    await pickTerm('#w-series', 'Mar', 'Mario')
    await type('#w-first', '')
    await submit()
    expect(calls.find((c) => c.method === 'PATCH')!.body).toMatchObject({
      title: 'Mario Kart 8 Deluxe',
      genres: [{ id: 'genre-racing' }, { id: 'genre-party' }, { name: 'Brand New' }],
      series: [{ id: 'series-mario' }],
      developers: [{ id: 'company-epd' }],
      first_release_date: null,
    })
    await vi.waitFor(() => expect(router.currentRoute.value.fullPath).toBe('/works/work-1'))
  })

  it("uploads and removes the game's own cover right away", async () => {
    const withCover = makeWork({
      has_cover: true,
      cover_url: '/media/covers/works/w.png',
      cover_aspect: 1.7778,
    })
    mockApi(routes())
    await renderApp('/works/work-1/edit')
    await vi.waitFor(() => expect(document.querySelector('#w-title')).not.toBeNull())
    expect(pageText()).toContain('No cover of its own')
    expect(document.querySelector('[data-testid="work-cover-remove"]')).toBeNull()

    const post = vi.spyOn(api, 'POST')
    post.mockResolvedValueOnce({
      data: withCover,
      error: undefined,
      response: new Response('{}'),
    })
    const input = document.querySelector('[data-testid="work-cover-input"]') as HTMLInputElement
    Object.defineProperty(input, 'files', { value: [new File(['x'], 'k.png')], configurable: true })
    input.dispatchEvent(new Event('change'))
    await vi.waitFor(() => expect(pageText()).toContain('Cover saved'))
    expect(post.mock.calls[0]![0]).toBe('/api/catalog/works/{work_id}/cover')
    post.mockRestore()

    mockApi(
      routes({
        'GET /api/catalog/works/work-1': withCover,
        'DELETE /api/catalog/works/work-1/cover': makeWork(),
      }),
    )
    await renderApp('/works/work-1/edit')
    await vi.waitFor(() =>
      expect(document.querySelector('[data-testid="work-cover-remove"]')).not.toBeNull(),
    )
    ;(document.querySelector('[data-testid="work-cover-remove"]') as HTMLElement).click()
    await vi.waitFor(() => expect(pageText()).toContain('Cover removed'))
  })

  it('shows errors when saving the game fails', async () => {
    mockApi(
      routes({
        'PATCH /api/catalog/works/work-1': {
          status: 400,
          body: { detail: 'A title is required.' },
        },
      }),
    )
    await renderApp('/works/work-1/edit')
    await vi.waitFor(() => expect(document.querySelector('#w-title')).not.toBeNull())
    await submit()
    await vi.waitFor(() => expect(pageText()).toContain('A title is required.'))
  })

  it('edits a release with its date precision and a barcode', async () => {
    const calls = mockApi(
      routes({
        'PATCH /api/catalog/releases/rel-1': release,
        'POST /api/catalog/releases/rel-1/barcodes': release,
        'GET /api/catalog/editions': [{ name: 'Deluxe Edition', uses: 4 }],
        'GET /api/catalog/companies': [],
      }),
    )
    const { router } = await renderApp('/releases/rel-1/edit')
    await vi.waitFor(() => expect(document.querySelector('#r-title')).not.toBeNull())
    expect(pageText()).toContain('Catalog data applies to every library')
    // The edition: free text, with the editions in use as suggestions.
    const edition = document.querySelector('#r-edition') as HTMLInputElement
    edition.dispatchEvent(new Event('focus'))
    await type('#r-edition', 'Del')
    await vi.waitFor(() =>
      expect(document.querySelector('#r-edition-suggestions')?.textContent).toContain(
        'Deluxe Edition',
      ),
    )
    key('#r-edition', 'Enter')
    await settle()
    expect(edition.value).toBe('Deluxe Edition')
    // One publisher: picking another replaces it; a new name is created on save.
    expect(chips('#r-publisher')).toEqual(['Nintendo'])
    await pickTerm('#r-publisher', 'Nintendo of Europe', 'Create “Nintendo of Europe”')
    expect(chips('#r-publisher')).toEqual(['Nintendo of Europe'])
    // Studios of this release only (a port), besides the game's developers.
    expect(chips('#r-developers')).toEqual([])
    await pickTerm('#r-developers', 'Panic Button', 'Create “Panic Button”')
    ;(document.querySelector('[data-testid="precision-tba"]') as HTMLElement).click()
    await type('#r-barcode', '4006381333931')
    await type('#r-age', 'USK 6')
    await type('#r-code', 'LA-H-AAAAA-EUR')
    await type('#r-number', '42')
    await submit()
    expect(calls.find((c) => c.method === 'PATCH')!.body).toMatchObject({
      title: 'MK8 DE',
      edition: 'Deluxe Edition',
      publisher: { name: 'Nintendo of Europe' },
      release_developers: [{ name: 'Panic Button' }],
      release_precision: 'tba',
      release_date: null,
      age_rating: 'USK 6',
      product_code: 'LA-H-AAAAA-EUR',
      release_number: 42,
    })
    expect(calls.find((c) => c.path.endsWith('/barcodes'))!.body).toEqual({ code: '4006381333931' })
    await vi.waitFor(() => expect(router.currentRoute.value.name).not.toBe('release-edit'))
  })

  it('uploads a catalog cover and reports errors', async () => {
    const calls = mockApi(
      routes({
        'PATCH /api/catalog/releases/rel-1': { status: 409, body: { detail: 'Barcode taken.' } },
      }),
    )
    await renderApp('/releases/rel-1/edit')
    await vi.waitFor(() => expect(document.querySelector('#r-title')).not.toBeNull())
    await type('#r-number', '')
    // Removing the publisher's chip sends null (no publisher).
    ;(document.querySelector('[aria-label="Remove Nintendo"]') as HTMLElement).click()
    await submit()
    await vi.waitFor(() => expect(pageText()).toContain('Barcode taken.'))
    expect(calls.find((c) => c.method === 'PATCH')!.body).toMatchObject({ publisher: null })

    const post = vi.spyOn(api, 'POST')
    post.mockResolvedValueOnce({
      data: release,
      error: undefined,
      response: new Response('{}'),
    })
    const input = document.querySelector('[data-testid="cover-input"]') as HTMLInputElement
    Object.defineProperty(input, 'files', { value: [new File(['x'], 'c.png')], configurable: true })
    input.dispatchEvent(new Event('change'))
    await vi.waitFor(() => expect(pageText()).toContain('Cover saved'))
    post.mockResolvedValueOnce({
      data: undefined,
      error: { detail: 'Not an image.' },
      response: new Response('{}', { status: 400 }),
    })
    input.dispatchEvent(new Event('change'))
    await vi.waitFor(() => expect(pageText()).toContain('Not an image.'))
    post.mockRestore()
  })
})
