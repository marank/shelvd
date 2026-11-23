import { afterEach, describe, expect, it, vi } from 'vitest'
import { toast } from 'vue-sonner'
import type { Library } from '@/api/types'
import { keys } from '@/features/library/composables/queryKeys'
import { mockApi, pageText, renderComponent } from '@/test/utils'
import LibrarySettingsView from '../views/LibrarySettingsView.vue'
import { $, $$, exists, LIB, library, member } from './fixtures'

vi.mock('vue-sonner', () => ({
  toast: { success: vi.fn<(message: string) => void>(), error: vi.fn<(message: string) => void>() },
}))

const url = `/l/${LIB}/settings`
const members = [
  member({ id: 'm1', username: 'alice', role: 'editor' }),
  member({ id: 'm2', username: 'dave', role: 'viewer' }),
]

function api(lib: Library, extra: Record<string, unknown> = {}) {
  return mockApi({
    'GET /api/libraries/:id': lib,
    'GET /api/libraries/:id/members': members,
    ...extra,
  })
}

afterEach(() => vi.clearAllMocks())

describe('LibrarySettingsView', () => {
  it('shows load errors', async () => {
    mockApi({ 'GET /api/libraries/:id': { status: 404, body: { detail: 'Library not found.' } } })
    await renderComponent(LibrarySettingsView, { url })
    await vi.waitFor(() => expect(pageText()).toContain('Library not found.'))
  })

  it('gives viewers and editors a read-only view and lets them leave', async () => {
    const calls = api(library('editor'), {
      'DELETE /api/libraries/:id/members/:mid': { status: 204 },
      'GET /api/libraries': [],
    })
    const { router, queryClient } = await renderComponent(LibrarySettingsView, { url })
    await vi.waitFor(() => expect($$('[data-testid=member-row]')).toHaveLength(2))
    expect(($('#library-name').element as HTMLInputElement).disabled).toBe(true)
    expect(exists('[data-testid=general-save]')).toBe(false)
    expect(pageText()).toContain('Only the owner can change this.')
    expect($('[data-testid=member-owner]').text()).toContain('bob')
    expect($$('[data-testid=member-role-badge]').map((b) => b.text())).toEqual([
      'Can edit',
      'Can view',
    ])
    expect(exists('[data-testid=member-role]')).toBe(false)
    expect(exists('[data-testid=member-remove]')).toBe(false)
    expect(exists('[data-testid=member-add]')).toBe(false)
    expect(exists('[data-testid=settings-public]')).toBe(false)
    expect(exists('[data-testid=settings-danger]')).toBe(false)
    expect(pageText()).toContain('can also add and change games, places and loans.')

    const invalidate = vi.spyOn(queryClient, 'invalidateQueries')
    await $('[data-testid=leave-library]').trigger('click')
    await vi.waitFor(() => expect(exists('[data-testid=confirm-dialog]')).toBe(true))
    expect(pageText()).toContain('Leave Games?')
    await $('[data-testid=confirm-button]').trigger('click')
    await vi.waitFor(() => expect(router.currentRoute.value.name).toBe('home'))
    expect(calls.find((c) => c.method === 'DELETE')?.path).toBe(`/api/libraries/${LIB}/members/m1`)
    expect(invalidate).toHaveBeenCalledWith({ queryKey: keys.libraries })
  })

  it('hides the import for viewers', async () => {
    api(library('viewer'))
    await renderComponent(LibrarySettingsView, { url })
    await vi.waitFor(() => expect($$('[data-testid=member-row]')).toHaveLength(2))
    expect(exists('[data-testid=settings-import]')).toBe(false)
  })

  it('shows an error when leaving fails', async () => {
    api(library('viewer'), {
      'DELETE /api/libraries/:id/members/:mid': { status: 400, body: { detail: 'Nope.' } },
    })
    await renderComponent(LibrarySettingsView, { url })
    await vi.waitFor(() => expect(exists('[data-testid=leave-library]')).toBe(true))
    await $('[data-testid=leave-library]').trigger('click')
    await vi.waitFor(() => expect(exists('[data-testid=confirm-button]')).toBe(true))
    await $('[data-testid=confirm-button]').trigger('click')
    await vi.waitFor(() => expect($('[data-testid=confirm-error]').text()).toBe('Nope.'))
  })

  it('lets the owner edit name and description', async () => {
    let fail = false
    const calls = api(library('owner'), {
      'PATCH /api/libraries/:id': () =>
        fail ? { status: 400, body: { detail: 'Name required.' } } : library('owner'),
    })
    await renderComponent(LibrarySettingsView, { url })
    await vi.waitFor(() => expect(exists('[data-testid=general-save]')).toBe(true))
    expect(($('#library-description').element as HTMLTextAreaElement).value).toBe('All my games')
    await $('#library-name').setValue('Retro')
    await $('#library-description').setValue('Old stuff')
    await $('[data-testid=general-save]').trigger('click')
    await vi.waitFor(() =>
      expect(calls.find((c) => c.method === 'PATCH')?.body).toEqual({
        name: 'Retro',
        description: 'Old stuff',
        viewer_loans: 'status',
      }),
    )
    await vi.waitFor(() => expect(toast.success).toHaveBeenCalledWith('Saved.'))
    fail = true
    await $('[data-testid=settings-general] form').trigger('submit')
    await vi.waitFor(() => expect(toast.error).toHaveBeenCalledWith('Name required.'))
    await $('#library-name').setValue(' ')
    await $('[data-testid=settings-general] form').trigger('submit')
    expect(calls.filter((c) => c.method === 'PATCH')).toHaveLength(2)
  })

  it('lets the owner add members, change roles and remove them', async () => {
    let addReply: unknown = { status: 404, body: { detail: 'No such user.' } }
    let patchFails = false
    const calls = api(library('owner'), {
      'POST /api/libraries/:id/members': () => addReply,
      'PATCH /api/libraries/:id/members/:mid': () =>
        patchFails ? { status: 400, body: { detail: 'Bad role.' } } : members[1],
      'DELETE /api/libraries/:id/members/:mid': { status: 204 },
    })
    const { router } = await renderComponent(LibrarySettingsView, { url })
    await vi.waitFor(() => expect($$('select[data-testid=member-role]')).toHaveLength(2))
    expect(exists('[data-testid=leave-library]')).toBe(false)
    expect($('[data-testid=member-owner]').text()).toContain('alice')

    await $('[data-testid=member-add]').trigger('submit') // empty: ignored
    expect(calls.some((c) => c.method === 'POST')).toBe(false)
    await $('[data-testid=member-username]').setValue('erin')
    await $('select[data-testid=member-new-role]').setValue('editor')
    await $('[data-testid=member-add]').trigger('submit')
    await vi.waitFor(() => expect($('[data-testid=member-error]').text()).toBe('No such user.'))
    addReply = { status: 409, body: { detail: 'Already a member.' } }
    await $('[data-testid=member-add]').trigger('submit')
    await vi.waitFor(() => expect($('[data-testid=member-error]').text()).toBe('Already a member.'))
    addReply = { status: 201, body: member({ id: 'm3', username: 'erin', role: 'editor' }) }
    await $('[data-testid=member-add]').trigger('submit')
    await vi.waitFor(() =>
      expect(toast.success).toHaveBeenCalledWith('erin can now access this library.'),
    )
    expect(exists('[data-testid=member-error]')).toBe(false)
    expect(calls.filter((c) => c.method === 'POST').at(-1)?.body).toEqual({
      username: 'erin',
      role: 'editor',
    })

    await $$('select[data-testid=member-role]')[1]!.setValue('editor')
    await vi.waitFor(() =>
      expect(calls.find((c) => c.method === 'PATCH')?.body).toEqual({ role: 'editor' }),
    )
    expect(calls.find((c) => c.method === 'PATCH')?.path).toBe(`/api/libraries/${LIB}/members/m2`)
    patchFails = true
    await $$('select[data-testid=member-role]')[1]!.setValue('viewer')
    await vi.waitFor(() => expect(toast.error).toHaveBeenCalledWith('Bad role.'))

    await $$('[data-testid=member-remove]')[1]!.trigger('click')
    await vi.waitFor(() => expect(exists('[data-testid=confirm-dialog]')).toBe(true))
    expect(pageText()).toContain('Remove dave?')
    await $('[data-testid=confirm-button]').trigger('click')
    await vi.waitFor(() => expect(exists('[data-testid=confirm-dialog]')).toBe(false))
    expect(calls.find((c) => c.method === 'DELETE')?.path).toBe(`/api/libraries/${LIB}/members/m2`)
    expect(toast.success).toHaveBeenCalledWith('dave removed.')
    expect(router.currentRoute.value.name).toBe('library-settings')
  })

  it('turns the public link on and off, copies and opens it', async () => {
    let lib = library('owner')
    const writeText = vi
      .fn<(text: string) => Promise<void>>()
      .mockResolvedValueOnce(undefined)
      .mockRejectedValueOnce(new Error('x'))
    Object.defineProperty(navigator, 'clipboard', { value: { writeText }, configurable: true })
    let fail = false
    api(lib, {
      'GET /api/libraries/:id': () => lib,
      'POST /api/libraries/:id/public-link': () => {
        lib = library('owner', { public_token: 'tok123' })
        return lib
      },
      'DELETE /api/libraries/:id/public-link': () => {
        if (fail) return { status: 500, body: { detail: 'Server down.' } }
        lib = library('owner')
        return lib
      },
    })
    await renderComponent(LibrarySettingsView, { url })
    await vi.waitFor(() => expect(exists('[data-testid=public-toggle]')).toBe(true))
    expect(pageText()).toContain('no people, places, prices or notes')
    expect(exists('[data-testid=public-url]')).toBe(false)

    await $('[data-testid=public-toggle]').trigger('click')
    await vi.waitFor(() => expect(exists('[data-testid=public-url]')).toBe(true))
    const link = `${window.location.origin}/share/tok123`
    expect(($('[data-testid=public-url]').element as HTMLInputElement).value).toBe(link)
    expect($('[data-testid=public-open]').attributes('href')).toBe(link)
    expect(toast.success).toHaveBeenCalledWith('Public link created.')
    await $('[data-testid=public-url]').trigger('focus')

    await $('[data-testid=public-copy]').trigger('click')
    await vi.waitFor(() => expect(writeText).toHaveBeenCalledWith(link))
    await vi.waitFor(() => expect(toast.success).toHaveBeenCalledWith('Copied'))
    await $('[data-testid=public-copy]').trigger('click')
    await vi.waitFor(() => expect(toast.error).toHaveBeenCalledWith("Couldn't copy the link."))

    fail = true
    await $('[data-testid=public-toggle]').trigger('click')
    await vi.waitFor(() => expect(toast.error).toHaveBeenCalledWith('Server down.'))
    fail = false
    await $('[data-testid=public-toggle]').trigger('click')
    await vi.waitFor(() => expect(exists('[data-testid=public-url]')).toBe(false))
    expect(toast.success).toHaveBeenCalledWith('Public link turned off.')
  })

  it('deletes the library only after the name was typed', async () => {
    let fail = true
    const calls = api(library('owner'), {
      'DELETE /api/libraries/:id': () =>
        fail ? { status: 409, body: { detail: 'Still busy.' } } : { status: 204 },
      'GET /api/libraries': [],
    })
    const { router, queryClient } = await renderComponent(LibrarySettingsView, { url })
    await vi.waitFor(() => expect(exists('[data-testid=library-delete]')).toBe(true))
    await $('[data-testid=library-delete]').trigger('click')
    await vi.waitFor(() => expect(exists('[data-testid=confirm-name]')).toBe(true))
    expect(pageText()).toContain('Type “Games” to confirm')
    const button = () => $('[data-testid=confirm-button]').element as HTMLButtonElement
    expect(button().disabled).toBe(true)
    await $('[data-testid=confirm-name]').setValue('Game')
    expect(button().disabled).toBe(true)
    await $('[data-testid=confirm-name]').setValue('Games')
    expect(button().disabled).toBe(false)
    await $('[data-testid=confirm-button]').trigger('click')
    await vi.waitFor(() => expect($('[data-testid=confirm-error]').text()).toBe('Still busy.'))

    const invalidate = vi.spyOn(queryClient, 'invalidateQueries')
    fail = false
    await $('[data-testid=confirm-button]').trigger('click')
    await vi.waitFor(() => expect(router.currentRoute.value.name).toBe('home'))
    expect(
      calls.filter((c) => c.method === 'DELETE' && c.path === `/api/libraries/${LIB}`),
    ).toHaveLength(2)
    expect(invalidate).toHaveBeenCalledWith({ queryKey: keys.libraries })
    expect(toast.success).toHaveBeenCalledWith('Games deleted.')
  })
})
