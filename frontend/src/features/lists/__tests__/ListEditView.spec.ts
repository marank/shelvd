import { beforeEach, describe, expect, it, vi } from 'vitest'
import { mockApi, pageText, renderComponent, settle, type ApiCall } from '@/test/utils'
import ListEditView from '../views/ListEditView.vue'
import { entry, list } from './fixtures'

const toast = vi.hoisted(() => ({
  success: vi.fn<(message: string) => void>(),
  error: vi.fn<(message: string) => void>(),
  info: vi.fn<(message: string) => void>(),
}))
vi.mock('vue-sonner', async (original) => ({ ...(await original<object>()), toast }))

function el<T extends HTMLElement = HTMLInputElement>(selector: string): T {
  return document.body.querySelector(selector) as T
}

async function type(selector: string, value: string) {
  const input = el(selector)
  input.value = value
  input.dispatchEvent(new Event('input'))
  await settle(1)
}

async function submit() {
  el<HTMLFormElement>('form').dispatchEvent(new Event('submit'))
  await settle()
}

const created = ({ body }: ApiCall) => ({
  status: 201,
  body: list('n1', (body as { name: string }).name),
})

describe('ListEditView', () => {
  beforeEach(() => vi.clearAllMocks())

  it('creates a list and opens it', async () => {
    const calls = mockApi({ 'POST /api/lists': created })
    const { router } = await renderComponent(ListEditView, { url: '/lists/new' })
    expect(pageText()).toContain('New list')
    expect(el('[data-testid="edit-save"]').textContent.trim()).toBe('Create')
    expect(el('[data-testid="edit-back"]').getAttribute('href')).toBe('/lists')
    expect(el('[data-testid="public-link"]')).toBeNull()
    expect(el('[data-testid="delete-list"]')).toBeNull()
    // no GET for a list that doesn't exist yet
    expect(calls.some((c) => c.path.startsWith('/api/lists/'))).toBe(false)

    await submit()
    expect(el('[data-testid="edit-error"]').textContent.trim()).toBe('Please enter a name.')
    expect(calls.some((c) => c.method === 'POST')).toBe(false)

    await type('#list-name', '  Favourites ')
    await type('#list-description', ' Best ones ')
    await submit()
    await vi.waitFor(() => expect(router.currentRoute.value.fullPath).toBe('/lists/n1'))
    expect(router.currentRoute.value.name).toBe('list-detail')
    expect(calls.find((c) => c.method === 'POST')?.body).toEqual({
      name: 'Favourites',
      description: 'Best ones',
    })
    expect(toast.success).toHaveBeenCalledWith('List created.')
  })

  it('shows a failed create on the page', async () => {
    mockApi({ 'POST /api/lists': { status: 400, body: { detail: 'Name taken' } } })
    await renderComponent(ListEditView, { url: '/lists/new' })
    await type('#list-name', 'Dupes')
    await submit()
    await vi.waitFor(() =>
      expect(el('[data-testid="edit-error"]').textContent.trim()).toBe('Name taken'),
    )
  })

  it('creates a list for a game, adds it and goes back to the referring page', async () => {
    const calls = mockApi({
      'POST /api/lists': created,
      'POST /api/lists/:id/entries': { status: 201, body: entry('e1', 'Zelda', 1) },
    })
    const back = '/l/lib1?item=i1'
    const { router } = await renderComponent(ListEditView, {
      url: `/lists/new?release=r1&item=i1&back=${encodeURIComponent(back)}`,
    })
    expect(el('[data-testid="edit-back"]').getAttribute('href')).toBe(back)
    await type('#list-name', 'Borrow')
    await submit()
    await vi.waitFor(() => expect(router.currentRoute.value.fullPath).toBe(back))
    const post = calls.find((c) => c.path === '/api/lists/n1/entries')
    expect(post?.body).toEqual({ release_id: 'r1', item_id: 'i1', note: '' })
    expect(toast.success).toHaveBeenCalledWith('Added to "Borrow".')
  })

  it('opens the new list when adding the game fails and ignores foreign back links', async () => {
    mockApi({
      'POST /api/lists': created,
      'POST /api/lists/:id/entries': { status: 500, body: { detail: 'Broken' } },
    })
    const { router } = await renderComponent(ListEditView, {
      url: `/lists/new?release=r1&back=${encodeURIComponent('//evil.example')}`,
    })
    expect(el('[data-testid="edit-back"]').getAttribute('href')).toBe('/lists')
    await type('#list-name', 'Borrow')
    await submit()
    await vi.waitFor(() => expect(toast.error).toHaveBeenCalledWith('Broken'))
    await vi.waitFor(() => expect(router.currentRoute.value.name).toBe('list-detail'))
    expect(router.currentRoute.value.params).toEqual({ listId: 'n1' })
  })

  it('adds the game without an item and opens the list without a back link', async () => {
    const calls = mockApi({
      'POST /api/lists': created,
      'POST /api/lists/:id/entries': { status: 201, body: entry('e1', 'Zelda', 1) },
    })
    const { router } = await renderComponent(ListEditView, { url: '/lists/new?release=r1' })
    await type('#list-name', 'Borrow')
    await submit()
    await vi.waitFor(() => expect(router.currentRoute.value.name).toBe('list-detail'))
    expect(calls.find((c) => c.path === '/api/lists/n1/entries')?.body).toEqual({
      release_id: 'r1',
      item_id: null,
      note: '',
    })
  })

  it('edits name and description and shows the public link card', async () => {
    let fail = true
    const calls = mockApi({
      'GET /api/lists/l1': list('l1', 'Wishlist', { description: 'Want these' }),
      'PATCH /api/lists/l1': ({ body }: ApiCall) =>
        fail
          ? { status: 400, body: { detail: 'Too long' } }
          : { ...list('l1', 'Wishlist'), ...(body as object) },
    })
    const { router } = await renderComponent(ListEditView, { url: '/lists/l1/edit' })
    await vi.waitFor(() => expect(el('#list-name').value).toBe('Wishlist'))
    expect(pageText()).toContain('Edit list')
    expect(el('#list-description').value).toBe('Want these')
    expect(el('[data-testid="edit-back"]').getAttribute('href')).toBe('/lists/l1')
    expect(el('[data-testid="public-link"]')).not.toBeNull()
    expect(el('[data-testid="enable-link"]').getAttribute('type')).toBe('button')

    await type('#list-name', 'Wants')
    await submit()
    await vi.waitFor(() =>
      expect(el('[data-testid="edit-error"]').textContent.trim()).toBe('Too long'),
    )
    fail = false
    await submit()
    await vi.waitFor(() => expect(router.currentRoute.value.name).toBe('list-detail'))
    expect(calls.filter((c) => c.method === 'PATCH').at(-1)?.body).toEqual({
      name: 'Wants',
      description: 'Want these',
    })
    expect(toast.success).toHaveBeenCalledWith('Saved.')
  })

  it('reloads the form when switching lists', async () => {
    mockApi({
      'GET /api/lists/:id': (_: ApiCall, { id }: Record<string, string>) =>
        list(id!, id === 'l1' ? 'One' : 'Two'),
    })
    const { router } = await renderComponent(ListEditView, { url: '/lists/l1/edit' })
    await vi.waitFor(() => expect(el('#list-name').value).toBe('One'))
    await router.push('/lists/l2/edit')
    await vi.waitFor(() => expect(el('#list-name').value).toBe('Two'))
  })

  it('shows unknown lists and other load errors', async () => {
    mockApi({ 'GET /api/lists/l2': { status: 500, body: { detail: 'Server sad' } } })
    const { router } = await renderComponent(ListEditView, { url: '/lists/l1/edit' })
    await vi.waitFor(() =>
      expect(el('[data-testid="list-load-error"]').textContent.trim()).toBe(
        "This list doesn't exist (anymore).",
      ),
    )
    await router.push('/lists/l2/edit')
    await vi.waitFor(() =>
      expect(el('[data-testid="list-load-error"]').textContent.trim()).toBe('Server sad'),
    )
  })

  it('deletes the list after confirmation and reports failures', async () => {
    let fail = true
    const calls = mockApi({
      'GET /api/lists/l1': list('l1', 'Wishlist'),
      'DELETE /api/lists/l1': () =>
        fail ? { status: 500, body: { detail: 'Nope' } } : { status: 204 },
    })
    const { router } = await renderComponent(ListEditView, { url: '/lists/l1/edit' })
    await vi.waitFor(() => expect(el('[data-testid="delete-list"]')).not.toBeNull())
    el('[data-testid="delete-list"]').click()
    await settle()
    expect(pageText()).toContain('Delete "Wishlist"?')
    expect(calls.some((c) => c.method === 'PATCH')).toBe(false)
    el('[data-testid="confirm-button"]').click()
    await vi.waitFor(() => expect(toast.error).toHaveBeenCalledWith('Nope'))
    fail = false
    el('[data-testid="confirm-button"]').click()
    await vi.waitFor(() => expect(router.currentRoute.value.name).toBe('lists'))
    expect(toast.success).toHaveBeenCalledWith('List deleted.')
  })
})
