<template><div><p class="text-[10px] uppercase tracking-wider text-aave-graphite">{{ label }}</p><p class="mt-2 font-mono text-sm font-semibold text-aave-ash">{{ value }}</p></div></template>
<script setup lang="ts">
defineProps<{ label: string; value: string }>()
</script>
