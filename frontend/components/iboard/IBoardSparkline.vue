<script setup lang="ts">
import { computed } from "vue"
import type { SparklineGeometry, StockRowDisplay } from "./types"

const props = withDefaults(
  defineProps<{
    stk: StockRowDisplay
    width?: number
    height?: number
  }>(),
  {
    width: 72,
    height: 26,
  },
)

const sparkCache = new Map<string, SparklineGeometry>()

const geometry = computed<SparklineGeometry>(() => {
  const stk = props.stk
  const width = props.width
  const height = props.height

  const cacheKey = `${stk.symbol}_${stk.lastPrice}_${stk.refPrice}_${stk.sparkline?.length || 0}`
  const cached = sparkCache.get(cacheKey)
  if (cached) return cached

  const midY = height / 2.0
  const ref = stk.refPrice || stk.lastPrice || 100
  const last = stk.lastPrice || ref
  const chg = last - ref

  let points: number[] = []
  if (stk.sparkline && stk.sparkline.length >= 4) {
    points = [...stk.sparkline]
  } else {
    const n = 14
    const high = stk.highPrice > 0 ? stk.highPrice : Math.max(ref, last)
    const low = stk.lowPrice > 0 ? stk.lowPrice : Math.min(ref, last)
    const seed = (stk.symbol || "SEC")
      .split("")
      .reduce((acc, c) => acc + c.charCodeAt(0), 0)

    for (let i = 0; i < n; i++) {
      const t = i / (n - 1)
      const base = ref + t * chg
      const jitter =
        ((((seed * (i + 1) * 17) % 100) - 50) / 100.0) *
        Math.abs(chg * 0.4 || ref * 0.002)
      let p = base + jitter
      if (high > low) {
        p = Math.max(low, Math.min(high, p))
      }
      points.push(p)
    }
    points[0] = ref
    points[points.length - 1] = last
  }

  const maxDev =
    Math.max(...points.map((p) => Math.abs(p - ref)), Math.abs(chg)) ||
    ref * 0.005
  const maxH = height / 2.0 - 3.0

  const nodes: [number, number][] = []
  for (let i = 0; i < points.length; i++) {
    const x = Number(((i / (points.length - 1)) * width).toFixed(1))
    const p = points[i]
    const y = Number((midY - ((p - ref) / maxDev) * maxH).toFixed(1))
    nodes.push([x, y])
  }

  const k = 0.22
  let d = `M ${nodes[0][0]},${nodes[0][1]}`
  for (let i = 1; i < nodes.length; i++) {
    const p0 = nodes[i - 2] || nodes[i - 1]
    const p1 = nodes[i - 1]
    const p2 = nodes[i]
    const p3 = nodes[i + 1] || p2

    const cp1x = Number((p1[0] + (p2[0] - p0[0]) * k).toFixed(1))
    const cp1y = Number((p1[1] + (p2[1] - p0[1]) * k).toFixed(1))
    const cp2x = Number((p2[0] - (p3[0] - p1[0]) * k).toFixed(1))
    const cp2y = Number((p2[1] - (p3[1] - p1[1]) * k).toFixed(1))

    d += ` C ${cp1x},${cp1y} ${cp2x},${cp2y} ${p2[0]},${p2[1]}`
  }

  const areaStr = `${d} L ${width},${midY} L 0,${midY} Z`
  const lastPoint = {
    x: nodes[nodes.length - 1][0],
    y: nodes[nodes.length - 1][1],
  }

  const result: SparklineGeometry = {
    linePath: d,
    areaPath: areaStr,
    lastPoint,
  }
  sparkCache.set(cacheKey, result)
  return result
})
</script>

<template>
  <div
    class="w-[72px] h-[26px] mx-auto flex items-center justify-center select-none"
  >
    <svg class="w-full h-full overflow-hidden" :viewBox="`0 0 ${width} ${height}`">
      <defs>
        <clipPath :id="`top-clip-${stk.symbol}`">
          <rect x="0" y="0" :width="width" :height="height / 2" />
        </clipPath>
        <clipPath :id="`bot-clip-${stk.symbol}`">
          <rect x="0" :y="height / 2" :width="width" :height="height / 2" />
        </clipPath>
      </defs>

      <!-- Đường tham chiếu Baseline -->
      <line
        x1="0"
        :y1="height / 2"
        :x2="width"
        :y2="height / 2"
        stroke="rgba(255, 255, 255, 0.16)"
        stroke-width="0.8"
        stroke-dasharray="2 2"
      />

      <!-- Vùng tăng giá -->
      <path
        :d="geometry.areaPath"
        fill="rgba(16, 185, 129, 0.30)"
        :clip-path="`url(#top-clip-${stk.symbol})`"
      />

      <!-- Vùng giảm giá -->
      <path
        :d="geometry.areaPath"
        fill="rgba(239, 68, 68, 0.36)"
        :clip-path="`url(#bot-clip-${stk.symbol})`"
      />

      <!-- Đường biểu đồ trên tham chiếu -->
      <path
        fill="none"
        stroke="#10b981"
        stroke-width="1.3"
        stroke-linecap="round"
        stroke-linejoin="round"
        :d="geometry.linePath"
        :clip-path="`url(#top-clip-${stk.symbol})`"
      />

      <!-- Đường biểu đồ dưới tham chiếu -->
      <path
        fill="none"
        stroke="#f43f5e"
        stroke-width="1.3"
        stroke-linecap="round"
        stroke-linejoin="round"
        :d="geometry.linePath"
        :clip-path="`url(#bot-clip-${stk.symbol})`"
      />

      <!-- Điểm giá mới nhất -->
      <circle
        :cx="geometry.lastPoint.x"
        :cy="geometry.lastPoint.y"
        r="1.8"
        :fill="stk.change >= 0 ? '#10b981' : '#f43f5e'"
      />
    </svg>
  </div>
</template>
