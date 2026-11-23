<script setup lang="ts">
// "Diese Ausgabe": what this box is – which version, how many can play it, what's printed
// on it. Publisher and developers are beside the cover; the date is in the head.
import FieldColumns from '@/components/app/FieldColumns.vue'
import type { Item, Release } from '@/api/types'
import type { ItemFieldKey } from '@/lib/itemFields'

defineProps<{ release: Release; item?: Item }>()
const GROUPS: ItemFieldKey[][] = [
  ['platform.name', 'release.region', 'release.edition', 'release.date'],
  ['release.players_offline', 'release.players_online', 'release.age_rating'],
  ['release.barcodes', 'release.product_code', 'release.developers'],
]
</script>

<template>
  <FieldColumns :groups="GROUPS" :release="release" :item="item" />
</template>
