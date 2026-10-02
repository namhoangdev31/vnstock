<template>
  <div class="space-y-4">
    <!-- Action Bar -->
    <div class="flex items-center justify-between p-3.5 rounded-xl bg-[#090d16]/80 border border-white/[0.08] shadow-md backdrop-blur-xl">
      <div class="flex items-center gap-2 text-xs text-slate-400 font-mono">
        <UIcon name="i-heroicons-document-text" class="w-4 h-4 text-emerald-400" />
        <span>Technical Requirements Document (Markdown Specification)</span>
      </div>

      <div class="flex items-center gap-2 font-mono">
        <UButton
          size="xs"
          color="gray"
          variant="solid"
          icon="i-heroicons-clipboard-document"
          class="text-xs"
          @click="copyContent"
        >
          {{ copied ? 'Đã sao chép!' : 'Sao chép' }}
        </UButton>
        <UButton
          size="xs"
          color="gray"
          variant="solid"
          icon="i-heroicons-arrow-down-tray"
          class="text-xs"
          @click="downloadContent"
        >
          Tải file .md
        </UButton>
      </div>
    </div>

    <!-- Rendered Markdown Body -->
    <div
      class="prose prose-invert prose-sm max-w-none p-6 sm:p-8 rounded-2xl bg-[#090d16]/90 border border-white/[0.08] leading-relaxed text-slate-300 overflow-x-auto shadow-2xl backdrop-blur-xl"
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
