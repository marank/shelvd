import { describe, expect, it, vi } from 'vitest'
import { createMemoryHistory, createRouter } from 'vue-router'
import { installChunkReload } from '@/router'

function setup(load: () => Promise<unknown>) {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/', component: { render: () => null } },
      { path: '/lazy', component: load as never },
    ],
  })
  const reload = vi.fn<(url: string) => void>()
  installChunkReload(router, reload)
  return { router, reload }
}

describe('chunk reload', () => {
  it('reloads once when a lazy page fails to load, not in a loop', async () => {
    const fail = () =>
      Promise.reject(new TypeError('error loading dynamically imported module: /x.js'))
    const { router, reload } = setup(fail)
    await router.push('/lazy').catch(() => {})
    expect(reload).toHaveBeenCalledWith('/lazy')
    await router.push('/lazy').catch(() => {})
    expect(reload).toHaveBeenCalledTimes(1)
    // A successful navigation resets the guard.
    await router.push('/')
    await router.push('/lazy').catch(() => {})
    expect(reload).toHaveBeenCalledTimes(2)
  })

  it('leaves other errors alone', async () => {
    const { router, reload } = setup(() => Promise.reject(new Error('boom')))
    await expect(router.push('/lazy')).rejects.toThrow('boom')
    expect(reload).not.toHaveBeenCalled()
  })

  it('still reloads when storage is blocked', async () => {
    const spy = vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => {
      throw new Error('blocked')
    })
    const { router, reload } = setup(() =>
      Promise.reject(new TypeError('Failed to fetch dynamically imported module')),
    )
    await router.push('/lazy').catch(() => {})
    expect(reload).toHaveBeenCalledOnce()
    spy.mockRestore()
  })
})
