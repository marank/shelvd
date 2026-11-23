import { describe, expect, it, vi } from 'vitest'
import { toast } from 'vue-sonner'
import { layoutRoutes, makeLibrary, switchPlatform } from '@/test/fixtures'
import { mockApi, pageText, pickTerm, renderApp, settle } from '@/test/utils'

vi.mock('vue-sonner', () => ({
  toast: {
    success: vi.fn<(message: string) => void>(),
    error: vi.fn<(message: string) => void>(),
    warning: vi.fn<(message: string) => void>(),
  },
}))

const q = (selector: string) => document.querySelector(selector) as HTMLElement
const qa = (selector: string) => [...document.querySelectorAll<HTMLElement>(selector)]
const submit = async () => {
  await settle()
  document.querySelector('form')!.dispatchEvent(new Event('submit'))
  await settle()
}

const ps5 = { ...switchPlatform, id: 'p-ps5', name: 'PlayStation 5', short_name: 'PS5' }
const work = (id: string, title: string, year: number | null, platforms = [switchPlatform]) => ({
  id,
  title,
  year,
  cover_url: null,
  cover_aspect: null,
  manufacturer: 'Nintendo',
  platforms,
})
const entry = (id: string, name: string, uses: number, extra: Record<string, unknown> = {}) => ({
  id,
  name,
  uses,
  image_url: null,
  summary: '',
  country: '',
  founded: null,
  ...extra,
})
const companies = [
  entry('c-nin', 'Nintendo', 4, { country: 'JP', founded: 1889, image_url: '/media/n.svg' }),
  entry('c-typo', 'Nintnedo', 1),
  entry('c-505', '505 Games', 2, { summary: 'An Italian publisher.' }),
  entry('c-atlus', 'Atlus', 3),
]
const nintendo = {
  id: 'c-nin',
  name: 'Nintendo',
  description: 'Kyoto.',
  description_language: 'en',
  descriptions: { en: 'Kyoto.' },
  image_url: null,
  works: [work('w-zelda', 'Zelda', 1986)],
  published: [
    work('w-zelda', 'Zelda', 1986),
    work('w-pik', 'Pikmin', 2001, [switchPlatform, ps5]),
    work('w-new', 'Upcoming', null),
  ],
  related: [{ kind: 'genres', id: 'g-adv', name: 'Adventure', count: 2 }],
  company: {
    founded: 1889,
    dissolved: null,
    country: 'JP',
    headquarters: 'Kyoto',
    website: 'https://www.nintendo.co.jp',
    parent: null,
    subsidiaries: [{ id: 'c-retro', name: 'Retro Studios' }],
  },
}
const routes = (extra: Record<string, unknown> = {}) => ({
  ...layoutRoutes(makeLibrary()),
  'GET /api/catalog/companies': companies,
  'GET /api/catalog/companies/:id': nintendo,
  'GET /api/libraries/lib-1/owned': [{ release_id: 'r-pik', work_id: 'w-pik', copies: 2 }],
  ...extra,
})
const titles = () => qa('[data-testid="term-work"] p.font-medium').map((p) => p.textContent.trim())

describe('term pages', () => {
  it('lists every company by initial, searches and opens one', async () => {
    const calls = mockApi(routes())
    const { router } = await renderApp('/companies')
    await vi.waitFor(() => expect(qa('[data-testid="term-row"]')).toHaveLength(4))
    expect(calls.find((c) => c.path === '/api/catalog/companies')!.query.get('limit')).toBe('1000')
    expect(q('[data-testid="nav-companies"]').getAttribute('aria-current')).toBe('page')
    expect(qa('[data-testid="TermsView"] h2').map((h) => h.textContent.trim())).toEqual([
      '# · 1',
      'A · 1',
      'N · 2',
    ])
    expect(q('[data-testid="term-count"]').textContent.trim()).toBe('4 entries')
    // What it is: a company's country and year, else the start of its description.
    const rows = qa('[data-testid="term-row"]').map((r) => r.textContent.replace(/\s+/g, ' '))
    expect(rows[0]).toContain('An Italian publisher.')
    expect(rows[2]).toContain('Japan · 1889')
    expect(q('[data-testid="term-mark-image"]').getAttribute('src')).toBe('/media/n.svg')

    // Most used first, in one list; tiles; both remembered.
    q('[data-testid="term-overview-sort-uses"]').click()
    await settle()
    expect(qa('[data-testid="TermsView"] h2')).toHaveLength(0)
    expect(qa('[data-testid="term-row"] .font-medium').map((n) => n.textContent)).toEqual([
      'Nintendo',
      'Atlus',
      '505 Games',
      'Nintnedo',
    ])
    q('[data-testid="term-layout-tiles"]').click()
    await settle()
    expect(qa('[data-testid="term-tile"]')).toHaveLength(4)
    expect(q('[data-testid="term-tile"]').textContent).toContain('Used 4×')
    expect(localStorage.getItem('shelvd.term-layout')).toBe('"tiles"')
    expect(localStorage.getItem('shelvd.term-sort')).toBe('"uses"')
    q('[data-testid="term-layout-table"]').click()
    q('[data-testid="term-overview-sort-name"]').click()
    await settle()
    const search = q('[data-testid="term-search"]') as HTMLInputElement
    search.value = 'zzz'
    search.dispatchEvent(new Event('input'))
    await settle()
    expect(q('[data-testid="no-terms"]')).not.toBeNull()
    search.value = 'endo'
    search.dispatchEvent(new Event('input'))
    await settle()
    expect(qa('[data-testid="term-row"] .font-medium').map((r) => r.textContent)).toEqual([
      'Nintendo',
    ])
    q('[data-testid="term-row"]').click()
    await vi.waitFor(() => expect(router.currentRoute.value.path).toBe('/companies/c-nin'))
  })

  it("shows a company's figures, related entries and games – the library's marked", async () => {
    mockApi(
      routes({
        'GET /api/catalog/genres/:id': {
          ...nintendo,
          id: 'g-1',
          name: 'Puzzle',
          description: '',
          image_url: '/media/terms/genre/g-1.svg',
          works: [],
          published: [],
          related: [],
        },
      }),
    )
    const { router } = await renderApp('/companies/c-nin')
    await vi.waitFor(() =>
      expect(q('[data-testid="term-title"]').textContent.trim()).toBe('Nintendo'),
    )
    const stats = q('[data-testid="hero-stats"]').textContent
    expect(stats).toContain('3') // games, each once
    expect(stats).toContain('1986–2001')
    await vi.waitFor(() => expect(q('[data-stat="owned"] dd').textContent.trim()).toBe('1'))
    expect(qa('[data-testid="term-platforms"] [title]').map((b) => b.title)).toEqual([
      'Nintendo Switch',
      'PlayStation 5',
    ])
    expect(q('[data-testid="term-description"]').textContent).toContain('Kyoto.')
    expect(q('[data-testid="term-related"] a').getAttribute('href')).toBe('/genres/g-adv')
    // Oldest first (unknown years last).
    expect(titles()).toEqual(['Zelda', 'Pikmin', 'Upcoming'])
    expect(q('[data-testid="term-work"]').getAttribute('href')).toBe('/works/w-zelda')
    q('[data-testid="term-sort-title"]').click()
    await settle()
    expect(titles()).toEqual(['Pikmin', 'Upcoming', 'Zelda'])
    q('[data-testid="term-role-developed"]').click()
    await settle()
    expect(titles()).toEqual(['Zelda'])
    q('[data-testid="term-role-published"]').click()
    q('[data-testid="term-only-owned"]').click()
    await settle()
    expect(titles()).toEqual(['Pikmin'])

    await router.push('/genres/g-1')
    await vi.waitFor(() => expect(q('[data-testid="term-image"] img')).not.toBeNull())
    expect(q('[data-testid="term-image"] img').getAttribute('src')).toBe(
      '/media/terms/genre/g-1.svg',
    )
    expect(pageText()).toContain('Not used by any game yet.')
    expect(q('[data-testid="term-roles"]')).toBeNull()
    expect(q('[data-testid="term-add-description"]').getAttribute('href')).toBe('/genres/g-1/edit')
  })

  it('folds a long description, says when no owned game fits the role, and 404s', async () => {
    const long = Array.from({ length: 8 }, (_, i) => `Line ${i + 1}.`).join('\n')
    mockApi(
      routes({
        'GET /api/catalog/companies/:id': (_: unknown, { id }: Record<string, string>) =>
          id === 'c-gone'
            ? { status: 404, body: { detail: 'Not found.' } }
            : {
                ...nintendo,
                description: long,
                works: [work('w-zelda', 'Zelda', 1986)],
                published: [work('w-pik', 'Pikmin', 1986)],
              },
      }),
    )
    const { router } = await renderApp('/companies/c-nin')
    await vi.waitFor(() => expect(q('[data-testid="term-description"]')).not.toBeNull())
    // One year only: no range.
    expect(q('[data-stat="years"] dd').textContent.trim()).toBe('1986')
    const description = q('[data-testid="term-description"]')
    expect(description.className).toContain('line-clamp-5')
    const toggle = description.nextElementSibling as HTMLElement
    expect(toggle.textContent.trim()).toBe('More')
    toggle.click()
    await settle()
    expect(description.className).not.toContain('line-clamp-5')
    expect(toggle.textContent.trim()).toBe('Less')

    // Only the published game is in the library: the developed one isn't.
    await vi.waitFor(() => expect(q('[data-testid="term-only-owned"]')).not.toBeNull())
    q('[data-testid="term-only-owned"]').click()
    q('[data-testid="term-role-developed"]').click()
    await settle()
    expect(titles()).toEqual([])
    expect(q('[data-testid="term-unused"]').textContent).toContain(
      'None of these games is in your library.',
    )

    await router.push('/companies/c-gone')
    await vi.waitFor(() => expect(pageText()).toContain('Not found.'))
    expect(q('[data-testid="term-hero"]')).toBeNull()
  })

  it('reports failing picture and delete requests, and removes the picture', async () => {
    let failRemove = true
    const calls = mockApi(
      routes({
        'GET /api/catalog/companies/:id': { ...nintendo, image_url: '/media/terms/c-nin.svg' },
        'POST /api/catalog/companies/:id/image': {
          status: 400,
          body: { detail: 'Not a picture.' },
        },
        'DELETE /api/catalog/companies/:id/image': () =>
          failRemove
            ? { status: 500, body: { detail: 'Could not remove it.' } }
            : { ...nintendo, image_url: null },
        'DELETE /api/catalog/companies/:id': { status: 409, body: { detail: 'Still in use.' } },
      }),
    )
    const { router } = await renderApp('/companies/c-nin/edit')
    await vi.waitFor(() => expect(q('[data-testid="term-image-remove"]')).not.toBeNull())
    expect(q('[data-testid="term-image-preview"] img').getAttribute('src')).toBe(
      '/media/terms/c-nin.svg',
    )
    // The upload button opens the (hidden) file chooser.
    const file = q('[data-testid="term-image-file"]') as HTMLInputElement
    const choose = vi.spyOn(file, 'click').mockImplementation(() => {})
    ;(file.nextElementSibling as HTMLElement).click()
    expect(choose).toHaveBeenCalled()
    // Cancelling the chooser sends nothing.
    file.dispatchEvent(new Event('change'))
    await settle()
    expect(calls.some((c) => c.path.endsWith('/image'))).toBe(false)
    Object.defineProperty(file, 'files', {
      value: [new File(['x'], 'notes.txt', { type: 'text/plain' })],
    })
    file.dispatchEvent(new Event('change'))
    await vi.waitFor(() => expect(toast.error).toHaveBeenCalledWith('Not a picture.'))

    q('[data-testid="term-image-remove"]').click()
    await vi.waitFor(() => expect(toast.error).toHaveBeenCalledWith('Could not remove it.'))
    failRemove = false
    q('[data-testid="term-image-remove"]').click()
    await vi.waitFor(() =>
      expect(calls.filter((c) => c.method === 'DELETE' && c.path.endsWith('/image'))).toHaveLength(
        2,
      ),
    )

    q('[data-testid="term-delete"]').click()
    await settle()
    q('[data-testid="confirm-button"]').click()
    await vi.waitFor(() =>
      expect(q('[data-testid="confirm-error"]').textContent).toContain('Still in use.'),
    )
    expect(router.currentRoute.value.path).toBe('/companies/c-nin/edit')
    // Cancel closes the dialog.
    const cancel = [...q('[data-testid="confirm-dialog"]').querySelectorAll('button')].find(
      (b) => b.textContent.trim() === 'Cancel',
    )!
    cancel.click()
    await vi.waitFor(() => expect(q('[data-testid="confirm-dialog"]')).toBeNull())
  })

  it("shows a company's details", async () => {
    mockApi(
      routes({
        'GET /api/catalog/companies/:id': {
          ...nintendo,
          description_language: 'en',
          company: {
            ...nintendo.company,
            dissolved: 2001,
            parent: { id: 'c-hold', name: 'Nintendo Holdings' },
          },
        },
      }),
    )
    await renderApp('/companies/c-nin')
    await vi.waitFor(() => expect(q('[data-testid="term-company"]')).not.toBeNull())
    expect(pageText()).toContain('Existed')
    expect(pageText()).toContain('1889–2001')
    expect(pageText()).toContain('Japan')
    expect(q('[data-testid="term-company"]').textContent).toContain('Kyoto')
    expect(q('[data-testid="term-website"]').textContent).toContain('nintendo.co.jp')
    expect(q('[data-testid="term-website"]').getAttribute('rel')).toContain('noopener')
    expect(q('[data-testid="term-parent"]').getAttribute('href')).toBe('/companies/c-hold')
    expect(q('[data-testid="term-subsidiaries"]').textContent).toContain('Retro Studios')
    expect(q('[data-testid="term-description-language"]')).toBeNull() // in English already
  })

  it('shows what little is known', async () => {
    const company = {
      ...nintendo.company,
      founded: null,
      dissolved: 2001,
      country: '',
      headquarters: '',
      website: '',
      subsidiaries: [],
    }
    mockApi(
      routes({
        'GET /api/catalog/companies/:id': { ...nintendo, company, description_language: 'de' },
      }),
    )
    await renderApp('/companies/c-nin')
    await vi.waitFor(() => expect(pageText()).toContain('?–2001'))
    // No English text: the German one, said so.
    expect(q('[data-testid="term-description-language"]').textContent).toContain('Only in German')
    expect(q('[data-testid="term-company"]')).toBeNull()
    expect(q('[data-testid="term-subsidiaries"]')).toBeNull()
    expect(pageText()).not.toContain('Country')
  })

  it('renames (a clash says to merge) and deletes', async () => {
    let clash = true
    const calls = mockApi(
      routes({
        'PATCH /api/catalog/companies/:id': () =>
          clash
            ? { status: 409, body: { detail: '“Nintendo” already exists. Merge the two instead.' } }
            : { ...nintendo, name: 'Nintendo Co.' },
        'POST /api/catalog/companies/:id/image': { ...nintendo, image_url: '/media/x.svg' },
        'DELETE /api/catalog/companies/:id': { status: 204 },
      }),
    )
    const { router, queryClient } = await renderApp('/companies/c-nin/edit')
    const invalidate = vi.spyOn(queryClient, 'invalidateQueries')
    await vi.waitFor(() => expect((q('#term-name') as HTMLInputElement).value).toBe('Nintendo'))
    await submit()
    expect(pageText()).toContain('Merge the two instead.')
    clash = false
    // The picture is saved right away.
    const file = q('[data-testid="term-image-file"]') as HTMLInputElement
    Object.defineProperty(file, 'files', {
      value: [new File(['<svg/>'], 'logo.svg', { type: 'image/svg+xml' })],
    })
    file.dispatchEvent(new Event('change'))
    await vi.waitFor(() => expect(toast.success).toHaveBeenCalledWith('Picture saved.'))
    expect(calls.some((c) => c.path.endsWith('/image') && c.method === 'POST')).toBe(true)
    const name = q('#term-name') as HTMLInputElement
    name.value = 'Nintendo Co.'
    name.dispatchEvent(new Event('input'))
    // One text per language, the reader's first.
    expect(qa('textarea').map((a) => a.id)).toEqual(['term-description-en', 'term-description-de'])
    expect(pageText()).toContain('Description (German)')
    const description = q('#term-description-en') as HTMLTextAreaElement
    expect(description.value).toBe('Kyoto.')
    description.value = 'Kyoto, since 1889.'
    description.dispatchEvent(new Event('input'))
    const german = q('#term-description-de') as HTMLTextAreaElement
    german.value = 'Kyōto.'
    german.dispatchEvent(new Event('input'))
    // A company's details, the country named as typed.
    expect((q('#company-founded') as HTMLInputElement).value).toBe('1889')
    const country = q('#company-country') as HTMLInputElement
    country.value = 'jp'
    country.dispatchEvent(new Event('input'))
    const type = (selector: string, value: string) => {
      const input = q(selector) as HTMLInputElement
      input.value = value
      input.dispatchEvent(new Event('input'))
    }
    type('#company-dissolved', '1990')
    type('#company-founded', '')
    type('#company-headquarters', 'Kyōto')
    type('#company-website', 'https://nintendo.com')
    await pickTerm('#company-parent', 'Nint', 'Nintnedo')
    await settle()
    expect(q('#company-country-name').textContent).toContain('Japan')
    await submit()
    await vi.waitFor(() => expect(router.currentRoute.value.path).toBe('/companies/c-nin'))
    expect(calls.filter((c) => c.method === 'PATCH').at(-1)!.body).toEqual({
      name: 'Nintendo Co.',
      descriptions: { de: 'Kyōto.', en: 'Kyoto, since 1889.' },
      company: {
        founded: null,
        dissolved: 1990,
        country: 'jp',
        headquarters: 'Kyōto',
        website: 'https://nintendo.com',
        parent: { id: 'c-typo', name: 'Nintnedo' },
      },
    })
    // Names show in the sidebar's group tree too.
    const invalidated = invalidate.mock.calls.map((c) => (c[0] as { queryKey: unknown }).queryKey)
    expect(invalidated).toEqual(expect.arrayContaining([['terms'], ['works'], ['tree']]))

    await router.push('/companies/c-nin/edit')
    await vi.waitFor(() => expect(q('[data-testid="term-delete"]')).not.toBeNull())
    q('[data-testid="term-delete"]').click()
    await settle()
    expect(q('[data-testid="confirm-dialog"]').textContent).toContain('The 3 games stay')
    q('[data-testid="confirm-button"]').click()
    await vi.waitFor(() => expect(router.currentRoute.value.path).toBe('/companies'))
    expect(calls.some((c) => c.method === 'DELETE')).toBe(true)
    expect(toast.success).toHaveBeenCalledWith('“Nintendo” deleted.')
  })

  it('merges into an existing entry picked from the suggestions', async () => {
    const calls = mockApi(
      routes({
        'GET /api/catalog/companies/:id': { ...nintendo, id: 'c-typo', name: 'Nintnedo' },
        'POST /api/catalog/companies/:id/merge': { id: 'c-nin', name: 'Nintendo' },
      }),
    )
    const { router } = await renderApp('/companies/c-typo/merge')
    await vi.waitFor(() => expect(q('#merge-target')).not.toBeNull())
    expect(pageText()).toContain('3 games change')
    await submit()
    expect(pageText()).toContain('Pick the entry that should stay.')
    // Neither itself nor "create" is offered.
    const field = q('#merge-target') as HTMLInputElement
    field.dispatchEvent(new Event('focus'))
    field.value = 'Nint'
    field.dispatchEvent(new Event('input'))
    await settle()
    await vi.waitFor(() => expect(q('#merge-target-suggestions')).not.toBeNull())
    expect(q('#merge-target-suggestions').textContent).not.toContain('Nintnedo')
    expect(q('#merge-target-suggestions').textContent).not.toContain('Create')
    await pickTerm('#merge-target', 'Nint', 'Nintendo')
    await submit()
    await vi.waitFor(() => expect(router.currentRoute.value.path).toBe('/companies/c-nin'))
    expect(calls.find((c) => c.method === 'POST')!.body).toEqual({ target_id: 'c-nin' })
  })

  it('takes a description from Wikipedia', async () => {
    const entry = {
      external_id: 'Q11',
      title: 'Nintendo',
      label: 'Japanese video game company',
      text: 'A company.\n\nSource: Wikipedia, CC BY-SA 4.0',
      has_image: true,
    }
    const calls = mockApi(
      routes({
        'GET /api/catalog/companies/:id': { ...nintendo, description: '' },
        'GET /api/lookup/providers': [
          { name: 'igdb', label: 'IGDB', kind: 'metadata', enabled: true },
          { name: 'wikipedia', label: 'Wikipedia', kind: 'metadata', enabled: true },
        ],
        'GET /api/catalog/companies/:id/description/:source/candidates': [entry],
        'POST /api/catalog/companies/:id/description/:source': {
          description: entry.text,
          image: true,
        },
      }),
    )
    const { router } = await renderApp('/companies/c-nin')
    await vi.waitFor(() =>
      expect(q('[data-testid="term-describe-empty-wikipedia"]')).not.toBeNull(),
    )
    // Wikipedia first, then IGDB.
    expect(qa('[data-testid^="term-describe-empty-"]').map((a) => a.textContent.trim())).toEqual([
      'Description from Wikipedia …',
      'Description from IGDB …',
    ])
    q('[data-testid="term-describe-empty-wikipedia"]').click()
    await vi.waitFor(() => expect(q('[data-testid="take-Q11"]')).not.toBeNull())
    expect(router.currentRoute.value.fullPath).toBe('/companies/c-nin/description/wikipedia')
    expect(q('[data-testid="description-source-igdb"]').textContent).toContain('Search IGDB')
    expect(pageText()).toContain('Japanese video game company')
    expect(q('[data-testid="take-Q11"]').textContent).toContain('Use')
    // The entry has a logo and the company no picture yet: taken along by default.
    expect(pageText()).toContain('Also use the logo')
    expect(q('[data-testid="description-logo"]').getAttribute('aria-checked')).toBe('true')

    ;(q('[data-testid="description-query"]') as HTMLInputElement).value = ' Big N '
    q('[data-testid="description-query"]').dispatchEvent(new Event('input'))
    await settle()
    q('[data-testid="description-search"]').dispatchEvent(new Event('submit'))
    await vi.waitFor(() =>
      expect(
        calls.some((c) => c.path.endsWith('/candidates') && c.query.get('q') === 'Big N'),
      ).toBe(true),
    )

    q('[data-testid="take-Q11"]').click()
    await vi.waitFor(() => expect(router.currentRoute.value.name).toBe('companies-detail'))
    expect(calls.find((c) => c.method === 'POST')!.body).toEqual({
      external_id: 'Q11',
      image: true,
    })
    expect(toast.success).toHaveBeenCalledWith('Description and logo added')
  })

  it("keeps a company's picture unless asked, and says when a logo can't be used", async () => {
    const entry = {
      external_id: 'Q11',
      title: 'Nintendo',
      label: '',
      text: 'A company.',
      has_image: true,
    }
    const calls = mockApi(
      routes({
        'GET /api/catalog/companies/:id': { ...nintendo, image_url: '/media/logo.svg' },
        'GET /api/lookup/providers': [
          { name: 'wikipedia', label: 'Wikipedia', kind: 'metadata', enabled: true },
        ],
        'GET /api/catalog/companies/:id/description/:source/candidates': [entry],
        'POST /api/catalog/companies/:id/description/:source': {
          description: entry.text,
          image: false,
        },
      }),
    )
    await renderApp('/companies/c-nin/description/wikipedia')
    await vi.waitFor(() => expect(q('[data-testid="take-Q11"]')).not.toBeNull())
    expect(pageText()).toContain('Replaces the current picture')
    const box = q('[data-testid="description-logo"]')
    expect(box.getAttribute('aria-checked')).toBe('false')
    box.click()
    await settle()
    q('[data-testid="take-Q11"]').click()
    await vi.waitFor(() => expect(toast.warning).toHaveBeenCalledWith("The logo couldn't be used."))
    expect(calls.find((c) => c.method === 'POST')!.body).toEqual({
      external_id: 'Q11',
      image: true,
    })
    expect(toast.success).toHaveBeenCalledWith('Description added')
  })

  it('says how each entry fits, in which language, and offers details alone', async () => {
    const base = { label: '', has_image: false, confident: false }
    const entries = [
      {
        ...base,
        external_id: 'Q1',
        title: 'Nintendo',
        text: 'Ein Unternehmen.',
        language: 'de',
        confident: true,
      },
      { ...base, external_id: 'Q2', title: 'Nintendo', text: '', language: '', confident: true },
      { ...base, external_id: 'Q3', title: 'Nintendo Power', text: 'A magazine.', language: 'en' },
    ]
    const calls = mockApi(
      routes({
        'GET /api/lookup/providers': [
          { name: 'wikipedia', label: 'Wikipedia', kind: 'metadata', enabled: true },
        ],
        'GET /api/catalog/companies/:id/description/:source/candidates': entries,
        'POST /api/catalog/companies/:id/description/:source': {
          description: 'Kyoto.',
          image: false,
        },
      }),
    )
    await renderApp('/companies/c-nin/description/wikipedia')
    await vi.waitFor(() => expect(q('[data-testid="take-Q2"]')).not.toBeNull())
    expect(qa('[data-testid^="confident-"]').map((b) => b.dataset.testid)).toEqual([
      'confident-Q1',
      'confident-Q2',
    ])
    const rows = qa('[data-testid="description-candidates"] li').map((li) => li.textContent)
    expect(rows[0]).toContain('German')
    expect(rows[1]).toContain('No text – only details')
    expect(rows[2]).not.toContain('English')
    expect(q('[data-testid="take-Q2"]').textContent).toContain('Use details')
    q('[data-testid="take-Q2"]').click()
    await vi.waitFor(() => expect(calls.some((c) => c.method === 'POST')).toBe(true))
  })

  it('offers Wikipedia in the menu, not for genres, and reports failures', async () => {
    mockApi(
      routes({
        'GET /api/lookup/providers': [
          { name: 'wikipedia', label: 'Wikipedia', kind: 'metadata', enabled: true },
          { name: 'igdb', label: 'IGDB', kind: 'metadata', enabled: true },
        ],
        'GET /api/catalog/series/:id': { ...nintendo, id: 's-1', name: 'Zelda' },
        'GET /api/catalog/series/:id/description/:source/candidates': [
          { external_id: 'Q1', title: 'Zelda', label: '', text: 'A series.' },
        ],
        'POST /api/catalog/series/:id/description/:source': {
          status: 502,
          body: { detail: 'The source did not answer. Try again later.' },
        },
        'GET /api/catalog/genres/:id': {
          ...nintendo,
          id: 'g-1',
          name: 'Adventure',
          description: '',
        },
      }),
    )
    const { router } = await renderApp('/series/s-1')
    await vi.waitFor(() => expect(q('[data-testid="term-menu"]')).not.toBeNull())
    q('[data-testid="term-menu"]').dispatchEvent(
      new KeyboardEvent('keydown', { key: 'Enter', bubbles: true }),
    )
    await vi.waitFor(() => expect(q('[data-testid="term-describe-wikipedia"]')).not.toBeNull())
    // IGDB describes companies only.
    expect(q('[data-testid="term-describe-igdb"]')).toBeNull()
    q('[data-testid="term-describe-wikipedia"]').click()
    await vi.waitFor(() => expect(q('[data-testid="take-Q1"]')).not.toBeNull())
    // It has a description already: replacing it.
    expect(q('[data-testid="take-Q1"]').textContent).toContain('Replace')
    q('[data-testid="take-Q1"]').click()
    await vi.waitFor(() =>
      expect(toast.error).toHaveBeenCalledWith('The source did not answer. Try again later.'),
    )
    expect(router.currentRoute.value.name).toBe('series-description')

    await router.push('/genres/g-1')
    await vi.waitFor(() => expect(q('[data-testid="term-add-description"]')).not.toBeNull())
    expect(q('[data-testid^="term-describe-empty"]')).toBeNull()
    expect(q('[data-testid="term-choose-image"]')).toBeNull()
  })

  it("chooses a picture from the linked entries' logos", async () => {
    const images = [
      { source: 'igdb', label: 'Logo', token: 'tok-1' },
      { source: 'wikipedia', label: 'Nintendo red logo (1975–2006)', token: 'tok/2' },
    ]
    const calls = mockApi(
      routes({
        'GET /api/lookup/providers': [
          { name: 'wikipedia', label: 'Wikipedia', kind: 'metadata', enabled: true },
          { name: 'igdb', label: 'IGDB', kind: 'metadata', enabled: true },
        ],
        'GET /api/catalog/companies/:id/images': images,
        'POST /api/catalog/companies/:id/images': nintendo,
      }),
    )
    const { router } = await renderApp('/companies/c-nin')
    await vi.waitFor(() => expect(q('[data-testid="term-menu"]')).not.toBeNull())
    q('[data-testid="term-menu"]').dispatchEvent(
      new KeyboardEvent('keydown', { key: 'Enter', bubbles: true }),
    )
    await vi.waitFor(() => expect(q('[data-testid="term-choose-image"]')).not.toBeNull())
    q('[data-testid="term-choose-image"]').click()
    await vi.waitFor(() => expect(q('[data-testid="term-image-wikipedia"]')).not.toBeNull())
    expect(router.currentRoute.value.fullPath).toBe('/companies/c-nin/image')
    const tile = q('[data-testid="term-image-wikipedia"]')
    expect(tile.textContent).toContain('Nintendo red logo (1975–2006)')
    expect(tile.textContent).toContain('Wikipedia')
    expect(tile.querySelector('img')!.getAttribute('src')).toBe(
      '/api/catalog/term-image-preview?token=tok%2F2',
    )
    // A picture that doesn't load can't be taken.
    q('[data-testid="term-image-igdb"] img').dispatchEvent(new Event('error'))
    await settle()
    expect(q('[data-testid="term-image-igdb"]').textContent).toContain("Can't be loaded")
    expect((q('[data-testid="term-image-igdb"]') as HTMLButtonElement).disabled).toBe(true)

    tile.click()
    await vi.waitFor(() => expect(router.currentRoute.value.name).toBe('companies-detail'))
    expect(calls.find((c) => c.method === 'POST')!.body).toEqual({
      token: 'tok/2',
      target: 'image',
    })
    expect(toast.success).toHaveBeenCalled()
  })

  it('says where pictures come from when there are none, and reports failures', async () => {
    mockApi(
      routes({
        'GET /api/lookup/providers': [
          { name: 'wikipedia', label: 'Wikipedia', kind: 'metadata', enabled: true },
        ],
        'GET /api/catalog/companies/:id/images': [],
        'GET /api/catalog/series/:id': {
          ...nintendo,
          id: 's-1',
          name: 'Zelda',
          image_url: '/media/zelda.svg',
        },
        'GET /api/catalog/series/:id/images': [
          { source: 'wikipedia', label: '', token: 't' },
          { source: 'elsewhere', label: 'Logo', token: 'u' },
        ],
        'POST /api/catalog/series/:id/images': {
          status: 502,
          body: { detail: "The picture couldn't be loaded." },
        },
      }),
    )
    const { router } = await renderApp('/companies/c-nin/edit')
    await vi.waitFor(() => expect(q('[data-testid="term-image-choose"]')).not.toBeNull())
    q('[data-testid="term-image-choose"]').click()
    await vi.waitFor(() => expect(q('[data-testid="term-images-none"]')).not.toBeNull())
    expect(q('[data-testid="term-images-none"]').textContent).toContain(
      'Description from Wikipedia …',
    )

    await router.push('/series/s-1/image')
    await vi.waitFor(() => expect(q('[data-testid="term-image-wikipedia"]')).not.toBeNull())
    expect(q('[data-testid="term-image-wikipedia"]').textContent).toContain('–')
    expect(q('[data-testid="term-image-elsewhere"]').textContent).toContain('elsewhere')
    expect(q('[data-testid="term-image-current"] img').getAttribute('src')).toBe('/media/zelda.svg')
    q('[data-testid="term-image-wikipedia"]').click()
    await vi.waitFor(() =>
      expect(toast.error).toHaveBeenCalledWith("The picture couldn't be loaded."),
    )
    expect(router.currentRoute.value.name).toBe('series-image')
  })

  it("says when the sources can't list pictures", async () => {
    mockApi(
      routes({
        'GET /api/catalog/companies/:id/images': {
          status: 502,
          body: { detail: 'The source did not answer. Try again later.' },
        },
      }),
    )
    await renderApp('/companies/c-nin/image')
    await vi.waitFor(() =>
      expect(pageText()).toContain('The source did not answer. Try again later.'),
    )
  })

  it("links a series and its franchise both ways, and sets a series' franchise", async () => {
    const mario = { ...nintendo, id: 'f-mario', name: 'Mario', company: null, franchise: null }
    const kart = {
      ...nintendo,
      id: 's-kart',
      name: 'Mario Kart',
      company: null,
      franchise: { id: 'f-mario', name: 'Mario' },
      parts: [],
    }
    const calls = mockApi(
      routes({
        'GET /api/lookup/providers': [
          { name: 'wikipedia', label: 'Wikipedia', kind: 'metadata', enabled: true },
        ],
        'GET /api/catalog/series/:id': kart,
        'GET /api/catalog/franchises/:id': {
          ...mario,
          parts: [{ id: 's-kart', name: 'Mario Kart' }],
        },
        'GET /api/catalog/franchises': [entry('f-mario', 'Mario', 9), entry('f-zelda', 'Zelda', 5)],
        'PATCH /api/catalog/series/:id': kart,
      }),
    )
    const { router } = await renderApp('/series/s-kart')
    await vi.waitFor(() => expect(q('[data-testid="term-franchise"]')).not.toBeNull())
    expect(q('[data-testid="term-franchise"]').textContent).toContain('Part of Mario')
    q('[data-testid="term-franchise"] a').click()
    await vi.waitFor(() => expect(q('[data-testid="term-parts"]')).not.toBeNull())
    expect(q('[data-testid="term-parts"]').textContent).toContain('Mario Kart')
    // Franchises are described by Wikipedia too.
    q('[data-testid="term-menu"]').dispatchEvent(
      new KeyboardEvent('keydown', { key: 'Enter', bubbles: true }),
    )
    await vi.waitFor(() => expect(q('[data-testid="term-describe-wikipedia"]')).not.toBeNull())

    await router.push('/series/s-kart/edit')
    await vi.waitFor(() => expect(q('#series-franchise')).not.toBeNull())
    expect(pageText()).toContain('The brand the series belongs to')
    await pickTerm('#series-franchise', 'Zel', 'Zelda')
    await submit()
    await vi.waitFor(() => expect(calls.some((c) => c.method === 'PATCH')).toBe(true))
    expect(calls.find((c) => c.method === 'PATCH')!.body).toMatchObject({
      series: { franchise: { id: 'f-zelda' } },
    })
  })
})
