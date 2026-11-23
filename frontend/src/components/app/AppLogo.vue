<script setup lang="ts">
// The spine bloom: twelve spines around a disc, long and short alternating.
// Mirrors public/favicon.svg; colours repeat A B C B so the mark is symmetric.
const COLORS = ['#D4537E', '#EF9F27', '#7F77DD', '#EF9F27']
const petals = Array.from({ length: 12 }, (_, k) => ({
  long: k % 2 === 0,
  fill: COLORS[k % 4],
  angle: k * 30,
}))
</script>

<template>
  <svg viewBox="0 0 100 100" role="img" aria-label="shelvd">
    <rect
      v-for="p in petals"
      :key="p.angle"
      x="45.25"
      :y="p.long ? 3 : 10.88"
      width="9.5"
      :height="p.long ? 24.62 : 16.74"
      rx="4.75"
      :fill="p.fill"
      :transform="`rotate(${p.angle} 50 50)`"
    />
    <circle cx="50" cy="50" r="11.09" fill="none" stroke-width="13.59" class="stroke-foreground" />
  </svg>
</template>
