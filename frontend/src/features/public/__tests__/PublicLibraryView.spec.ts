import { describe, expect, it, vi } from 'vitest'
import { Select } from '@/components/ui/select'
import { mockApi, pageText, renderApp, settle, type ApiCall } from '@/test/utils'
import { item } from './fixtures'

function last(calls: ApiCall[]): ApiCall {
  return calls[calls.length - 1]!
}

const LIB = { name: 'Max’s games', description: 'All my handhelds', owner: 'max', item_count: 3 }
const TREE = {
  total: 3,
  group_by: ['platform.name'],
  nodes: [
    { field: 'platform.name', key: 'nds', label: 'Nintendo DS', count: 2, children: [] },
    { field: 'platform.name', key: 'none', label: '', count: 1, children: [] },
  ],
}

describe('PublicLibraryView', () => {
  it('shows the shared library without login', async () => {
    mockApi({
      'GET /api/public/libraries/tok': LIB,
      'GET /api/public/libraries/tok/tree': TREE,
      'GET /api/public/libraries/tok/items': {
        count: 2,
        items: [
          item('a', 'Mario Kart DS', { release_date: null }),
          { ...item('b', 'Zelda'), cover_url: '/media/zelda.jpg' },
        ],
      },
    })
    const { router, wrapper } = await renderApp('/share/tok', { user: null })
    expect(router.currentRoute.value.name).toBe('public-library')
    expect(wrapper.find('h1').text()).toBe('Max’s games')
    expect(pageText()).toContain('All my handhelds')
    expect(pageText()).toContain('Shared by max')
    expect(pageText()).toContain('3 games')
    const folders = wrapper.findAll('[data-testid="folder"]')
    expect(folders.map((f) => f.text())).toEqual(['Nintendo DS 2', 'Not set 1'])
    const cards = wrapper.findAll('[data-testid="public-item"]')
    expect(cards).toHaveLength(2)
    expect(cards[1]!.text()).toContain('Zelda')
    expect(cards[1]!.text()).toContain('NDS')
    expect(cards[1]!.find('[data-testid="public-item-date"]').text()).toBe('05/15/2006')
    expect(cards[1]!.find('img').attributes('src')).toBe('/media/zelda.jpg')
    // the copy's title, not the catalog title; no date when the release has none
    expect(cards[0]!.text()).not.toContain('Catalog')
    expect(cards[0]!.find('[data-testid="public-item-date"]').exists()).toBe(false)
    expect(wrapper.find('[data-testid="showing"]').text()).toBe('2 of 2')
    expect(wrapper.find('[data-testid="load-more"]').exists()).toBe(false)
  })

  it('filters by folder, regroups and filters titles on the client', async () => {
    const calls = mockApi({
      'GET /api/public/libraries/tok': LIB,
      'GET /api/public/libraries/tok/tree': TREE,
      'GET /api/public/libraries/tok/items': {
        count: 2,
        items: [item('a', 'Mario Kart DS'), item('b', 'Zelda')],
      },
    })
    const { wrapper } = await renderApp('/share/tok', { user: null })
    await wrapper.findAll('[data-testid="folder"]')[0]!.trigger('click')
    await settle()
    const itemCalls = () => calls.filter((c) => c.path.endsWith('/items'))
    expect(last(itemCalls()).query.getAll('filter')).toEqual(['platform.name:nds'])
    expect(last(itemCalls()).query.get('sort')).toBe('game.title')
    expect(wrapper.findAll('[data-testid="folder"]')[0]!.attributes('aria-pressed')).toBe('true')

    await wrapper.find('[data-testid="title-filter"]').setValue('zel')
    expect(wrapper.findAll('[data-testid="public-item"]')).toHaveLength(1)
    await wrapper.find('[data-testid="title-filter"]').setValue('xyz')
    expect(pageText()).toContain('No loaded game matches "xyz".')
    await wrapper.find('[data-testid="title-filter"]').setValue('')

    wrapper.findComponent(Select).vm.$emit('update:modelValue', 'game.genres')
    await settle()
    const treeCalls = calls.filter((c) => c.path.endsWith('/tree'))
    expect(last(treeCalls).query.getAll('group_by')).toEqual(['game.genres'])
    expect(last(itemCalls()).query.getAll('filter')).toEqual([])

    await wrapper.findAll('[data-testid="folder"]')[1]!.trigger('click')
    await settle()
    expect(last(itemCalls()).query.getAll('filter')).toEqual(['game.genres:none'])
    await wrapper.find('[data-testid="folders"] button').trigger('click')
    await settle()
    expect(last(itemCalls()).query.getAll('filter')).toEqual([])
  })

  it('loads more items page by page', async () => {
    const calls = mockApi({
      'GET /api/public/libraries/tok': LIB,
      'GET /api/public/libraries/tok/tree': TREE,
      'GET /api/public/libraries/tok/items': ({ query }: ApiCall) =>
        query.get('offset') === '0'
          ? { count: 3, items: [item('a', 'A'), item('b', 'B')] }
          : { count: 3, items: [item('c', 'C')] },
    })
    const { wrapper } = await renderApp('/share/tok', { user: null })
    expect(wrapper.find('[data-testid="showing"]').text()).toBe('2 of 3')
    await wrapper.find('[data-testid="load-more"]').trigger('click')
    await vi.waitFor(() => expect(wrapper.findAll('[data-testid="public-item"]')).toHaveLength(3))
    expect(last(calls.filter((c) => c.path.endsWith('/items'))).query.get('offset')).toBe('2')
    expect(wrapper.find('[data-testid="load-more"]').exists()).toBe(false)
  })

  it('shows an empty library', async () => {
    mockApi({
      'GET /api/public/libraries/tok': { ...LIB, description: '', item_count: 0 },
      'GET /api/public/libraries/tok/tree': { total: 0, group_by: ['platform.name'], nodes: [] },
      'GET /api/public/libraries/tok/items': { count: 0, items: [] },
    })
    await renderApp('/share/tok', { user: null })
    expect(pageText()).toContain('No games here.')
  })

  it('explains invalid links', async () => {
    mockApi({})
    await renderApp('/share/gone', { user: null })
    expect(pageText()).toContain('This link is no longer valid')
  })

  it('shows other errors inline', async () => {
    mockApi({
      'GET /api/public/libraries/tok': { status: 500, body: { detail: 'Header broke' } },
      'GET /api/public/libraries/tok/tree': TREE,
      'GET /api/public/libraries/tok/items': { status: 500, body: { detail: 'Items broke' } },
    })
    await renderApp('/share/tok', { user: null })
    expect(pageText()).toContain('Header broke')
    expect(pageText()).toContain('Items broke')
  })
})
