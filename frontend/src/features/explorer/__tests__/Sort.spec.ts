import { describe, expect, it, vi } from 'vitest'
import { formatSort, parseSort } from '@/lib/itemFields'
import { layoutRoutes, makeItem, makeLibrary, makeOverview } from '@/test/fixtures'
import { mockApi, openMenu, pageText, renderApp, settle } from '@/test/utils'

function routes(extra: Record<string, unknown> = {}) {
  return {
    ...layoutRoutes(makeLibrary(), [makeOverview({ group_by: [], sort: 'copy.value' })]),
    'GET /api/libraries/lib-1/tree': { total: 1, group_by: [], nodes: [] },
    'GET /api/libraries/lib-1/items': { count: 1, items: [makeItem()] },
    ...extra,
  }
}

const q = (selector: string) => document.querySelector(selector) as HTMLElement
const click = async (selector: string) => {
  q(selector).click()
  await settle()
}

describe('sorting', () => {
  it('reads and writes sort levels', () => {
    expect(parseSort('location.box, -release.number,colour.x,copy.value,-copy.acquired')).toEqual([
      { key: 'location.box', desc: false },
      { key: 'release.number', desc: true },
      { key: 'copy.value', desc: false },
      { key: 'copy.acquired', desc: true },
    ])
    // The default (by title) reads as no levels and is written back as itself.
    expect(parseSort(undefined)).toEqual([])
    expect(parseSort('game.title')).toEqual([])
    expect(formatSort([])).toBe('game.title')
    expect(
      formatSort([
        { key: 'game.title', desc: true },
        { key: 'location.box', desc: false },
      ]),
    ).toBe('-game.title,location.box')
  })

  it('chooses several levels in the dialog and saves them with the view', async () => {
    const calls = mockApi(
      routes({ 'PATCH /api/libraries/lib-1/overviews/overview-1': makeOverview() }),
    )
    const { router } = await renderApp('/l/lib-1')
    await vi.waitFor(() =>
      expect(document.querySelector('[data-testid="sort-button"]')).not.toBeNull(),
    )
    // The saved sort shows by its field name.
    expect(q('[data-testid="sort-button"]').textContent).toContain("Collector's value")

    await click('[data-testid="sort-button"]')
    expect(document.querySelectorAll('[data-testid="sort-levels"] li')).toHaveLength(1)
    // A hidden field and the title can be sort levels too.
    await click('[data-testid="field-location.box"]')
    await click('[data-testid="field-game.title"]')
    const flips = () => document.querySelectorAll<HTMLElement>('[data-testid="flip-sort"]')
    flips()[1]!.click()
    await settle()
    // Drag "Title" (3rd) to the top.
    const rows = () => [...document.querySelectorAll<HTMLElement>('[data-testid="sort-levels"] li')]
    rows()[2]!.dispatchEvent(new Event('dragstart'))
    rows()[0]!.dispatchEvent(new Event('drop'))
    await settle()
    expect(rows().map((r) => r.textContent)).toEqual([
      expect.stringContaining('Title'),
      expect.stringContaining("Collector's value"),
      expect.stringContaining('Box'),
    ])
    // The move buttons do the same by keyboard: Box up, then back down.
    rows()[2]!.querySelector<HTMLElement>('[data-testid="sort-up"]')!.click()
    await settle()
    expect(rows()[1]!.textContent).toContain('Box')
    rows()[1]!.querySelector<HTMLElement>('[data-testid="sort-down"]')!.click()
    await settle()
    expect(rows()[2]!.textContent).toContain('Box')
    await click('[data-testid="apply-sort"]')
    expect(router.currentRoute.value.query.sort).toBe('game.title,copy.value,-location.box')
    await vi.waitFor(() =>
      expect(calls.some((c) => c.query.get('sort') === 'game.title,copy.value,-location.box')).toBe(
        true,
      ),
    )
    expect(q('[data-testid="sort-button"]').textContent).toContain('+2')

    await openMenu('view-menu')
    await click('[data-testid="save-view"]')
    await vi.waitFor(() => expect(calls.some((c) => c.method === 'PATCH')).toBe(true))
    expect(calls.find((c) => c.method === 'PATCH')!.body).toMatchObject({
      sort: 'game.title,copy.value,-location.box',
    })
  })

  it('limits levels, removes and resets', async () => {
    mockApi(routes())
    const { router } = await renderApp('/l/lib-1')
    await vi.waitFor(() =>
      expect(document.querySelector('[data-testid="sort-button"]')).not.toBeNull(),
    )
    await click('[data-testid="sort-button"]')
    for (const key of ['location.box', 'release.year', 'owner.name', 'release.region'])
      await click(`[data-testid="field-${key}"]`)
    expect(document.querySelectorAll('[data-testid="sort-levels"] li')).toHaveLength(5)
    expect((q('[data-testid="field-copy.notes"]') as HTMLButtonElement).disabled).toBe(true)
    await click('[data-testid="remove-sort"]')
    expect(document.querySelectorAll('[data-testid="sort-levels"] li')).toHaveLength(4)
    await click('[data-testid="reset-sort"]')
    expect(pageText()).toContain('By title (default)')
    await click('[data-testid="apply-sort"]')
    expect(router.currentRoute.value.query.sort).toBe('game.title')
  })
})
