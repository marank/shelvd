import { onBeforeUnmount, ref, shallowRef, type Ref } from 'vue'
import type { Detector } from '../lib/detector'

export type ScannerState = 'idle' | 'starting' | 'scanning' | 'error'
/** Why the camera can't be used; each has a friendly message in the UI. */
export type ScannerError = 'insecure' | 'unsupported' | 'denied' | 'no-camera' | 'failed'

export interface ScannerOptions {
  /** The <video> element the camera stream is shown in (and frames are read from). */
  video: Ref<HTMLVideoElement | null>
  onDetect: (code: string) => void
  /** Ignore the same code again within this many milliseconds. */
  repeatMs?: number
  /** Pause between detection attempts. */
  intervalMs?: number
  createDetector?: () => Promise<Detector>
}

async function defaultDetector(): Promise<Detector> {
  const { createDetector } = await import('../lib/detector')
  return createDetector()
}

function errorOf(error: unknown): ScannerError {
  const name = (error as { name?: string } | null)?.name
  if (name === 'NotAllowedError' || name === 'SecurityError') return 'denied'
  if (name === 'NotFoundError' || name === 'OverconstrainedError') return 'no-camera'
  return 'failed'
}

/** Camera stream + detection loop. The camera stops on stop() and on unmount. */
export function useBarcodeScanner(options: ScannerOptions) {
  const { video, onDetect, repeatMs = 2500, intervalMs = 150 } = options
  const createDetector = options.createDetector ?? defaultDetector
  const state = ref<ScannerState>('idle')
  const error = ref<ScannerError | null>(null)
  const stream = shallowRef<MediaStream | null>(null)
  let detector: Detector | null = null
  let timer: ReturnType<typeof setTimeout> | undefined
  let session = 0
  let last = { code: '', at: 0 }

  function fail(reason: ScannerError) {
    stop()
    state.value = 'error'
    error.value = reason
  }

  function emitOnce(code: string) {
    const now = Date.now()
    if (code === last.code && now - last.at < repeatMs) return
    last = { code, at: now }
    onDetect(code)
  }

  async function tick(current: number) {
    if (current !== session) return
    const element = video.value
    if (detector && element && element.readyState >= 2) {
      try {
        const found = await detector.detect(element)
        if (current !== session) return
        const code = found.find((b) => b.rawValue)?.rawValue
        if (code) emitOnce(code)
      } catch {
        // A frame that can't be read (e.g. while resizing): try the next one.
      }
    }
    if (current === session) timer = setTimeout(() => void tick(current), intervalMs)
  }

  async function start(): Promise<void> {
    stop()
    const current = ++session
    error.value = null
    if (!window.isSecureContext) return fail('insecure')
    // eslint-disable-next-line @typescript-eslint/no-unnecessary-condition -- missing in old browsers and some embedded views despite the DOM types
    if (!navigator.mediaDevices?.getUserMedia) return fail('unsupported')
    state.value = 'starting'
    try {
      const media = await navigator.mediaDevices.getUserMedia({
        audio: false,
        video: { facingMode: { ideal: 'environment' } },
      })
      if (current !== session) {
        media.getTracks().forEach((track) => track.stop())
        return
      }
      stream.value = media
      const element = video.value
      if (element) {
        element.srcObject = media
        element.muted = true
        element.setAttribute('playsinline', '')
        await element.play().catch(() => undefined)
      }
      detector = await createDetector()
      if (current !== session) return
      state.value = 'scanning'
      void tick(current)
    } catch (e) {
      if (current === session) fail(errorOf(e))
    }
  }

  function stop(): void {
    session++
    clearTimeout(timer)
    stream.value?.getTracks().forEach((track) => track.stop())
    stream.value = null
    if (video.value) video.value.srcObject = null
    if (state.value !== 'error') state.value = 'idle'
  }

  onBeforeUnmount(stop)

  return { state, error, stream, start, stop }
}
