<script setup lang="ts">
import TradingViewChart from "~/components/TradingViewChart.vue"
</script>

<template>
  <div class="w-full border border-white/[0.08] rounded-2xl bg-aave-obsidian overflow-hidden shadow-2xl mt-8 transition-all duration-300 hover:border-aave-violet/40">
    <div class="w-full h-[580px] bg-surface-abyss">
      <TradingViewChart symbol="VN30F1M" interval="1" class="w-full h-full" />
    </div>
  </div>
</template>