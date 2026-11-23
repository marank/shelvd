<script setup lang="ts">
// Loaded lazily (defineAsyncComponent): pulls in the detector only when the camera is used.
import { CameraOff, RotateCcw } from '@lucide/vue'
import { onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { Button } from '@/components/ui/button'
import { Spinner } from '@/components/ui/spinner'
import { useBarcodeScanner } from '../composables/useBarcodeScanner'

const emit = defineEmits<{ detect: [code: string] }>()
const { t } = useI18n()
const video = ref<HTMLVideoElement | null>(null)
const { state, error, start } = useBarcodeScanner({
  video,
  onDetect: (code) => emit('detect', code),
})

onMounted(() => void start())
</script>

<template>
  <div
    class="relative aspect-[4/3] w-full overflow-hidden rounded-lg border bg-muted sm:aspect-video"
    data-testid="camera"
  >
    <video
      ref="video"
      class="size-full object-cover"
      :class="{ invisible: state !== 'scanning' }"
      muted
      playsinline
      autoplay
    />
    <div
      v-if="state === 'scanning'"
      class="pointer-events-none absolute inset-x-[12%] top-1/2 h-1/3 -translate-y-1/2 rounded-md border-2 border-white/80 shadow-[0_0_0_9999px_rgb(0_0_0/0.25)]"
    >
      <div class="absolute inset-x-2 top-1/2 h-px bg-red-500/80" />
    </div>
    <div
      v-if="state === 'starting' || state === 'idle'"
      class="absolute inset-0 flex items-center justify-center gap-2 text-sm text-muted-foreground"
    >
      <Spinner />
      {{ t('add.scan.starting') }}
    </div>
    <div
      v-else-if="state === 'error'"
      class="absolute inset-0 flex flex-col items-center justify-center gap-2 p-4 text-center"
      data-testid="camera-error"
      role="status"
    >
      <CameraOff class="size-6 text-muted-foreground" />
      <p class="max-w-sm text-sm text-balance">
        {{ t(`add.scan.errors.${error ?? 'failed'}`) }}
      </p>
      <p class="max-w-sm text-xs text-muted-foreground">{{ t('add.scan.useField') }}</p>
      <Button
        v-if="error !== 'insecure' && error !== 'unsupported'"
        variant="outline"
        size="sm"
        @click="start()"
      >
        <RotateCcw class="size-3.5" />
        {{ t('actions.retry') }}
      </Button>
    </div>
  </div>
</template>
