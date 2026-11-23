<script setup lang="ts">
import { Check, ImageOff } from '@lucide/vue'
import { useI18n } from 'vue-i18n'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Spinner } from '@/components/ui/spinner'
import { imagePreviewUrl, type ImageTarget } from '../composables/useTermPages'

/** A picture to choose (preview through the server): a term takes it with a click on the
 * tile, a platform as its logo, photo or badge icon with one of three buttons. */
const props = defineProps<{
  candidate: { source: string; label: string; kind: string; token: string }
  sourceLabel: string
  targets: ImageTarget[] | null // null: the whole tile takes it as the picture
  taking: boolean
  disabled: boolean
  broken: boolean
}>()
const emit = defineEmits<{ take: [target: ImageTarget]; broken: [] }>()
const { t } = useI18n()
const testid = `term-image-${props.candidate.source}`
</script>

<template>
  <div v-if="targets" class="grid gap-2 rounded-lg border bg-card p-2" :data-testid="testid">
    <span
      class="relative grid grid-cols-1 grid-rows-1 aspect-[4/3] place-items-center rounded-md bg-muted/40 p-3"
    >
      <ImageOff v-if="broken" class="size-6 text-muted-foreground/60" />
      <img
        v-else
        :src="imagePreviewUrl(candidate.token)"
        alt=""
        loading="lazy"
        class="max-h-full max-w-full object-contain"
        @error="emit('broken')"
      />
      <Spinner v-if="taking" class="absolute" />
    </span>
    <span class="line-clamp-2 text-xs">
      {{ broken ? t('terms.images.broken') : candidate.label || '–' }}
    </span>
    <span class="flex flex-wrap gap-1">
      <Badge variant="outline" class="font-normal">{{ sourceLabel }}</Badge>
      <Badge variant="secondary" class="font-normal">
        {{ t(`terms.images.kinds.${candidate.kind}`) }}
      </Badge>
    </span>
    <span class="grid grid-cols-3 gap-1">
      <Button
        v-for="target in targets"
        :key="target"
        size="sm"
        variant="outline"
        class="px-1 text-xs"
        :disabled="disabled || broken"
        :data-testid="`take-${target}-${candidate.source}`"
        @click="emit('take', target)"
      >
        {{ t(`terms.images.as.${target}`) }}
      </Button>
    </span>
  </div>
  <button
    v-else
    type="button"
    class="group grid w-full gap-2 rounded-lg border bg-card p-2 text-left transition-colors hover:border-primary disabled:opacity-60"
    :disabled="disabled || broken"
    :data-testid="testid"
    @click="emit('take', 'image')"
  >
    <span
      class="relative grid grid-cols-1 grid-rows-1 aspect-[4/3] place-items-center rounded-md bg-muted/40 p-3"
    >
      <ImageOff v-if="broken" class="size-6 text-muted-foreground/60" />
      <img
        v-else
        :src="imagePreviewUrl(candidate.token)"
        alt=""
        loading="lazy"
        class="max-h-full max-w-full object-contain"
        @error="emit('broken')"
      />
      <Spinner v-if="taking" class="absolute" />
      <Check
        v-else
        class="absolute top-1.5 right-1.5 size-4 text-primary opacity-0 transition-opacity group-hover:opacity-100"
      />
    </span>
    <span class="grid gap-1">
      <span class="line-clamp-2 text-xs">
        {{ broken ? t('terms.images.broken') : candidate.label || '–' }}
      </span>
      <Badge variant="outline" class="w-fit font-normal">{{ sourceLabel }}</Badge>
    </span>
  </button>
</template>
