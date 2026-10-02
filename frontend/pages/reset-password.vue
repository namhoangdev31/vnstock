<template>
  <div>
    <div class="mb-6 text-center">
      <h2 class="text-xl font-bold text-slate-100">Đặt lại mật khẩu</h2>
      <p class="text-xs text-slate-400 mt-1">Nhập mật khẩu mới an toàn cho tài khoản của bạn</p>
    </div>

    <form class="space-y-4" @submit.prevent="handleReset">
      <div>
        <label class="block text-xs font-medium text-slate-300 mb-1.5">Mật khẩu mới (tối thiểu 8 ký tự)</label>
        <UInput
          v-model="password"
          type="password"
          placeholder="Mật khẩu mới"
          icon="i-heroicons-lock-closed"
          size="md"
          required
          minlength="8"
          class="w-full"
        />
      </div>

      <div>
        <label class="block text-xs font-medium text-slate-300 mb-1.5">Xác nhận mật khẩu mới</label>
        <UInput
          v-model="confirmPassword"
          type="password"
          placeholder="Nhập lại mật khẩu mới"
          icon="i-heroicons-lock-closed"
          size="md"
          required
          minlength="8"
          class="w-full"
        />
      </div>

      <div v-if="passwordMismatch" class="text-xs text-rose-400">
        Mật khẩu xác nhận không khớp!
      </div>

      <UButton
        type="submit"
        block
        size="md"
        color="emerald"
        :loading="isSubmitting"
        :disabled="passwordMismatch || !password"
        class="mt-2 font-semibold shadow-lg shadow-emerald-500/20"
      >
        Lưu mật khẩu mới
      </UButton>
    </form>

    <div class="mt-6 text-center text-xs text-slate-400">
      <NuxtLink to="/login" class="text-emerald-400 font-semibold hover:underline">
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
  title: "Đặt lại mật khẩu - Vnstock Quants",
})

const route = useRoute()
const router = useRouter()
const { showSuccessToast, showErrorToast } = useCustomToast()

const password = ref("")
const confirmPassword = ref("")
const isSubmitting = ref(false)

const token = computed(() => {
  return (route.query.token as string) || ""
})

const passwordMismatch = computed(() => {
  return (
    confirmPassword.value.length > 0 && password.value !== confirmPassword.value
  )
})

const handleReset = async () => {
  if (password.value !== confirmPassword.value) {
    showErrorToast("Lỗi nhập liệu", "Mật khẩu xác nhận không khớp.")
    return
  }
  if (!token.value) {
    showErrorToast(
      "Lỗi xác thực",
      "Token đặt lại mật khẩu không hợp lệ hoặc đã hết hạn.",
    )
    return
  }

  isSubmitting.value = true
  try {
    await LoginService.resetPassword({
      body: {
        new_password: password.value,
        token: token.value,
      },
    })
    showSuccessToast(
      "Thành công!",
      "Mật khẩu đã được cập nhật thành công. Vui lòng đăng nhập với mật khẩu mới.",
    )
    await router.push("/login")
  } catch (err: unknown) {
    const error = err as { body?: { detail?: string }; message?: string }
    showErrorToast(
      "Lỗi đặt lại mật khẩu",
      error?.body?.detail ||
        error?.message ||
        "Không thể đặt lại mật khẩu. Vui lòng thử lại.",
    )
  } finally {
    isSubmitting.value = false
  }
}
</script>
