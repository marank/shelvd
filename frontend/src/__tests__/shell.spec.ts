import { describe, expect, it, vi } from 'vitest'
import CoverImage from '@/components/app/CoverImage.vue'
import { layoutRoutes, makeLibrary, makeOverview } from '@/test/fixtures'
import { mockApi, pageText, renderApp, renderComponent, settle } from '@/test/utils'
import { useAuthStore } from '@/stores/auth'
import { useUiStore } from '@/stores/ui'

const tree = {
  total: 1,
  group_by: ['platform', 'year'],
  nodes: [
    {
      field: 'platform',
      key: 'sw',
      label: 'Nintendo Switch',
      count: 1,
      children: [{ field: 'year', key: '2017', label: '2017', count: 1, children: [] }],
    },
    { field: 'platform', key: 'none', label: '', count: 2, children: [] },
  ],
}

function routes(extra: Record<string, unknown> = {}) {
  return {
    ...layoutRoutes(makeLibrary(), [
      makeOverview({ group_by: ['platform', 'year'] }),
      makeOverview({ id: 'o2', name: 'Flat', group_by: [] }),
    ]),
    'GET /api/libraries/lib-1/tree': tree,
    'GET /api/libraries/lib-1/items': { count: 0, items: [] },
    ...extra,
  }
}

function openMenu(testId: string) {
  document
    .querySelector(`[data-testid="${testId}"]`)!
    .dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', bubbles: true }))
}

function menuItem(text: string): HTMLElement {
  return [...document.querySelectorAll('[role="menuitem"], [role="menuitemradio"]')].find((el) =>
    el.textContent.includes(text),
  ) as HTMLElement
}

describe('app shell', () => {
  it('navigates the sidebar tree and overviews', async () => {
    mockApi(routes())
    const { router } = await renderApp('/l/lib-1')
    await vi.waitFor(() =>
      expect(document.querySelector('[data-testid="sidebar-tree"]')).not.toBeNull(),
    )
    const sidebar = document.querySelector('[data-testid="sidebar-tree"]')!
    expect(sidebar.textContent).toContain('Not set')
    const expand = sidebar.querySelector('button[aria-expanded]') as HTMLElement
    expand.click()
    await settle()
    expect(sidebar.textContent).toContain('2017')
    ;(
      [...sidebar.querySelectorAll('button')].find((b) => b.textContent === '2017') as HTMLElement
    ).click()
    await settle()
    expect(router.currentRoute.value.query.p).toEqual(['sw', '2017'])
    expand.click()
    await settle()
    expect(sidebar.textContent).not.toContain('2017')

    ;(
      [...document.querySelectorAll('[data-sidebar="menu-button"]')].find((b) =>
        b.textContent.includes('Flat'),
      ) as HTMLElement
    ).click()
    await settle()
    expect(router.currentRoute.value.query.v).toBe('o2')

    // From another page, opening a folder goes back to the explorer.
    await router.push('/lists')
    await settle()
    await router.push({
      name: 'explorer',
      params: { libraryId: 'lib-1' },
      query: { g: 'platform,year' },
    })
    await settle()
    expect(router.currentRoute.value.query.g).toBe('platform,year')
  })

  it('switches libraries, theme, language and logs out', async () => {
    mockApi(
      routes({
        'GET /api/libraries': [
          makeLibrary(),
          makeLibrary({ id: 'lib-2', name: 'Filme', role: 'viewer' }),
        ],
        'POST /api/auth/logout': { status: 204 },
      }),
    )
    const { router } = await renderApp('/l/lib-1')
    openMenu('library-switcher')
    await settle()
    menuItem('Filme').click()
    await vi.waitFor(() => expect(router.currentRoute.value.params.libraryId).toBe('lib-2'))

    openMenu('library-switcher')
    await settle()
    menuItem('New library').click()
    await vi.waitFor(() => expect(router.currentRoute.value.query.new).toBe('1'))

    openMenu('user-menu')
    await settle()
    menuItem('Dark').click()
    await settle()
    expect(useUiStore().theme).toBe('dark')
    openMenu('user-menu')
    await settle()
    menuItem('Deutsch').click()
    await settle()
    expect(pageText()).toContain('Verwalten')
    openMenu('user-menu')
    await settle()
    menuItem('English').click()
    await settle()

    openMenu('user-menu')
    await settle()
    menuItem('Log out').click()
    await vi.waitFor(() => expect(router.currentRoute.value.name).toBe('login'))
    expect(useAuthStore().user).toBeNull()
  })

  it('adds onto Upcoming when on Upcoming', async () => {
    mockApi(routes({ 'GET /api/watchlist': [] }))
    await renderApp('/upcoming')
    await vi.waitFor(() =>
      expect(document.querySelector('[data-testid="add-button"]')).not.toBeNull(),
    )
    ;(document.querySelector('[data-testid="add-button"]') as HTMLElement).click()
    expect(useUiStore().addDestination).toBe('track')
    expect(document.querySelectorAll('[data-testid="add-button"]')).toHaveLength(1)
  })

  it('searches from the topbar on any page', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true })
    mockApi(routes({ 'GET /api/lists': [] }))
    const { router } = await renderApp('/lists')
    const input = document.querySelector('[data-testid="global-search"]') as HTMLInputElement
    document.body.dispatchEvent(new KeyboardEvent('keydown', { key: '/', bubbles: true }))
    expect(document.activeElement).toBe(input)
    input.value = 'zelda'
    input.dispatchEvent(new Event('input'))
    await vi.advanceTimersByTimeAsync(300)
    await settle()
    expect(router.currentRoute.value.name).toBe('explorer')
    expect(router.currentRoute.value.query.q).toBe('zelda')

    input.value = 'mario'
    input.dispatchEvent(new Event('input'))
    await vi.advanceTimersByTimeAsync(300)
    await settle()
    expect(router.currentRoute.value.query.q).toBe('mario')
    ;(document.querySelector('[aria-label="Close"]') as HTMLElement).click()
    await vi.advanceTimersByTimeAsync(300)
    await settle()
    expect(router.currentRoute.value.query.q).toBeUndefined()
    input.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }))

    // "/" typed inside an input is just a character.
    input.dispatchEvent(new KeyboardEvent('keydown', { key: '/', bubbles: true }))
    ;(document.querySelector('[data-testid="add-button"]') as HTMLElement).click()
    expect(useUiStore().addMode).toBe('search')
    // Outside Upcoming the dialog decides by the release itself.
    expect(useUiStore().addDestination).toBeNull()
    vi.useRealTimers()
  })

  it('creates the first library on the home page', async () => {
    const created = makeLibrary({ id: 'new-lib' })
    const calls = mockApi({
      'GET /api/libraries': [],
      'POST /api/libraries': { status: 201, body: created },
      'GET /api/libraries/new-lib': created,
      'GET /api/libraries/new-lib/overviews': [],
      'GET /api/libraries/new-lib/tree': { total: 0, group_by: [], nodes: [] },
      'GET /api/libraries/new-lib/items': { count: 0, items: [] },
      'GET /api/catalog/platforms': [],
    })
    const { router } = await renderApp('/')
    await vi.waitFor(() => expect(pageText()).toContain('Welcome to shelvd'))
    const form = document.querySelector('[data-testid="library-name"]')!.closest('form')!
    form.dispatchEvent(new Event('submit'))
    await vi.waitFor(() => expect(router.currentRoute.value.params.libraryId).toBe('new-lib'))
    expect(calls.find((c) => c.method === 'POST')!.body).toEqual({
      name: 'My games',
      description: '',
    })
    expect(pageText()).toContain('All items')
  })

  it('redirects home to the remembered library and shows 404s', async () => {
    mockApi(routes())
    localStorage.setItem('shelvd.library', 'lib-1')
    const { router } = await renderApp('/')
    await vi.waitFor(() => expect(router.currentRoute.value.name).toBe('explorer'))
    await router.push('/does/not/exist')
    await vi.waitFor(() => expect(pageText()).toContain('404'))
  })

  it('shows covers uncropped in their own aspect ratio', async () => {
    const natural = await renderComponent(CoverImage, {
      props: { src: '/media/ds.jpg', title: 'Zelda', aspect: 1.12 },
    })
    const cover = natural.wrapper.find('[data-testid="cover"]')
    expect(cover.attributes('style')).toContain('aspect-ratio: 1.12')
    expect(cover.find('img').classes()).toContain('object-contain')

    const box = await renderComponent(CoverImage, {
      props: { src: '/media/ds.jpg', title: 'Zelda', aspect: 1.12, fit: 'box' },
    })
    expect(box.wrapper.find('[data-testid="cover"]').attributes('style')).toContain(
      'aspect-ratio: 1 / 1',
    )

    const unknown = await renderComponent(CoverImage, {
      props: { src: '/media/x.jpg', title: 'X', sizeBy: 'height' },
    })
    expect(unknown.wrapper.find('[data-testid="cover"]').attributes('style')).toBeUndefined()
    expect(unknown.wrapper.find('img').classes()).toContain('w-auto')
    const width = await renderComponent(CoverImage, { props: { src: '/media/x.jpg', title: 'X' } })
    expect(width.wrapper.find('img').classes()).toContain('h-auto')
  })

  it('renders a cover or a placeholder', async () => {
    const { wrapper } = await renderComponent(CoverImage, {
      props: { src: '/media/c.jpg', title: 'Super Mario Odyssey', manufacturer: 'Nintendo' },
    })
    const img = wrapper.find('img')
    expect(img.attributes('src')).toBe('/media/c.jpg')
    await img.trigger('error')
    expect(wrapper.find('[data-testid="cover-placeholder"]').text()).toBe('SM')
  })
})
