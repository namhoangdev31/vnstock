<template>
  <div class="space-y-6">
    <!-- Header -->
    <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
      <div>
        <h1 class="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
          <UIcon name="i-heroicons-chart-bar" class="w-7 h-7 text-emerald-400" />
          Thị trường cổ phiếu Việt Nam
        </h1>
        <p class="text-xs sm:text-sm text-slate-400 mt-1">
          Dữ liệu niêm yết HOSE, HNX, UPCOM đồng bộ từ vnstock — Tổng số: <span class="font-mono text-emerald-400 font-semibold">{{ total }}</span> mã
        </p>
      </div>

      <UButton
        color="gray"
        variant="solid"
        size="sm"
        :loading="isLoading"
        class="self-start sm:self-auto"
        @click="loadSymbols"
      >
        <template #leading>
          <UIcon name="i-heroicons-arrow-path" :class="{ 'animate-spin': isLoading }" class="w-4 h-4" />
        </template>
        Làm mới
      </UButton>
    </div>

    <!-- Filter Bar -->
    <div class="flex flex-col sm:flex-row gap-3">
      <div class="relative flex-1 max-w-md">
        <UInput
          v-model="search"
          placeholder="Tìm theo mã CK hoặc tên công ty..."
          icon="i-heroicons-magnifying-glass"
          size="md"
          class="w-full"
          @input="onSearchChange"
        />
      </div>

      <USelectMenu
        v-model="selectedExchange"
        :options="exchangeOptions"
        value-attribute="value"
        option-attribute="label"
        class="w-44"
        size="md"
        placeholder="Chọn sàn"
        @change="onExchangeChange"
      />
    </div>

    <!-- Stock Symbols Table Card -->
    <div class="rounded-xl border border-slate-800 bg-slate-900/60 overflow-hidden shadow-xl">
      <div class="p-4 border-b border-slate-800/80 flex items-center justify-between">
        <span class="text-xs font-semibold text-slate-300 uppercase tracking-wider">
          Bảng mã niêm yết
        </span>
        <span class="text-xs text-slate-400">
          Hiển thị trang {{ page + 1 }} / {{ maxPages || 1 }}
        </span>
      </div>

      <div class="overflow-x-auto">
        <table class="w-full text-left text-xs">
          <thead class="bg-slate-900/90 text-slate-400 uppercase font-mono text-[11px] border-b border-slate-800">
            <tr>
              <th class="py-3 px-4 w-28">Mã CK</th>
              <th class="py-3 px-4">Tên công ty</th>
              <th class="py-3 px-4 w-24">Sàn</th>
              <th class="py-3 px-4 w-36">Ngành</th>
              <th class="py-3 px-4 w-28">Loại</th>
              <th class="py-3 px-4 w-24 text-center">Trạng thái</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-800/60">
            <tr v-if="isLoading" class="text-center">
              <td colspan="6" class="py-12 text-slate-400">
                <UIcon name="i-heroicons-arrow-path" class="w-8 h-8 animate-spin mx-auto text-emerald-400 mb-2" />
                <p>Đang tải danh sách cổ phiếu...</p>
              </td>
            </tr>

            <tr v-else-if="symbols.length === 0" class="text-center">
              <td colspan="6" class="py-12 text-slate-400">
                <UIcon name="i-heroicons-face-frown" class="w-8 h-8 mx-auto text-slate-600 mb-2" />
                <p>Không tìm thấy mã cổ phiếu nào phù hợp với bộ lọc.</p>
              </td>
            </tr>

            <tr
              v-for="sym in symbols"
              :key="sym.symbol"
              class="hover:bg-slate-800/40 transition-colors group"
            >
              <td class="py-3 px-4 font-mono font-bold text-sm">
                <NuxtLink
                  :to="`/stock/${sym.symbol}`"
                  class="text-emerald-400 hover:text-emerald-300 hover:underline flex items-center gap-1.5"
                >
                  {{ sym.symbol }}
                  <UIcon name="i-heroicons-arrow-up-right" class="w-3.5 h-3.5 opacity-0 group-hover:opacity-100 transition-opacity" />
                </NuxtLink>
              </td>
              <td class="py-3 px-4 font-medium text-slate-200 max-w-xs truncate">
                {{ sym.organ_name || '—' }}
              </td>
              <td class="py-3 px-4">
                <span
                  class="inline-block px-2 py-0.5 rounded text-[11px] font-mono font-semibold"
                  :class="getExchangeBadgeClass(sym.exchange)"
                >
                  {{ sym.exchange || '—' }}
                </span>
              </td>
              <td class="py-3 px-4 text-slate-400 truncate max-w-xs">
                {{ sym.industry || '—' }}
              </td>
              <td class="py-3 px-4 text-slate-400">
                {{ sym.asset_type }}
              </td>
              <td class="py-3 px-4 text-center">
                <span
                  v-if="sym.is_active"
                  class="inline-flex items-center gap-1 text-[11px] text-emerald-400 font-semibold"
                >
                  <UIcon name="i-heroicons-check-circle" class="w-4 h-4" />
                  Giao dịch
                </span>
                <span
                  v-else
                  class="inline-flex items-center gap-1 text-[11px] text-rose-400 font-semibold"
                >
                  <UIcon name="i-heroicons-minus-circle" class="w-4 h-4" />
                  Tạm dừng
                </span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Pagination Footer -->
      <div v-if="total > limit" class="p-4 border-t border-slate-800 flex items-center justify-between">
        <p class="text-xs text-slate-400">
          Hiển thị từ {{ page * limit + 1 }} đến {{ Math.min((page + 1) * limit, total) }} trong tổng số {{ total }}
        </p>

        <div class="flex items-center gap-2">
          <UButton
            color="gray"
            variant="solid"
            size="xs"
            :disabled="page === 0 || isLoading"
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
  { label: "HOSE (HSX)", value: "HOSE" },
  { label: "HNX", value: "HNX" },
  { label: "UPCOM", value: "UPCOM" },
]

const maxPages = computed(() => Math.ceil(total.value / limit) || 1)

let searchDebounceTimer: NodeJS.Timeout | null = null

const onSearchChange = () => {
  if (searchDebounceTimer) clearTimeout(searchDebounceTimer)
  searchDebounceTimer = setTimeout(() => {
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
      return "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
    case "HNX":
      return "bg-blue-500/10 text-blue-400 border border-blue-500/20"
    case "UPCOM":
      return "bg-amber-500/10 text-amber-400 border border-amber-500/20"
    default:
      return "bg-slate-800 text-slate-400"
  }
}

const loadSymbols = async () => {
  isLoading.value = true
  try {
    const exchange =
      selectedExchange.value === "ALL" ? undefined : selectedExchange.value
    const res = await StockService.listSymbols({
      query: {
        skip: page.value * limit,
        limit,
        search: search.value.trim() || undefined,
        exchange,
      },
    })
    symbols.value = res.data ?? []
    total.value = res.count ?? 0
  } catch (err: unknown) {
    const error = err as { message?: string }
    showErrorToast(
      "Lỗi tải danh sách cổ phiếu",
      error?.message || "Không thể kết nối đến máy chủ.",
    )
  } finally {
    isLoading.value = false
  }
}

onMounted(() => {
  loadSymbols()
})
</script>
