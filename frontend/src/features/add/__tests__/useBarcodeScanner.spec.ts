import { mount } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { defineComponent, h, ref, type VNode } from 'vue'
import type { Detector } from '../lib/detector'
import { useBarcodeScanner, type ScannerOptions } from '../composables/useBarcodeScanner'

vi.mock('../lib/detector', () => ({
  createDetector: vi.fn<() => Promise<Detector>>(() =>
    Promise.resolve({ detect: () => Promise.resolve([{ rawValue: '111' }]) }),
  ),
}))

function fakeStream() {
  const track = { stop: vi.fn<() => void>() }
  return { track, stream: { getTracks: () => [track] } as unknown as MediaStream }
}

/** Mounts a component that runs the composable in its setup and renders `render`. */
function mountHost(run: () => void, render: () => VNode) {
  return mount(
    defineComponent({
      setup() {
        run()
        return render
      },
    }),
  )
}

function setup(options: Partial<ScannerOptions> = {}) {
  const onDetect = vi.fn<(code: string) => void>()
  let api!: ReturnType<typeof useBarcodeScanner>
  const video = ref<HTMLVideoElement | null>(null)
  const wrapper = mountHost(
    () => (api = useBarcodeScanner({ video, onDetect, intervalMs: 5, ...options })),
    () => h('video', { ref: video }),
  )
  const element = wrapper.find('video').element as HTMLVideoElement
  Object.defineProperty(element, 'readyState', { value: 4, configurable: true })
  return { wrapper, api: () => api, onDetect, video: element }
}

function stubMedia(getUserMedia: () => Promise<MediaStream>) {
  vi.stubGlobal('isSecureContext', true)
  Object.defineProperty(navigator, 'mediaDevices', {
    value: { getUserMedia: vi.fn<() => Promise<MediaStream>>(getUserMedia) },
    configurable: true,
  })
}

beforeEach(() => {
  vi.spyOn(HTMLMediaElement.prototype, 'play').mockResolvedValue(undefined)
})

afterEach(() => {
  Object.defineProperty(navigator, 'mediaDevices', { value: undefined, configurable: true })
  vi.restoreAllMocks()
})

describe('useBarcodeScanner', () => {
  it('refuses insecure contexts', async () => {
    vi.stubGlobal('isSecureContext', false)
    const { api } = setup()
    await api().start()
    expect(api().state.value).toBe('error')
    expect(api().error.value).toBe('insecure')
  })

  it('reports a browser without getUserMedia', async () => {
    vi.stubGlobal('isSecureContext', true)
    const { api } = setup()
    await api().start()
    expect(api().error.value).toBe('unsupported')
  })

  it.each([
    ['NotAllowedError', 'denied'],
    ['SecurityError', 'denied'],
    ['NotFoundError', 'no-camera'],
    ['OverconstrainedError', 'no-camera'],
    ['AbortError', 'failed'],
  ])('maps %s to %s', async (name, expected) => {
    stubMedia(() => Promise.reject(Object.assign(new Error(name), { name })))
    const { api } = setup()
    await api().start()
    expect(api().state.value).toBe('error')
    expect(api().error.value).toBe(expected)
  })

  it('maps non-errors to failed', async () => {
    // eslint-disable-next-line @typescript-eslint/prefer-promise-reject-errors -- the case under test: a rejection that isn't an Error
    stubMedia(() => Promise.reject(null))
    const { api } = setup()
    await api().start()
    expect(api().error.value).toBe('failed')
  })

  it('scans, debounces repeated codes and stops the camera on unmount', async () => {
    const { track, stream } = fakeStream()
    stubMedia(() => Promise.resolve(stream))
    const codes = ['', '4006381333931', '4006381333931', 'broken', '5000000000000']
    const detector: Detector = {
      detect: vi.fn<Detector['detect']>(() => {
        const next = codes.shift()
        if (next === undefined) return Promise.resolve([])
        if (next === 'broken') return Promise.reject(new Error('frame'))
        return Promise.resolve(next ? [{ rawValue: next }] : [])
      }),
    }
    const { api, onDetect, video, wrapper } = setup({
      createDetector: () => Promise.resolve(detector),
    })
    await api().start()
    expect(api().state.value).toBe('scanning')
    expect(video.srcObject).toBe(stream)
    await vi.waitFor(() => expect(onDetect).toHaveBeenCalledTimes(2))
    expect(onDetect.mock.calls).toEqual([['4006381333931'], ['5000000000000']])

    wrapper.unmount()
    expect(track.stop).toHaveBeenCalled()
    expect(api().state.value).toBe('idle')
    expect(api().stream.value).toBeNull()
  })

  it('emits the same code again after the repeat window', async () => {
    const { stream } = fakeStream()
    stubMedia(() => Promise.resolve(stream))
    const detector: Detector = { detect: () => Promise.resolve([{ rawValue: '123' }]) }
    const { api, onDetect } = setup({
      createDetector: () => Promise.resolve(detector),
      repeatMs: 0,
    })
    await api().start()
    await vi.waitFor(() => expect(onDetect.mock.calls.length).toBeGreaterThan(1))
    api().stop()
  })

  it('skips frames until the video has data', async () => {
    const { stream } = fakeStream()
    stubMedia(() => Promise.resolve(stream))
    const detect = vi.fn<Detector['detect']>(() => Promise.resolve([]))
    const { api, video } = setup({ createDetector: () => Promise.resolve({ detect }) })
    Object.defineProperty(video, 'readyState', { value: 0, configurable: true })
    await api().start()
    await new Promise((r) => setTimeout(r, 30))
    expect(detect).not.toHaveBeenCalled()
    api().stop()
  })

  it('drops a stream that arrives after stop()', async () => {
    const { track, stream } = fakeStream()
    let resolve!: (s: MediaStream) => void
    stubMedia(() => new Promise((r) => (resolve = r)))
    const { api } = setup()
    const started = api().start()
    api().stop()
    resolve(stream)
    await started
    expect(track.stop).toHaveBeenCalled()
    expect(api().state.value).toBe('idle')
  })

  it('stops when stopped while the detector loads', async () => {
    const { stream } = fakeStream()
    stubMedia(() => Promise.resolve(stream))
    let resolve!: (d: Detector) => void
    const { api } = setup({ createDetector: () => new Promise((r) => (resolve = r)) })
    const started = api().start()
    await vi.waitFor(() => expect(resolve).toBeTypeOf('function'))
    api().stop()
    resolve({ detect: () => Promise.resolve([]) })
    await started
    expect(api().state.value).toBe('idle')
  })

  it('ignores a detection that finishes after stop()', async () => {
    const { stream } = fakeStream()
    stubMedia(() => Promise.resolve(stream))
    let finish!: (v: Array<{ rawValue: string }>) => void
    const detect = vi.fn<Detector['detect']>(
      () => new Promise<Array<{ rawValue: string }>>((r) => (finish = r)),
    )
    const { api, onDetect } = setup({ createDetector: () => Promise.resolve({ detect }) })
    await api().start()
    await vi.waitFor(() => expect(detect).toHaveBeenCalled())
    api().stop()
    finish([{ rawValue: '1' }])
    await new Promise((r) => setTimeout(r, 10))
    expect(onDetect).not.toHaveBeenCalled()
  })

  it('loads the default detector lazily', async () => {
    const { stream } = fakeStream()
    stubMedia(() => Promise.resolve(stream))
    const { api, onDetect } = setup()
    await api().start()
    await vi.waitFor(() => expect(onDetect).toHaveBeenCalledWith('111'))
    api().stop()
  })

  it('works without a video element', async () => {
    const { stream } = fakeStream()
    stubMedia(() => Promise.resolve(stream))
    const onDetect = vi.fn<(code: string) => void>()
    let api!: ReturnType<typeof useBarcodeScanner>
    const wrapper = mountHost(
      () => (api = useBarcodeScanner({ video: ref(null), onDetect, intervalMs: 5 })),
      () => h('div'),
    )
    await api.start()
    expect(api.state.value).toBe('scanning')
    wrapper.unmount()
  })
})
