import { describe, expect, it, vi } from 'vitest'
import { toast } from 'vue-sonner'
import { mockApi, pageText, renderComponent } from '@/test/utils'
import PeopleView from '../views/PeopleView.vue'
import { $, $$, exists, LIB, library, person } from './fixtures'

vi.mock('vue-sonner', () => ({
  toast: { success: vi.fn<(message: string) => void>(), error: vi.fn<(message: string) => void>() },
}))

const url = `/l/${LIB}/people`
const people = [
  person({ id: 'p2', name: 'Zoe', email: 'zoe@example.com', notes: 'Neighbour', open_loans: 2 }),
  person({ id: 'p1', name: 'Carol' }),
]

function api(role: 'owner' | 'editor' | 'viewer', extra: Record<string, unknown> = {}) {
  return mockApi({
    'GET /api/libraries/:id': library(role),
    'GET /api/libraries/:id/people': people,
    ...extra,
  })
}

const rows = () => $$('[data-testid=person-row]')

describe('PeopleView', () => {
  it('lists people read-only for viewers with links into the explorer', async () => {
    api('viewer')
    const { router } = await renderComponent(PeopleView, { url })
    await vi.waitFor(() => expect(rows()).toHaveLength(2))
    expect(rows()[0]!.text()).toContain('Carol')
    expect(rows()[1]!.text()).toContain('zoe@example.com')
    expect(rows()[1]!.text()).toContain('Neighbour')
    // Who borrowed what is not for viewers (the API sends no contact details either).
    expect(exists('[data-testid=person-loans]')).toBe(false)
    expect(exists('[data-testid=person-lent]')).toBe(false)
    expect(exists('[data-testid=person-new]')).toBe(false)
    expect(exists('[data-testid=person-edit]')).toBe(false)
    expect(exists('[data-testid=person-delete]')).toBe(false)

    const owned = $$('[data-testid=person-owned]')[0]!
    expect(owned.attributes('href')).toBe(`/l/${LIB}?g=owner&p=p1`)
    await owned.trigger('click')
    await vi.waitFor(() => expect(router.currentRoute.value.query).toEqual({ g: 'owner', p: 'p1' }))
  })

  it('shows an empty state with a create button for editors', async () => {
    mockApi({ 'GET /api/libraries/:id': library('editor'), 'GET /api/libraries/:id/people': [] })
    await renderComponent(PeopleView, { url })
    await vi.waitFor(() => expect(exists('[data-testid=people-empty]')).toBe(true))
    expect($('[data-testid=people-empty]').text()).toContain('Add person')
    expect($('[data-testid=person-new-empty]').attributes('href')).toBe(`/l/${LIB}/people/new`)
  })

  it('shows load errors', async () => {
    mockApi({
      'GET /api/libraries/:id': library('viewer'),
      'GET /api/libraries/:id/people': { status: 403, body: { detail: 'Forbidden.' } },
    })
    await renderComponent(PeopleView, { url })
    await vi.waitFor(() => expect(pageText()).toContain('Forbidden.'))
  })

  it('links to the new and edit pages', async () => {
    api('editor')
    const { router } = await renderComponent(PeopleView, { url })
    await vi.waitFor(() => expect($$('[data-testid=person-edit]')).toHaveLength(2))
    expect($('[data-testid=person-new]').attributes('href')).toBe(`/l/${LIB}/people/new`)
    expect($$('[data-testid=person-edit]')[1]!.attributes('href')).toBe(`/l/${LIB}/people/p2/edit`)
    await $$('[data-testid=person-edit]')[1]!.trigger('click')
    await vi.waitFor(() => expect(router.currentRoute.value.name).toBe('person-edit'))
  })

  it('shows the 409 message when a person with loans is deleted', async () => {
    let fail = true
    const calls = api('owner', {
      'DELETE /api/libraries/:id/people/:pid': () =>
        fail ? { status: 409, body: { detail: 'Zoe still has loans.' } } : { status: 204 },
    })
    await renderComponent(PeopleView, { url })
    await vi.waitFor(() => expect($$('[data-testid=person-delete]')).toHaveLength(2))
    await $$('[data-testid=person-delete]')[1]!.trigger('click')
    await vi.waitFor(() => expect(exists('[data-testid=confirm-dialog]')).toBe(true))
    expect(pageText()).toContain('Delete Zoe?')
    await $('[data-testid=confirm-button]').trigger('click')
    await vi.waitFor(() =>
      expect($('[data-testid=confirm-error]').text()).toBe('Zoe still has loans.'),
    )
    fail = false
    await $('[data-testid=confirm-button]').trigger('click')
    await vi.waitFor(() => expect(exists('[data-testid=confirm-dialog]')).toBe(false))
    expect(calls.filter((c) => c.method === 'DELETE')).toHaveLength(2)
    expect(toast.success).toHaveBeenCalledWith('Zoe deleted.')
  })

  it('closes the delete confirmation on cancel', async () => {
    const calls = api('owner')
    await renderComponent(PeopleView, { url })
    await vi.waitFor(() => expect($$('[data-testid=person-delete]')).toHaveLength(2))
    await $$('[data-testid=person-delete]')[0]!.trigger('click')
    await vi.waitFor(() => expect(exists('[data-testid=confirm-dialog]')).toBe(true))
    await $$('[data-testid=confirm-dialog] button')
      .find((b) => b.text() === 'Cancel')!
      .trigger('click')
    await vi.waitFor(() => expect(exists('[data-testid=confirm-dialog]')).toBe(false))
    expect(calls.some((c) => c.method === 'DELETE')).toBe(false)
  })
})
