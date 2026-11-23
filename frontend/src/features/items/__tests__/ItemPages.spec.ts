import { describe, expect, it, vi } from 'vitest'
import { api } from '@/api/client'
import { layoutRoutes, makeItem, makeLibrary, makeRelease } from '@/test/fixtures'
import { mockApi, pageText, renderApp, settle } from '@/test/utils'

const release = makeRelease({ id: 'rel-1', work_id: 'work-1' })
const item = makeItem({
  id: 'item-1',
  release,
  title: 'Mein MK8',
  title_override: 'Mein MK8',
  has_cover_override: true,
  purchase_price: '49.90',
  acquired_on: '2020-01-01',
  location: {
    id: 'loc-1',
    name: 'Box',
    path: 'Office › Box',
    trail: [
      { name: 'Office', kind: 'room' },
      { name: 'Box', kind: 'box' },
    ],
  },
  owner: { id: 'p1', name: 'Lena' },
})

function routes(extra: Record<string, unknown> = {}) {
  return {
    ...layoutRoutes(makeLibrary()),
    'GET /api/libraries/lib-1/tree': { total: 0, group_by: [], nodes: [] },
    'GET /api/libraries/lib-1/items/item-1': item,
    'GET /api/items/item-1': item,
    'GET /api/libraries/lib-1/locations': [
      {
        id: 'loc-1',
        parent_id: null,
        name: 'Box',
        kind: 'box',
        notes: '',
        path: 'Office › Box',
        item_count: 1,
      },
    ],
    'GET /api/libraries/lib-1/people': [
      { id: 'p1', name: 'Lena', email: '', notes: '', open_loans: 0 },
    ],
    'GET /api/catalog/works/work-1': {
      id: 'work-1',
      title: 'MK8',
      media_type: 'game',
      summary: '',
      first_release_date: null,
      genres: [],
      developers: [],
      cover_url: null,
      releases: [],
    },
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

async function submit() {
  await settle()
  document.querySelector('form')!.dispatchEvent(new Event('submit'))
  await settle()
}

describe('item edit page', () => {
  it('keeps its own edition, region and date beside the release and resets them', async () => {
    const own = {
      ...item,
      edition_override: 'Classics',
      region_override: 'jp' as const,
      release_precision_override: 'year' as const,
      release_date_override: '1999-01-01',
      overrides: ['title', 'edition', 'region', 'release_date'],
    }
    const calls = mockApi(
      routes({
        'GET /api/libraries/lib-1/items/item-1': own,
        'GET /api/items/item-1': own,
        'GET /api/catalog/releases/rel-1': { ...release, edition: 'Standard' },
        'PATCH /api/libraries/lib-1/items/item-1': own,
        'POST /api/libraries/lib-1/items/item-1/reset': item,
      }),
    )
    const { router } = await renderApp('/items/item-1/edit')
    await vi.waitFor(() => expect(document.querySelector('#f-edition')).not.toBeNull())
    expect((document.querySelector('#f-edition') as HTMLInputElement).value).toBe('Classics')
    await vi.waitFor(() =>
      expect((document.querySelector('#f-edition') as HTMLInputElement).placeholder).toBe(
        'Standard',
      ),
    )
    expect(pageText()).toContain('Differs in: title, edition, region, date')
    // One back to the release's value, the region kept, the date dropped.
    ;(document.querySelector('[data-testid="reset-edition"]') as HTMLElement).click()
    ;(document.querySelector('[data-testid="own-date"]') as HTMLInputElement).click()
    await submit()
    expect(calls.find((c) => c.method === 'PATCH')!.body).toMatchObject({
      edition_override: '',
      region_override: 'jp',
      release_precision_override: '',
      release_date_override: null,
    })
    await router.push('/items/item-1/edit')
    await vi.waitFor(() =>
      expect(document.querySelector('[data-testid="reset-all"]')).not.toBeNull(),
    )
    ;(document.querySelector('[data-testid="reset-all"]') as HTMLElement).click()
    await vi.waitFor(() =>
      expect(calls.some((c) => c.path === '/api/libraries/lib-1/items/item-1/reset')).toBe(true),
    )
  })

  it('is closed for viewers', async () => {
    mockApi({ ...routes(), ...layoutRoutes(makeLibrary({ role: 'viewer' })) })
    await renderApp('/items/item-1/edit')
    await vi.waitFor(() =>
      expect(document.querySelector('[data-testid="forbidden"]')).not.toBeNull(),
    )
  })

  it('saves the copy incl. its own title and goes back to it', async () => {
    const calls = mockApi(routes({ 'PATCH /api/libraries/lib-1/items/item-1': item }))
    const { router } = await renderApp('/items/item-1/edit')
    await vi.waitFor(() => expect(document.querySelector('#f-title')).not.toBeNull())
    expect((document.querySelector('#f-title') as HTMLInputElement).value).toBe('Mein MK8')
    await type('#f-title', '  ')
    await type('#f-price', '')
    await type('#f-acquired', '')
    await type('#f-notes', 'Mint')
    await type('#f-value', '99.5')
    await type('#f-tags', 'Steelbook, signiert ,')
    await submit()
    expect(calls.find((c) => c.method === 'PATCH')!.body).toMatchObject({
      title_override: '',
      purchase_price: null,
      acquired_on: null,
      notes: 'Mint',
      current_value: '99.5',
      tags: ['Steelbook', 'signiert'],
      location_id: 'loc-1',
      owner_id: 'p1',
    })
    await vi.waitFor(() => expect(router.currentRoute.value.path).toBe('/items/item-1'))
  })

  it('shows save errors and manages the own cover', async () => {
    const calls = mockApi(
      routes({
        'PATCH /api/libraries/lib-1/items/item-1': {
          status: 400,
          body: { detail: 'Unknown person.' },
        },
        'DELETE /api/libraries/lib-1/items/item-1/cover': item,
      }),
    )
    await renderApp('/items/item-1/edit')
    await vi.waitFor(() => expect(document.querySelector('#f-title')).not.toBeNull())
    await type('#f-price', '12.5')
    await submit()
    await vi.waitFor(() =>
      expect(document.querySelector('[data-testid="edit-error"]')?.textContent).toContain(
        'Unknown person.',
      ),
    )

    ;(document.querySelector('[data-testid="reset-cover"]') as HTMLElement).click()
    await vi.waitFor(() => expect(calls.some((c) => c.method === 'DELETE')).toBe(true))

    const post = vi.spyOn(api, 'POST')
    post.mockResolvedValueOnce({
      data: item,
      error: undefined,
      response: new Response('{}'),
    })
    const input = document.querySelector('[data-testid="cover-input"]') as HTMLInputElement
    const file = new File(['x'], 'c.png', { type: 'image/png' })
    Object.defineProperty(input, 'files', { value: [file], configurable: true })
    input.dispatchEvent(new Event('change'))
    await vi.waitFor(() => expect(post).toHaveBeenCalled())
    const [path, options] = post.mock.calls[0] as unknown as [
      string,
      { bodySerializer: () => FormData },
    ]
    expect(path).toBe('/api/libraries/{library_id}/items/{item_id}/cover')
    expect(options.bodySerializer().get('file')).toBe(file)
    post.mockResolvedValueOnce({
      data: undefined,
      error: { detail: 'Too large.' },
      response: new Response('{}', { status: 400 }),
    })
    Object.defineProperty(input, 'files', { value: [file], configurable: true })
    input.dispatchEvent(new Event('change'))
    await vi.waitFor(() => expect(pageText()).toContain('Too large.'))
    post.mockRestore()
  })
})

describe('lend page', () => {
  it('lends to a new person', async () => {
    const calls = mockApi(routes({ 'POST /api/libraries/lib-1/loans': { status: 201, body: {} } }))
    const { router } = await renderApp('/items/item-1/lend')
    await vi.waitFor(() => expect(document.querySelector('#l-name')).not.toBeNull())
    await type('#l-name', ' Max ')
    await type('#l-due', '2026-12-24')
    await submit()
    expect(calls.find((c) => c.method === 'POST')!.body).toMatchObject({
      item_id: 'item-1',
      borrower_id: null,
      borrower_name: 'Max',
      due_on: '2026-12-24',
    })
    await vi.waitFor(() => expect(router.currentRoute.value.path).toBe('/items/item-1'))
  })

  it('shows conflicts', async () => {
    mockApi(
      routes({
        'POST /api/libraries/lib-1/loans': { status: 409, body: { detail: 'Already lent.' } },
      }),
    )
    await renderApp('/items/item-1/lend')
    await vi.waitFor(() => expect(document.querySelector('#l-name')).not.toBeNull())
    await submit()
    await vi.waitFor(() => expect(pageText()).toContain('Already lent.'))
  })
})
