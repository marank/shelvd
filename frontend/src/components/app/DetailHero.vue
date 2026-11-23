<script setup lang="ts">
import { EllipsisVertical } from '@lucide/vue'
import CoverImage from '@/components/app/CoverImage.vue'
import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { Skeleton } from '@/components/ui/skeleton'

/** The top of every detail page (game, release, copy, term): cover left (above on
 * phones) – or the `visual` slot instead –, badges, the title with the page's actions
 * menu, then whatever the level adds. */
defineProps<{
  title: string
  cover?: { src: string | null; aspect: number | null }
  manufacturer?: string
  /** Wait with the cover (it may still change). */
  coverPending?: boolean
  menuLabel: string
  testid: string
  /** Muted beside the title, e.g. a release's number ("#129"). */
  suffix?: string
}>()
</script>

<template>
  <section class="flex flex-col gap-5 @lg:flex-row" :data-testid="`${testid}-hero`">
    <slot v-if="$slots.visual" name="visual" />
    <Skeleton
      v-else-if="coverPending"
      data-testid="cover-pending"
      class="aspect-[5/7] h-80 shrink-0 self-center @lg:h-64 @lg:self-start @3xl:h-80"
    />
    <CoverImage
      v-else-if="cover"
      :src="cover.src"
      :aspect="cover.aspect"
      :title="title"
      :manufacturer="manufacturer"
      size-by="height"
      class="h-80 max-w-full shrink-0 self-center shadow-md @lg:h-64 @lg:self-start @3xl:h-80"
    />
    <div class="min-w-0 flex-1 space-y-3">
      <div v-if="$slots.badges" class="flex flex-wrap items-center gap-1.5">
        <slot name="badges" />
      </div>
      <!-- What this is and where it belongs ("Eine Ausgabe von …"). -->
      <p
        v-if="$slots.kicker"
        class="flex flex-wrap items-center gap-1.5 font-mono text-[11px] tracking-wider text-muted-foreground uppercase"
        :data-testid="`${testid}-kicker`"
      >
        <slot name="kicker" />
      </p>
      <div class="flex items-start gap-2">
        <h1
          class="min-w-0 flex-1 text-2xl leading-tight font-bold tracking-tight @lg:text-3xl"
          :data-testid="`${testid}-title`"
        >
          {{ title }}
          <span
            v-if="suffix"
            class="ml-1 font-normal text-muted-foreground"
            :data-testid="`${testid}-suffix`"
            >{{ suffix }}</span
          >
        </h1>
        <DropdownMenu v-if="$slots.menu">
          <DropdownMenuTrigger as-child>
            <Button
              variant="ghost"
              size="icon-sm"
              class="mt-0.5"
              :aria-label="menuLabel"
              :data-testid="`${testid}-menu`"
            >
              <EllipsisVertical class="size-4" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" class="w-64">
            <slot name="menu" />
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
      <slot />
    </div>
  </section>
</template>
