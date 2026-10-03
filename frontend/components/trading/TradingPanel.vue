<template><section class="rounded-xl border border-white/[0.08] bg-surface-midnight p-4 shadow-sm"><div v-if="title" class="mb-4 flex items-center justify-between gap-3"><h2 class="text-sm font-semibold text-aave-paper">{{ title }}</h2><slot name="actions" /></div><slot /></section></template>
<script setup lang="ts">
defineProps<{ title?: string }>()
</script>
