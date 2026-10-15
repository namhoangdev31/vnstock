<script setup lang="ts">
import type { IBoardIndexItem } from "~/client/types.gen"
import { MarketIndexSymbol } from "~/types/market"

interface Props {
  indices: IBoardIndexItem[]
}

const props = withDefaults(defineProps<Props>(), {
  indices: () => [],
})

const parseNum = (val: string | number | undefined | null): number => {
  if (typeof val === "number") return val
  if (!val) return 0
  const clean = String(val).replace(/,/g, "").trim()
  const n = Number.parseFloat(clean)
  return Number.isNaN(n) ? 0 : n
}

const formatPrice = (val: string | number | undefined | null): string => {
  if (val === undefined || val === null || val === "") return "-"
  const n = parseNum(val)
  if (Number.isNaN(n) || n === 0) return String(val)
  return n.toLocaleString("en-US", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })
}

const formatSignedChange = (
  val: string | number | undefined | null,
): string => {
  const n = parseNum(val)
  if (Math.abs(n) < 0.001) return "0.00"
  const sign = n > 0 ? "+" : ""
  return `${sign}${n.toFixed(2)}`
}

const getVolumeMillion = (item: IBoardIndexItem): string => {
  const isDeriv = item.name === MarketIndexSymbol.VN30F1M
  if (isDeriv) {
    if (item.raw_volume && item.raw_volume > 0) {
      return Math.round(item.raw_volume).toLocaleString("en-US")
    }
    return item.volume.replace("HĐ", "").trim()
  }
  if (item.raw_volume && item.raw_volume > 0) {
    return (item.raw_volume / 1e6).toLocaleString("en-US", {
      minimumFractionDigits: 3,
      maximumFractionDigits: 3,
    })
  }
  const clean = item.volume.replace("Triệu CP", "").trim()
  return clean || "-"
}

const getValueBillion = (item: IBoardIndexItem): string => {
  if (item.raw_value && item.raw_value > 0) {
    return item.raw_value.toLocaleString("en-US", {
      minimumFractionDigits: 3,
      maximumFractionDigits: 3,
    })
  }
  return item.value.replace("Tỷ", "").trim() || "-"
}

const getColorClass = (changeStr: string): string => {
  const chg = parseNum(changeStr)
  if (chg > 0.001) return "text-[#089981]"
  if (chg < -0.001) return "text-[#f23645]"
  return "text-[#f59e0b]"
}
</script>

<template>
  <div
    class="flex flex-col bg-[#10121a] rounded border border-white/[0.08] overflow-hidden select-none shadow-sm h-full"
  >

    <div
      class="grid grid-cols-12 gap-1 py-1 px-1.5 bg-[#141724] border-b border-white/[0.06] text-[9.5px] font-medium text-zinc-400 leading-none items-center"
    >
      <div class="col-span-3 flex items-center gap-1">
        <UIcon name="i-heroicons-cog-6-tooth" class="w-2.5 h-2.5 text-zinc-500" />
        <span>Chỉ số</span>
      </div>
      <div class="col-span-3 text-right">Điểm (+/-)</div>
      <div class="col-span-2 text-right">KLGD (Tr)</div>
      <div class="col-span-2 text-right">GTGD (Tỷ)</div>
      <div class="col-span-2 text-right">CK Tăng/Giảm</div>
    </div>

    <div class="flex flex-col divide-y divide-white/[0.03] text-[10px] font-mono tabular-nums">
      <div
        v-for="item in props.indices"
        :key="item.id || item.name"
        class="grid grid-cols-12 gap-1 py-1 px-1.5 items-center hover:bg-white/[0.04] transition-colors leading-tight"
      >

        <div class="col-span-3 font-bold text-white truncate text-[10.5px]">
          {{ item.name }}
        </div>

        <div
          class="col-span-3 text-right flex items-center justify-end gap-1 font-bold text-[10px]"
          :class="getColorClass(item.change)"
        >
          <span>{{ formatPrice(item.price) }}</span>
          <span class="text-[9px] font-normal font-mono opacity-90">
            {{ formatSignedChange(item.change) }}
          </span>
        </div>

        <div class="col-span-2 text-right text-zinc-300 text-[10px]">
          {{ getVolumeMillion(item) }}
        </div>

        <div class="col-span-2 text-right text-zinc-300 text-[10px]">
          {{ getValueBillion(item) }}
        </div>

        <div class="col-span-2 text-right flex items-center justify-end gap-1 text-[9px]">
          <template v-if="item.breadth">
            <span class="text-[#089981] flex items-center">
              <span>↑</span>
              <span>{{ item.breadth.advance }}</span>
            </span>
            <span class="text-[#f59e0b] flex items-center">
              <span>—</span>
              <span>{{ item.breadth.unchanged }}</span>
            </span>
            <span class="text-[#f23645] flex items-center">
              <span>↓</span>
              <span>{{ item.breadth.decline }}</span>
            </span>
          </template>
          <template v-else-if="item.name === MarketIndexSymbol.VN30F1M">
            <span class="text-zinc-500 text-[8.5px]">Phái sinh</span>
          </template>
          <template v-else>
            <span class="text-zinc-600">-</span>
          </template>
        </div>
      </div>
    </div>
  </div>
</template>
