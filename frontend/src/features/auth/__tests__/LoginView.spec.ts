import { describe, expect, it, vi } from 'vitest'
import { SOURCE_URL } from '@/lib/source'
import { mockApi, pageText, renderApp, settle, testUser } from '@/test/utils'

describe('login', () => {
  it('redirects anonymous users to the login page and back after signing in', async () => {
    const calls = mockApi({
      'POST /api/auth/login': ({ body }: { body: unknown }) =>
        (body as { password: string }).password === 'right'
          ? testUser
          : { status: 400, body: { detail: 'Invalid username or password.' } },
      'GET /api/libraries': [],
    })
    const { router, wrapper } = await renderApp('/lists', { user: null })
    expect(router.currentRoute.value.name).toBe('login')
    expect(router.currentRoute.value.query.next).toBe('/lists')
    // The AGPL's offer of the source, already before signing in.
    const source = document.querySelector('[data-testid="source-link"]')!
    expect(source.textContent).toContain('free software (AGPL-3.0)')
    expect(source.querySelector('a')!.getAttribute('href')).toBe(SOURCE_URL)

    await wrapper.find('#username').setValue('alice')
    await wrapper.find('#password').setValue('wrong')
    await wrapper.find('form').trigger('submit')
    await settle()
    expect(pageText()).toContain('Invalid username or password.')

    await wrapper.find('#password').setValue('right')
    await wrapper.find('form').trigger('submit')
    await vi.waitFor(() => expect(router.currentRoute.value.fullPath).toBe('/lists'))
    expect(calls.filter((c) => c.path === '/api/auth/login')).toHaveLength(2)
  })

  it('registers a new account', async () => {
    mockApi({
      'POST /api/auth/register': { status: 201, body: testUser },
      'GET /api/libraries': [],
    })
    const { router, wrapper } = await renderApp('/register', { user: null })
    await wrapper.find('#username').setValue('alice')
    await wrapper.find('#email').setValue('a@example.com')
    await wrapper.find('#password').setValue('long-password')
    await wrapper.find('form').trigger('submit')
    await vi.waitFor(() => expect(router.currentRoute.value.name).toBe('home'))
  })
})
