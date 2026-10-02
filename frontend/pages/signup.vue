<template>
  <div>
    <div class="mb-6 text-center">
      <h2 class="text-xl font-bold text-slate-100">Đăng ký tài khoản</h2>
      <p class="text-xs text-slate-400 mt-1">Khởi tạo môi trường nghiên cứu & mô phỏng cá nhân</p>
    </div>

    <form class="space-y-4" @submit.prevent="handleSignup">
      <div>
        <label class="block text-xs font-medium text-slate-300 mb-1.5">Họ và tên</label>
        <UInput
          v-model="form.full_name"
          type="text"
          placeholder="Nguyễn Văn A"
          icon="i-heroicons-user"
          size="md"
          required
          autofocus
          class="w-full"
        />
      </div>

      <div>
        <label class="block text-xs font-medium text-slate-300 mb-1.5">Email</label>
        <UInput
          v-model="form.email"
          type="email"
          placeholder="user@example.com"
          icon="i-heroicons-envelope"
          size="md"
          required
          class="w-full"
        />
      </div>

      <div>
        <label class="block text-xs font-medium text-slate-300 mb-1.5 flex items-center justify-between"><span>Mật khẩu</span><span class="text-[10px] text-aave-graphite font-normal">Tối thiểu 8 ký tự</span></label>
        <UInput
          v-model="form.password"
          :type="showPassword ? 'text' : 'password'"
          placeholder="Mật khẩu bảo mật"
          icon="i-heroicons-lock-closed"
          size="md"
          required
          minlength="8"
          class="w-full"
        >
          <template #trailing>
            <button
              type="button"
              class="text-slate-400 hover:text-slate-200"
              @click="showPassword = !showPassword"
            >
              <UIcon :name="showPassword ? 'i-heroicons-eye-slash' : 'i-heroicons-eye'" class="w-4 h-4" />
            </button>
          </template>
        </UInput>
      </div>

      <div>
        <label class="block text-xs font-medium text-slate-300 mb-1.5">Xác nhận mật khẩu</label>
        <UInput
          v-model="form.confirmPassword"
          :type="showPassword ? 'text' : 'password'"
          placeholder="Nhập lại mật khẩu"
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
        color="primary"
        :loading="isLoading"
        :disabled="passwordMismatch"
        class="mt-2 font-medium !rounded-full !bg-aave-violet !text-aave-charcoal hover:brightness-105 active:scale-[0.99] transition-all"
      >
        Tạo tài khoản
      </UButton>
    </form>

    <div class="mt-6 text-center text-xs text-slate-400">
      Đã có tài khoản?
      <NuxtLink to="/login" class="text-aave-violet font-medium hover:underline ml-1">
        Đăng nhập
      </NuxtLink>
    </div>
  </div>
</template>

<script setup lang="ts">
definePageMeta({
  layout: "auth",
})

useHead({
  title: "Đăng ký tài khoản - Vnstock Quants",
})

const { signup, isLoading } = useAuth()
const { showErrorToast } = useCustomToast()
const showPassword = ref(false)

const form = reactive({
  full_name: "",
  email: "",
  password: "",
  confirmPassword: "",
})

const passwordMismatch = computed(() => {
  return (
    form.confirmPassword.length > 0 && form.password !== form.confirmPassword
  )
})

const handleSignup = async () => {
  if (form.password !== form.confirmPassword) {
    showErrorToast("Lỗi nhập liệu", "Mật khẩu xác nhận không khớp.")
    return
  }
  try {
    await signup({
      email: form.email,
      full_name: form.full_name,
      password: form.password,
    })
  } catch {}
}
</script>
