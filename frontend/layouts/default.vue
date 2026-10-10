<template>
  <div class="min-h-screen bg-aave-inkwell text-aave-paper font-sans selection:bg-aave-violet selection:text-aave-charcoal flex flex-col">
    <!-- Top Navigation Header -->
    <header class="sticky top-0 z-40 h-14 bg-aave-obsidian border-b border-white/[0.06] backdrop-blur-md">
      <div class="h-full px-4 sm:px-6 flex items-center justify-between gap-4">
        <!-- Left: Brand Logo & Navigation -->
        <div class="flex items-center gap-6">
          <NuxtLink to="/app" class="flex items-center gap-2 group">
            <span class="font-semibold tracking-tight text-base text-white group-hover:text-aave-violet transition-colors">
              VISTOCK
            </span>
          </NuxtLink>

          <!-- Desktop Navigation Links -->
          <nav class="hidden md:flex items-center gap-1">
            <NuxtLink
              to="/app"
              class="px-3 py-1.5 rounded-lg text-xs font-medium transition-colors"
              :class="route.path.startsWith('/app') ? 'bg-white/[0.08] text-white font-semibold' : 'text-aave-graphite hover:text-white hover:bg-white/[0.04]'"
            >
              Đặt lệnh
            </NuxtLink>

            <NuxtLink
              v-if="user?.is_superuser"
              to="/admin"
              class="px-3 py-1.5 rounded-lg text-xs font-medium transition-colors"
              :class="route.path.startsWith('/admin') ? 'bg-white/[0.08] text-white font-semibold' : 'text-aave-graphite hover:text-white hover:bg-white/[0.04]'"
            >
              Quản trị
            </NuxtLink>
          </nav>
        </div>

        <!-- Right: Session info, clock, user menu -->
        <div class="flex items-center gap-3">
          <!-- Session Status Badge -->
          <UTooltip :text="sessionStatus.tooltip">
            <div class="hidden sm:inline-flex items-center gap-2 px-2.5 py-1 rounded-full bg-white/[0.03] border border-white/[0.06] text-xs font-mono">
              <span class="w-1.5 h-1.5 rounded-full" :class="sessionStatus.active ? 'bg-quant-bull' : 'bg-aave-graphite'" />
              <span class="text-white">{{ sessionStatus.label }}</span>
              <span class="text-aave-graphite">{{ currentTime }}</span>
            </div>
          </UTooltip>

          <!-- Landing Page Link -->
          <NuxtLink
            to="/"
            class="p-2 text-aave-graphite hover:text-white rounded-lg hover:bg-white/[0.05] transition-colors"
            title="Trang chủ"
          >
            <UIcon name="i-heroicons-globe-alt" class="w-4 h-4" />
          </NuxtLink>

          <!-- User Section -->
          <template v-if="user">
            <div class="flex items-center gap-2 pl-2 border-l border-white/[0.06]">
              <div class="w-7 h-7 rounded-full bg-aave-violet text-aave-charcoal font-mono font-bold text-xs flex items-center justify-center">
                {{ userInitials }}
              </div>
              <span class="text-xs font-medium text-white max-w-[120px] truncate hidden lg:inline">
                {{ user?.full_name || user?.email?.split('@')[0] || 'Tài khoản' }}
              </span>
              <button
                type="button"
                class="p-1.5 text-aave-graphite hover:text-rose-400 rounded-lg hover:bg-white/[0.05] transition-colors"
                title="Đăng xuất"
                @click="logout"
              >
                <UIcon name="i-heroicons-arrow-right-on-rectangle" class="w-4 h-4" />
              </button>
            </div>
          </template>
          <template v-else>
            <NuxtLink
              to="/login"
              class="text-xs font-medium text-white px-3 py-1.5 rounded-lg bg-white/[0.08] hover:bg-white/[0.12] transition-colors"
            >
              Đăng nhập
            </NuxtLink>
          </template>

          <!-- Mobile Menu Trigger -->
          <button
            type="button"
            class="md:hidden p-1.5 text-aave-graphite hover:text-white rounded-lg hover:bg-white/[0.05]"
            :aria-label="mobileOpen ? 'Đóng menu' : 'Mở menu'"
            @click="mobileOpen = !mobileOpen"
          >
            <UIcon :name="mobileOpen ? 'i-heroicons-x-mark' : 'i-heroicons-bars-3'" class="w-5 h-5" />
          </button>
        </div>
      </div>

      <!-- Mobile Navigation Drawer / Dropdown -->
      <div
        v-if="mobileOpen"
        class="md:hidden border-b border-white/[0.06] bg-aave-obsidian px-4 py-3 space-y-2 animate-fade-in-down"
      >
        <div class="flex items-center justify-between pb-2 border-b border-white/[0.06] text-xs font-mono text-aave-graphite">
          <span>{{ sessionStatus.label }}</span>
          <span>{{ currentTime }}</span>
        </div>

        <nav class="space-y-1">
          <NuxtLink
            to="/app"
            class="flex items-center gap-2 px-3 py-2 rounded-lg text-xs font-medium transition-colors"
            :class="route.path.startsWith('/app') ? 'bg-white/[0.08] text-white' : 'text-aave-graphite hover:text-white hover:bg-white/[0.04]'"
            @click="mobileOpen = false"
          >
            <UIcon name="i-heroicons-cpu-chip" class="w-4 h-4 text-aave-violet" />
            <span>Đặt lệnh Sandbox</span>
          </NuxtLink>

          <NuxtLink
            v-if="user?.is_superuser"
            to="/admin"
            class="flex items-center gap-2 px-3 py-2 rounded-lg text-xs font-medium transition-colors"
            :class="route.path.startsWith('/admin') ? 'bg-white/[0.08] text-white' : 'text-aave-graphite hover:text-white hover:bg-white/[0.04]'"
            @click="mobileOpen = false"
          >
            <UIcon name="i-heroicons-shield-check" class="w-4 h-4 text-aave-violet" />
            <span>Quản trị</span>
          </NuxtLink>

          <NuxtLink
            to="/"
            class="flex items-center gap-2 px-3 py-2 rounded-lg text-xs font-medium text-aave-graphite hover:text-white hover:bg-white/[0.04]"
            @click="mobileOpen = false"
          >
            <UIcon name="i-heroicons-globe-alt" class="w-4 h-4" />
            <span>Trang chủ Landing</span>
          </NuxtLink>
        </nav>

        <div v-if="user" class="pt-2 border-t border-white/[0.06] flex items-center justify-between text-xs">
          <span class="text-white truncate max-w-[200px]">
            {{ user?.full_name || user?.email }}
          </span>
          <button
            type="button"
            class="text-rose-400 hover:underline"
            @click="logout(); mobileOpen = false"
          >
            Đăng xuất
          </button>
        </div>
      </div>
    </header>

    <!-- Main Content Slot -->
    <main class="flex-1 w-full min-w-0 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
      <slot />
    </main>

    <!-- Minimalist Quiet Footer -->
    <footer class="border-t border-white/[0.06] bg-aave-obsidian py-3.5 px-6 text-center text-xs text-aave-graphite font-mono">
      <span>© 2026 Vistock Quants · Nền tảng nghiên cứu định lượng & mô phỏng giao dịch</span>
    </footer>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from "vue"

const route = useRoute()
const { user, logout } = useAuth()
const mobileOpen = ref(false)

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

const currentTime = ref("")
const sessionStatus = computed(() => {
  const now = new Date()
  const hours = now.getHours()
  const minutes = now.getMinutes()
  const timeNum = hours * 100 + minutes

  if (timeNum >= 845 && timeNum < 900) {
    return {
      label: "Phiên ATO",
      tooltip: "Thời gian mở cửa 08:45 đến 09:00",
      active: true,
    }
  }
  if (timeNum >= 900 && timeNum < 1130) {
    return {
      label: "Khớp lệnh sáng",
      tooltip: "Thời gian khớp lệnh 09:00 đến 11:30",
      active: true,
    }
  }
  if (timeNum >= 1130 && timeNum < 1300) {
    return {
      label: "Nghỉ trưa",
      tooltip: "Thời gian nghỉ trưa 11:30 đến 13:00",
      active: false,
    }
  }
  if (timeNum >= 1300 && timeNum < 1430) {
    return {
      label: "Khớp lệnh chiều",
      tooltip: "Thời gian khớp lệnh 13:00 đến 14:30",
      active: true,
    }
  }
  if (timeNum >= 1430 && timeNum < 1445) {
    return {
      label: "Phiên ATC",
      tooltip: "Thời gian đóng cửa 14:30 đến 14:45",
      active: true,
    }
  }
  return {
    label: "Ngoài giờ",
    tooltip: "Sau giờ giao dịch 24/7",
    active: false,
  }
})

const updateClock = () => {
  const now = new Date()
  currentTime.value = now.toLocaleTimeString("vi-VN", { hour12: false })
}

let timer: ReturnType<typeof setInterval> | null = null

onMounted(() => {
  updateClock()
  timer = setInterval(updateClock, 1000)
})

onUnmounted(() => {
  if (timer) clearInterval(timer)
})
</script>
