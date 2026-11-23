import { describe, expect, it, vi } from 'vitest'
import { computed, defineComponent, h } from 'vue'
import type { Addon, FigureTarget } from '@/addons'
import type { Integration } from '@/api/types'
import GameFacts from '@/features/game/components/GameFacts.vue'
import CopyHero from '@/features/items/components/CopyHero.vue'
import ImportCard from '@/features/manage/components/settings/ImportCard.vue'
import { layoutRoutes, makeItem, makeLibrary, makeRelease } from '@/test/fixtures'
import {
  mockApi,
  openMenu,
  pageText,
  renderApp,
  renderComponent,
  settle,
  testUser,
} from '@/test/utils'

/** A made-up add-on that uses every seam once. */
const fake = vi.hoisted(() => ({ targets: [] as unknown[] }))

vi.mock('@/addons', async (importOriginal) => {
  const real = await importOriginal<typeof import('@/addons')>()
  /** A paragraph with a test id; `text` reads the props named in `props`. */
  const paragraph = (
    testid: string,
    text: (props: Record<string, { key?: string; id?: string }>) => string,
    props: string[] = [],
  ) =>
    defineComponent({
      props,
      setup: (p) => () =>
        h('p', { 'data-testid': testid }, text(p as Record<string, { key?: string; id?: string }>)),
    })
  const Page = paragraph('fake-page', () => 'Fake page')
  const Fact = paragraph('fake-fact', (p) => `fact ${p.release?.id}`, ['release'])
  const Flow = paragraph('fake-flow', (p) => `flow ${p.integration?.key}`, ['integration'])
  const addon: Addon = {
    routes: [
      { path: '/fake', name: 'fake', component: Page },
      { path: '/l/:libraryId/fake-import', name: 'fake-import', component: Page },
    ],
    nav: [
      {
        route: 'fake',
        label: 'nav.upcoming',
        icon: Page,
        testid: 'nav-fake',
        activeOn: ['fake-more'],
      },
    ],
    accountMenu: [{ route: 'fake', label: 'nav.lists', icon: Page, testid: 'menu-fake' }],
    figures: (target: () => FigureTarget) =>
      computed(() => {
        fake.targets.push(target())
        return [{ key: 'fake', label: 'Fake figure', value: target().platformId ?? 'all' }]
      }),
    gameFacts: [Fact],
    integrationFlows: { fake_token: Flow },
    integrationLinks: { hltb: 'https://fake.example' },
    libraryImports: [
      { route: 'fake-import', label: 'nav.lists', icon: Page, testid: 'fake-import' },
    ],
  }
  real.addons.push(addon)
  return real
})

const staff = { ...testUser, is_staff: true }

describe('an installed add-on', () => {
  it('adds its page, a sidebar link and a user-menu link', async () => {
    mockApi(layoutRoutes(makeLibrary()))
    await renderApp('/fake')
    await vi.waitFor(() =>
      expect(document.querySelector('[data-testid="fake-page"]')).not.toBeNull(),
    )
    const link = document.querySelector('[data-testid="nav-fake"]')!
    expect(link.getAttribute('href')).toBe('/fake')
    await openMenu('user-menu')
    await settle()
    expect(document.querySelector('[data-testid="menu-fake"]')?.getAttribute('href')).toBe('/fake')
  })

  it("adds figures to a copy's head, for its platform", async () => {
    const item = makeItem()
    mockApi({ 'GET /api/lookup/providers': [] })
    await renderComponent(CopyHero, {
      props: { item, libraryId: 'lib-1', editable: false, compact: true },
    })
    await vi.waitFor(() => expect(pageText()).toContain('Fake figure'))
    expect(fake.targets).toContainEqual({
      workId: item.release.work_id,
      platformId: item.release.platform.id,
    })
  })

  it('adds its blocks to the game facts, with the release', async () => {
    const release = makeRelease({ id: 'rel-9' })
    await renderComponent(GameFacts, { props: { release, releases: [release], sources: false } })
    expect(document.querySelector('[data-testid="fake-fact"]')?.textContent).toBe('fact rel-9')
  })

  it("shows an integration's flow for its field, and its link", async () => {
    const integration: Integration = {
      key: 'hltb',
      name: 'HowLongToBeat',
      kind: 'facts',
      url: 'https://example.com/docs',
      unofficial: false,
      refreshes: false,
      enabled: true,
      active: true,
      fields: [
        { name: 'fake_token', type: 'text', secret: true, required: true, value: null, has_value: false, masked: '' },
      ],
      last_ok_at: null,
      last_error: '',
      last_error_at: null,
      last_run_at: null,
    } // prettier-ignore
    mockApi({
      ...layoutRoutes(makeLibrary()),
      'GET /api/lookup/providers': [
        { name: 'hltb', label: 'HowLongToBeat', kind: 'facts', enabled: true },
      ],
      'GET /api/integrations': [integration],
    })
    const { router } = await renderApp('/integrations/hltb', { user: staff })
    await vi.waitFor(() =>
      expect(document.querySelector('[data-testid="fake-flow"]')?.textContent).toBe('flow hltb'),
    )
    // The flow sets the field: no text box for it.
    expect(document.querySelector('[data-testid="field-fake_token"]')).toBeNull()
    await router.push('/integrations')
    await vi.waitFor(() =>
      expect(document.querySelector('[data-testid="attribution"] a')?.getAttribute('href')).toBe(
        'https://fake.example',
      ),
    )
  })

  it("adds its import to a library's settings, for that library", async () => {
    const library = makeLibrary({ id: 'lib-7', role: 'owner' })
    await renderComponent(ImportCard, { props: { library } })
    expect(document.querySelector('[data-testid="settings-import"]')).not.toBeNull()
    expect(document.querySelector('[data-testid="fake-import"]')?.getAttribute('href')).toBe(
      '/l/lib-7/fake-import',
    )
  })
})
