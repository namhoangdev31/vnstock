<template>
  <div class="space-y-4">
    <!-- Action Bar -->
    <div class="flex items-center justify-between p-3 rounded-lg bg-slate-900 border border-slate-800">
      <div class="flex items-center gap-2 text-xs text-slate-400">
        <UIcon name="i-heroicons-document-text" class="w-4 h-4 text-emerald-400" />
        <span>Technical Requirements Document (Markdown Specification)</span>
      </div>

      <div class="flex items-center gap-2">
        <UButton
          size="xs"
          color="gray"
          variant="solid"
          icon="i-heroicons-clipboard-document"
          @click="copyContent"
        >
          {{ copied ? 'Đã chép!' : 'Sao chép' }}
        </UButton>
        <UButton
          size="xs"
          color="gray"
          variant="solid"
          icon="i-heroicons-arrow-down-tray"
          @click="downloadContent"
        >
          Tải về .md
        </UButton>
      </div>
    </div>

    <!-- Rendered Markdown Body -->
    <div
      class="prose prose-invert prose-sm max-w-none p-6 rounded-xl bg-slate-900/60 border border-slate-800/80 leading-relaxed text-slate-300 overflow-x-auto"
      v-html="renderedHtml"
    />
  </div>
</template>

<script setup lang="ts">
import MarkdownIt from "markdown-it"

const props = defineProps<{
  content: string
  filename?: string
}>()

const { showSuccessToast, showErrorToast } = useCustomToast()
const md = new MarkdownIt({
  html: true,
  linkify: true,
  typographer: true,
})

const renderedHtml = computed(() => {
  return md.render(props.content || "")
})

const copied = ref(false)

const copyContent = async () => {
  try {
    await navigator.clipboard.writeText(props.content)
    copied.value = true
    showSuccessToast(
      "Đã sao chép nội dung",
      "Toàn bộ tài liệu đặc tả TRD đã được lưu vào clipboard.",
    )
    setTimeout(() => {
      copied.value = false
    }, 2500)
  } catch {
    showErrorToast("Lỗi sao chép", "Không thể truy cập clipboard trình duyệt.")
  }
}

const downloadContent = () => {
  const blob = new Blob([props.content], {
    type: "text/markdown;charset=utf-8",
  })
  const url = URL.createObjectURL(blob)
  const a = document.createElement("a")
  a.href = url
  a.download = props.filename || "trd-spec.md"
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}
</script>

<style scoped>
:deep(h1) {
  font-size: 1.5rem;
  font-weight: 700;
  color: #f8fafc;
  margin-top: 1.5rem;
  margin-bottom: 0.75rem;
  padding-bottom: 0.5rem;
  border-bottom: 1px solid #334155;
}
:deep(h2) {
  font-size: 1.25rem;
  font-weight: 700;
  color: #34d399;
  margin-top: 1.25rem;
  margin-bottom: 0.5rem;
}
:deep(h3) {
  font-size: 1.1rem;
  font-weight: 600;
  color: #e2e8f0;
  margin-top: 1rem;
  margin-bottom: 0.5rem;
}
:deep(p) {
  margin-bottom: 0.75rem;
  color: #cbd5e1;
}
:deep(ul), :deep(ol) {
  padding-left: 1.25rem;
  margin-bottom: 0.75rem;
}
:deep(li) {
  margin-bottom: 0.25rem;
}
:deep(code) {
  background-color: #0f172a;
  padding: 0.15rem 0.35rem;
  border-radius: 0.25rem;
  color: #38bdf8;
  font-family: monospace;
  font-size: 0.85em;
}
:deep(pre) {
  background-color: #020617;
  padding: 1rem;
  border-radius: 0.5rem;
  border: 1px solid #1e293b;
  overflow-x: auto;
  margin: 1rem 0;
}
:deep(pre code) {
  background-color: transparent;
  padding: 0;
  color: #e2e8f0;
}
:deep(blockquote) {
  border-left: 4px solid #10b981;
  padding-left: 1rem;
  margin: 1rem 0;
  color: #94a3b8;
  font-style: italic;
}
:deep(table) {
  width: 100%;
  border-collapse: collapse;
  margin: 1rem 0;
}
:deep(th), :deep(td) {
  border: 1px solid #1e293b;
  padding: 0.5rem 0.75rem;
  text-align: left;
}
:deep(th) {
  background-color: #0f172a;
  color: #34d399;
}
</style>
