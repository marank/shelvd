import { describe, expect, it } from 'vitest'
import { mockApi, pageText, renderApp } from '@/test/utils'
import { entry } from './fixtures'

describe('PublicListView', () => {
  it('shows a shared list read-only, ordered by position', async () => {
    mockApi({
      'GET /api/public/lists/tok': {
        name: 'Top 3',
        description: 'Best DS games',
        owner: 'max',
        entries: [entry('b', 'Zelda', 2), entry('a', 'Mario Kart', 1, 'Endless fun')],
      },
    })
    const { wrapper, router } = await renderApp('/share/list/tok', { user: null })
    expect(router.currentRoute.value.name).toBe('public-list')
    expect(wrapper.find('h1').text()).toBe('Top 3')
    expect(pageText()).toContain('Best DS games')
    expect(pageText()).toContain('Shared by max')
    const rows = wrapper.findAll('[data-testid="public-entry"]')
    expect(rows.map((r) => r.text())).toEqual([
      expect.stringContaining('Mario Kart'),
      expect.stringContaining('Zelda'),
    ])
    expect(rows[0]!.text()).toContain('Endless fun')
    expect(rows[0]!.text()).toContain('NDS')
    expect(rows[0]!.find('[data-testid="public-entry-date"]').text()).toBe('05/15/2006')
    expect(wrapper.find('input').exists()).toBe(false)
    expect(wrapper.find('button').exists()).toBe(false)
  })

  it('shows an empty list', async () => {
    mockApi({
      'GET /api/public/lists/tok': { name: 'Nothing', description: '', owner: 'max', entries: [] },
    })
    await renderApp('/share/list/tok', { user: null })
    expect(pageText()).toContain('This list is empty.')
  })

  it('explains invalid links', async () => {
    mockApi({})
    await renderApp('/share/list/gone', { user: null })
    expect(pageText()).toContain('This link is no longer valid')
  })

  it('shows other errors', async () => {
    mockApi({ 'GET /api/public/lists/tok': { status: 500, body: { detail: 'Oops' } } })
    await renderApp('/share/list/tok', { user: null })
    expect(pageText()).toContain('Oops')
  })
})
