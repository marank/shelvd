import { describe, expect, it, vi } from 'vitest'
import { layoutRoutes, makeLibrary } from '@/test/fixtures'
import { mockApi, pageText, plainUser, renderApp, settle } from '@/test/utils'

const entry = (kind: string, id: string, extra: Record<string, unknown> = {}) => ({
  kind,
  id,
  title: 'Homebrew Hero',
  detail: kind === 'barcode' ? '4006381333931 → Switch · PAL' : 'Switch · PAL',
  work_id: 'work-1',
  release_id: kind === 'work' ? null : 'rel-1',
  created_by: 'bob',
  created_at: '2026-11-11T10:00:00Z',
  copies: 1,
  ...extra,
})

describe('review queue', () => {
  it('lists unreviewed entries for admins, approves and removes barcodes', async () => {
    const calls = mockApi({
      ...layoutRoutes(makeLibrary()),
      'GET /api/catalog/review': {
        count: 3,
        entries: [entry('release', 'r1'), entry('barcode', 'b1'), entry('work', 'w1')],
      },
      'GET /api/catalog/review/count': { count: 3 },
      'POST /api/catalog/review/approve': { approved: 1 },
      'DELETE /api/catalog/barcodes/:id': { status: 204 },
    })
    const { router } = await renderApp('/l/lib-1')
    await vi.waitFor(() =>
      expect(document.querySelector('[data-testid="review-count"]')?.textContent).toContain('3'),
    )
    await router.push('/catalog/review')
    await vi.waitFor(() =>
      expect(document.querySelectorAll('[data-testid="review-entry"]')).toHaveLength(3),
    )
    expect(pageText()).toContain('bob')
    expect(pageText()).toContain('4006381333931 → Switch · PAL')
    ;(document.querySelector('[data-testid="approve"]') as HTMLElement).click()
    await settle()
    expect(calls.find((c) => c.path === '/api/catalog/review/approve')?.body).toEqual({
      releases: ['r1'],
    })
    ;(document.querySelector('[data-testid="remove-barcode"]') as HTMLElement).click()
    await settle()
    expect(calls.some((c) => c.method === 'DELETE' && c.path === '/api/catalog/barcodes/b1')).toBe(
      true,
    )
    ;(document.querySelector('[data-testid="approve-all"]') as HTMLElement).click()
    await settle()
    expect(calls.filter((c) => c.path === '/api/catalog/review/approve').at(-1)?.body).toEqual({
      works: ['w1'],
      releases: ['r1'],
      barcodes: ['b1'],
    })
  })

  it('is closed for everyone else', async () => {
    mockApi(layoutRoutes(makeLibrary()))
    const { router } = await renderApp('/l/lib-1', { user: plainUser })
    expect(document.querySelector('[data-testid="nav-review"]')).toBeNull()
    await router.push('/catalog/review')
    await vi.waitFor(() => expect(router.currentRoute.value.name).toBe('forbidden'))
    await vi.waitFor(() => expect(pageText()).toContain('Only admins can do this.'))
  })
})

describe('review queue errors', () => {
  it('says when the queue or an action fails', async () => {
    mockApi({
      ...layoutRoutes(makeLibrary()),
      'GET /api/catalog/review': {
        count: 1,
        entries: [
          {
            kind: 'barcode',
            id: 'b1',
            title: 'Homebrew Hero',
            detail: '4006381333931 → Switch · PAL',
            work_id: 'work-1',
            release_id: 'rel-1',
            created_by: null,
            created_at: '2026-11-11T10:00:00Z',
            copies: 0,
          },
        ],
      },
      'GET /api/catalog/review/count': { count: 1 },
      'POST /api/catalog/review/approve': { status: 409, body: { detail: 'Changed meanwhile.' } },
    })
    await renderApp('/catalog/review')
    await vi.waitFor(() =>
      expect(document.querySelectorAll('[data-testid="review-entry"]')).toHaveLength(1),
    )
    expect(pageText()).toContain('Unknown')
    ;(document.querySelector('[data-testid="approve"]') as HTMLElement).click()
    await vi.waitFor(() => expect(pageText()).toContain('Changed meanwhile.'))
  })

  it('shows an empty queue', async () => {
    mockApi({
      ...layoutRoutes(makeLibrary()),
      'GET /api/catalog/review': { count: 0, entries: [] },
      'GET /api/catalog/review/count': { count: 0 },
    })
    await renderApp('/catalog/review')
    await vi.waitFor(() =>
      expect(document.querySelector('[data-testid="review-empty"]')).not.toBeNull(),
    )
  })

  it('says when the queue can’t be loaded', async () => {
    mockApi({
      ...layoutRoutes(makeLibrary()),
      'GET /api/catalog/review': { status: 400, body: { detail: 'Broken.' } },
      'GET /api/catalog/review/count': { count: 0 },
    })
    await renderApp('/catalog/review')
    await vi.waitFor(() => expect(pageText()).toContain('Broken.'))
  })
})
