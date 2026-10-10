<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted } from "vue"

definePageMeta({
  layout: false,
})

const { user, token, logout } = useAuth()
const route = useRoute()
const router = useRouter()

// Market mode: 'underlying' (Cổ phiếu cơ sở) vs 'derivatives' (Thị trường phái sinh)
const currentMarket = ref<"underlying" | "derivatives">(
  route.query.market === "derivatives" ? "derivatives" : "underlying",
)

const isDerivatives = computed(() => currentMarket.value === "derivatives")

const toggleMarket = () => {
  const nextMarket =
    currentMarket.value === "underlying" ? "derivatives" : "underlying"
  currentMarket.value = nextMarket
  router.replace({
    query: {
      ...route.query,
      market: nextMarket === "derivatives" ? "derivatives" : undefined,
    },
  })
}

watch(
  () => route.query.market,
  (val) => {
    if (val === "derivatives" && currentMarket.value !== "derivatives") {
      currentMarket.value = "derivatives"
    } else if (val !== "derivatives" && currentMarket.value !== "underlying") {
      currentMarket.value = "underlying"
    }
  },
)

useHead({
  title: computed(() =>
    isDerivatives.value
      ? "Bảng giá phái sinh VN30F1M - Vistock"
      : "Bảng giá cổ phiếu cơ sở - Vistock",
  ),
})

// Active dropdown menu state with hover grace period
const activeMenu = ref<string | null>(null)
let menuTimer: ReturnType<typeof setTimeout> | null = null

const openMenu = (menu: string) => {
  if (menuTimer) clearTimeout(menuTimer)
  activeMenu.value = menu
}

const scheduleCloseMenu = () => {
  menuTimer = setTimeout(() => {
    activeMenu.value = null
  }, 150)
}

const toggleMenu = (menu: string) => {
  activeMenu.value = activeMenu.value === menu ? null : menu
}

const closeMenu = () => {
  if (menuTimer) clearTimeout(menuTimer)
  activeMenu.value = null
}

// User initials for authenticated avatar
const userInitials = computed(() => {
  if (user.value?.full_name) {
    const parts = user.value.full_name.trim().split(" ")
    return parts.length > 1
      ? (parts[0][0] + parts[parts.length - 1][0]).toUpperCase()
      : parts[0].slice(0, 2).toUpperCase()
  }
  if (user.value?.email) {
    return user.value.email.slice(0, 2).toUpperCase()
  }
  return "U"
})

// Realtime system clock (HH:mm:ss)
const currentTime = ref("")
const updateClock = () => {
  const now = new Date()
  currentTime.value = now.toLocaleTimeString("vi-VN", { hour12: false })
}

let clockTimer: ReturnType<typeof setInterval> | null = null

interface NewsHeadline {
  symbol: string
  title: string
  published_at?: string
  url?: string | null
  source?: string
  is_today?: boolean
}

// Rotating financial news headlines (today or yesterday)
const newsItems = ref<NewsHeadline[]>([])
const currentNewsIndex = ref(0)
let newsTimer: ReturnType<typeof setInterval> | null = null

const currentNews = computed<NewsHeadline | null>(() => {
  if (newsItems.value.length === 0) return null
  return newsItems.value[currentNewsIndex.value] || null
})

const pickNextRandomNews = () => {
  if (newsItems.value.length <= 1) return
  let nextIndex = currentNewsIndex.value
  const maxAttempts = 10
  for (let i = 0; i < maxAttempts; i++) {
    const candidate = Math.floor(Math.random() * newsItems.value.length)
    if (candidate !== currentNewsIndex.value) {
      nextIndex = candidate
      break
    }
  }
  currentNewsIndex.value = nextIndex
}

const loadMarketNews = async () => {
  try {
    const data = await $fetch<NewsHeadline[]>("/api/v1/stock/iboard/news", {
      params: { limit: 40, randomize: true },
    })
    if (Array.isArray(data) && data.length > 0) {
      newsItems.value = data
      currentNewsIndex.value = Math.floor(Math.random() * data.length)
    }
  } catch {
    // Keep empty if network error
  }
}

// Mobile menu toggle
const mobileOpen = ref(false)

onMounted(() => {
  updateClock()
  clockTimer = setInterval(updateClock, 1000)

  // Fetch real-time news from today or yesterday
  loadMarketNews()

  // Rotate randomly every 4500ms
  newsTimer = setInterval(pickNextRandomNews, 4500)
})

onUnmounted(() => {
  if (clockTimer) clearInterval(clockTimer)
  if (newsTimer) clearInterval(newsTimer)
  if (menuTimer) clearTimeout(menuTimer)
})
</script>

<template>
  <div class="min-h-screen bg-surface-abyss text-aave-paper font-sans select-none flex flex-col">
    <!-- Top Navigation Header (DNSE Style) -->
    <header class="sticky top-0 z-50 h-12 bg-surface-midnight border-b border-white/[0.08] text-white flex items-center justify-between px-3 sm:px-4 text-xs font-sans">
      <!-- Left: Logo, Home, and Navigation Links -->
      <div class="flex items-center gap-1 sm:gap-2 lg:gap-3 shrink-0">
        <!-- Brand Logo -->
        <NuxtLink to="/iboard" class="flex items-center gap-2 mr-1 group">
          <span class="font-bold tracking-tight text-sm text-white group-hover:text-rose-400 transition-colors">
            VISTOCK
          </span>
        </NuxtLink>

        <!-- Home Icon -->
        <NuxtLink
          to="/"
          class="p-1.5 text-aave-graphite hover:text-white rounded hover:bg-white/[0.06] transition-colors"
          title="Trang chủ"
        >
          <UIcon name="i-heroicons-home" class="w-4 h-4" />
        </NuxtLink>

        <!-- Desktop Navigation Items -->
        <nav class="hidden lg:flex items-center">
          <!-- 1. Bảng giá (Active link with red accent bottom border) -->
          <NuxtLink
            to="/iboard"
            class="h-12 flex items-center px-2.5 xl:px-3 font-semibold text-rose-500 border-b-2 border-rose-500 transition-colors"
          >
            Bảng giá
          </NuxtLink>

          <!-- 2. Đặt lệnh Dropdown (Matching screenshot) -->
          <div
            class="relative h-12 flex items-center"
            @mouseenter="openMenu('order')"
            @mouseleave="scheduleCloseMenu"
          >
            <button
              type="button"
              class="h-12 flex items-center gap-1 px-2 xl:px-2.5 text-aave-ash hover:text-white transition-colors"
              :class="{ 'text-white font-medium': activeMenu === 'order' }"
              @click="toggleMenu('order')"
            >
              <span>Đặt lệnh</span>
              <UIcon
                name="i-heroicons-chevron-down"
                class="w-3.5 h-3.5 transition-transform duration-200"
                :class="{ 'rotate-180': activeMenu === 'order' }"
              />
            </button>

            <!-- Dropdown Menu Box -->
            <div
              v-if="activeMenu === 'order'"
              class="absolute top-12 left-0 w-64 bg-surface-midnight border border-white/[0.1] rounded-b-xl shadow-2xl py-2 z-50 animate-fade-in-down"
            >
              <NuxtLink
                to="/app"
                class="flex items-start gap-3 px-3.5 py-2.5 hover:bg-white/[0.06] transition-colors group"
                @click="closeMenu"
              >
                <UIcon name="i-heroicons-pencil-square" class="w-4 h-4 text-aave-ash group-hover:text-rose-400 mt-0.5 shrink-0" />
                <div>
                  <div class="text-xs font-semibold text-white group-hover:text-rose-400">Đặt lệnh thường</div>
                  <div class="text-[11px] text-aave-graphite mt-0.5">Giao dịch cổ phiếu và phái sinh</div>
                </div>
              </NuxtLink>

              <NuxtLink
                to="/app"
                class="flex items-start gap-3 px-3.5 py-2.5 hover:bg-white/[0.06] transition-colors group"
                @click="closeMenu"
              >
                <UIcon name="i-heroicons-hand-raised" class="w-4 h-4 text-aave-ash group-hover:text-rose-400 mt-0.5 shrink-0" />
                <div>
                  <div class="text-xs font-semibold text-white group-hover:text-rose-400">Đặt lệnh thoả thuận</div>
                  <div class="text-[11px] text-aave-graphite mt-0.5">Giao dịch thoả thuận trong và ngoài hệ thống</div>
                </div>
              </NuxtLink>
            </div>
          </div>
          <!-- 3. Phân tích Dropdown -->
          <div
            class="relative h-12 flex items-center"
            @mouseenter="openMenu('analysis')"
            @mouseleave="scheduleCloseMenu"
          >
            <button
              type="button"
              class="h-12 flex items-center gap-1 px-2 xl:px-2.5 text-aave-ash hover:text-white transition-colors"
              :class="{ 'text-white font-medium': activeMenu === 'analysis' }"
              @click="toggleMenu('analysis')"
            >
              <span>Phân tích</span>
              <UIcon
                name="i-heroicons-chevron-down"
                class="w-3.5 h-3.5 transition-transform duration-200"
                :class="{ 'rotate-180': activeMenu === 'analysis' }"
              />
            </button>

            <div
              v-if="activeMenu === 'analysis'"
              class="absolute top-12 left-0 w-64 bg-surface-midnight border border-white/[0.1] rounded-b-xl shadow-2xl py-2 z-50 animate-fade-in-down"
            >
              <NuxtLink
                to="/app"
                class="flex items-start gap-3 px-3.5 py-2.5 hover:bg-white/[0.06] transition-colors group"
                @click="closeMenu"
              >
                <UIcon name="i-heroicons-chart-bar-square" class="w-4 h-4 text-aave-ash group-hover:text-rose-400 mt-0.5 shrink-0" />
                <div>
                  <div class="text-xs font-semibold text-white group-hover:text-rose-400">Biểu đồ kỹ thuật</div>
                  <div class="text-[11px] text-aave-graphite mt-0.5">Đồ thị nến đa khung thời gian</div>
                </div>
              </NuxtLink>

              <NuxtLink
                to="/admin"
                class="flex items-start gap-3 px-3.5 py-2.5 hover:bg-white/[0.06] transition-colors group"
                @click="closeMenu"
              >
                <UIcon name="i-heroicons-cpu-chip" class="w-4 h-4 text-aave-ash group-hover:text-rose-400 mt-0.5 shrink-0" />
                <div>
                  <div class="text-xs font-semibold text-white group-hover:text-rose-400">Mô hình định lượng</div>
                  <div class="text-[11px] text-aave-graphite mt-0.5">Tín hiệu Ensemble 3 động cơ</div>
                </div>
              </NuxtLink>

              <NuxtLink
                to="/admin"
                class="flex items-start gap-3 px-3.5 py-2.5 hover:bg-white/[0.06] transition-colors group"
                @click="closeMenu"
              >
                <UIcon name="i-heroicons-squares-2x2" class="w-4 h-4 text-aave-ash group-hover:text-rose-400 mt-0.5 shrink-0" />
                <div>
                  <div class="text-xs font-semibold text-white group-hover:text-rose-400">Bản đồ nhiệt thị trường</div>
                  <div class="text-[11px] text-aave-graphite mt-0.5">Dòng tiền ngành và nhóm vốn hóa</div>
                </div>
              </NuxtLink>
            </div>
          </div>

          <!-- 5. Tài sản Dropdown -->
          <div
            class="relative h-12 flex items-center"
            @mouseenter="openMenu('assets')"
            @mouseleave="scheduleCloseMenu"
          >
            <button
              type="button"
              class="h-12 flex items-center gap-1 px-2 xl:px-2.5 text-aave-ash hover:text-white transition-colors"
              :class="{ 'text-white font-medium': activeMenu === 'assets' }"
              @click="toggleMenu('assets')"
            >
              <span>Tài sản</span>
              <UIcon
                name="i-heroicons-chevron-down"
                class="w-3.5 h-3.5 transition-transform duration-200"
                :class="{ 'rotate-180': activeMenu === 'assets' }"
              />
            </button>

            <div
              v-if="activeMenu === 'assets'"
              class="absolute top-12 left-0 w-64 bg-surface-midnight border border-white/[0.1] rounded-b-xl shadow-2xl py-2 z-50 animate-fade-in-down"
            >
              <NuxtLink
                to="/app"
                class="flex items-start gap-3 px-3.5 py-2.5 hover:bg-white/[0.06] transition-colors group"
                @click="closeMenu"
              >
                <UIcon name="i-heroicons-circle-stack" class="w-4 h-4 text-aave-ash group-hover:text-rose-400 mt-0.5 shrink-0" />
                <div>
                  <div class="text-xs font-semibold text-white group-hover:text-rose-400">Tổng quan tài sản</div>
                  <div class="text-[11px] text-aave-graphite mt-0.5">Quản lý NAV, tiền mặt và cổ phiếu</div>
                </div>
              </NuxtLink>

              <NuxtLink
                to="/app"
                class="flex items-start gap-3 px-3.5 py-2.5 hover:bg-white/[0.06] transition-colors group"
                @click="closeMenu"
              >
                <UIcon name="i-heroicons-document-text" class="w-4 h-4 text-aave-ash group-hover:text-rose-400 mt-0.5 shrink-0" />
                <div>
                  <div class="text-xs font-semibold text-white group-hover:text-rose-400">Báo cáo lãi lỗ</div>
                  <div class="text-[11px] text-aave-graphite mt-0.5">Lãi lỗ danh mục và vị thế T+2</div>
                </div>
              </NuxtLink>
            </div>
          </div>

          <!-- 6. Tiện ích Dropdown -->
          <div
            class="relative h-12 flex items-center"
            @mouseenter="openMenu('tools')"
            @mouseleave="scheduleCloseMenu"
          >
            <button
              type="button"
              class="h-12 flex items-center gap-1 px-2 xl:px-2.5 text-aave-ash hover:text-white transition-colors"
              :class="{ 'text-white font-medium': activeMenu === 'tools' }"
              @click="toggleMenu('tools')"
            >
              <span>Tiện ích</span>
              <UIcon
                name="i-heroicons-chevron-down"
                class="w-3.5 h-3.5 transition-transform duration-200"
                :class="{ 'rotate-180': activeMenu === 'tools' }"
              />
            </button>

            <div
              v-if="activeMenu === 'tools'"
              class="absolute top-12 left-0 w-64 bg-surface-midnight border border-white/[0.1] rounded-b-xl shadow-2xl py-2 z-50 animate-fade-in-down"
            >
              <NuxtLink
                to="/app"
                class="flex items-start gap-3 px-3.5 py-2.5 hover:bg-white/[0.06] transition-colors group"
                @click="closeMenu"
              >
                <UIcon name="i-heroicons-cog-6-tooth" class="w-4 h-4 text-aave-ash group-hover:text-rose-400 mt-0.5 shrink-0" />
                <div>
                  <div class="text-xs font-semibold text-white group-hover:text-rose-400">Cài đặt hệ thống</div>
                  <div class="text-[11px] text-aave-graphite mt-0.5">Tùy biến bảng giá và phím tắt</div>
                </div>
              </NuxtLink>

              <NuxtLink
                to="/"
                class="flex items-start gap-3 px-3.5 py-2.5 hover:bg-white/[0.06] transition-colors group"
                @click="closeMenu"
              >
                <UIcon name="i-heroicons-book-open" class="w-4 h-4 text-aave-ash group-hover:text-rose-400 mt-0.5 shrink-0" />
                <div>
                  <div class="text-xs font-semibold text-white group-hover:text-rose-400">Quy tắc giao dịch</div>
                  <div class="text-[11px] text-aave-graphite mt-0.5">Khớp lệnh ATO, ATC và biên độ giá</div>
                </div>
              </NuxtLink>
            </div>
          </div>
        </nav>
      </div>

      <!-- Center: News Ticker / Marquee Box (Random news from today / yesterday) -->
      <div
        v-if="currentNews"
        class="hidden xl:flex items-center flex-1 max-w-sm 2xl:max-w-md mx-2 min-w-0"
      >
        <UTooltip
          :text="`${currentNews.symbol} • ${currentNews.title}${currentNews.published_at ? ' • ' + currentNews.published_at : ''}`"
          :popper="{ placement: 'bottom' }"
          class="w-full"
        >
          <component
            :is="currentNews.url ? 'a' : 'div'"
            :href="currentNews.url || undefined"
            :target="currentNews.url ? '_blank' : undefined"
            :rel="currentNews.url ? 'noopener noreferrer' : undefined"
            class="w-full flex items-center gap-2 px-3 py-1 rounded-full bg-white/[0.04] hover:bg-white/[0.08] transition-colors overflow-hidden group"
            :class="{ 'cursor-pointer': !!currentNews.url }"
          >
            <span class="px-1.5 py-0.5 rounded text-[10px] font-mono font-bold bg-white/10 text-white shrink-0">
              {{ currentNews.symbol }}
            </span>
            <span class="text-[11px] text-aave-ash truncate transition-colors group-hover:text-white">
              {{ currentNews.title }}
            </span>
          </component>
        </UTooltip>
      </div>

      <!-- Right: Clock, Tools, Auth Buttons -->
      <div class="flex items-center gap-2 sm:gap-3 shrink-0">
        <!-- Live Clock (HH:mm:ss) -->
        <div class="font-mono text-xs text-white tracking-wide shrink-0 hidden sm:block">
          {{ currentTime }}
        </div>

        <!-- Quick Action Icons -->
        <div class="flex items-center gap-0.5 text-aave-ash">
          <!-- Flame / Heatmap Icon -->
          <UTooltip text="Bản đồ nhiệt thị trường">
            <button
              type="button"
              class="p-1.5 text-rose-400 hover:text-rose-300 hover:bg-white/[0.06] rounded transition-colors"
            >
              <UIcon name="i-heroicons-fire" class="w-4 h-4" />
            </button>
          </UTooltip>

          <!-- Settings Gear -->
          <UTooltip text="Cài đặt bảng giá">
            <button
              type="button"
              class="p-1.5 hover:text-white hover:bg-white/[0.06] rounded transition-colors"
            >
              <UIcon name="i-heroicons-cog-6-tooth" class="w-4 h-4" />
            </button>
          </UTooltip>

          <!-- Market Switch Button: Cổ phiếu cơ sở <-> Thị trường phái sinh -->
          <UTooltip
            :text="
              isDerivatives
                ? 'Đang ở thị trường phái sinh • Nhấn để chuyển về cổ phiếu cơ sở'
                : 'Đang ở cổ phiếu cơ sở • Nhấn để chuyển sang thị trường phái sinh'
            "
          >
            <button
              type="button"
              role="switch"
              :aria-checked="isDerivatives"
              aria-label="Chuyển đổi thị trường cơ sở và phái sinh"
              class="h-7 px-2 flex items-center gap-1.5 rounded-full border transition-colors text-xs font-medium ml-1"
              :class="
                isDerivatives
                  ? 'bg-rose-600/20 border-rose-500/40 text-rose-300 hover:bg-rose-600/30'
                  : 'bg-white/[0.04] border-white/[0.08] text-aave-ash hover:text-white hover:bg-white/[0.08]'
              "
              @click="toggleMarket"
            >
              <UIcon
                :name="isDerivatives ? 'i-heroicons-bolt' : 'i-heroicons-chart-bar'"
                class="w-3.5 h-3.5 shrink-0"
                :class="isDerivatives ? 'text-rose-400' : 'text-aave-graphite'"
              />
              <span class="text-[11px] font-semibold tracking-wide hidden sm:inline">
                {{ isDerivatives ? 'Phái sinh' : 'Cơ sở' }}
              </span>
              <!-- Physical Switch Indicator Track -->
              <span
                class="w-6 h-3 rounded-full p-0.5 inline-flex items-center transition-colors relative shrink-0"
                :class="isDerivatives ? 'bg-rose-600' : 'bg-white/20'"
              >
                <span
                  class="w-2 h-2 rounded-full bg-white transition-transform duration-200 block shadow-sm"
                  :class="isDerivatives ? 'translate-x-3' : 'translate-x-0'"
                />
              </span>
            </button>
          </UTooltip>
        </div>

        <!-- User Authentication State -->
        <template v-if="token">
          <div class="flex items-center gap-2 pl-2 border-l border-white/[0.08]">
            <NuxtLink
              to="/app"
              class="flex items-center gap-2 hover:opacity-90 transition-opacity"
            >
              <div class="w-6 h-6 rounded-full bg-rose-600 text-white font-mono font-bold text-[10px] flex items-center justify-center">
                {{ userInitials }}
              </div>
              <span class="text-xs font-medium text-white max-w-[100px] truncate hidden md:inline">
                {{ user?.full_name || user?.email?.split('@')[0] || 'Tài khoản' }}
              </span>
            </NuxtLink>

            <button
              type="button"
              class="p-1 text-aave-ash hover:text-rose-400 rounded hover:bg-white/[0.06] transition-colors"
              title="Đăng xuất"
              @click="logout"
            >
              <UIcon name="i-heroicons-arrow-right-on-rectangle" class="w-4 h-4" />
            </button>
          </div>
        </template>
        <template v-else>
          <div class="flex items-center gap-2 pl-1 sm:pl-2 border-l border-white/[0.08]">
            <NuxtLink
              to="/login"
              class="px-3.5 py-1 rounded-full text-xs font-semibold bg-rose-600 hover:bg-rose-500 text-white transition-colors shrink-0 shadow-sm"
            >
              Đăng nhập
            </NuxtLink>
          </div>
        </template>

        <!-- Mobile Menu Hamburger Button -->
        <button
          type="button"
          class="lg:hidden p-1.5 text-aave-ash hover:text-white rounded hover:bg-white/[0.06]"
          :aria-label="mobileOpen ? 'Đóng menu' : 'Mở menu'"
          @click="mobileOpen = !mobileOpen"
        >
          <UIcon :name="mobileOpen ? 'i-heroicons-x-mark' : 'i-heroicons-bars-3'" class="w-5 h-5" />
        </button>
      </div>
    </header>

    <!-- Mobile Drawer for smaller screens -->
    <div
      v-if="mobileOpen"
      class="lg:hidden border-b border-white/[0.08] bg-surface-midnight px-4 py-3 space-y-2 animate-fade-in-down"
    >
      <div class="flex items-center justify-between pb-2 border-b border-white/[0.08] text-xs font-mono text-aave-graphite">
        <span>Bảng giá trực tuyến Vistock</span>
        <span>{{ currentTime }}</span>
      </div>

      <!-- Mobile Market Switcher -->
      <div class="flex items-center justify-between px-3 py-2 rounded bg-white/[0.03] border border-white/[0.06] text-xs">
        <span class="text-aave-ash">Thị trường</span>
        <button
          type="button"
          role="switch"
          :aria-checked="isDerivatives"
          class="flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-semibold border transition-colors"
          :class="
            isDerivatives
              ? 'bg-rose-600/20 text-rose-300 border-rose-500/30'
              : 'bg-white/[0.06] text-white border-white/[0.1]'
          "
          @click="toggleMarket"
        >
          <UIcon :name="isDerivatives ? 'i-heroicons-bolt' : 'i-heroicons-chart-bar'" class="w-3.5 h-3.5" />
          <span>{{ isDerivatives ? 'Phái sinh VN30F1M' : 'Cổ phiếu cơ sở' }}</span>
        </button>
      </div>

      <nav class="space-y-1">
        <NuxtLink
          to="/iboard"
          class="flex items-center gap-2 px-3 py-2 rounded text-xs font-semibold bg-rose-600/20 text-rose-400 border border-rose-500/30"
          @click="mobileOpen = false"
        >
          <UIcon name="i-heroicons-chart-bar-square" class="w-4 h-4" />
          <span>Bảng giá</span>
        </NuxtLink>

        <NuxtLink
          to="/app"
          class="flex items-center gap-2 px-3 py-2 rounded text-xs font-medium text-aave-ash hover:text-white hover:bg-white/[0.04]"
          @click="mobileOpen = false"
        >
          <UIcon name="i-heroicons-pencil-square" class="w-4 h-4" />
          <span>Đặt lệnh</span>
        </NuxtLink>


        <NuxtLink
          to="/admin"
          class="flex items-center gap-2 px-3 py-2 rounded text-xs font-medium text-aave-ash hover:text-white hover:bg-white/[0.04]"
          @click="mobileOpen = false"
        >
          <UIcon name="i-heroicons-cpu-chip" class="w-4 h-4" />
          <span>Phân tích</span>
        </NuxtLink>

        <NuxtLink
          to="/app"
          class="flex items-center gap-2 px-3 py-2 rounded text-xs font-medium text-aave-ash hover:text-white hover:bg-white/[0.04]"
          @click="mobileOpen = false"
        >
          <UIcon name="i-heroicons-circle-stack" class="w-4 h-4" />
          <span>Tài sản</span>
        </NuxtLink>

        <NuxtLink
          to="/"
          class="flex items-center gap-2 px-3 py-2 rounded text-xs font-medium text-aave-ash hover:text-white hover:bg-white/[0.04]"
          @click="mobileOpen = false"
        >
          <UIcon name="i-heroicons-globe-alt" class="w-4 h-4" />
          <span>Trang chủ Landing</span>
        </NuxtLink>
      </nav>
    </div>

    <!-- Main Workspace Content for iBoard -->
    <main class="flex-1 p-3 sm:p-4 overflow-y-auto">
      <div class="w-full h-full">
        <!-- Placeholder for iBoard trading grid -->
        <div class="rounded-xl border border-white/[0.06] bg-surface-midnight p-8 text-center text-aave-graphite">
          <div class="flex flex-col items-center justify-center gap-3 py-16">
            <UIcon
              :name="isDerivatives ? 'i-heroicons-bolt' : 'i-heroicons-chart-bar-square'"
              class="w-12 h-12 text-rose-500/70"
            />
            <div class="flex items-center gap-2">
              <h2 class="text-base font-semibold text-white">
                {{ isDerivatives ? 'Bảng giá phái sinh VN30F1M' : 'Bảng giá cổ phiếu cơ sở Vistock' }}
              </h2>
              <span
                class="px-2 py-0.5 rounded-full text-[10px] font-semibold tracking-wide uppercase"
                :class="
                  isDerivatives
                    ? 'bg-rose-600/20 text-rose-400 border border-rose-500/30'
                    : 'bg-white/10 text-aave-ash border border-white/10'
                "
              >
                {{ isDerivatives ? 'Phái sinh' : 'Cơ sở' }}
              </span>
            </div>
            <p class="text-xs text-aave-graphite max-w-md">
              {{
                isDerivatives
                  ? 'Không gian theo dõi hợp đồng tương lai chỉ số VN30, độ lệch Basis và sổ lệnh khớp liên tục thời gian thực.'
                  : 'Không gian hiển thị bảng giá khớp lệnh thời gian thực cho các mã HOSE, HNX, UPCOM và rổ chỉ số VN30.'
              }}
            </p>
          </div>
        </div>
      </div>
    </main>
  </div>
</template>
