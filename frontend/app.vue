<template>
  <div class="min-h-screen bg-aave-inkwell text-aave-paper antialiased selection:bg-aave-violet selection:text-aave-charcoal">
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
