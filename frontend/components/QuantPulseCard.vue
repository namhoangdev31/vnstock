<script setup lang="ts">
import TradingViewChart from "~/components/TradingViewChart.vue"
</script>

<template>
  <div class="w-full h-[620px] border border-zinc-800 rounded bg-zinc-950 overflow-hidden shadow-2xl mt-8">
    <TradingViewChart symbol="VN30F1M" interval="1" class="w-full h-full" />
  </div>
</template>