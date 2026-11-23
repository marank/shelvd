import { beforeEach, describe, expect, it, vi } from 'vitest'
import { defineComponent, h } from 'vue'
import { mockApi, pageText, renderComponent, settle } from '@/test/utils'
import AddToListMenu from '../components/AddToListMenu.vue'
import { entry, list } from './fixtures'

const toast = vi.hoisted(() => ({
  success: vi.fn<(message: string) => void>(),
  error: vi.fn<(message: string) => void>(),
  info: vi.fn<(message: string) => void>(),
}))
vi.mock('vue-sonner', async (original) => ({ ...(await original<object>()), toast }))

async function openMenu(trigger: HTMLElement) {
  trigger.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', bubbles: true }))
  await settle()
}

function items(selector: string): HTMLElement[] {
  return [...document.body.querySelectorAll<HTMLElement>(selector)]
}

async function select(el: HTMLElement) {
  el.click()
  await settle()
}

const lists = [list('l1', 'Wishlist', { entry_count: 2 }), list('l2', 'Favourites')]

describe('AddToListMenu', () => {
  beforeEach(() => vi.clearAllMocks())

  it('adds the release to a list', async () => {
    const calls = mockApi({
      'GET /api/lists': lists,
      'POST /api/lists/:id/entries': { status: 201, body: entry('e1', 'Zelda', 1) },
    })
    const { wrapper } = await renderComponent(AddToListMenu, {
      props: { releaseId: 'r1', itemId: 'i1' },
    })
    await openMenu(wrapper.find('[data-testid="add-to-list"]').element as HTMLElement)
    expect(pageText()).toContain('Wishlist')
    expect(pageText()).toContain('Favourites')
    await select(items('[data-testid="add-to-list-item"]')[0]!)
    await vi.waitFor(() => expect(toast.success).toHaveBeenCalledWith('Added to "Wishlist".'))
    const post = calls.find((c) => c.method === 'POST')
    expect(post?.path).toBe('/api/lists/l1/entries')
    expect(post?.body).toEqual({ release_id: 'r1', item_id: 'i1', note: '' })
  })

  it('shows an info toast when the release is already on the list', async () => {
    const calls = mockApi({
      'GET /api/lists': lists,
      'POST /api/lists/:id/entries': { status: 409, body: { detail: 'exists' } },
    })
    const { wrapper } = await renderComponent(AddToListMenu, { props: { releaseId: 'r1' } })
    await openMenu(wrapper.find('button').element)
    await select(items('[data-testid="add-to-list-item"]')[1]!)
    await vi.waitFor(() => expect(toast.info).toHaveBeenCalledWith('Already on "Favourites".'))
    expect(calls.find((c) => c.method === 'POST')?.body).toEqual({
      release_id: 'r1',
      item_id: null,
      note: '',
    })
  })

  it('shows other errors as error toasts', async () => {
    mockApi({
      'GET /api/lists': lists,
      'POST /api/lists/:id/entries': { status: 500, body: { detail: 'Broken' } },
    })
    const { wrapper } = await renderComponent(AddToListMenu, { props: { releaseId: 'r1' } })
    await openMenu(wrapper.find('button').element)
    await select(items('[data-testid="add-to-list-item"]')[0]!)
    await vi.waitFor(() => expect(toast.error).toHaveBeenCalledWith('Broken'))
  })

  it('opens the new-list page with the release, item and way back', async () => {
    mockApi({ 'GET /api/lists': [] })
    const { wrapper, router } = await renderComponent(AddToListMenu, {
      props: { releaseId: 'r1', itemId: 'i1' },
      url: '/l/lib1?item=i1',
    })
    await openMenu(wrapper.find('button').element)
    expect(pageText()).toContain('No lists yet')
    await select(items('[data-testid="add-to-new-list"]')[0]!)
    await vi.waitFor(() => expect(router.currentRoute.value.name).toBe('list-new'))
    expect(router.currentRoute.value.query).toEqual({
      release: 'r1',
      item: 'i1',
      back: '/l/lib1?item=i1',
    })
  })

  it('leaves out the item when there is none', async () => {
    mockApi({ 'GET /api/lists': lists })
    const { wrapper, router } = await renderComponent(AddToListMenu, {
      props: { releaseId: 'r1' },
      url: '/lists',
    })
    await openMenu(wrapper.find('button').element)
    await select(items('[data-testid="add-to-new-list"]')[0]!)
    await vi.waitFor(() => expect(router.currentRoute.value.name).toBe('list-new'))
    expect(router.currentRoute.value.query).toEqual({ release: 'r1', back: '/lists' })
  })

  it('accepts a custom trigger in the slot', async () => {
    mockApi({ 'GET /api/lists': lists })
    const Host = defineComponent({
      render: () =>
        h(
          AddToListMenu,
          { releaseId: 'r1' },
          { default: () => h('button', { id: 'mine' }, 'Mine') },
        ),
    })
    const { wrapper } = await renderComponent(Host)
    expect(wrapper.find('#mine').exists()).toBe(true)
    expect(wrapper.find('[data-testid="add-to-list"]').exists()).toBe(false)
    await openMenu(wrapper.find('#mine').element as HTMLElement)
    expect(pageText()).toContain('Wishlist')
  })
})
