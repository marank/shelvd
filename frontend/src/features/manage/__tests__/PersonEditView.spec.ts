import { describe, expect, it, vi } from 'vitest'
import { toast } from 'vue-sonner'
import { mockApi, pageText, renderComponent } from '@/test/utils'
import PersonEditView from '../views/PersonEditView.vue'
import { $, $$, exists, LIB, library, loan, person } from './fixtures'

vi.mock('vue-sonner', () => ({
  toast: { success: vi.fn<(message: string) => void>(), error: vi.fn<(message: string) => void>() },
}))

const people = [
  person({ id: 'p2', name: 'Zoe', email: 'zoe@example.com', notes: 'Neighbour', open_loans: 2 }),
  person({ id: 'p1', name: 'Carol' }),
]
const loans = [
  loan({
    id: 'l1',
    item_id: 'i1',
    item_title: 'Mario Kart 8',
    borrower: { id: 'p2', name: 'Zoe' },
    overdue: true,
  }),
  loan({
    id: 'l2',
    item_id: 'i2',
    item_title: 'Zelda',
    borrower: { id: 'p2', name: 'Zoe' },
    due_on: null,
  }),
  loan({ id: 'l3', item_title: 'Metroid', borrower: { id: 'p1', name: 'Carol' } }),
]

function api(role: 'owner' | 'editor' | 'viewer', extra: Record<string, unknown> = {}) {
  return mockApi({
    'GET /api/libraries/:id': library(role),
    'GET /api/libraries/:id/people': people,
    'GET /api/libraries/:id/loans': loans,
    ...extra,
  })
}

const value = (selector: string) => ($(selector).element as HTMLInputElement).value

describe('PersonEditView', () => {
  it('edits a person and lists their open loans', async () => {
    let fail = true
    const calls = api('editor', {
      'PATCH /api/libraries/:id/people/:pid': () =>
        fail ? { status: 422, body: { detail: [{ msg: 'Invalid email.' }] } } : people[0],
    })
    const { router } = await renderComponent(PersonEditView, {
      url: `/l/${LIB}/people/p2/edit`,
    })
    await vi.waitFor(() => expect(value('#person-name')).toBe('Zoe'))
    expect(pageText()).toContain('Edit person')
    expect(value('#person-email')).toBe('zoe@example.com')
    expect(value('#person-notes')).toBe('Neighbour')
    await vi.waitFor(() => expect($$('[data-testid=person-loan]')).toHaveLength(2))
    const [first, second] = $$('[data-testid=person-loan]')
    expect(first!.text()).toContain('Mario Kart 8')
    expect(first!.text()).toContain('Overdue')
    expect(first!.text()).toContain('→')
    expect(second!.text()).not.toContain('→')
    expect(first!.find('a').attributes('href')).toBe(`/l/${LIB}?item=i1`)
    expect($('[data-testid=person-owned]').attributes('href')).toBe(`/l/${LIB}?g=owner&p=p2`)
    expect(calls.find((c) => c.path.endsWith('/loans'))?.query.get('open')).toBe('true')

    await $('#person-name').setValue('Zoë')
    await $('#person-email').setValue(' zoe@example ')
    await $('form').trigger('submit')
    await vi.waitFor(() => expect($('[data-testid=edit-error]').text()).toBe('Invalid email.'))
    fail = false
    await $('form').trigger('submit')
    await vi.waitFor(() => expect(router.currentRoute.value.name).toBe('people'))
    const patch = calls.filter((c) => c.method === 'PATCH').at(-1)!
    expect(patch.path).toBe(`/api/libraries/${LIB}/people/p2`)
    expect(patch.body).toEqual({ name: 'Zoë', email: 'zoe@example', notes: 'Neighbour' })
    expect(toast.success).toHaveBeenCalledWith('Zoë saved.')
  })

  it('says when nothing is lent and reloads when switching people', async () => {
    api('owner', { 'GET /api/libraries/:id/loans': [] })
    const { router } = await renderComponent(PersonEditView, {
      url: `/l/${LIB}/people/p1/edit`,
    })
    await vi.waitFor(() => expect(exists('[data-testid=person-no-loans]')).toBe(true))
    expect(value('#person-name')).toBe('Carol')
    await router.push(`/l/${LIB}/people/p2/edit`)
    await vi.waitFor(() => expect(value('#person-name')).toBe('Zoe'))
  })

  it('creates a person and requires a name', async () => {
    const calls = api('owner', {
      'POST /api/libraries/:id/people': {
        status: 201,
        body: person({ id: 'p3', name: 'Dan' }),
      },
    })
    const { router } = await renderComponent(PersonEditView, { url: `/l/${LIB}/people/new` })
    await vi.waitFor(() => expect(exists('#person-name')).toBe(true))
    expect(pageText()).toContain('Add person')
    expect(exists('[data-testid=person-delete]')).toBe(false)
    expect(exists('[data-testid=person-owned]')).toBe(false)
    await $('form').trigger('submit')
    await vi.waitFor(() =>
      expect($('[data-testid=edit-error]').text()).toBe('Please enter a name.'),
    )
    expect(calls.some((c) => c.method === 'POST')).toBe(false)
    await $('#person-name').setValue(' Dan ')
    await $('#person-notes').setValue('Cousin')
    await $('form').trigger('submit')
    await vi.waitFor(() => expect(router.currentRoute.value.name).toBe('people'))
    expect(calls.find((c) => c.method === 'POST')?.body).toEqual({
      name: 'Dan',
      email: '',
      notes: 'Cousin',
    })
    expect(toast.success).toHaveBeenCalledWith('Dan saved.')
  })

  it('shows unknown people and load errors', async () => {
    api('owner')
    await renderComponent(PersonEditView, { url: `/l/${LIB}/people/nope/edit` })
    await vi.waitFor(() =>
      expect($('[data-testid=person-load-error]').text()).toBe(
        "This person doesn't exist (anymore).",
      ),
    )
  })

  it('shows a failing people request', async () => {
    mockApi({
      'GET /api/libraries/:id': library('owner'),
      'GET /api/libraries/:id/people': { status: 403, body: { detail: 'Forbidden.' } },
    })
    await renderComponent(PersonEditView, { url: `/l/${LIB}/people/p1/edit` })
    await vi.waitFor(() => expect($('[data-testid=person-load-error]').text()).toBe('Forbidden.'))
  })

  it('does not let viewers save or delete', async () => {
    const calls = api('viewer')
    await renderComponent(PersonEditView, { url: `/l/${LIB}/people/p1/edit` })
    await vi.waitFor(() => expect(value('#person-name')).toBe('Carol'))
    expect(exists('[data-testid=person-delete]')).toBe(false)
    await $('form').trigger('submit')
    await vi.waitFor(() =>
      expect($('[data-testid=edit-error]').text()).toBe('You can only view this library.'),
    )
    expect(calls.some((c) => c.method === 'PATCH')).toBe(false)
  })

  it('shows the 409 message when a person with loans is deleted', async () => {
    let fail = true
    const calls = api('owner', {
      'DELETE /api/libraries/:id/people/:pid': () =>
        fail ? { status: 409, body: { detail: 'Zoe still has loans.' } } : { status: 204 },
    })
    const { router } = await renderComponent(PersonEditView, {
      url: `/l/${LIB}/people/p2/edit`,
    })
    await vi.waitFor(() => expect(exists('[data-testid=person-delete]')).toBe(true))
    await $('[data-testid=person-delete]').trigger('click')
    await vi.waitFor(() => expect(exists('[data-testid=confirm-dialog]')).toBe(true))
    expect(pageText()).toContain('Delete Zoe?')
    await $('[data-testid=confirm-button]').trigger('click')
    await vi.waitFor(() =>
      expect($('[data-testid=confirm-error]').text()).toBe('Zoe still has loans.'),
    )
    fail = false
    await $('[data-testid=confirm-button]').trigger('click')
    await vi.waitFor(() => expect(router.currentRoute.value.name).toBe('people'))
    expect(calls.filter((c) => c.method === 'DELETE')).toHaveLength(2)
    expect(calls.some((c) => c.method === 'PATCH')).toBe(false)
    expect(toast.success).toHaveBeenCalledWith('Zoe deleted.')
  })
})
