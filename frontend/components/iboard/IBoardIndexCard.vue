<template>
  <div
    class="flex flex-col justify-between min-w-[262px] max-w-[295px] flex-1 px-3 py-2 rounded-lg bg-surface-abyss border border-white/[0.06] hover:border-white/[0.16] transition-colors cursor-pointer select-none"
    :class="{ 'ring-1 ring-white/[0.2] border-white/[0.2]': active }"
    @click="$emit('select', item.id)"
  >
    <!-- Row 1: Symbol Name and Percent Change -->
    <div class="flex items-center justify-between gap-2">
      <span class="text-xs font-bold text-white tracking-wide uppercase">{{ item.name }}</span>
      <span class="text-xs font-mono font-medium" :class="colorClass">
        {{ item.changePercent }}
      </span>
    </div>

    <!-- Row 2: Main Price and Point Change -->
    <div class="flex items-center justify-between gap-2 mt-0.5">
      <span class="text-sm sm:text-base font-bold font-mono tabular-nums leading-tight" :class="colorClass">
        {{ item.price }}
      </span>
      <span class="text-xs font-mono font-medium leading-tight" :class="colorClass">
        {{ item.change }}
      </span>
    </div>

    <!-- Row 3 & 4: Details (Volume, Breadth / Derivatives) and Chart -->
    <div class="flex items-end justify-between gap-2 mt-1">
      <div class="flex flex-col min-w-0 flex-1">
        <!-- World indices: Keep clean with no volume/breadth, matching DNSE -->
        <template v-if="isWorld">
          <div class="h-6" />
        </template>

        <template v-else>
          <!-- Volume / Value: Compact font so 829.39 Triệu CP | 19,176.09 Tỷ fits without overlap -->
          <div class="text-[9.5px] font-mono text-aave-ash whitespace-nowrap leading-tight tracking-tighter">
            <template v-if="item.volume && item.value">
              <span>{{ item.volume }}</span>
              <span class="mx-0.5 text-aave-graphite">|</span>
              <span>{{ item.value }}</span>
            </template>
            <template v-else-if="item.volume">
              <span>{{ item.volume }}</span>
            </template>
            <template v-else-if="item.value">
              <span>{{ item.value }}</span>
            </template>
            <template v-else>
              <span class="text-aave-graphite">Dữ liệu phiên</span>
            </template>
          </div>

          <!-- Breadth or Derivatives price band -->
          <div class="flex items-center gap-1 mt-1 text-[9.5px] font-mono leading-none">
            <!-- Derivatives Band (Ceiling / Ref / Floor) -->
            <template v-if="isDerivatives">
              <UTooltip text="Giá Trần">
                <span class="text-fuchsia-400 font-medium">{{ derivativesPrices.ceil }}</span>
              </UTooltip>
              <UTooltip text="Giá Tham Chiếu">
                <span class="text-amber-400 font-medium">{{ derivativesPrices.ref }}</span>
              </UTooltip>
              <UTooltip text="Giá Sàn">
                <span class="text-cyan-400 font-medium">{{ derivativesPrices.floor }}</span>
              </UTooltip>
            </template>

            <!-- Standard Stock Market Breadth with DNSE ceiling/floor colors -->
            <template v-else-if="hasBreadth && item.breadth">
              <span class="flex items-center gap-0.5 text-emerald-400 font-medium">
                <span>▲</span>
                <span>{{ item.breadth.advance }}</span>
                <span class="text-[9px] text-fuchsia-400 font-normal">({{ item.breadth.ceiling }})</span>
              </span>
              <span class="flex items-center gap-0.5 text-amber-400 font-medium">
                <span>■</span>
                <span>{{ item.breadth.unchanged }}</span>
              </span>
              <span class="flex items-center gap-0.5 text-rose-500 font-medium">
                <span>▼</span>
                <span>{{ item.breadth.decline }}</span>
                <span class="text-[9px] text-cyan-400 font-normal">({{ item.breadth.floor }})</span>
              </span>
            </template>

            <!-- Fallback -->
            <template v-else>
              <span class="text-[9px] font-mono text-aave-graphite">Chỉ số thị trường</span>
            </template>
          </div>
        </template>
      </div>

      <!-- Intraday Reference-Baseline Chart (Dual-Clip SVG matching DNSE) -->
      <div class="w-[76px] h-[32px] flex items-end justify-end shrink-0 select-none">
        <svg class="w-full h-full overflow-hidden" viewBox="0 0 76 32">
          <defs>
            <clipPath :id="`card-top-clip-${item.id}`">
              <rect x="0" y="0" width="76" :height="chartData.baselineY" />
            </clipPath>
            <clipPath :id="`card-bot-clip-${item.id}`">
              <rect x="0" :y="chartData.baselineY" width="76" :height="32 - chartData.baselineY" />
            </clipPath>
          </defs>

          <!-- Reference Baseline Line (Dashed) -->
          <line
            x1="0"
            :y1="chartData.baselineY"
            x2="76"
            :y2="chartData.baselineY"
            stroke="rgba(255, 255, 255, 0.16)"
            stroke-width="0.8"
            stroke-dasharray="2 2"
          />

          <!-- Top Shaded Area (Emerald Gain above baseline) -->
          <path
            :d="chartData.areaPath"
            fill="rgba(16, 185, 129, 0.28)"
            :clip-path="`url(#card-top-clip-${item.id})`"
          />

          <!-- Bottom Shaded Area (Burgundy Loss below baseline) -->
          <path
            :d="chartData.areaPath"
            fill="rgba(239, 68, 68, 0.35)"
            :clip-path="`url(#card-bot-clip-${item.id})`"
          />

          <!-- Line Path Green (Above Baseline) -->
          <path
            fill="none"
            stroke="#10b981"
            stroke-width="1.3"
            stroke-linecap="round"
            stroke-linejoin="round"
            :d="chartData.linePath"
            :clip-path="`url(#card-top-clip-${item.id})`"
          />

          <!-- Line Path Red (Below Baseline) -->
          <path
            fill="none"
            stroke="#f43f5e"
            stroke-width="1.3"
            stroke-linecap="round"
            stroke-linejoin="round"
            :d="chartData.linePath"
            :clip-path="`url(#card-bot-clip-${item.id})`"
          />

          <!-- Live Endpoint Halo Circle -->
          <circle
            :cx="chartData.lastPoint.x"
            :cy="chartData.lastPoint.y"
            r="3.2"
            :fill="chartData.lastColor"
            opacity="0.22"
          />

          <!-- Live Endpoint Core Dot -->
          <circle
            :cx="chartData.lastPoint.x"
            :cy="chartData.lastPoint.y"
            r="1.6"
            :fill="chartData.lastColor"
          />
        </svg>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue"
import type { IndexDisplayItem } from "./types"

const props = defineProps<{
  item: IndexDisplayItem
  active?: boolean
}>()

defineEmits<{
  select: [id: string]
}>()

const isDerivatives = computed(() => {
  const id = props.item.id.toLowerCase()
  const name = props.item.name.toUpperCase()
  return id.includes("vn30f") || name.includes("VN30F")
})

const isWorld = computed(() => {
  const id = props.item.id.toLowerCase()
  const name = props.item.name.toUpperCase()
  return (
    id === "dji" ||
    id === "sp500" ||
    id === "nasdaq" ||
    name.includes("DOW JONES") ||
    name.includes("S&P") ||
    name.includes("NASDAQ")
  )
})

const hasBreadth = computed(() => {
  const b = props.item.breadth
  return b && (b.advance > 0 || b.unchanged > 0 || b.decline > 0)
})

const colorClass = computed(() => {
  if (props.item.isPositive) return "text-emerald-400"
  if (props.item.isUnchanged) return "text-amber-400"
  return "text-rose-500"
})

const derivativesPrices = computed(() => {
  if (props.item.ceilingPrice && props.item.refPrice && props.item.floorPrice) {
    return {
      ceil: Number(props.item.ceilingPrice).toLocaleString("en-US", {
        minimumFractionDigits: 1,
        maximumFractionDigits: 1,
      }),
      ref: Number(props.item.refPrice).toLocaleString("en-US", {
        minimumFractionDigits: 1,
        maximumFractionDigits: 1,
      }),
      floor: Number(props.item.floorPrice).toLocaleString("en-US", {
        minimumFractionDigits: 1,
        maximumFractionDigits: 1,
      }),
    }
  }

  const curP = parseFloat(props.item.price.replace(/,/g, "")) || 1885.0
  const chg =
    parseFloat(props.item.change.replace(/,/g, "").replace(/\+/g, "")) || -10.0
  const refP = curP - chg
  const ceilP = Math.floor(refP * 1.07 * 10) / 10
  const flrP = Math.round(refP * 0.93 * 10) / 10

  return {
    ceil: ceilP.toLocaleString("en-US", {
      minimumFractionDigits: 1,
      maximumFractionDigits: 1,
    }),
    ref: refP.toLocaleString("en-US", {
      minimumFractionDigits: 1,
      maximumFractionDigits: 1,
    }),
    floor: flrP.toLocaleString("en-US", {
      minimumFractionDigits: 1,
      maximumFractionDigits: 1,
    }),
  }
})

interface SmoothChartData {
  linePath: string
  areaPath: string
  baselineY: number
  lastPoint: { x: number; y: number }
  lastColor: string
}

const pointsToSmoothBezier = (
  nodes: [number, number][],
  baselineY: number,
  width = 76,
  k = 0.22,
) => {
  if (nodes.length < 2) {
    return {
      linePath: "",
      areaPath: "",
      lastPoint: { x: 0, y: 0 },
    }
  }

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

  const areaPath = `${d} L ${width},${baselineY} L 0,${baselineY} Z`
  const lastPoint = {
    x: nodes[nodes.length - 1][0],
    y: nodes[nodes.length - 1][1],
  }

  return { linePath: d, areaPath, lastPoint }
}

// Scaled signature trajectories matching DNSE iBoard (76px x 32px)
const dnseSignatureNodes: Record<
  string,
  {
    nodes: [number, number][]
    baselineY: number
  }
> = {
  vn30f1m: {
    baselineY: 9,
    nodes: [
      [0, 7],
      [8, 5],
      [14, 7],
      [22, 13],
      [30, 17],
      [38, 15],
      [46, 20],
      [54, 25],
      [62, 21],
      [70, 16],
      [76, 19],
    ],
  },
  vn30: {
    baselineY: 5,
    nodes: [
      [0, 5],
      [6, 4],
      [12, 6],
      [18, 12],
      [26, 16],
      [34, 14],
      [42, 20],
      [50, 24],
      [58, 20],
      [64, 15],
      [70, 19],
      [76, 18],
    ],
  },
  vnindex: {
    baselineY: 5,
    nodes: [
      [0, 5],
      [6, 4],
      [12, 7],
      [18, 15],
      [26, 21],
      [34, 25],
      [42, 22],
      [50, 18],
      [58, 13],
      [64, 17],
      [70, 22],
      [76, 21],
    ],
  },
  hnx30: {
    baselineY: 5,
    nodes: [
      [0, 5],
      [8, 4],
      [16, 9],
      [26, 15],
      [36, 19],
      [46, 23],
      [56, 21],
      [66, 25],
      [76, 24],
    ],
  },
  dji: {
    baselineY: 28,
    nodes: [
      [0, 27],
      [10, 25],
      [20, 23],
      [30, 20],
      [40, 17],
      [50, 14],
      [60, 10],
      [68, 7],
      [76, 6],
    ],
  },
}

const chartData = computed<SmoothChartData>(() => {
  const isUp = props.item.isPositive
  const isUnch = props.item.isUnchanged
  const normId = props.item.id.toLowerCase()

  // Determine reference price
  let refP = 0
  if (props.item.refPrice) {
    refP = Number(props.item.refPrice)
  } else if (props.item.price && props.item.change) {
    const curP = parseFloat(props.item.price.replace(/,/g, "")) || 0
    const chg =
      parseFloat(props.item.change.replace(/,/g, "").replace(/\+/g, "")) || 0
    refP = curP - chg
  }

  const width = 76
  const height = 32
  const topMargin = 3
  const botMargin = 29
  const effH = botMargin - topMargin

  // 1. If real intraday sparkline data is provided
  if (props.item.sparkline && props.item.sparkline.length >= 4) {
    const rawPts = props.item.sparkline
    if (refP <= 0) refP = rawPts[0]

    const allPts = [...rawPts, refP]
    const minP = Math.min(...allPts)
    const maxP = Math.max(...allPts)
    const span = maxP - minP || refP * 0.005 || 1
    const pad = span * 0.08
    const yMin = minP - pad
    const yMax = maxP + pad
    const yRange = yMax - yMin

    const baselineY = Number(
      Math.max(
        4,
        Math.min(28, botMargin - ((refP - yMin) / yRange) * effH),
      ).toFixed(1),
    )

    const nodes: [number, number][] = rawPts.map((val, idx) => {
      const x = Number(((idx / (rawPts.length - 1)) * width).toFixed(1))
      const y = Number(
        Math.max(
          2,
          Math.min(30, botMargin - ((val - yMin) / yRange) * effH),
        ).toFixed(1),
      )
      return [x, y]
    })

    const spline = pointsToSmoothBezier(nodes, baselineY, width)
    const lastColor = spline.lastPoint.y <= baselineY ? "#10b981" : "#f43f5e"

    return {
      baselineY,
      linePath: spline.linePath,
      areaPath: spline.areaPath,
      lastPoint: spline.lastPoint,
      lastColor,
    }
  }

  // 2. Fallback to signature presets
  if (dnseSignatureNodes[normId]) {
    const p = dnseSignatureNodes[normId]
    const spline = pointsToSmoothBezier(p.nodes, p.baselineY, width)
    const lastColor = spline.lastPoint.y <= p.baselineY ? "#10b981" : "#f43f5e"
    return {
      baselineY: p.baselineY,
      linePath: spline.linePath,
      areaPath: spline.areaPath,
      lastPoint: spline.lastPoint,
      lastColor,
    }
  }

  // 3. Fallback smooth dynamic trajectory
  const count = 14
  const seed = (normId || "idx")
    .split("")
    .reduce((acc, c) => acc + c.charCodeAt(0), 0)

  if (isUnch) {
    const baselineY = 16
    const nodes: [number, number][] = []
    for (let i = 0; i < count; i++) {
      const x = Number(((i / (count - 1)) * width).toFixed(1))
      const jitter = Math.sin(i * 1.5 + seed) * 1.0
      nodes.push([x, Number((baselineY + jitter).toFixed(1))])
    }
    const spline = pointsToSmoothBezier(nodes, baselineY, width)
    return {
      baselineY,
      linePath: spline.linePath,
      areaPath: spline.areaPath,
      lastPoint: spline.lastPoint,
      lastColor: "#fbbf24",
    }
  }

  if (isUp) {
    const baselineY = 28
    const nodes: [number, number][] = []
    for (let i = 0; i < count; i++) {
      const t = i / (count - 1)
      const x = Number((t * width).toFixed(1))
      const baseY = 26 - t * 20
      const wave = Math.sin(i * 1.2 + seed) * 1.2
      const y = Number(Math.max(4, Math.min(28, baseY + wave)).toFixed(1))
      nodes.push([x, y])
    }
    const spline = pointsToSmoothBezier(nodes, baselineY, width)
    return {
      baselineY,
      linePath: spline.linePath,
      areaPath: spline.areaPath,
      lastPoint: spline.lastPoint,
      lastColor: "#10b981",
    }
  }

  // Descending (Down)
  const baselineY = 5
  const nodes: [number, number][] = []
  for (let i = 0; i < count; i++) {
    const t = i / (count - 1)
    const x = Number((t * width).toFixed(1))
    const baseY = 6 + t * 18
    const wave = Math.sin(i * 1.2 + seed) * 1.2
    const y = Number(Math.max(4, Math.min(28, baseY + wave)).toFixed(1))
    nodes.push([x, y])
  }
  const spline = pointsToSmoothBezier(nodes, baselineY, width)
  return {
    baselineY,
    linePath: spline.linePath,
    areaPath: spline.areaPath,
    lastPoint: spline.lastPoint,
    lastColor: "#f43f5e",
  }
})
</script>
