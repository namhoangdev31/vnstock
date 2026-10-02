<template>
  <div class="min-h-screen bg-[#07090e] text-slate-100 antialiased selection:bg-emerald-500 selection:text-white terminal-grid-bg">
    <NuxtLayout>
      <NuxtPage />
    </NuxtLayout>
    <UNotifications />
  </div>
</template>

<script setup lang="ts">
const { initToken, fetchUser } = useAuth()

onMounted(async () => {
  initToken()
  await fetchUser()
})
</script>
