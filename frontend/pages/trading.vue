<template>
  <div class="space-y-5">
    <a href="#trading-content" class="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-50 focus:rounded-md focus:bg-aave-violet focus:px-3 focus:py-2 focus:text-aave-charcoal">Bỏ qua đến nội dung giao dịch</a>
    <header class="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
      <div><p class="text-[10px] uppercase tracking-wider text-aave-violet">Quantitative Trading Cockpit</p><h1 class="mt-1 text-2xl font-semibold text-aave-paper">Trạm điều hành giao dịch mô phỏng</h1><p class="mt-1 max-w-2xl text-sm text-aave-graphite">Telemetry, dòng tiền, kịch bản xác suất và paper trading trong cùng một workspace.</p></div>
      <SimulationWarningBadge />
    </header>
    <div id="trading-content" class="flex gap-1 overflow-x-auto border-b border-white/[0.08]" role="tablist" aria-label="Các màn hình cockpit">
      <button v-for="tab in tabs" :key="tab.id" :id="`tab-${tab.id}`" role="tab" :aria-selected="activeTab === tab.id" :aria-controls="`panel-${tab.id}`" class="min-h-11 whitespace-nowrap px-3 text-xs font-semibold focus-visible:outline focus-visible:outline-2 focus-visible:outline-aave-violet" :class="activeTab === tab.id ? 'border-b-2 border-aave-violet text-aave-violet' : 'text-aave-graphite hover:text-aave-ash'" @click="activeTab = tab.id">{{ tab.label }}</button>
    </div>
    <main :id="`panel-${activeTab}`" role="tabpanel" :aria-labelledby="`tab-${activeTab}`">
      <DerivativesStation v-if="activeTab === 'derivatives'" /><FlowRadar v-else-if="activeTab === 'flow'" /><PredictionTerminal v-else-if="activeTab === 'prediction'" /><PaperCockpit v-else />
    </main>
  </div>
</template>
<script setup lang="ts">
useHead({ title: "Trading Cockpit - Vnstock Quants" })
const activeTab = shallowRef<"derivatives" | "flow" | "prediction" | "paper">(
  "derivatives",
)
const tabs = [
  { id: "derivatives", label: "Phái sinh Live" },
  { id: "flow", label: "Radar dòng tiền" },
  { id: "prediction", label: "ATC và T+1" },
  { id: "paper", label: "Paper Cockpit" },
] as const
</script>
