<template>
  <div>
    <div class="mb-6 text-center">
      <h2 class="text-xl font-bold text-slate-100">Khôi phục mật khẩu</h2>
      <p class="text-xs text-slate-400 mt-1">Nhập email đã đăng ký để nhận liên kết đặt lại mật khẩu</p>
    </div>

    <form class="space-y-4" @submit.prevent="handleRecover">
      <div>
        <label class="block text-xs font-medium text-slate-300 mb-1.5">Email tài khoản</label>
        <UInput
          v-model="email"
          type="email"
          placeholder="user@example.com"
          icon="i-heroicons-envelope"
          size="md"
          required
          autofocus
          class="w-full"
        />
      </div>

      <UButton
        type="submit"
        block
        size="md"
        color="emerald"
        :loading="isSubmitting"
        class="mt-2 font-semibold shadow-lg shadow-emerald-500/20"
      >
        Gửi yêu cầu
      </UButton>
    </form>

    <div class="mt-6 text-center text-xs text-slate-400">
      Nhớ lại mật khẩu?
      <NuxtLink to="/login" class="text-emerald-400 font-semibold hover:underline ml-1">
        Quay lại đăng nhập
      </NuxtLink>
    </div>
  </div>
</template>

<script setup lang="ts">
import { LoginService } from "~/client"

definePageMeta({
  layout: "auth",
})

useHead({
  title: "Khôi phục mật khẩu - Vnstock Quants",
})

const { showSuccessToast, showErrorToast } = useCustomToast()
const email = ref("")
const isSubmitting = ref(false)

const handleRecover = async () => {
  if (!email.value) return
  isSubmitting.value = true
  try {
    await LoginService.recoverPassword({
      path: { email: email.value },
    })
    showSuccessToast(
      "Đã gửi email khôi phục!",
      "Vui lòng kiểm tra hòm thư của bạn để lấy liên kết đặt lại mật khẩu.",
    )
  } catch (err: unknown) {
    const error = err as { body?: { detail?: string }; message?: string }
    showErrorToast(
      "Lỗi yêu cầu",
      error?.body?.detail || error?.message || "Không thể gửi email khôi phục.",
    )
  } finally {
    isSubmitting.value = false
  }
}
</script>
