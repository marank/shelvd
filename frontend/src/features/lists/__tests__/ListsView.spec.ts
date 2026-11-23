import { describe, expect, it, vi } from 'vitest'
import { mockApi, pageText, renderComponent } from '@/test/utils'
import ListsView from '../views/ListsView.vue'
import { list } from './fixtures'

describe('ListsView', () => {
  it('shows an explanatory empty state', async () => {
    mockApi({ 'GET /api/lists': [] })
    await renderComponent(ListsView, { url: '/lists' })
    expect(pageText()).toContain('No lists yet')
    expect(pageText()).toContain('wishlist')
  })

  it('shows lists as cards with a public badge', async () => {
    mockApi({
      'GET /api/lists': [
        list('l1', 'Wishlist', { entry_count: 3, description: 'Things I want' }),
        list('l2', 'Top 10', { public_token: 'tok', entry_count: 1 }),
      ],
    })
    const { wrapper } = await renderComponent(ListsView, { url: '/lists' })
    const cards = wrapper.findAll('[data-testid="list-card"]')
    expect(cards).toHaveLength(2)
    expect(cards[0]!.text()).toContain('Wishlist')
    expect(cards[0]!.text()).toContain('3 entries')
    expect(cards[0]!.text()).toContain('Things I want')
    expect(cards[0]!.find('[data-testid="public-badge"]').exists()).toBe(false)
    expect(cards[1]!.find('[data-testid="public-badge"]').exists()).toBe(true)
    expect(cards[1]!.text()).toContain('1 entry')
    expect(cards[1]!.attributes('href')).toBe('/lists/l2')
  })

  it('shows an error when loading fails', async () => {
    mockApi({ 'GET /api/lists': { status: 500, body: { detail: 'Boom' } } })
    await renderComponent(ListsView, { url: '/lists' })
    expect(pageText()).toContain('Boom')
  })

  it('links to the page for a new list from the header and the empty state', async () => {
    mockApi({ 'GET /api/lists': [] })
    const { wrapper, router } = await renderComponent(ListsView, { url: '/lists' })
    expect(wrapper.find('[data-testid="new-list"]').attributes('href')).toBe('/lists/new')
    expect(wrapper.find('[data-testid="new-list-empty"]').attributes('href')).toBe('/lists/new')
    await wrapper.find('[data-testid="new-list-empty"]').trigger('click')
    await vi.waitFor(() => expect(router.currentRoute.value.name).toBe('list-new'))
  })
})
