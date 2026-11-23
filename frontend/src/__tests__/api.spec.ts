import { describe, expect, it, vi } from 'vitest'
import {
  csrfMiddleware,
  setApiLanguage,
  setUnauthorizedHandler,
  unauthorizedMiddleware,
} from '@/api/client'
import { ensureCsrf, getCsrfToken } from '@/api/csrf'
import { ApiError, unwrap } from '@/api/errors'

type Hook = (options: { request: Request; response?: Response }) => unknown

describe('api', () => {
  it('reads and fetches the CSRF cookie', async () => {
    const fetch = vi.fn<typeof globalThis.fetch>(() =>
      Promise.resolve(new Response(null, { status: 204 })),
    )
    vi.stubGlobal('fetch', fetch)
    expect(getCsrfToken()).toBeUndefined()
    await ensureCsrf()
    expect(fetch).toHaveBeenCalledWith('/api/auth/csrf', { credentials: 'same-origin' })
    document.cookie = 'csrftoken=abc'
    expect(getCsrfToken()).toBe('abc')
    await ensureCsrf()
    expect(fetch).toHaveBeenCalledTimes(1)
  })

  it('sends the CSRF token and language on unsafe requests', () => {
    document.cookie = 'csrftoken=tok'
    setApiLanguage('en')
    const onRequest = csrfMiddleware.onRequest as Hook
    const post = onRequest({
      request: new Request('http://x/api/a', { method: 'POST' }),
    }) as Request
    expect(post.headers.get('X-CSRFToken')).toBe('tok')
    expect(post.headers.get('Accept-Language')).toBe('en')
    const get = onRequest({ request: new Request('http://x/api/a') }) as Request
    expect(get.headers.get('X-CSRFToken')).toBeNull()
  })

  it('reports 401 except for the boot-time /me check', () => {
    const handler = vi.fn<() => void>()
    setUnauthorizedHandler(handler)
    const onResponse = unauthorizedMiddleware.onResponse as Hook
    onResponse({
      request: new Request('http://x/api/auth/me'),
      response: new Response(null, { status: 401 }),
    })
    expect(handler).not.toHaveBeenCalled()
    onResponse({
      request: new Request('http://x/api/items'),
      response: new Response(null, { status: 401 }),
    })
    expect(handler).toHaveBeenCalledOnce()
    onResponse({
      request: new Request('http://x/api/items'),
      response: new Response(null, { status: 200 }),
    })
    expect(handler).toHaveBeenCalledOnce()
  })

  it('unwraps data and turns errors into ApiError messages', async () => {
    const ok = { data: { a: 1 }, response: new Response('{}', { status: 200 }) }
    expect(await unwrap(Promise.resolve(ok))).toEqual({ a: 1 })
    const detail = { error: { detail: 'Nope.' }, response: new Response('', { status: 400 }) }
    await expect(unwrap(Promise.resolve(detail))).rejects.toThrow('Nope.')
    const validation = {
      error: { detail: [{ msg: 'field required' }, 'other'] },
      response: new Response('', { status: 422 }),
    }
    await expect(unwrap(Promise.resolve(validation))).rejects.toThrow('field required, other')
    const bare = { error: 'x', response: new Response('', { status: 500, statusText: 'Boom' }) }
    const error = await unwrap(Promise.resolve(bare)).catch((e: unknown) => e)
    expect(error).toBeInstanceOf(ApiError)
    expect((error as ApiError).status).toBe(500)
    expect((error as ApiError).message).toBe('Boom')
  })
})
