import { describe, expect, it, vi } from 'vitest'
import { nextTick } from 'vue'
import { mockApi, pickerChips, pickTerm, renderApp, settle, type ApiCall } from '@/test/utils'
import { layoutRoutes, makeLibrary } from '@/test/fixtures'
import { $, baseRoutes, release, submit, type } from './fixtures'

const FORM = 'form'

describe('Entering a game by hand', () => {
  it('takes title and barcode from the search and opens the new game', async () => {
    const created = release({ id: 'r-new', title: 'Homebrew Hero' })
    const calls = mockApi({
      ...layoutRoutes(makeLibrary()),
      ...baseRoutes(),
      'POST /api/catalog/releases': { status: 201, body: created },
      'GET /api/catalog/releases/:id': created,
      'GET /api/catalog/companies': ({ query }: ApiCall) =>
        [{ id: 'c-ann', name: 'Ann Games', uses: 3 }].filter((c) =>
          c.name.includes(query.get('q') ?? ''),
        ),
      'GET /api/catalog/genres': [],
      'GET /api/catalog/series': [],
      'GET /api/catalog/editions': [{ name: 'Limited Edition', uses: 2 }],
    })
    const { router } = await renderApp('/releases/new?title=Homebrew%20Hero&barcode=4006381333931')
    expect(($('#manual-title') as HTMLInputElement).value).toBe('Homebrew Hero')
    expect(($('#manual-barcode') as HTMLInputElement).value).toBe('4006381333931')

    // Title and platform are required.
    submit(FORM)
    await settle()
    expect(calls.some((c) => c.method === 'POST')).toBe(false)

    type('#manual-platform', 'p-switch')
    type('#manual-region', 'de')
    type('[data-testid="date-start"]', '2020-01-02')
    await pickTerm('#manual-edition', 'Lim', 'Limited Edition')
    await pickTerm('#manual-publisher', 'Indie', 'Create “Indie”')
    await pickTerm('#manual-developers', 'Ann', 'Ann Games')
    await pickTerm('#manual-developers', 'Bob', 'Create “Bob”')
    await pickTerm('#manual-genres', 'Platformer', 'Create “Platformer”')
    expect(pickerChips('#manual-developers')).toEqual(['Ann Games', 'Bob'])
    type('#manual-summary', 'Jumps.')
    await nextTick()
    submit(FORM)
    await settle()
    expect(
      calls.find((c) => c.path === '/api/catalog/releases' && c.method === 'POST')?.body,
    ).toEqual({
      title: 'Homebrew Hero',
      platform_id: 'p-switch',
      region: 'de',
      edition: 'Limited Edition',
      release_precision: 'day',
      release_date: '2020-01-02',
      release_date_end: null,
      publisher: { name: 'Indie' },
      series: [],
      franchises: [],
      developers: [{ id: 'c-ann' }, { name: 'Bob' }],
      genres: [{ name: 'Platformer' }],
      summary: 'Jumps.',
      barcode: '4006381333931',
    })
    await vi.waitFor(() => expect(router.currentRoute.value.path).toBe('/releases/r-new'))
  })

  it('shows creation errors and sends empty optional fields as null', async () => {
    const calls = mockApi({
      ...layoutRoutes(makeLibrary()),
      ...baseRoutes(),
      'POST /api/catalog/releases': { status: 409, body: { detail: 'Already exists.' } },
    })
    await renderApp('/releases/new')
    type('#manual-title', 'X')
    type('#manual-platform', 'p-ps5')
    await nextTick()
    submit(FORM)
    await settle()
    expect($('[data-testid="edit-error"]').textContent).toContain('Already exists.')
    expect(calls.find((c) => c.method === 'POST')?.body).toMatchObject({
      release_date: null,
      barcode: null,
      publisher: null,
      developers: [],
    })
  })
})
