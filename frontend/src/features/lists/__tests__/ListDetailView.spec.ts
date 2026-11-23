import { beforeEach, describe, expect, it, vi } from 'vitest'
import { mockApi, pageText, renderComponent, settle, type ApiCall } from '@/test/utils'
import ListDetailView from '../views/ListDetailView.vue'
import { entry, list } from './fixtures'

const toast = vi.hoisted(() => ({
  success: vi.fn<(message: string) => void>(),
  error: vi.fn<(message: string) => void>(),
  info: vi.fn<(message: string) => void>(),
}))
vi.mock('vue-sonner', async (original) => ({ ...(await original<object>()), toast }))

const URL = '/lists/l1'

function body(selector: string): HTMLElement {
  return document.body.querySelector(selector) as HTMLElement
}

function patches(calls: ApiCall[]) {
  return calls.filter((c) => c.method === 'PATCH').map((c) => [c.path.split('/').pop(), c.body])
}

function setup(
  entries = [entry('a', 'Alpha', 1, 'first'), entry('b', 'Beta', 2), entry('c', 'Gamma', 3)],
  extra = {},
) {
  return mockApi({
    'GET /api/lists/l1': list('l1', 'Wishlist', { description: 'Want these', ...extra }),
    'GET /api/lists/l1/entries': entries,
    'PATCH /api/lists/l1/entries/:id': ({ body: b }: ApiCall, { id }: Record<string, string>) => ({
      ...entry(id!, 'x', 1),
      ...(b as object),
    }),
    'DELETE /api/lists/l1/entries/:id': { status: 204 },
    'PATCH /api/lists/l1': ({ body: b }: ApiCall) => ({
      ...list('l1', 'Wishlist'),
      ...(b as object),
    }),
    'DELETE /api/lists/l1': { status: 204 },
    'POST /api/lists/l1/public-link': list('l1', 'Wishlist', { public_token: 'tok123' }),
    'DELETE /api/lists/l1/public-link': list('l1', 'Wishlist'),
  })
}

describe('ListDetailView', () => {
  beforeEach(() => vi.clearAllMocks())

  it('shows the list and its entries ordered by position', async () => {
    setup([entry('b', 'Beta', 2), entry('a', 'Alpha', 1, 'first')])
    const { wrapper } = await renderComponent(ListDetailView, { url: URL })
    expect(wrapper.find('h1').text()).toBe('Wishlist')
    expect(pageText()).toContain('Want these')
    const rows = wrapper.findAll('[data-testid="entry"]')
    expect(rows.map((r) => r.text())).toEqual([
      expect.stringContaining('Alpha'),
      expect.stringContaining('Beta'),
    ])
    expect(rows[0]!.text()).toContain('Switch')
    expect(rows[0]!.find('[data-testid="entry-date"]').text()).toBe('03/03/2017')
    expect((rows[0]!.find('[data-testid="entry-note"]').element as HTMLInputElement).value).toBe(
      'first',
    )
    expect(rows[0]!.find('[data-testid="move-up"]').attributes('disabled')).toBeDefined()
    expect(rows[1]!.find('[data-testid="move-down"]').attributes('disabled')).toBeDefined()
  })

  it('shows an empty state', async () => {
    setup([])
    await renderComponent(ListDetailView, { url: URL })
    expect(pageText()).toContain('This list is empty')
  })

  it('shows a not-found page for unknown lists', async () => {
    mockApi({ 'GET /api/lists/l1/entries': [] })
    await renderComponent(ListDetailView, { url: URL })
    expect(pageText()).toContain("This list doesn't exist (anymore).")
  })

  it('shows other loading errors in the header', async () => {
    mockApi({
      'GET /api/lists/l1': { status: 500, body: { detail: 'Server sad' } },
      'GET /api/lists/l1/entries': [],
    })
    await renderComponent(ListDetailView, { url: URL })
    expect(pageText()).toContain('Server sad')
  })

  it('links to the edit page', async () => {
    setup()
    const { wrapper } = await renderComponent(ListDetailView, { url: URL })
    expect(wrapper.find('[data-testid="edit-list"]').attributes('href')).toBe('/lists/l1/edit')
    expect(document.body.querySelector('[role="dialog"]')).toBeNull()
  })

  it('deletes the list after confirmation', async () => {
    const calls = setup()
    const { wrapper, router } = await renderComponent(ListDetailView, { url: URL })
    await wrapper.find('[data-testid="delete-list"]').trigger('click')
    await settle()
    expect(pageText()).toContain('Delete "Wishlist"?')
    body('[data-testid="confirm-button"]').click()
    await vi.waitFor(() => expect(router.currentRoute.value.name).toBe('lists'))
    expect(calls.some((c) => c.method === 'DELETE' && c.path === '/api/lists/l1')).toBe(true)
    expect(toast.success).toHaveBeenCalledWith('List deleted.')
  })

  it('keeps the list when deleting is cancelled', async () => {
    const calls = setup()
    const { wrapper } = await renderComponent(ListDetailView, { url: URL })
    await wrapper.find('[data-testid="delete-list"]').trigger('click')
    await settle()
    const cancel = [...document.body.querySelectorAll('button')].find(
      (b) => b.textContent.trim() === 'Cancel',
    )!
    cancel.click()
    await vi.waitFor(() =>
      expect(document.body.querySelector('[data-testid="confirm-button"]')).toBeNull(),
    )
    expect(calls.some((c) => c.method === 'DELETE')).toBe(false)
  })

  it('updates the note field when the entry changes on the server', async () => {
    let note = 'old'
    mockApi({
      'GET /api/lists/l1': list('l1', 'Wishlist'),
      'GET /api/lists/l1/entries': () => [entry('a', 'Alpha', 1, note)],
      'PATCH /api/lists/l1/entries/:id': ({ body: b }: ApiCall) => {
        note = `${(b as { note: string }).note}!`
        return entry('a', 'Alpha', 1, note)
      },
    })
    const { wrapper } = await renderComponent(ListDetailView, { url: URL })
    const input = wrapper.find('[data-testid="entry-note"]')
    await input.setValue('new')
    await input.trigger('blur')
    await vi.waitFor(() => expect((input.element as HTMLInputElement).value).toBe('new!'))
  })

  it('reports a failed delete', async () => {
    mockApi({
      'GET /api/lists/l1': list('l1', 'Wishlist'),
      'GET /api/lists/l1/entries': [],
      'DELETE /api/lists/l1': { status: 500, body: { detail: 'Nope' } },
    })
    const { wrapper } = await renderComponent(ListDetailView, { url: URL })
    await wrapper.find('[data-testid="delete-list"]').trigger('click')
    await settle()
    body('[data-testid="confirm-button"]').click()
    await vi.waitFor(() => expect(toast.error).toHaveBeenCalledWith('Nope'))
  })

  it('saves a changed note on blur and skips unchanged notes', async () => {
    const calls = setup()
    const { wrapper } = await renderComponent(ListDetailView, { url: URL })
    const note = wrapper.findAll('[data-testid="entry-note"]')[0]!
    await note.trigger('blur')
    expect(patches(calls)).toEqual([])
    await note.setValue(' great game ')
    await note.trigger('keydown', { key: 'Enter' })
    await note.trigger('blur')
    await vi.waitFor(() => expect(toast.success).toHaveBeenCalledWith('Note saved.'))
    expect(patches(calls)).toEqual([['a', { note: 'great game' }]])
  })

  it('reports a failed note update', async () => {
    mockApi({
      'GET /api/lists/l1': list('l1', 'Wishlist'),
      'GET /api/lists/l1/entries': [entry('a', 'Alpha', 1)],
      'PATCH /api/lists/l1/entries/:id': { status: 400, body: { detail: 'Bad note' } },
    })
    const { wrapper } = await renderComponent(ListDetailView, { url: URL })
    const note = wrapper.find('[data-testid="entry-note"]')
    await note.setValue('x')
    await note.trigger('blur')
    await vi.waitFor(() => expect(toast.error).toHaveBeenCalledWith('Bad note'))
  })

  it('moves entries by swapping positions with the neighbour', async () => {
    const calls = setup()
    const { wrapper } = await renderComponent(ListDetailView, { url: URL })
    await wrapper.findAll('[data-testid="move-down"]')[0]!.trigger('click')
    await vi.waitFor(() =>
      expect(patches(calls)).toEqual([
        ['a', { position: 2 }],
        ['b', { position: 1 }],
      ]),
    )
    calls.length = 0
    await settle()
    await wrapper.findAll('[data-testid="move-up"]')[2]!.trigger('click')
    await vi.waitFor(() =>
      expect(patches(calls)).toEqual([
        ['c', { position: 2 }],
        ['b', { position: 3 }],
      ]),
    )
  })

  it('renumbers entries whose positions collide', async () => {
    const calls = setup([entry('a', 'Alpha', 1), entry('b', 'Beta', 1), entry('c', 'Gamma', 1)])
    const { wrapper } = await renderComponent(ListDetailView, { url: URL })
    await wrapper.findAll('[data-testid="move-down"]')[0]!.trigger('click')
    await vi.waitFor(() =>
      expect(patches(calls)).toEqual([
        ['a', { position: 2 }],
        ['c', { position: 3 }],
      ]),
    )
  })

  it('reports a failed move', async () => {
    mockApi({
      'GET /api/lists/l1': list('l1', 'Wishlist'),
      'GET /api/lists/l1/entries': [entry('a', 'Alpha', 1), entry('b', 'Beta', 2)],
      'PATCH /api/lists/l1/entries/:id': { status: 500, body: { detail: 'Move failed' } },
    })
    const { wrapper } = await renderComponent(ListDetailView, { url: URL })
    await wrapper.findAll('[data-testid="move-down"]')[0]!.trigger('click')
    await vi.waitFor(() => expect(toast.error).toHaveBeenCalledWith('Move failed'))
  })

  it('removes an entry', async () => {
    const calls = setup()
    const { wrapper } = await renderComponent(ListDetailView, { url: URL })
    await wrapper.findAll('[data-testid="remove-entry"]')[1]!.trigger('click')
    await vi.waitFor(() => expect(toast.success).toHaveBeenCalledWith('Removed from the list.'))
    expect(calls.some((c) => c.method === 'DELETE' && c.path === '/api/lists/l1/entries/b')).toBe(
      true,
    )
  })

  it('reports a failed removal', async () => {
    mockApi({
      'GET /api/lists/l1': list('l1', 'Wishlist'),
      'GET /api/lists/l1/entries': [entry('a', 'Alpha', 1)],
    })
    const { wrapper } = await renderComponent(ListDetailView, { url: URL })
    await wrapper.find('[data-testid="remove-entry"]').trigger('click')
    await vi.waitFor(() => expect(toast.error).toHaveBeenCalledWith('Not found'))
  })

  it('creates, copies and turns off the public link', async () => {
    let token: string | null = null
    const calls = mockApi({
      'GET /api/lists/l1': () => list('l1', 'Wishlist', { public_token: token }),
      'GET /api/lists/l1/entries': [],
      'POST /api/lists/l1/public-link': () => (
        (token = 'tok123'),
        list('l1', 'W', { public_token: token })
      ),
      'DELETE /api/lists/l1/public-link': () => ((token = null), list('l1', 'W')),
    })
    const writeText = vi.fn<(text: string) => Promise<void>>().mockResolvedValue(undefined)
    vi.stubGlobal('navigator', { ...navigator, clipboard: { writeText } })
    const { wrapper } = await renderComponent(ListDetailView, { url: URL })
    expect(pageText()).toContain('Only you can see this list.')
    await wrapper.find('[data-testid="enable-link"]').trigger('click')
    await vi.waitFor(() => expect(wrapper.find('[data-testid="link-url"]').exists()).toBe(true))
    const url = `${window.location.origin}/share/list/tok123`
    expect((wrapper.find('[data-testid="link-url"]').element as HTMLInputElement).value).toBe(url)
    expect(wrapper.find('a[target="_blank"]').attributes('href')).toBe(url)
    expect(toast.success).toHaveBeenCalledWith('Public link created.')
    await wrapper.find('[data-testid="link-url"]').trigger('focus')

    await wrapper.find('[data-testid="copy-link"]').trigger('click')
    await vi.waitFor(() => expect(toast.success).toHaveBeenCalledWith('Link copied.'))
    expect(writeText).toHaveBeenCalledWith(url)

    writeText.mockRejectedValueOnce(new Error('denied'))
    await wrapper.find('[data-testid="copy-link"]').trigger('click')
    await vi.waitFor(() => expect(toast.error).toHaveBeenCalledWith("Couldn't copy the link."))

    await wrapper.find('[data-testid="disable-link"]').trigger('click')
    await vi.waitFor(() => expect(wrapper.find('[data-testid="enable-link"]').exists()).toBe(true))
    expect(toast.success).toHaveBeenCalledWith('Public link turned off.')
    expect(calls.filter((c) => c.path.endsWith('public-link')).map((c) => c.method)).toEqual([
      'POST',
      'DELETE',
    ])
  })

  it('reports a failed public link toggle', async () => {
    mockApi({
      'GET /api/lists/l1': list('l1', 'Wishlist'),
      'GET /api/lists/l1/entries': [],
      'POST /api/lists/l1/public-link': { status: 500, body: { detail: 'No link' } },
    })
    const { wrapper } = await renderComponent(ListDetailView, { url: URL })
    await wrapper.find('[data-testid="enable-link"]').trigger('click')
    await vi.waitFor(() => expect(toast.error).toHaveBeenCalledWith('No link'))
  })
})
