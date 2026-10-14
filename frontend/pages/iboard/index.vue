<script setup lang="ts">
import { useHead } from "#app";
import { definePageMeta } from "#imports";
import { computed, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";

definePageMeta({
  layout: false,
});

const route = useRoute();
const router = useRouter();

const currentMarket = ref<"underlying" | "derivatives">(
  route.query.market === "derivatives" ? "derivatives" : "underlying",
);

const isDerivatives = computed(() => currentMarket.value === "derivatives");

const toggleMarket = () => {
  const nextMarket =
    currentMarket.value === "underlying" ? "derivatives" : "underlying";
  currentMarket.value = nextMarket;
  router.replace({
    query: {
      ...route.query,
      market: nextMarket === "derivatives" ? "derivatives" : undefined,
    },
  });
};

watch(
  () => route.query.market,
  (val) => {
    if (val === "derivatives" && currentMarket.value !== "derivatives") {
      currentMarket.value = "derivatives";
    } else if (val !== "derivatives" && currentMarket.value !== "underlying") {
      currentMarket.value = "underlying";
    }
  },
);

useHead({
  title: computed(() =>
    isDerivatives.value
      ? "Bảng giá phái sinh VN30F1M - Vistocks"
      : "Bảng giá cổ phiếu cơ sở - Vistocks",
  ),
});
</script>

<template>
  <div
    class="min-h-screen bg-surface-abyss text-aave-paper font-sans select-none flex flex-col"
  >
    <IBoardHeader
      :is-derivatives="isDerivatives"
      @toggle-market="toggleMarket"
    />

    <IBoardContent :is-derivatives="isDerivatives" />
  </div>
</template>
