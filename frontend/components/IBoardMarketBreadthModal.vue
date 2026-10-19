<script setup lang="ts">
import { computed, ref, watch } from "vue"
import type {
  MarketBreadthDetailResponse,
  MarketBreadthPoint,
  MarketBreadthSeriesResponse,
} from "~/types/marketBreadth"

interface Props {
  modelValue: boolean
  initialIndex?: string
}

const props = withDefaults(defineProps<Props>(), {
  modelValue: false,
  initialIndex: "VNINDEX",
})

const emit = defineEmits<{
  "update:modelValue": [value: boolean]
  "select-symbol": [symbol: string]
}>()

const supportedIndices = [
  { code: "VNINDEX", label: "VN-Index" },
  { code: "VN30", label: "VN30" },
  { code: "HNX", label: "HNX-Index" },
  { code: "HNX30", label: "HNX30" },
  { code: "UPCOM", label: "UPCoM" },
]

const currentIndex = ref<string>(props.initialIndex || "VNINDEX")
const activeTab = ref<"chart" | "detail">("chart")
const detailFilter = ref<
  "all" | "ceiling" | "advance" | "no_change" | "decline" | "floor"
>("all")
const searchQuery = ref<string>("")

const seriesData = ref<MarketBreadthSeriesResponse | null>(null)
const detailData = ref<MarketBreadthDetailResponse | null>(null)
const isLoading = ref<boolean>(false)
const errorMessage = ref<string | null>(null)

const hoverIndex = ref<number | null>(null)

const svgWidth = 840
const svgHeight = 360
const padding = { top: 24, right: 24, bottom: 44, left: 48 }
const chartW = computed(() => svgWidth - padding.left - padding.right)
const chartH = computed(() => svgHeight - padding.top - padding.bottom)

const normalizeIndexCode = (code: string): string => {
  const c = (code || "VNINDEX").toUpperCase()
  if (c === "HNX-INDEX" || c === "HNXINDEX") return "HNX"
  if (c === "UPCOMINDEX") return "UPCOM"
  return c
}

const fetchBreadthData = async (indexCode: string) => {
  const norm = normalizeIndexCode(indexCode)
  isLoading.value = true
  errorMessage.value = null
  try {
    const [seriesRes, detailRes] = await Promise.all([
      $fetch<MarketBreadthSeriesResponse>(
        `/api/v1/stock/iboard/market-breadth/${norm}`,
      ),
      $fetch<MarketBreadthDetailResponse>(
        `/api/v1/stock/iboard/market-breadth/${norm}/detail`,
      ),
    ])
    seriesData.value = seriesRes
    detailData.value = detailRes
  } catch (err) {
    console.error("Lỗi tải dữ liệu độ rộng thị trường:", err)
    errorMessage.value = "Không thể tải dữ liệu độ rộng thị trường."
  } finally {
    isLoading.value = false
  }
}

watch(
  () => props.modelValue,
  (isOpen) => {
    if (isOpen) {
      currentIndex.value = normalizeIndexCode(props.initialIndex || "VNINDEX")
      hoverIndex.value = null
      fetchBreadthData(currentIndex.value)
    }
  },
  { immediate: true },
)

const handleSelectIndex = (code: string) => {
  currentIndex.value = code
  hoverIndex.value = null
  fetchBreadthData(code)
}

const latestPoint = computed<MarketBreadthPoint | null>(() => {
  if (!seriesData.value) return null
  if (seriesData.value.latest) return seriesData.value.latest
  const arr = seriesData.value.data
  return arr && arr.length > 0 ? arr[arr.length - 1] : null
})

const activePoint = computed<MarketBreadthPoint | null>(() => {
  if (!seriesData.value?.data.length) return null
  if (hoverIndex.value !== null && seriesData.value.data[hoverIndex.value]) {
    return seriesData.value.data[hoverIndex.value]
  }
  return latestPoint.value
})

const pointsCount = computed(() => seriesData.value?.data.length || 0)

const getX = (idx: number): number => {
  if (pointsCount.value <= 1) return padding.left
  return padding.left + (idx / (pointsCount.value - 1)) * chartW.value
}

const getY = (pct: number): number => {
  const clamped = Math.max(0, Math.min(100, pct))
  return padding.top + chartH.value - (clamped / 100) * chartH.value
}

const buildStackedPaths = computed(() => {
  const points = seriesData.value?.data || []
  if (points.length < 2) {
    return { floor: "", decline: "", unchanged: "", advance: "", ceiling: "" }
  }

  const n = points.length

  const yFloor: number[] = []
  const yDecline: number[] = []
  const yUnchanged: number[] = []
  const yAdvance: number[] = []
  const yCeiling: number[] = []

  for (let i = 0; i < n; i++) {
    const pt = points[i]
    const fl = pt.floor_pct
    const dec = fl + pt.decline_pure_pct
    const unc = dec + pt.unchanged_pct
    const adv = unc + pt.advance_pure_pct
    const ceil = 100.0

    yFloor.push(getY(fl))
    yDecline.push(getY(dec))
    yUnchanged.push(getY(unc))
    yAdvance.push(getY(adv))
    yCeiling.push(getY(ceil))
  }

  const yBottomZero = getY(0)

  const buildPolygon = (
    topArr: number[],
    botArr: number[] | number,
  ): string => {
    let forward = `M ${getX(0).toFixed(1)} ${topArr[0].toFixed(1)}`
    for (let i = 1; i < n; i++) {
      forward += ` L ${getX(i).toFixed(1)} ${topArr[i].toFixed(1)}`
    }

    let backward = ""
    if (typeof botArr === "number") {
      backward += ` L ${getX(n - 1).toFixed(1)} ${botArr.toFixed(1)}`
      backward += ` L ${getX(0).toFixed(1)} ${botArr.toFixed(1)}`
    } else {
      for (let i = n - 1; i >= 0; i--) {
        backward += ` L ${getX(i).toFixed(1)} ${botArr[i].toFixed(1)}`
      }
    }

    return `${forward}${backward} Z`
  }

  return {
    floor: buildPolygon(yFloor, yBottomZero),
    decline: buildPolygon(yDecline, yFloor),
    unchanged: buildPolygon(yUnchanged, yDecline),
    advance: buildPolygon(yAdvance, yUnchanged),
    ceiling: buildPolygon(yCeiling, yAdvance),
  }
})

const xTicks = computed(() => {
  const points = seriesData.value?.data || []
  if (points.length < 2) return []

  const step = Math.max(1, Math.floor(points.length / 8))
  const ticks: Array<{ index: number; time: string; x: number }> = []

  for (let i = 0; i < points.length; i += step) {
    ticks.push({
      index: i,
      time: points[i].time,
      x: getX(i),
    })
  }

  const lastIdx = points.length - 1
  if (ticks.length > 0 && lastIdx - ticks[ticks.length - 1].index > step / 2) {
    ticks.push({
      index: lastIdx,
      time: points[lastIdx].time,
      x: getX(lastIdx),
    })
  }

  return ticks
})

const handleSvgMouseMove = (event: MouseEvent) => {
  const svgEl = event.currentTarget as SVGSVGElement
  if (!svgEl || pointsCount.value < 2) return

  const rect = svgEl.getBoundingClientRect()
  const mouseSvgX = ((event.clientX - rect.left) / rect.width) * svgWidth

  const effectiveX = Math.max(
    padding.left,
    Math.min(padding.left + chartW.value, mouseSvgX),
  )
  const ratio = (effectiveX - padding.left) / chartW.value
  const targetIdx = Math.round(ratio * (pointsCount.value - 1))

  hoverIndex.value = Math.max(0, Math.min(pointsCount.value - 1, targetIdx))
}

const handleSvgMouseLeave = () => {
  hoverIndex.value = null
}

const filteredSymbols = computed(() => {
  if (!detailData.value) return []

  const query = searchQuery.value.trim().toUpperCase()
  const categories: Array<{
    type: "ceiling" | "advance" | "no_change" | "decline" | "floor"
    label: string
    colorClass: string
    symbols: string[]
  }> = [
    {
      type: "ceiling",
      label: "Trần",
      colorClass:
        "text-market-ceiling border-market-ceiling/30 bg-market-ceiling/10",
      symbols: detailData.value.ceiling || [],
    },
    {
      type: "advance",
      label: "Tăng",
      colorClass:
        "text-market-advance border-market-advance/30 bg-market-advance/10",
      symbols: detailData.value.advance || [],
    },
    {
      type: "no_change",
      label: "Tham chiếu",
      colorClass:
        "text-market-unchanged border-market-unchanged/30 bg-market-unchanged/10",
      symbols: detailData.value.no_change || [],
    },
    {
      type: "decline",
      label: "Giảm",
      colorClass:
        "text-market-decline border-market-decline/30 bg-market-decline/10",
      symbols: detailData.value.decline || [],
    },
    {
      type: "floor",
      label: "Sàn",
      colorClass: "text-market-floor border-market-floor/30 bg-market-floor/10",
      symbols: detailData.value.floor || [],
    },
  ]

  return categories
    .filter((cat) => {
      if (detailFilter.value === "all") return true
      return cat.type === detailFilter.value
    })
    .map((cat) => ({
      ...cat,
      filtered: cat.symbols.filter((sym) =>
        query ? sym.toUpperCase().includes(query) : true,
      ),
    }))
})

const handleStockClick = (symbol: string) => {
  emit("select-symbol", symbol)
}

const closeModal = () => {
  emit("update:modelValue", false)
}
</script>

<template>
  <UModal
    :model-value="modelValue"
    :ui="{ width: 'sm:max-w-4xl' }"
    @update:model-value="(val) => emit('update:modelValue', val)"
  >
    <div
      class="bg-tv-card border border-tv-border rounded-xl overflow-hidden flex flex-col select-none text-tv-primary shadow-2xl"
    >
      <div
        class="flex items-center justify-between px-5 py-3.5 border-b border-tv-border bg-tv-surface"
      >
        <div class="flex items-center gap-3">
          <div class="flex items-center gap-2">
            <span class="w-2.5 h-2.5 rounded-full bg-market-advance"></span>
            <h2 class="text-base font-bold font-mono tracking-wide text-white">
              Độ rộng thị trường — {{ currentIndex }}
            </h2>
          </div>

          <div class="flex items-center gap-1 ml-2">
            <button
              v-for="idx in supportedIndices"
              :key="idx.code"
              type="button"
              class="px-2.5 py-1 rounded text-xs font-mono font-medium transition-colors cursor-pointer"
              :class="
                currentIndex === idx.code
                  ? 'bg-aave-violet text-white font-bold'
                  : 'text-tv-secondary hover:text-white hover:bg-white/[0.06]'
              "
              @click="handleSelectIndex(idx.code)"
            >
              {{ idx.code }}
            </button>
          </div>
        </div>

        <div class="flex items-center gap-2">
          <div class="flex items-center p-0.5 rounded bg-tv-card border border-tv-border">
            <button
              type="button"
              class="px-3 py-1 rounded text-xs font-medium transition-colors cursor-pointer"
              :class="
                activeTab === 'chart'
                  ? 'bg-white/[0.12] text-white font-semibold'
                  : 'text-tv-secondary hover:text-white'
              "
              @click="activeTab = 'chart'"
            >
              Biểu đồ tỷ lệ %
            </button>
            <button
              type="button"
              class="px-3 py-1 rounded text-xs font-medium transition-colors cursor-pointer"
              :class="
                activeTab === 'detail'
                  ? 'bg-white/[0.12] text-white font-semibold'
                  : 'text-tv-secondary hover:text-white'
              "
              @click="activeTab = 'detail'"
            >
              Danh sách mã
            </button>
          </div>

          <button
            type="button"
            class="p-1 rounded text-tv-secondary hover:text-white hover:bg-white/[0.08] transition-colors cursor-pointer ml-1"
            aria-label="Đóng cửa sổ"
            @click="closeModal"
          >
            <UIcon name="i-heroicons-x-mark" class="w-5 h-5" />
          </button>
        </div>
      </div>

      <div
        v-if="activePoint"
        class="grid grid-cols-2 sm:grid-cols-6 gap-2 px-5 py-2.5 bg-tv-surface/60 border-b border-tv-border/80 text-xs font-mono tabular-nums"
      >
        <div class="flex flex-col">
          <span class="text-tv-secondary text-[10px]">Thời gian</span>
          <span class="text-white font-bold text-sm">{{ activePoint.time }}</span>
        </div>

        <div class="flex flex-col">
          <div class="flex items-center gap-1.5">
            <span class="w-2 h-2 rounded-xs bg-market-ceiling"></span>
            <span class="text-tv-secondary text-[10px]">Trần</span>
          </div>
          <div class="flex items-baseline gap-1">
            <span class="text-market-ceiling font-bold">{{ activePoint.ceiling }}</span>
            <span class="text-[10px] text-tv-secondary font-normal">{{ activePoint.ceiling_pct.toFixed(2) }}%</span>
          </div>
        </div>

        <div class="flex flex-col">
          <div class="flex items-center gap-1.5">
            <span class="w-2 h-2 rounded-xs bg-market-advance"></span>
            <span class="text-tv-secondary text-[10px]">Tăng</span>
          </div>
          <div class="flex items-baseline gap-1">
            <span class="text-market-advance font-bold">{{ activePoint.advance }}</span>
            <span class="text-[10px] text-tv-secondary font-normal">
              {{ (activePoint.total > 0 ? (activePoint.advance / activePoint.total) * 100 : 0).toFixed(2) }}%
            </span>
          </div>
        </div>

        <div class="flex flex-col">
          <div class="flex items-center gap-1.5">
            <span class="w-2 h-2 rounded-xs bg-market-unchanged"></span>
            <span class="text-tv-secondary text-[10px]">Tham chiếu</span>
          </div>
          <div class="flex items-baseline gap-1">
            <span class="text-market-unchanged font-bold">{{ activePoint.unchanged }}</span>
            <span class="text-[10px] text-tv-secondary font-normal">{{ activePoint.unchanged_pct.toFixed(2) }}%</span>
          </div>
        </div>

        <div class="flex flex-col">
          <div class="flex items-center gap-1.5">
            <span class="w-2 h-2 rounded-xs bg-market-decline"></span>
            <span class="text-tv-secondary text-[10px]">Giảm</span>
          </div>
          <div class="flex items-baseline gap-1">
            <span class="text-market-decline font-bold">{{ activePoint.decline }}</span>
            <span class="text-[10px] text-tv-secondary font-normal">
              {{ (activePoint.total > 0 ? (activePoint.decline / activePoint.total) * 100 : 0).toFixed(2) }}%
            </span>
          </div>
        </div>

        <div class="flex flex-col">
          <div class="flex items-center gap-1.5">
            <span class="w-2 h-2 rounded-xs bg-market-floor"></span>
            <span class="text-tv-secondary text-[10px]">Sàn</span>
          </div>
          <div class="flex items-baseline gap-1">
            <span class="text-market-floor font-bold">{{ activePoint.floor }}</span>
            <span class="text-[10px] text-tv-secondary font-normal">{{ activePoint.floor_pct.toFixed(2) }}%</span>
          </div>
        </div>
      </div>

      <div class="relative p-5 min-h-[380px] flex flex-col justify-center">
        <div
          v-if="isLoading && !seriesData"
          class="flex flex-col items-center justify-center gap-2 py-16 text-tv-secondary"
        >
          <UIcon name="i-heroicons-arrow-path" class="w-7 h-7 animate-spin text-aave-violet" />
          <span class="text-xs font-mono">Đang tải dữ liệu độ rộng thị trường...</span>
        </div>

        <div
          v-else-if="errorMessage && !seriesData"
          class="flex flex-col items-center justify-center gap-2 py-16 text-tv-bear"
        >
          <UIcon name="i-heroicons-exclamation-circle" class="w-7 h-7" />
          <span class="text-xs font-mono">{{ errorMessage }}</span>
        </div>

        <div v-else-if="activeTab === 'chart'" class="relative w-full">
          <div class="flex items-center justify-between mb-2">
            <span class="text-xs font-mono font-medium text-tv-secondary">
              Tỷ lệ %
            </span>
            <span class="text-[11px] font-mono text-zinc-400">
              Tổng số mã: {{ activePoint?.total || 0 }}
            </span>
          </div>

          <div class="relative w-full overflow-hidden border border-tv-border rounded bg-tv-surface">
            <svg
              :viewBox="`0 0 ${svgWidth} ${svgHeight}`"
              class="w-full h-auto block select-none cursor-crosshair"
              preserveAspectRatio="none"
              @mousemove="handleSvgMouseMove"
              @mouseleave="handleSvgMouseLeave"
            >
              <g class="grid-lines" stroke="#2a2e39" stroke-width="1" stroke-dasharray="2 2">
                <line
                  v-for="pct in [0, 20, 40, 60, 80, 100]"
                  :key="pct"
                  :x1="padding.left"
                  :y1="getY(pct)"
                  :x2="padding.left + chartW"
                  :y2="getY(pct)"
                />
              </g>

              <g class="y-labels" fill="#787b86" font-size="10" font-family="JetBrains Mono" text-anchor="end">
                <text
                  v-for="pct in [0, 20, 40, 60, 80, 100]"
                  :key="pct"
                  :x="padding.left - 8"
                  :y="getY(pct) + 3.5"
                >
                  {{ pct }}
                </text>
              </g>

              <g class="x-ticks" fill="#787b86" font-size="9.5" font-family="JetBrains Mono" text-anchor="middle">
                <text
                  v-for="tick in xTicks"
                  :key="tick.time"
                  :x="tick.x"
                  :y="svgHeight - padding.bottom + 18"
                >
                  {{ tick.time }}
                </text>
              </g>

              <g class="layers">
                <path
                  :d="buildStackedPaths.floor"
                  fill="var(--color-market-floor)"
                  opacity="0.95"
                />
                <path
                  :d="buildStackedPaths.decline"
                  fill="var(--color-market-decline)"
                  opacity="0.95"
                />
                <path
                  :d="buildStackedPaths.unchanged"
                  fill="var(--color-market-unchanged)"
                  opacity="0.95"
                />
                <path
                  :d="buildStackedPaths.advance"
                  fill="var(--color-market-advance)"
                  opacity="0.95"
                />
                <path
                  :d="buildStackedPaths.ceiling"
                  fill="var(--color-market-ceiling)"
                  opacity="0.95"
                />
              </g>

              <g v-if="hoverIndex !== null && seriesData && seriesData.data.length > 0">
                <line
                  :x1="getX(hoverIndex)"
                  :y1="padding.top"
                  :x2="getX(hoverIndex)"
                  :y2="padding.top + chartH"
                  stroke="#ffffff"
                  stroke-width="1.2"
                  stroke-dasharray="3 3"
                />
              </g>
            </svg>

            <div
              v-if="hoverIndex !== null && activePoint"
              class="absolute z-20 pointer-events-none bg-[#0e111a] border border-white/[0.16] rounded-md p-2.5 shadow-xl text-[11px] font-mono tabular-nums min-w-[170px]"
              :style="{
                left: `${Math.min(72, Math.max(8, (getX(hoverIndex) / svgWidth) * 100))}%`,
                top: '16px',
              }"
            >
              <div class="font-bold text-white border-b border-white/[0.08] pb-1 mb-1.5 flex justify-between">
                <span>{{ activePoint.time }}</span>
                <span class="text-zinc-400 font-normal">{{ activePoint.total }} mã</span>
              </div>
              <div class="flex flex-col gap-1">
                <div class="flex items-center justify-between">
                  <span class="text-market-ceiling flex items-center gap-1.5">
                    <span class="w-2 h-2 rounded-xs bg-market-ceiling inline-block"></span>
                    Trần:
                  </span>
                  <span class="text-white font-semibold">
                    {{ activePoint.ceiling }} • {{ activePoint.ceiling_pct.toFixed(2) }}%
                  </span>
                </div>
                <div class="flex items-center justify-between">
                  <span class="text-market-advance flex items-center gap-1.5">
                    <span class="w-2 h-2 rounded-xs bg-market-advance inline-block"></span>
                    Tăng:
                  </span>
                  <span class="text-white font-semibold">
                    {{ activePoint.advance }} • {{ (activePoint.total > 0 ? (activePoint.advance / activePoint.total) * 100 : 0).toFixed(2) }}%
                  </span>
                </div>
                <div class="flex items-center justify-between">
                  <span class="text-market-unchanged flex items-center gap-1.5">
                    <span class="w-2 h-2 rounded-xs bg-market-unchanged inline-block"></span>
                    Tham chiếu:
                  </span>
                  <span class="text-white font-semibold">
                    {{ activePoint.unchanged }} • {{ activePoint.unchanged_pct.toFixed(2) }}%
                  </span>
                </div>
                <div class="flex items-center justify-between">
                  <span class="text-market-decline flex items-center gap-1.5">
                    <span class="w-2 h-2 rounded-xs bg-market-decline inline-block"></span>
                    Giảm:
                  </span>
                  <span class="text-white font-semibold">
                    {{ activePoint.decline }} • {{ (activePoint.total > 0 ? (activePoint.decline / activePoint.total) * 100 : 0).toFixed(2) }}%
                  </span>
                </div>
                <div class="flex items-center justify-between">
                  <span class="text-market-floor flex items-center gap-1.5">
                    <span class="w-2 h-2 rounded-xs bg-market-floor inline-block"></span>
                    Sàn:
                  </span>
                  <span class="text-white font-semibold">
                    {{ activePoint.floor }} • {{ activePoint.floor_pct.toFixed(2) }}%
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div v-else class="flex flex-col gap-3 min-h-[360px]">
          <div class="flex flex-wrap items-center justify-between gap-2">
            <div class="flex items-center gap-1.5">
              <button
                type="button"
                class="px-2.5 py-1 rounded text-xs font-mono font-medium transition-colors cursor-pointer"
                :class="
                  detailFilter === 'all'
                    ? 'bg-white/[0.14] text-white font-bold'
                    : 'text-tv-secondary hover:text-white hover:bg-white/[0.05]'
                "
                @click="detailFilter = 'all'"
              >
                Tất cả
              </button>
              <button
                type="button"
                class="px-2.5 py-1 rounded text-xs font-mono font-medium transition-colors cursor-pointer"
                :class="
                  detailFilter === 'ceiling'
                    ? 'bg-market-ceiling text-white font-bold'
                    : 'text-market-ceiling hover:bg-market-ceiling/10'
                "
                @click="detailFilter = 'ceiling'"
              >
                Trần ({{ detailData?.ceiling?.length || 0 }})
              </button>
              <button
                type="button"
                class="px-2.5 py-1 rounded text-xs font-mono font-medium transition-colors cursor-pointer"
                :class="
                  detailFilter === 'advance'
                    ? 'bg-market-advance text-black font-bold'
                    : 'text-market-advance hover:bg-market-advance/10'
                "
                @click="detailFilter = 'advance'"
              >
                Tăng ({{ detailData?.advance?.length || 0 }})
              </button>
              <button
                type="button"
                class="px-2.5 py-1 rounded text-xs font-mono font-medium transition-colors cursor-pointer"
                :class="
                  detailFilter === 'no_change'
                    ? 'bg-market-unchanged text-black font-bold'
                    : 'text-market-unchanged hover:bg-market-unchanged/10'
                "
                @click="detailFilter = 'no_change'"
              >
                Tham chiếu ({{ detailData?.no_change?.length || 0 }})
              </button>
              <button
                type="button"
                class="px-2.5 py-1 rounded text-xs font-mono font-medium transition-colors cursor-pointer"
                :class="
                  detailFilter === 'decline'
                    ? 'bg-market-decline text-white font-bold'
                    : 'text-market-decline hover:bg-market-decline/10'
                "
                @click="detailFilter = 'decline'"
              >
                Giảm ({{ detailData?.decline?.length || 0 }})
              </button>
              <button
                type="button"
                class="px-2.5 py-1 rounded text-xs font-mono font-medium transition-colors cursor-pointer"
                :class="
                  detailFilter === 'floor'
                    ? 'bg-market-floor text-black font-bold'
                    : 'text-market-floor hover:bg-market-floor/10'
                "
                @click="detailFilter = 'floor'"
              >
                Sàn ({{ detailData?.floor?.length || 0 }})
              </button>
            </div>

            <div class="relative w-48">
              <input
                v-model="searchQuery"
                type="text"
                placeholder="Tìm mã cổ phiếu..."
                class="w-full bg-tv-surface border border-tv-border rounded px-2.5 py-1 text-xs text-white placeholder-tv-secondary focus:outline-hidden focus:border-aave-violet font-mono"
              />
            </div>
          </div>

          <div class="max-h-[340px] overflow-y-auto flex flex-col gap-3 pr-1">
            <div
              v-for="cat in filteredSymbols"
              :key="cat.type"
              class="flex flex-col gap-1.5"
            >
              <div class="flex items-center gap-2 border-b border-tv-border/60 pb-1">
                <span class="text-xs font-bold font-mono" :class="cat.colorClass.split(' ')[0]">
                  {{ cat.label }}
                </span>
                <span class="text-[10px] text-tv-secondary font-mono">
                  {{ cat.filtered.length }} mã
                </span>
              </div>

              <div
                v-if="cat.filtered.length > 0"
                class="flex flex-wrap gap-1.5"
              >
                <button
                  v-for="sym in cat.filtered"
                  :key="sym"
                  type="button"
                  class="px-2 py-0.5 rounded border text-[11px] font-mono font-semibold transition-transform hover:scale-105 cursor-pointer"
                  :class="cat.colorClass"
                  @click="handleStockClick(sym)"
                >
                  {{ sym }}
                </button>
              </div>

              <div
                v-else
                class="text-xs text-tv-secondary font-mono italic py-1"
              >
                Không có mã nào phù hợp bộ lọc.
              </div>
            </div>
          </div>
        </div>
      </div>

      <div
        class="px-5 py-2.5 border-t border-tv-border bg-tv-surface flex items-center justify-between text-[11px] text-tv-secondary font-mono"
      >
        <span>Nguồn dữ liệu: Thống kê độ rộng thị trường thời gian thực</span>
        <span class="text-zinc-500">Nhấn vào mã cổ phiếu để xem biểu đồ chi tiết</span>
      </div>
    </div>
  </UModal>
</template>
