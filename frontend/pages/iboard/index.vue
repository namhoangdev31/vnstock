<script setup lang="ts">
definePageMeta({
  layout: false,
})

useHead({
  title: "",
})
const { token } = useAuth()
</script>

<template>
  <div class="min-h-screen bg-aave-paper text-aave-obsidian relative">
    <header class="sticky top-0 z-50 backdrop-blur-xl bg-white/80 border-b border-black/[0.06] transition-colors">
      <div class="max-w-[1200px] mx-auto px-6 py-2 h-18 flex items-center justify-between">
        <NuxtLink to="/" class="flex items-center gap-2 group">
          <span
            class="font-medium tracking-tight text-base text-aave-obsidian flex items-center gap-2 font-sans group-hover:text-aave-violet transition-colors">
            Vnstock
          </span>
        </NuxtLink>
        <nav class="hidden md:flex items-center gap-7 text-sm font-medium text-aave-iron">
          <a href="/" class="hover:text-aave-obsidian transition-colors">Phái sinh</a>
          <a href="/" class="hover:text-aave-obsidian transition-colors">Cơ sở</a>
        </nav>
        <div class="flex items-center gap-3">
          <template v-if="token">
            <NuxtLink to="/" class="btn-aave-dark text-sm !py-2.5 !px-5">
              <span>Vào Dashboard</span>
            </NuxtLink>
          </template>
          <template v-else>
            <NuxtLink
              to="/login"
              class="text-sm font-medium text-aave-iron hover:text-aave-obsidian px-3 py-2 transition-colors">
              Đăng nhập
            </NuxtLink>
            <NuxtLink to="/signup" class="btn-aave-dark text-sm !py-2.5 !px-5">
              <span>Mở Sandbox</span>
            </NuxtLink>
          </template>
        </div>
      </div>
    </header>
  </div>
</template>
