<script setup lang="ts">
import { ref } from "vue"
import { defaultFactors, type FactorItem } from "~/data/factors"

const factors: FactorItem[] = defaultFactors

const activeFactorId = ref<string | null>("f01")
const hoveredFactorId = ref<string | null>(null)

const setActive = (id: string) => {
  activeFactorId.value = activeFactorId.value === id ? null : id
}

const getLineOpacity = (id: string): number => {
  const current = hoveredFactorId.value || activeFactorId.value
  if (!current) return 0.85
  return current === id ? 1 : 0.25
}

const getLineWidth = (id: string): number => {
  const current = hoveredFactorId.value || activeFactorId.value
  if (!current) return 1.8
  return current === id ? 2.6 : 1.4
}
</script>

<template>
  <section id="yeu-to" class="max-w-[1200px] mx-auto px-6 py-20 border-t border-white/[0.06]">
    <!-- Section Header -->
    <div class="mx-auto max-w-3xl text-center mb-10 reveal-item">
      <p class="inline-flex items-center gap-2.5 font-mono text-xs font-bold uppercase tracking-[0.14em] text-aave-violet">
        <span aria-hidden="true" class="h-0.5 w-6 shrink-0 bg-current" />
        <span>Dữ liệu</span>
      </p>
      <h2 class="mt-3 text-2xl sm:text-3xl lg:text-4xl font-bold text-white tracking-tight">
        Hiệu suất tích lũy của các yếu tố
      </h2>
      <div class="mx-auto my-4 h-0.5 w-16 bg-aave-violet/60" />
    </div>

    <!-- Cards Grid -->
    <div class="grid gap-6 lg:grid-cols-[1.05fr_0.95fr] lg:gap-8 items-start">
      <!-- Factor Table Card -->
      <div class="reveal-left overflow-hidden rounded-2xl border border-white/[0.08] bg-aave-obsidian shadow-sm transition-all duration-300 hover:border-aave-violet/30">
        <div class="flex items-center justify-between border-b border-white/[0.06] bg-surface-midnight px-5 py-4">
          <h3 class="text-sm sm:text-base font-bold text-white tracking-tight">
            Bảng theo dõi yếu tố
          </h3>
        </div>

        <div class="overflow-x-auto">
          <table class="w-full border-collapse text-left text-xs sm:text-sm">
            <thead>
              <tr class="border-b border-white/[0.06] text-[11px] font-mono font-bold uppercase tracking-wider text-aave-graphite">
                <th class="px-4 sm:px-5 py-3">Mã</th>
                <th class="px-4 sm:px-5 py-3 text-right">Tích lũy</th>
                <th class="px-4 sm:px-5 py-3 text-right">Biến động</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-white/[0.04]">
              <tr
                v-for="item in factors"
                :key="item.id"
                class="cursor-pointer transition-colors duration-150"
                :class="[
                  (hoveredFactorId === item.id || activeFactorId === item.id)
                    ? 'bg-white/[0.06]'
                    : 'hover:bg-white/[0.03]',
                ]"
                @mouseenter="hoveredFactorId = item.id"
                @mouseleave="hoveredFactorId = null"
                @click="setActive(item.id)"
              >
                <td class="px-4 sm:px-5 py-3.5 font-medium text-white">
                  <span class="inline-flex items-center gap-2.5">
                    <span
                      class="h-2 w-2 rounded-full shrink-0 transition-transform duration-200"
                      :class="(hoveredFactorId === item.id || activeFactorId === item.id) ? 'scale-125' : 'scale-100'"
                      :style="{ backgroundColor: item.color }"
                    />
                    <span>{{ item.code }} · {{ item.name }}</span>
                  </span>
                </td>
                <td class="px-4 sm:px-5 py-3.5 text-right font-mono font-semibold text-quant-bull tabular-nums">
                  {{ item.cumulative }}
                </td>
                <td class="px-4 sm:px-5 py-3.5 text-right font-mono font-semibold text-quant-bull tabular-nums">
                  {{ item.volatility }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- Chart Card -->
      <div class="reveal-right overflow-hidden rounded-2xl border border-white/[0.08] bg-aave-obsidian shadow-sm transition-all duration-300 hover:border-aave-violet/30" style="--reveal-delay: 150ms">
        <div class="flex items-center justify-between border-b border-white/[0.06] bg-surface-midnight px-5 py-4">
          <h3 class="text-sm sm:text-base font-bold text-white tracking-tight">
            Hiệu suất tích lũy
          </h3>
        </div>

        <div class="p-5">
          <!-- SVG Multi-line Graph -->
          <svg
            viewBox="0 0 520 210"
            class="h-auto w-full select-none"
            role="img"
            aria-label="Cumulative return chart"
          >
            <!-- Grid Lines -->
            <g class="stroke-white/[0.08]">
              <line x1="52" y1="190" x2="512" y2="190" stroke-width="1" />
              <line x1="52" y1="144.23" x2="512" y2="144.23" stroke-width="1" />
              <line x1="52" y1="101" x2="512" y2="101" stroke-width="1" />
              <line x1="52" y1="55.23" x2="512" y2="55.23" stroke-width="1" />
              <line x1="52" y1="12" x2="512" y2="12" stroke-width="1" />
            </g>

            <!-- Axis Labels -->
            <g stroke="none" fill="currentColor" class="text-aave-graphite font-mono font-bold">
              <text x="44" y="190" text-anchor="end" dominant-baseline="central" font-size="12">-10%</text>
              <text x="44" y="144.23" text-anchor="end" dominant-baseline="central" font-size="12">+8%</text>
              <text x="44" y="101" text-anchor="end" dominant-baseline="central" font-size="12">+25%</text>
              <text x="44" y="55.23" text-anchor="end" dominant-baseline="central" font-size="12">+43%</text>
              <text x="44" y="12" text-anchor="end" dominant-baseline="central" font-size="12">+60%</text>
            </g>

            <!-- Factor Trend Paths -->
            <g>
              <g
                v-for="item in factors"
                :key="`path-${item.id}`"
                :style="{
                  opacity: getLineOpacity(item.id),
                  transition: 'opacity 0.25s ease',
                }"
              >
                <path
                  :d="item.path"
                  fill="none"
                  pathLength="100"
                  class="chart-line-path"
                  :stroke="item.color"
                  :stroke-width="getLineWidth(item.id)"
                  stroke-linecap="round"
                  stroke-linejoin="round"
                />
              </g>
            </g>
          </svg>

          <!-- Legend Items -->
          <div class="mt-5 grid grid-cols-2 gap-2 text-xs text-aave-ash sm:grid-cols-3">
            <button
              v-for="item in factors"
              :key="`legend-${item.id}`"
              type="button"
              class="inline-flex items-center gap-2 rounded-lg px-2 py-1.5 transition-all text-left focus:outline-none"
              :class="[
                (hoveredFactorId === item.id || activeFactorId === item.id)
                  ? 'bg-white/[0.08] text-white'
                  : 'hover:bg-white/[0.04]',
              ]"
              @mouseenter="hoveredFactorId = item.id"
              @mouseleave="hoveredFactorId = null"
              @click="setActive(item.id)"
            >
              <span
                class="h-1 w-5 shrink-0 rounded-sm transition-transform duration-200"
                :class="(hoveredFactorId === item.id || activeFactorId === item.id) ? 'scale-x-110' : 'scale-x-80'"
                :style="{ backgroundColor: item.color }"
              />
              <span class="truncate">{{ item.code }} · {{ item.name }}</span>
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Bottom Disclaimer -->
    <p class="mt-6 text-xs text-center text-aave-graphite">
      Dữ liệu chỉ minh họa phương pháp nghiên cứu. Không phản ánh kết quả đầu tư hay tư vấn đầu tư.
    </p>
  </section>
</template>
