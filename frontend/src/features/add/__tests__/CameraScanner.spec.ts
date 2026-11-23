import { describe, expect, it, vi } from 'vitest'
import { renderComponent, settle } from '@/test/utils'
import CameraScanner from '../components/CameraScanner.vue'
import { $, $$, click } from './fixtures'

vi.mock('../lib/detector', () => ({
  createDetector: () =>
    Promise.resolve({ detect: () => Promise.resolve([{ rawValue: '4006381333931' }]) }),
}))

function stubCamera(getUserMedia: () => Promise<unknown>) {
  vi.stubGlobal('isSecureContext', true)
  Object.defineProperty(navigator, 'mediaDevices', {
    value: { getUserMedia: vi.fn<() => Promise<unknown>>(getUserMedia) },
    configurable: true,
  })
  vi.spyOn(HTMLMediaElement.prototype, 'play').mockResolvedValue(undefined)
  Object.defineProperty(HTMLMediaElement.prototype, 'readyState', {
    get: () => 4,
    configurable: true,
  })
}

describe('CameraScanner', () => {
  it('shows the stream with a frame and emits detected codes', async () => {
    const stop = vi.fn<() => void>()
    stubCamera(() => Promise.resolve({ getTracks: () => [{ stop }] }))
    const onDetect = vi.fn<(code: string) => void>()
    const { wrapper } = await renderComponent(CameraScanner, { props: { onDetect } })
    await vi.waitFor(() => expect(onDetect).toHaveBeenCalledWith('4006381333931'))
    expect(onDetect).toHaveBeenCalledTimes(1)
    expect($('video').classList.contains('invisible')).toBe(false)
    wrapper.unmount()
    expect(stop).toHaveBeenCalled()
  })

  it('explains a denied permission and retries', async () => {
    let calls = 0
    stubCamera(() => {
      calls++
      return Promise.reject(Object.assign(new Error('denied'), { name: 'NotAllowedError' }))
    })
    await renderComponent(CameraScanner)
    await vi.waitFor(() =>
      expect($('[data-testid="camera-error"]').textContent).toContain('denied'),
    )
    click($$('[data-testid="camera-error"] button')[0]!)
    await settle()
    expect(calls).toBe(2)
  })

  it('offers no retry when the browser cannot use a camera at all', async () => {
    vi.stubGlobal('isSecureContext', true)
    Object.defineProperty(navigator, 'mediaDevices', { value: undefined, configurable: true })
    await renderComponent(CameraScanner, { locale: 'de' })
    await vi.waitFor(() =>
      expect($('[data-testid="camera-error"]').textContent).toContain('Kamera'),
    )
    expect($$('[data-testid="camera-error"] button')).toHaveLength(0)
  })
})
