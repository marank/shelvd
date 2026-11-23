import { afterEach, describe, expect, it, vi } from 'vitest'
import { toast } from 'vue-sonner'
import { fieldLinks } from '@/lib/itemFields'
import { layoutRoutes, makeLibrary, switchPlatform } from '@/test/fixtures'
import { mockApi, pageText, renderApp, settle } from '@/test/utils'

vi.mock('vue-sonner', () => ({
  toast: {
    success: vi.fn<(message: string) => void>(),
    error: vi.fn<(message: string) => void>(),
    warning: vi.fn<(message: string) => void>(),
  },
}))

const q = (selector: string) => document.querySelector(selector) as HTMLElement
const qa = (selector: string) => [...document.querySelectorAll<HTMLElement>(selector)]
const ref = (id: string, name: string, short_name: string) => ({
  id,
  name,
  short_name,
  manufacturer: 'Nintendo',
  color: '',
  icon: '',
  icon_url: null,
})
const switchPage = {
  ...switchPlatform,
  igdb_id: 130,
  release_count: 2,
  image_url: '/media/platforms/p-switch-picture.svg',
  photo_url: null as string | null,
  description: 'A hybrid console.',
  description_language: 'en',
  descriptions: { en: 'A hybrid console.' },
  generation: 8,
  discontinued: 2025,
  manufacturer_company: { id: 'c-nin', name: 'Nintendo' },
  predecessors: [ref('p-wiiu', 'Nintendo Wii U', 'Wii U')],
  successors: [ref('p-s2', 'Nintendo Switch 2', 'Switch 2')],
  can_describe: true,
}
const work = (id: string, title: string, year: number | null) => ({
  id,
  title,
  year,
  cover_url: null,
  cover_aspect: null,
  manufacturer: 'Nintendo',
  platforms: [switchPlatform],
})
const games = {
  works: [work('w-zelda', 'Zelda', 2017), work('w-astral', 'Astral Chain', 2019)],
  related: [{ kind: 'genres', id: 'g-adv', name: 'Adventure', count: 2 }],
}
const providers = [
  { name: 'wikipedia', label: 'Wikipedia', kind: 'metadata', enabled: true },
  { name: 'igdb', label: 'IGDB', kind: 'metadata', enabled: true },
]
const routes = (extra: Record<string, unknown> = {}) => ({
  ...layoutRoutes(makeLibrary()),
  'GET /api/catalog/platforms': [switchPlatform, ref('p-wiiu', 'Nintendo Wii U', 'Wii U')],
  'GET /api/catalog/platforms/:id': switchPage,
  'GET /api/catalog/platforms/:id/games': games,
  'GET /api/lookup/providers': providers,
  'GET /api/libraries/lib-1/owned': [{ release_id: 'r-z', work_id: 'w-zelda', copies: 1 }],
  ...extra,
})
const openMenu = async () => {
  await vi.waitFor(() => expect(q('[data-testid="platform-menu"]')).not.toBeNull())
  q('[data-testid="platform-menu"]').dispatchEvent(
    new KeyboardEvent('keydown', { key: 'Enter', bubbles: true }),
  )
}

describe('platform page', () => {
  afterEach(() => vi.clearAllMocks())

  it('shows facts, description, neighbours and games', async () => {
    mockApi(routes())
    const { router } = await renderApp(`/platforms/${switchPlatform.id}`)
    await vi.waitFor(() => expect(q('[data-testid="platform-description"]')).not.toBeNull())
    expect(q('[data-testid="term-image"] img').getAttribute('src')).toBe(switchPage.image_url)
    const text = pageText()
    expect(text).toContain('Generation')
    expect(text).toContain('2017–2025')
    expect(q('[data-testid="platform-description"]').textContent).toContain('A hybrid console.')
    expect(q('[data-testid="platform-manufacturer"]').getAttribute('href')).toBe('/companies/c-nin')
    expect(q('[data-testid="platform-predecessors"] a').getAttribute('href')).toBe(
      '/platforms/p-wiiu',
    )
    expect(q('[data-testid="platform-successors"]').textContent).toContain('Switch 2')
    expect(q('[data-testid="platform-related"]').textContent).toContain('Adventure')
    const titles = () =>
      qa('[data-testid="term-work"] p.font-medium').map((p) => p.textContent.trim())
    expect(titles()).toEqual(['Zelda', 'Astral Chain'])
    q('[data-testid="platform-sort-title"]').click()
    await settle()
    expect(titles()).toEqual(['Astral Chain', 'Zelda'])
    q('[data-testid="platform-only-owned"]').click()
    await settle()
    expect(titles()).toEqual(['Zelda'])

    await openMenu()
    await vi.waitFor(() => expect(q('[data-testid="platform-describe-wikipedia"]')).not.toBeNull())
    expect(q('[data-testid="platform-describe-igdb"]').getAttribute('href')).toBe(
      `/platforms/${switchPlatform.id}/description/igdb`,
    )
    expect(q('[data-testid="platform-edit"]').getAttribute('href')).toContain(
      `/catalog/platforms/${switchPlatform.id}/edit?back=`,
    )
    q('[data-testid="platform-choose-image"]').click()
    await vi.waitFor(() => expect(router.currentRoute.value.name).toBe('platforms-image'))
  })

  it('offers sources while there is no description, and says when it has no games', async () => {
    mockApi(
      routes({
        'GET /api/catalog/platforms/:id': {
          ...switchPage,
          description: '',
          descriptions: {},
          image_url: null,
          generation: null,
          discontinued: null,
          manufacturer: '',
          manufacturer_company: null,
          predecessors: [],
          successors: [],
        },
        'GET /api/catalog/platforms/:id/games': { works: [], related: [] },
      }),
    )
    await renderApp(`/platforms/${switchPlatform.id}`)
    await vi.waitFor(() => expect(q('[data-testid="platform-unused"]')).not.toBeNull())
    expect(q('[data-testid="platform-facts"]')).toBeNull()
    expect(qa('[data-testid^="platform-describe-empty-"]')).toHaveLength(2)
    expect(q('[data-testid="platform-add-description"]')).not.toBeNull()
  })

  it('takes a description and a picture or an icon', async () => {
    const calls = mockApi(
      routes({
        'GET /api/catalog/platforms/:id': { ...switchPage, icon_url: '/media/platforms/p.svg' },
        'GET /api/catalog/platforms/:id/description/:source/candidates': [
          {
            external_id: 'Q19610114',
            title: 'Nintendo Switch',
            label: 'Hybrid console',
            text: 'Eine Konsole.',
            language: 'de',
            confident: true,
            has_image: true,
          },
        ],
        'POST /api/catalog/platforms/:id/description/:source': {
          description: 'Eine Konsole.',
          image: false,
        },
        'GET /api/catalog/platforms/:id/images': [
          { source: 'wikipedia', label: 'Switch small', kind: 'icon', token: 'tok-icon' },
        ],
        'POST /api/catalog/platforms/:id/images': { image_url: null, icon_url: '/x.svg' },
      }),
    )
    const { router } = await renderApp(`/platforms/${switchPlatform.id}/description/wikipedia`)
    await vi.waitFor(() => expect(q('[data-testid="take-Q19610114"]')).not.toBeNull())
    expect(q('[data-testid="description-source-igdb"]').getAttribute('href')).toBe(
      `/platforms/${switchPlatform.id}/description/igdb`,
    )
    q('[data-testid="take-Q19610114"]').click()
    await vi.waitFor(() => expect(router.currentRoute.value.name).toBe('platforms-detail'))
    const post = calls.find((c) => c.method === 'POST')!
    expect(post.path).toBe(`/api/catalog/platforms/${switchPlatform.id}/description/wikipedia`)

    await router.push(`/platforms/${switchPlatform.id}/image`)
    await vi.waitFor(() => expect(q('[data-testid="take-icon-wikipedia"]')).not.toBeNull())
    expect(q('[data-testid="term-icon-current"] img').getAttribute('src')).toBe(
      '/media/platforms/p.svg',
    )
    expect(q('[data-testid="term-image-wikipedia"]').textContent).toContain('Small logo')
    q('[data-testid="take-icon-wikipedia"]').click()
    await vi.waitFor(() => expect(toast.success).toHaveBeenCalledWith('Icon saved'))
    expect(calls.filter((c) => c.method === 'POST').at(-1)!.body).toEqual({
      token: 'tok-icon',
      target: 'icon',
    })
    expect(router.currentRoute.value.name).toBe('platforms-detail')
  })

  it('edits description, facts, predecessors and the picture', async () => {
    const calls = mockApi(
      routes({
        'PATCH /api/catalog/platforms/:id': switchPage,
        'POST /api/catalog/platforms/:id/image': switchPage,
        'DELETE /api/catalog/platforms/:id/image': { ...switchPage, image_url: null },
      }),
    )
    const back = `/platforms/${switchPlatform.id}`
    const { router } = await renderApp(
      `/catalog/platforms/${switchPlatform.id}/edit?back=${encodeURIComponent(back)}`,
    )
    await vi.waitFor(() =>
      expect((q('#platform-description-en') as HTMLTextAreaElement).value).toBe(
        'A hybrid console.',
      ),
    )
    expect((q('#platform-generation') as HTMLInputElement).value).toBe('8')
    expect(q('[data-testid="predecessor-p-wiiu"]').getAttribute('aria-pressed')).toBe('true')
    q('[data-testid="predecessor-p-wiiu"]').click()
    await settle()
    const year = q('#platform-discontinued') as HTMLInputElement
    year.value = ''
    year.dispatchEvent(new Event('input'))
    await settle()
    expect(q('[data-testid="platform-image-choose"]').getAttribute('href')).toBe(
      `/platforms/${switchPlatform.id}/image`,
    )

    const file = q('[data-testid="platform-image-file"]') as HTMLInputElement
    Object.defineProperty(file, 'files', { value: [new File(['<svg/>'], 'logo.svg')] })
    file.dispatchEvent(new Event('change'))
    await vi.waitFor(() => expect(toast.success).toHaveBeenCalledWith('Logo saved'))
    q('[data-testid="platform-image-remove"]').click()
    await vi.waitFor(() =>
      expect(calls.some((c) => c.method === 'DELETE' && c.path.endsWith('/image'))).toBe(true),
    )

    q('[data-testid="edit-save"]').click()
    await vi.waitFor(() => expect(router.currentRoute.value.fullPath).toBe(back))
    expect(calls.find((c) => c.method === 'PATCH')!.body).toMatchObject({
      descriptions: { de: '', en: 'A hybrid console.' },
      generation: 8,
      discontinued: null,
      predecessors: [],
    })
  })

  it('reports failing picture uploads', async () => {
    mockApi(
      routes({
        'POST /api/catalog/platforms/:id/image': {
          status: 400,
          body: { detail: 'This file is not an image.' },
        },
        'DELETE /api/catalog/platforms/:id/image': {
          status: 500,
          body: { detail: 'Nope.' },
        },
      }),
    )
    await renderApp(`/catalog/platforms/${switchPlatform.id}/edit`)
    await vi.waitFor(() => expect(q('[data-testid="platform-image-file"]')).not.toBeNull())
    const file = q('[data-testid="platform-image-file"]') as HTMLInputElement
    Object.defineProperty(file, 'files', { value: [new File(['x'], 'x.txt')] })
    file.dispatchEvent(new Event('change'))
    await vi.waitFor(() => expect(toast.error).toHaveBeenCalledWith('This file is not an image.'))
    q('[data-testid="platform-image-remove"]').click()
    await vi.waitFor(() => expect(toast.error).toHaveBeenCalledWith('Nope.'))
  })

  it('shows the photo of the device, the logo above the figures', async () => {
    mockApi(
      routes({
        'GET /api/catalog/platforms/:id': { ...switchPage, photo_url: '/media/p-photo.jpg' },
      }),
    )
    await renderApp(`/platforms/${switchPlatform.id}`)
    await vi.waitFor(() => expect(q('[data-testid="platform-logo"]')).not.toBeNull())
    expect(q('[data-testid="term-image"] img').getAttribute('src')).toBe('/media/p-photo.jpg')
    expect(q('[data-testid="platform-logo"]').getAttribute('src')).toBe(switchPage.image_url)
  })

  it('takes a photo, and finds pictures on Wikimedia Commons', async () => {
    const calls = mockApi(
      routes({
        'GET /api/catalog/platforms/:id/images': [
          { source: 'igdb', label: 'Logo', kind: 'logo', token: 'tok-logo' },
        ],
        'GET /api/catalog/commons-images': [
          { source: 'wikipedia', label: 'Switch console', kind: 'photo', token: 'tok-photo' },
        ],
        'POST /api/catalog/platforms/:id/images': {
          image_url: null,
          photo_url: '/p.jpg',
          icon_url: null,
        },
      }),
    )
    const { router } = await renderApp(`/platforms/${switchPlatform.id}/image`)
    await vi.waitFor(() => expect(q('[data-testid="take-photo-igdb"]')).not.toBeNull())
    expect(qa('[data-testid="term-images"] button').map((b) => b.textContent.trim())).toEqual([
      'As logo',
      'As photo',
      'As icon',
    ])
    const field = q('[data-testid="commons-query"]') as HTMLInputElement
    expect(field.placeholder).toBe('Nintendo Switch icon')
    field.value = 'Switch console'
    field.dispatchEvent(new Event('input'))
    await settle()
    field.closest('form')!.dispatchEvent(new Event('submit'))
    await vi.waitFor(() => expect(q('[data-testid="commons-images"]')).not.toBeNull())
    expect(calls.find((c) => c.path === '/api/catalog/commons-images')!.query.get('q')).toBe(
      'Switch console',
    )
    expect(q('[data-testid="commons-images"]').textContent).toContain('Wikimedia Commons')
    q('[data-testid="commons-images"] [data-testid="take-photo-wikipedia"]').click()
    await vi.waitFor(() => expect(toast.success).toHaveBeenCalledWith('Photo saved'))
    expect(calls.filter((c) => c.method === 'POST').at(-1)!.body).toEqual({
      token: 'tok-photo',
      target: 'photo',
    })
    expect(router.currentRoute.value.name).toBe('platforms-detail')
  })

  it('says when Commons finds nothing or fails', async () => {
    mockApi(
      routes({
        'GET /api/catalog/platforms/:id/images': [],
        'GET /api/catalog/commons-images': [],
      }),
    )
    await renderApp(`/platforms/${switchPlatform.id}/image`)
    await vi.waitFor(() => expect(q('[data-testid="commons-query"]')).not.toBeNull())
    const field = q('[data-testid="commons-query"]') as HTMLInputElement
    field.value = 'nothing'
    field.dispatchEvent(new Event('input'))
    await settle()
    field.closest('form')!.dispatchEvent(new Event('submit'))
    await vi.waitFor(() => expect(q('[data-testid="commons-none"]')).not.toBeNull())
  })

  it('uploads a photo of the device', async () => {
    mockApi(routes({ 'POST /api/catalog/platforms/:id/photo': switchPage }))
    await renderApp(`/catalog/platforms/${switchPlatform.id}/edit`)
    await vi.waitFor(() => expect(q('[data-testid="platform-photo-file"]')).not.toBeNull())
    expect(q('[data-testid="platform-photo-remove"]')).toBeNull()
    const file = q('[data-testid="platform-photo-file"]') as HTMLInputElement
    Object.defineProperty(file, 'files', { value: [new File(['x'], 'photo.jpg')] })
    file.dispatchEvent(new Event('change'))
    await vi.waitFor(() => expect(toast.success).toHaveBeenCalledWith('Photo saved'))
  })

  it('folds a long description, names a maker without a page, marks broken pictures', async () => {
    const long = Array.from({ length: 8 }, (_, i) => `Line ${i}`).join('\n')
    mockApi(
      routes({
        'GET /api/catalog/platforms/:id': {
          ...switchPage,
          description: long,
          description_language: 'de',
          manufacturer_company: null,
          icon_url: '/media/p.svg',
          icon_dark: true,
        },
        'GET /api/catalog/platforms/:id/images': [
          { source: 'igdb', label: 'Logo', kind: 'logo', token: 'tok-logo' },
        ],
      }),
    )
    const { router } = await renderApp(`/platforms/${switchPlatform.id}`)
    await vi.waitFor(() => expect(q('[data-testid="platform-description"]')).not.toBeNull())
    expect(q('[data-testid="platform-description-language"]').textContent).toContain('German')
    expect(q('[data-testid="platform-manufacturer"]')).toBeNull()
    expect(q('[data-testid="platform-facts"]').textContent).toContain('Nintendo')
    const more = [...document.querySelectorAll('button')].find((b) =>
      b.textContent.includes('More'),
    )!
    more.click()
    await settle()
    expect(q('[data-testid="platform-description"]').className).not.toContain('line-clamp-5')

    await router.push(`/platforms/${switchPlatform.id}/image`)
    await vi.waitFor(() => expect(q('[data-testid="term-image-igdb"] img')).not.toBeNull())
    q('[data-testid="term-image-igdb"] img').dispatchEvent(new Event('error'))
    await settle()
    expect(q('[data-testid="term-image-igdb"]').textContent).toContain("Can't be loaded")
    expect((q('[data-testid="take-photo-igdb"]') as HTMLButtonElement).disabled).toBe(true)
  })

  it("links a release's platform to its page", () => {
    const links = fieldLinks('platform.name', { platform: switchPlatform } as never)
    expect(links).toEqual([
      expect.objectContaining({ name: switchPlatform.name, to: expect.anything() }),
    ])
  })
})
