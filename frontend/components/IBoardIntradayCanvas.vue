<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from "vue"

interface Props {
  sparkline?: (number | null)[]
  refPrice?: number | null
  currentPrice?: number | null
  isPositive?: boolean
  symbol?: string
}

const props = withDefaults(defineProps<Props>(), {
  sparkline: () => [],
  refPrice: null,
  currentPrice: null,
  isPositive: true,
  symbol: "",
})

const canvasRef = ref<HTMLCanvasElement | null>(null)
const containerRef = ref<HTMLDivElement | null>(null)
const hoverData = ref<{
  active: boolean
  x: number
  y: number
  price: number | null
  time: string
  isLunch?: boolean
} | null>(null)

let resizeObserver: ResizeObserver | null = null

const hours = ["09h", "10h", "11h", "12h", "13h", "14h", "15h"]

function renderCanvas() {
  const canvas = canvasRef.value
  const container = containerRef.value
  if (!canvas || !container) return

  const dpr = window.devicePixelRatio || 1
  const width = container.clientWidth
  const height = container.clientHeight
  if (width <= 0 || height <= 0) return

  canvas.width = width * dpr
  canvas.height = height * dpr
  canvas.style.width = `${width}px`
  canvas.style.height = `${height}px`

  const ctx = canvas.getContext("2d")
  if (!ctx) return
  ctx.resetTransform()
  ctx.scale(dpr, dpr)
  ctx.clearRect(0, 0, width, height)

  const rawPoints = props.sparkline || []
  const validPoints = rawPoints.filter(
    (p): p is number => p !== null && p !== undefined && p > 0,
  )

  if (validPoints.length < 2) {
    ctx.strokeStyle = "#29292A"
    ctx.lineWidth = 1
    ctx.strokeRect(0, 0, width, height)
    for (let i = 1; i < 4; i++) {
      const gy = (i / 4) * height
      ctx.beginPath()
      ctx.moveTo(0, gy)
      ctx.lineTo(width, gy)
      ctx.stroke()
    }
    for (let i = 1; i < 6; i++) {
      const gx = (i / 6) * width
      ctx.beginPath()
      ctx.moveTo(gx, 0)
      ctx.lineTo(gx, height)
      ctx.stroke()
    }
    return
  }

  const effectiveRef =
    props.refPrice && props.refPrice > 0
      ? props.refPrice
      : validPoints[0] || 1000

  const minP = Math.min(...validPoints, effectiveRef)
  const maxP = Math.max(...validPoints, effectiveRef)
  const spread = maxP - minP || effectiveRef * 0.005
  const padding = spread * 0.12
  const yMin = minP - padding
  const yMax = maxP + padding

  const getY = (p: number) => height - ((p - yMin) / (yMax - yMin)) * height
  const getX = (idx: number) => (idx / (rawPoints.length - 1)) * width

  ctx.strokeStyle = "#29292A"
  ctx.lineWidth = 1
  ctx.strokeRect(0, 0, width, height)

  for (let i = 1; i <= 3; i++) {
    const gy = (i / 4) * height
    ctx.beginPath()
    ctx.moveTo(0, gy)
    ctx.lineTo(width, gy)
    ctx.stroke()
  }

  for (let i = 1; i < 6; i++) {
    const gx = (i / 6) * width
    ctx.beginPath()
    ctx.moveTo(gx, 0)
    ctx.lineTo(gx, height)
    ctx.stroke()
  }

  const refY = getY(effectiveRef)
  ctx.beginPath()
  ctx.setLineDash([3, 2])
  ctx.strokeStyle = "#888888"
  ctx.lineWidth = 1
  ctx.moveTo(0, refY)
  ctx.lineTo(width, refY)
  ctx.stroke()
  ctx.setLineDash([])

  ctx.fillStyle = "#E4E4E6"
  ctx.font = "9.5px monospace"
  ctx.textAlign = "center"
  const labelY = Math.max(10, Math.min(height - 4, refY - 3))
  ctx.fillText(effectiveRef.toFixed(2), width * 0.5, labelY)

  const refRatio = Math.max(0.01, Math.min(0.99, refY / height))
  const lineGrad = ctx.createLinearGradient(0, 0, 0, height)
  lineGrad.addColorStop(0, "#0BDF39")
  lineGrad.addColorStop(Math.max(0, refRatio - 0.005), "#0BDF39")
  lineGrad.addColorStop(Math.min(1, refRatio + 0.005), "#FF0017")
  lineGrad.addColorStop(1, "#FF0017")

  ctx.beginPath()
  ctx.lineWidth = 1.2
  ctx.strokeStyle = lineGrad
  ctx.lineJoin = "round"
  ctx.lineCap = "round"

  let inPath = false
  for (let i = 0; i < rawPoints.length; i++) {
    const p = rawPoints[i]
    if (p === null || p === undefined) {
      inPath = false
      continue
    }
    const x = getX(i)
    const y = getY(p)
    if (!inPath) {
      ctx.moveTo(x, y)
      inPath = true
    } else {
      ctx.lineTo(x, y)
    }
  }
  ctx.stroke()

  let lastIdx = -1
  for (let i = rawPoints.length - 1; i >= 0; i--) {
    if (rawPoints[i] !== null && rawPoints[i] !== undefined) {
      lastIdx = i
      break
    }
  }
  if (lastIdx !== -1) {
    const lastP = rawPoints[lastIdx] as number
    const lastX = getX(lastIdx)
    const lastY = getY(lastP)
    const dotColor = lastP >= effectiveRef ? "#0BDF39" : "#FF0017"

    ctx.beginPath()
    ctx.arc(lastX, lastY, 2.5, 0, Math.PI * 2)
    ctx.fillStyle = dotColor
    ctx.shadowColor = dotColor
    ctx.shadowBlur = 4
    ctx.fill()
    ctx.shadowBlur = 0
  }

  if (hoverData.value?.active) {
    const hx = hoverData.value.x
    const hy = hoverData.value.y

    ctx.beginPath()
    ctx.setLineDash([2, 2])
    ctx.strokeStyle = "rgba(255, 255, 255, 0.4)"
    ctx.lineWidth = 1
    ctx.moveTo(hx, 0)
    ctx.lineTo(hx, height)
    ctx.stroke()
    ctx.setLineDash([])

    if (!hoverData.value.isLunch && hoverData.value.price !== null) {
      ctx.beginPath()
      ctx.arc(hx, hy, 2.5, 0, Math.PI * 2)
      ctx.fillStyle = "#ffffff"
      ctx.fill()
    }
  }
}

function handleMouseMove(e: MouseEvent) {
  const canvas = canvasRef.value
  const points = props.sparkline || []
  if (!canvas || points.length < 2) return

  const rect = canvas.getBoundingClientRect()
  const mouseX = Math.max(0, Math.min(rect.width, e.clientX - rect.left))
  const idx = Math.round((mouseX / rect.width) * (points.length - 1))
  const clampedIdx = Math.max(0, Math.min(points.length - 1, idx))

  const width = rect.width
  const height = rect.height

  const validPoints = points.filter(
    (p): p is number => p !== null && p !== undefined && p > 0,
  )
  const effectiveRef = props.refPrice || validPoints[0] || 1000
  const minP = Math.min(...validPoints, effectiveRef)
  const maxP = Math.max(...validPoints, effectiveRef)
  const spread = maxP - minP || effectiveRef * 0.005
  const padding = spread * 0.12
  const yMin = minP - padding
  const yMax = maxP + padding
  const getY = (p: number) => height - ((p - yMin) / (yMax - yMin)) * height
  const getX = (i: number) => (i / (points.length - 1)) * width

  const p = points[clampedIdx]

  let curHour = 9
  let curMin = 0
  if (points.length === 360) {
    curHour = 9 + Math.floor(clampedIdx / 60)
    curMin = clampedIdx % 60
  } else {
    curHour = 9 + Math.floor((clampedIdx / points.length) * 5.75)
    curMin = Math.floor(((clampedIdx / points.length) * 345) % 60)
  }
  const timeStr = `${String(curHour).padStart(2, "0")}:${String(curMin).padStart(2, "0")}`

  if (p === null || p === undefined) {
    hoverData.value = {
      active: true,
      x: getX(clampedIdx),
      y: height / 2,
      price: null,
      time: timeStr,
      isLunch: true,
    }
  } else {
    hoverData.value = {
      active: true,
      x: getX(clampedIdx),
      y: getY(p),
      price: p,
      time: timeStr,
      isLunch: false,
    }
  }
  renderCanvas()
}

function handleMouseLeave() {
  hoverData.value = null
  renderCanvas()
}

watch(
  () => [props.sparkline, props.refPrice, props.currentPrice],
  () => {
    renderCanvas()
  },
  { deep: true },
)

onMounted(() => {
  renderCanvas()
  if (containerRef.value) {
    resizeObserver = new ResizeObserver(() => {
      renderCanvas()
    })
    resizeObserver.observe(containerRef.value)
  }
})

onBeforeUnmount(() => {
  if (resizeObserver) {
    resizeObserver.disconnect()
    resizeObserver = null
  }
})
</script>

<template>
  <div class="w-full flex flex-col relative select-none">
    <div
      ref="containerRef"
      class="w-full h-[114px] relative cursor-crosshair overflow-hidden"
      @mousemove="handleMouseMove"
      @mouseleave="handleMouseLeave"
    >
      <canvas ref="canvasRef" class="w-full h-full block" />

      <div
        v-if="hoverData?.active"
        class="absolute pointer-events-none z-30 px-1 py-0.5 rounded bg-zinc-900/90 border border-white/20 text-[9px] font-mono tabular-nums text-white shadow-lg flex items-center gap-1 -translate-x-1/2 -translate-y-full top-0"
        :style="{ left: `${hoverData.x}px` }"
      >
        <span class="text-zinc-400">{{ hoverData.time }}</span>
        <template v-if="hoverData.isLunch">
          <span class="text-zinc-400 italic">Nghỉ trưa</span>
        </template>
        <strong
          v-else-if="hoverData.price !== null"
          :class="
            hoverData.price >= (props.refPrice || 0)
              ? 'text-tv-bull'
              : 'text-tv-bear'
          "
        >
          {{ hoverData.price.toFixed(2) }}
        </strong>
      </div>
    </div>

    <div
      class="w-full flex items-center justify-between text-[9px] font-mono text-zinc-400 pt-0.5 px-0.5 leading-none"
    >
      <span v-for="h in hours" :key="h">{{ h }}</span>
    </div>
  </div>
</template>
