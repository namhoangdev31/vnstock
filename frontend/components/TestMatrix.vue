<template>
  <div class="space-y-4 font-mono">

    <div class="flex flex-col sm:flex-row items-center justify-between gap-3 p-4 rounded-xl bg-surface-abyss/80 border border-white/[0.08] shadow-lg">
      <div class="flex items-center gap-3 w-full sm:w-auto">
        <div class="relative flex-1 sm:w-72">
          <UInput
            v-model="search"
            placeholder="Tìm mã test hoặc kịch bản..."
            icon="i-heroicons-magnifying-glass"
            size="sm"
            class="w-full text-xs font-mono"
          />
        </div>

        <select
          v-model="selectedGroup"
          class="bg-surface-abyss border border-white/[0.1] rounded-lg px-3 py-1.5 text-xs text-slate-300 focus:outline-none focus:ring-1 focus:ring-emerald-500 font-mono"
        >
          <option value="ALL">Tất cả nhóm ({{ tests.length }})</option>
          <option v-for="grp in groups" :key="grp" :value="grp">
            {{ grp }}
          </option>
        </select>
      </div>

      <div class="flex items-center gap-2 self-end sm:self-auto text-xs font-mono">
        <span class="px-2.5 py-1 rounded-md bg-emerald-500/10 text-emerald-400 font-bold border border-emerald-500/20">
          PASS: {{ passCount }} / {{ tests.length }}
        </span>
        <span class="text-slate-400">
          ({{ Math.round((passCount / (tests.length || 1)) * 100) }}%)
        </span>
      </div>
    </div>

    <div class="rounded-xl border border-white/[0.08] bg-surface-abyss/80 overflow-hidden shadow-xl">
      <div class="overflow-x-auto">
        <table class="w-full text-left text-xs">
          <thead class="bg-white/[0.02] text-slate-400 uppercase font-mono text-[10px] border-b border-white/[0.06] tracking-wider">
            <tr>
              <th class="py-3 px-4 w-28">Mã Test</th>
              <th class="py-3 px-4 w-44">Phân nhóm</th>
              <th class="py-3 px-4 font-sans">Kịch bản kiểm thử</th>
              <th class="py-3 px-4 font-sans">Kết quả kỳ vọng</th>
              <th class="py-3 px-4 w-24 text-center">Trạng thái</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-white/[0.04]">
            <tr v-if="filteredTests.length === 0">
              <td colspan="5" class="py-8 text-center text-slate-400 font-sans">
                Không tìm thấy ca kiểm thử nào.
              </td>
            </tr>

            <tr
              v-for="tc in filteredTests"
              :key="tc.id"
              class="hover:bg-white/[0.02] transition-colors"
            >
              <td class="py-3 px-4 font-bold text-emerald-400 text-xs">
                {{ tc.id }}
              </td>
              <td class="py-3 px-4 text-slate-400 font-mono text-[11px]">
                {{ tc.group }}
              </td>
              <td class="py-3 px-4 text-slate-200 font-sans text-xs">
                {{ tc.scenario }}
              </td>
              <td class="py-3 px-4 text-slate-400 font-sans text-xs">
                {{ tc.expectation }}
              </td>
              <td class="py-3 px-4 text-center">
                <span
                  class="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-bold"
                  :class="tc.status === 'PASS' ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' : 'bg-amber-500/10 text-amber-400 border border-amber-500/20'"
                >
                  <UIcon :name="tc.status === 'PASS' ? 'i-heroicons-check-circle' : 'i-heroicons-clock'" class="w-3.5 h-3.5" />
                  {{ tc.status }}
                </span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
export interface TestCase {
  id: string
  group: string
  scenario: string
  expectation: string
  status: "PASS" | "PENDING"
}

const props = defineProps<{
  tests: TestCase[]
}>()

const search = ref("")
const selectedGroup = ref("ALL")

const groups = computed(() => {
  const set = new Set<string>()
  props.tests.forEach((t) => {
    set.add(t.group)
  })
  return Array.from(set)
})

const passCount = computed(() => {
  return props.tests.filter((t) => t.status === "PASS").length
})

const filteredTests = computed(() => {
  return props.tests.filter((t) => {
    const matchesGroup =
      selectedGroup.value === "ALL" || t.group === selectedGroup.value
    const q = search.value.toLowerCase().trim()
    const matchesQuery =
      !q ||
      t.id.toLowerCase().includes(q) ||
      t.scenario.toLowerCase().includes(q) ||
      t.expectation.toLowerCase().includes(q)
    return matchesGroup && matchesQuery
  })
})
</script>
