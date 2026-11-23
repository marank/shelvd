import { afterEach, describe, expect, it, vi } from 'vitest'
import { toast } from 'vue-sonner'
import PlatformBadge from '@/components/app/PlatformBadge.vue'
import type { Platform } from '@/api/types'
import { layoutRoutes, makeLibrary } from '@/test/fixtures'
import { mount } from '@vue/test-utils'
import { mockApi, pageText, renderApp, settle } from '@/test/utils'

vi.mock('vue-sonner', () => ({
  toast: {
    success: vi.fn<(message: string) => void>(),
    error: vi.fn<(message: string) => void>(),
  },
}))

const q = (selector: string) => document.querySelector(selector) as HTMLElement
const qa = (selector: string) => [...document.querySelectorAll<HTMLElement>(selector)]
const input = async (selector: string, value: string) => {
  const el = q(selector) as HTMLInputElement
  el.value = value
  el.dispatchEvent(new Event('input'))
  await settle()
}

function platform(overrides: Partial<Platform> = {}): Platform {
  return {
    id: 'p-1',
    name: 'Nintendo Switch',
    short_name: 'Switch',
    slug: 'switch',
    manufacturer: 'Nintendo',
    media_type: 'game',
    release_year: 2017,
    color: '',
    icon: '',
    icon_url: null,
    icon_dark: false,
    ...overrides,
  }
}
const pocket = platform({ id: 'p-2', name: 'Analogue Pocket', short_name: 'Pocket', manufacturer: 'Analogue', slug: 'pocket', release_year: 2021, color: '#112233', icon: 'handheld' }) // prettier-ignore
const page = {
  image_url: null,
  description: '',
  description_language: '',
  descriptions: {},
  generation: null,
  discontinued: null,
  manufacturer_company: null,
  predecessors: [],
  successors: [],
  can_describe: false,
}
const detail = { ...platform(), ...page, igdb_id: 130, release_count: 3 }
const routes = (extra: Record<string, unknown> = {}) => ({
  ...layoutRoutes(makeLibrary()),
  'GET /api/catalog/platforms': [
    {
      ...platform(),
      image_url: null,
      photo_url: '/p.jpg',
      generation: 8,
      discontinued: null,
      game_count: 12,
    },
    {
      ...pocket,
      image_url: '/logo.svg',
      photo_url: null,
      generation: null,
      discontinued: 2024,
      game_count: 3,
    },
  ],
  'GET /api/catalog/platforms/:id': detail,
  ...extra,
})

describe('PlatformBadge', () => {
  it('shows an uploaded icon, else the symbol in its colour, else a dot', async () => {
    const wrapper = mount(PlatformBadge, {
      props: { platform: platform({ icon_url: '/media/platforms/p-1.svg', icon: 'console' }) },
    })
    expect(wrapper.find('[data-testid="platform-icon"]').attributes('src')).toBe(
      '/media/platforms/p-1.svg',
    )
    expect(wrapper.find('[data-testid="platform-symbol"]').exists()).toBe(false)
    // Only a dark mark is inverted on dark backgrounds.
    expect(wrapper.find('[data-testid="platform-icon"]').classes()).not.toContain('dark:invert')
    await wrapper.setProps({
      platform: platform({ icon_url: '/media/platforms/p-1.svg', icon_dark: true }),
    })
    expect(wrapper.find('[data-testid="platform-icon"]').classes()).toContain('dark:invert')
    await wrapper.setProps({ platform: pocket })
    const symbol = wrapper.find('[data-testid="platform-symbol"]')
    expect(symbol.attributes('style')).toContain('color: rgb(17, 34, 51)')
    await wrapper.setProps({ platform: platform() })
    expect(wrapper.find('svg').exists()).toBe(false)
    expect(wrapper.text()).toBe('Switch')
  })
})

describe('platforms', () => {
  afterEach(() => vi.clearAllMocks())

  it('lists platforms by manufacturer and searches them', async () => {
    mockApi(routes())
    await renderApp('/catalog/platforms')
    await vi.waitFor(() => expect(qa('[data-testid="platform-row"]')).toHaveLength(2))
    expect(q('[data-testid="maker-Nintendo"]').textContent).toContain('Nintendo Switch')
    expect(q('[data-testid="maker-Analogue"]').textContent).toContain('Pocket · Game')
    expect(q('[data-testid="maker-Analogue"]').textContent).toContain('2021')
    await input('[data-testid="platform-search"]', 'pocket')
    expect(qa('[data-testid="platform-row"]')).toHaveLength(1)
    await input('[data-testid="platform-search"]', 'zzz')
    expect(pageText()).toContain('No platform found.')
    expect(q('[data-testid="nav-platforms"]').getAttribute('href')).toBe('/catalog/platforms')

    // Tiles: a photo of the device, else the logo, else its mark; the choice is kept.
    await input('[data-testid="platform-search"]', '')
    q('[data-testid="platform-layout-tiles"]').click()
    await settle()
    expect(qa('[data-testid="platform-tile"]')).toHaveLength(2)
    expect(q('[data-testid="platform-tile-photo"]').getAttribute('src')).toBe('/p.jpg')
    expect(q('[data-testid="maker-Analogue"]').textContent).toContain('3 games')
    expect(localStorage.getItem('shelvd.platform-layout')).toBe('"tiles"')
    q('[data-testid="platform-layout-table"]').click()
    await settle()
    expect(qa('[data-testid="platform-row"]')).toHaveLength(2)
  })

  it('edits colour, symbol and IGDB id; can’t delete a platform in use', async () => {
    const calls = mockApi(routes({ 'PATCH /api/catalog/platforms/:id': detail }))
    const { router } = await renderApp('/catalog/platforms/p-1/edit')
    await vi.waitFor(() =>
      expect((q('[data-testid="platform-name"]') as HTMLInputElement).value).toBe(
        'Nintendo Switch',
      ),
    )
    expect((q('#platform-igdb') as HTMLInputElement).value).toBe('130')
    expect((q('[data-testid="platform-delete"]') as HTMLButtonElement).disabled).toBe(true)

    const color = q('[data-testid="platform-color"]') as HTMLInputElement
    color.value = '#ff0000'
    color.dispatchEvent(new Event('input'))
    await settle()
    q('[data-testid="icon-disc"]').click()
    await settle()
    expect(q('[data-testid="icon-disc"]').getAttribute('aria-checked')).toBe('true')
    const preview = q('[data-testid="platform-preview"] [data-testid="platform-symbol"]')
    expect(preview.getAttribute('style')).toContain('color: rgb(255, 0, 0)')
    expect(q('[data-testid="platform-color-reset"]').textContent).toContain('Manufacturer colour')
    await input('#platform-igdb', '')

    q('[data-testid="edit-save"]').click()
    await vi.waitFor(() => expect(router.currentRoute.value.name).toBe('platforms'))
    const body = calls.find((c) => c.method === 'PATCH')!.body as Record<string, unknown>
    expect(body).toMatchObject({
      color: '#ff0000',
      icon: 'disc',
      igdb_id: null,
      release_year: 2017,
    })
    expect(toast.success).toHaveBeenCalledWith('Nintendo Switch saved')
  })

  it('uploads and removes an own icon, and deletes an unused platform', async () => {
    const unused = { ...detail, release_count: 0, icon_url: '/media/platforms/p-1.png' }
    const calls = mockApi(
      routes({
        'GET /api/catalog/platforms/:id': unused,
        'POST /api/catalog/platforms/:id/icon': unused,
        'DELETE /api/catalog/platforms/:id/icon': { ...unused, icon_url: null },
        'DELETE /api/catalog/platforms/:id': { status: 204 },
      }),
    )
    const { router } = await renderApp('/catalog/platforms/p-1/edit')
    await vi.waitFor(() => expect(q('[data-testid="platform-own-icon"]')).not.toBeNull())
    const file = q('[data-testid="platform-icon-file"]') as HTMLInputElement
    Object.defineProperty(file, 'files', { value: [new File(['<svg/>'], 'icon.svg')] })
    file.dispatchEvent(new Event('change'))
    await vi.waitFor(() => expect(toast.success).toHaveBeenCalledWith('Icon uploaded'))
    expect(calls.some((c) => c.method === 'POST' && c.path.endsWith('/icon'))).toBe(true)

    q('[data-testid="platform-icon-remove"]').click()
    await vi.waitFor(() =>
      expect(calls.some((c) => c.method === 'DELETE' && c.path.endsWith('/icon'))).toBe(true),
    )

    q('[data-testid="platform-delete"]').click()
    await settle()
    q('[data-testid="confirm-button"]').click()
    await vi.waitFor(() => expect(router.currentRoute.value.name).toBe('platforms'))
    expect(toast.success).toHaveBeenCalledWith('Nintendo Switch deleted')
  })

  it('creates a platform, then stays on it for the icon', async () => {
    const calls = mockApi(
      routes({
        'POST /api/catalog/platforms': { ...detail, id: 'p-9', name: 'Analogue Pocket' },
      }),
    )
    const { router } = await renderApp('/catalog/platforms/new')
    await vi.waitFor(() => expect(q('[data-testid="platform-name"]')).not.toBeNull())
    expect(pageText()).toContain('You can upload an icon of your own once the platform exists.')
    q('[data-testid="edit-save"]').click()
    await settle()
    expect(q('[data-testid="edit-error"]').textContent).toContain('Enter a name.')
    await input('[data-testid="platform-name"]', 'Analogue Pocket')
    await input('[data-testid="platform-manufacturer"]', 'Analogue')
    q('[data-testid="edit-save"]').click()
    await vi.waitFor(() =>
      expect(router.currentRoute.value.path).toBe('/catalog/platforms/p-9/edit'),
    )
    expect(calls.find((c) => c.method === 'POST')!.body).toMatchObject({
      name: 'Analogue Pocket',
      manufacturer: 'Analogue',
      color: '',
      icon: '',
      igdb_id: null,
      release_year: null,
    })
  })

  it('shows the server’s error when saving fails', async () => {
    mockApi(
      routes({
        'PATCH /api/catalog/platforms/:id': {
          status: 409,
          body: { detail: 'A platform with this name already exists.' },
        },
      }),
    )
    await renderApp('/catalog/platforms/p-1/edit')
    await vi.waitFor(() => expect(q('[data-testid="platform-name"]')).not.toBeNull())
    q('[data-testid="edit-save"]').click()
    await vi.waitFor(() =>
      expect(q('[data-testid="edit-error"]').textContent).toContain('already exists'),
    )
  })
})

describe('libraries overview', () => {
  it('lists libraries with their settings and offers a new one', async () => {
    mockApi({
      ...layoutRoutes(makeLibrary()),
      'GET /api/libraries': [
        makeLibrary(),
        makeLibrary({ id: 'lib-2', name: 'Bobs Regal', role: 'viewer', owner: 'bob', public_token: 'x' }),
      ],
    }) // prettier-ignore
    await renderApp('/libraries')
    await vi.waitFor(() => expect(qa('[data-testid="library-row"]')).toHaveLength(2))
    expect(qa('[data-testid="library-row"]')[1]!.textContent).toContain('Can view · bob')
    expect(qa('[data-testid="library-row"]')[1]!.textContent).toContain('Public')
    expect(q('[data-testid="library-settings-lib-2"]').getAttribute('href')).toBe(
      '/l/lib-2/settings',
    )
    expect(q('[data-testid="library-new"]').getAttribute('href')).toBe('/?new=1')
    expect(q('[data-testid="nav-libraries"]').getAttribute('href')).toBe('/libraries')
  })
})
