<template>
  <div class="space-y-5">
    <!-- Header Strip -->
    <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4 p-5 rounded-2xl bg-[#090d16]/80 border border-white/[0.08] backdrop-blur-xl">
      <div>
        <div class="flex items-center gap-2 text-[10px] font-mono font-bold uppercase tracking-wider text-emerald-400 mb-1">
          <span>MARKET UNIVERSE</span>
          <span class="text-slate-600">/</span>
          <span>HOSE - HNX - UPCOM</span>
        </div>
        <h1 class="text-xl sm:text-2xl font-bold tracking-tight text-white font-mono flex items-center gap-2.5">
          <UIcon name="i-heroicons-chart-bar" class="w-6 h-6 text-emerald-400" />
          Danh Mục Cổ Phiếu Niêm Yết
        </h1>
        <p class="text-xs text-slate-400 mt-1">
          Dữ liệu vũ trụ cổ phiếu đồng bộ từ vnstock adapter. Tổng số: <span class="font-mono text-emerald-400 font-bold">{{ total.toLocaleString('vi-VN') }}</span> mã.
        </p>
      </div>

      <UButton
        color="gray"
        variant="solid"
        size="sm"
        :loading="isLoading"
        class="self-start sm:self-auto font-mono text-xs"
        @click="loadSymbols"
      >
        <template #leading>
          <UIcon name="i-heroicons-arrow-path" :class="{ 'animate-spin': isLoading }" class="w-3.5 h-3.5 text-emerald-400" />
        </template>
        Làm mới dữ liệu
      </UButton>
    </div>

    <!-- Filter & Search Toolbar -->
    <div class="flex flex-col sm:flex-row items-center justify-between gap-3 p-3.5 rounded-xl bg-[#090d16]/60 border border-white/[0.06]">
      <div class="relative flex-1 w-full sm:max-w-md">
        <UInput
          v-model="search"
          placeholder="Tìm theo mã chứng khoán hoặc tên công ty..."
          icon="i-heroicons-magnifying-glass"
          size="sm"
          class="w-full font-mono text-xs"
          @input="onSearchChange"
        />
      </div>

      <div class="flex items-center gap-2 w-full sm:w-auto">
        <USelectMenu
          v-model="selectedExchange"
          :options="exchangeOptions"
          value-attribute="value"
          option-attribute="label"
          class="w-full sm:w-44 font-mono text-xs"
          size="sm"
          placeholder="Lọc sàn"
          @change="onExchangeChange"
        />
      </div>
    </div>

    <!-- Stock Symbols Table Card -->
    <div class="rounded-xl border border-white/[0.08] bg-[#090d16]/80 overflow-hidden shadow-2xl backdrop-blur-xl">
      <div class="p-3.5 border-b border-white/[0.06] flex items-center justify-between bg-white/[0.01]">
        <div class="flex items-center gap-2 text-xs font-mono text-slate-300">
          <span class="w-1.5 h-1.5 rounded-full bg-emerald-400" />
          <span class="font-bold uppercase tracking-wider text-[11px]">BẢNG NIÊM YẾT</span>
        </div>
        <span class="text-[11px] font-mono text-slate-400">
          Trang {{ page + 1 }} / {{ maxPages || 1 }}
        </span>
      </div>

      <div class="overflow-x-auto">
        <table class="w-full text-left text-xs">
          <thead class="bg-white/[0.02] text-slate-400 uppercase font-mono text-[10px] border-b border-white/[0.06] tracking-wider">
            <tr>
              <th class="py-3 px-4 w-28">Mã CK</th>
              <th class="py-3 px-4">Tên công ty</th>
              <th class="py-3 px-4 w-28 text-center">Sàn</th>
              <th class="py-3 px-4 w-40">Ngành nghề (ICB)</th>
              <th class="py-3 px-4 w-24">Loại</th>
              <th class="py-3 px-4 w-28 text-center">Trạng thái</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-white/[0.04] font-mono">
            <tr v-if="isLoading" class="text-center">
              <td colspan="6" class="py-14 text-slate-400">
                <UIcon name="i-heroicons-arrow-path" class="w-7 h-7 animate-spin mx-auto text-emerald-400 mb-2" />
                <p class="text-xs font-mono">Đang truy vấn dữ liệu từ cơ sở dữ liệu...</p>
              </td>
            </tr>

            <tr v-else-if="symbols.length === 0" class="text-center">
              <td colspan="6" class="py-14 text-slate-400">
                <UIcon name="i-heroicons-inbox" class="w-7 h-7 mx-auto text-slate-600 mb-2" />
                <p class="text-xs font-mono">Không tìm thấy mã cổ phiếu phù hợp.</p>
              </td>
            </tr>

            <tr
              v-for="sym in symbols"
              :key="sym.symbol"
              class="hover:bg-white/[0.02] transition-colors group"
            >
              <td class="py-3 px-4 font-bold text-sm">
                <NuxtLink
                  :to="`/stock/${sym.symbol}`"
                  class="text-emerald-400 hover:text-emerald-300 flex items-center gap-1.5 transition-colors"
                >
                  <span>{{ sym.symbol }}</span>
                  <UIcon name="i-heroicons-arrow-up-right" class="w-3.5 h-3.5 opacity-0 group-hover:opacity-100 transition-opacity" />
                </NuxtLink>
              </td>
              <td class="py-3 px-4 font-sans text-slate-200 max-w-xs truncate font-medium">
                {{ sym.organ_name || 'N/A' }}
              </td>
              <td class="py-3 px-4 text-center">
                <span
                  class="inline-block px-2 py-0.5 rounded text-[10px] font-mono font-bold tracking-tight"
                  :class="getExchangeBadgeClass(sym.exchange)"
                >
                  {{ sym.exchange || 'N/A' }}
                </span>
              </td>
              <td class="py-3 px-4 text-slate-400 truncate max-w-xs text-[11px] font-sans">
                {{ sym.industry || 'Chưa phân loại' }}
              </td>
              <td class="py-3 px-4 text-slate-400 text-[11px]">
                {{ sym.asset_type || 'STOCK' }}
              </td>
              <td class="py-3 px-4 text-center">
                <span
                  v-if="sym.is_active"
                  class="inline-flex items-center gap-1 text-[10px] text-emerald-400 font-bold px-2 py-0.5 rounded bg-emerald-500/10 border border-emerald-500/20"
                >
                  <span class="w-1.5 h-1.5 rounded-full bg-emerald-400" />
                  GIAO DỊCH
                </span>
                <span
                  v-else
                  class="inline-flex items-center gap-1 text-[10px] text-rose-400 font-bold px-2 py-0.5 rounded bg-rose-500/10 border border-rose-500/20"
                >
                  <span class="w-1.5 h-1.5 rounded-full bg-rose-400" />
                  TẠM DỪNG
                </span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Pagination Footer -->
      <div v-if="total > limit" class="p-3.5 border-t border-white/[0.06] bg-white/[0.01] flex flex-col sm:flex-row items-center justify-between gap-3 font-mono">
        <p class="text-xs text-slate-400">
          Hiển thị {{ page * limit + 1 }} - {{ Math.min((page + 1) * limit, total) }} / {{ total }} mã
        </p>

        <div class="flex items-center gap-2">
          <UButton
            color="gray"
            variant="solid"
            size="xs"
            :disabled="page === 0 || isLoading"
            class="font-mono text-xs"
            @click="page--; loadSymbols()"
          >
            Trang trước
          </UButton>
          <span class="text-xs font-mono text-slate-300 px-2">
            {{ page + 1 }} / {{ maxPages }}
          </span>
          <UButton
            color="gray"
            variant="solid"
            size="xs"
            :disabled="page >= maxPages - 1 || isLoading"
            class="font-mono text-xs"
            @click="page++; loadSymbols()"
          >
            Trang sau
          </UButton>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { StockSymbolItem } from "~/client/stockService"
import { StockService } from "~/client/stockService"

useHead({
  title: "Thị trường cổ phiếu - Vnstock Quants",
})

const { showErrorToast } = useCustomToast()

const search = ref("")
const selectedExchange = ref<string>("ALL")
const page = ref(0)
const limit = 50
const total = ref(0)
const symbols = ref<StockSymbolItem[]>([])
const isLoading = ref(false)

const exchangeOptions = [
  { label: "Tất cả các sàn", value: "ALL" },
  { label: "HOSE (Sở GDCK TP.HCM)", value: "HOSE" },
  { label: "HNX (Sở GDCK Hà Nội)", value: "HNX" },
  { label: "UPCOM (Thị trường đăng ký)", value: "UPCOM" },
]

const maxPages = computed(() => Math.ceil(total.value / limit) || 1)

let searchTimeout: ReturnType<typeof setTimeout> | null = null

const onSearchChange = () => {
  if (searchTimeout) clearTimeout(searchTimeout)
  searchTimeout = setTimeout(() => {
    page.value = 0
    loadSymbols()
  }, 350)
}

const onExchangeChange = () => {
  page.value = 0
  loadSymbols()
}

const getExchangeBadgeClass = (exchange: string | null) => {
  switch (exchange) {
    case "HOSE":
      return "bg-cyan-500/10 text-cyan-400 border border-cyan-500/20"
    case "HNX":
      return "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
    case "UPCOM":
      return "bg-amber-500/10 text-amber-400 border border-amber-500/20"
    default:
      return "bg-slate-800 text-slate-400 border border-slate-700"
  }
}

const loadSymbols = async () => {
  isLoading.value = true
  try {
    const exchange =
      selectedExchange.value === "ALL" ? undefined : selectedExchange.value
    const q = search.value.trim() || undefined

    const res = await StockService.listSymbols({
      query: {
        skip: page.value * limit,
        limit,
        exchange,
        search: q,
      },
    })
    symbols.value = res.data
    total.value = res.count
  } catch (err: unknown) {
    const errorMsg =
      err instanceof Error ? err.message : "Không thể tải danh sách cổ phiếu"
    showErrorToast("Lỗi truy vấn", errorMsg)
  } finally {
    isLoading.value = false
  }
}

onMounted(() => {
  loadSymbols()
})
</script>
