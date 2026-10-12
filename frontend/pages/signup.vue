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

    <div class="relative my-6">
      <div class="absolute inset-0 flex items-center">
        <div class="w-full border-t border-slate-800" />
      </div>
      <div class="relative flex justify-center text-xs uppercase">
        <span class="bg-surface-canvas px-2 text-slate-500">Hoặc tiếp tục với</span>
      </div>
    </div>

    <div class="space-y-2.5">
      <UButton
        type="button"
        block
        size="md"
        variant="outline"
        :loading="isGoogleLoading"
        class="font-medium !rounded-full border-slate-700 text-slate-200 hover:bg-slate-800 active:scale-[0.99] transition-all"
        @click="handleGoogleSignUp"
      >
        <template #leading>
          <UIcon name="i-logos-google-icon" class="w-4 h-4 mr-1" />
        </template>
        Đăng ký với Google
      </UButton>

      <UButton
        type="button"
        block
        size="md"
        variant="outline"
        :loading="isAppleLoading"
        class="font-medium !rounded-full border-slate-700 text-slate-200 hover:bg-slate-800 active:scale-[0.99] transition-all"
        @click="handleAppleSignUp"
      >
        <template #leading>
          <UIcon name="i-simple-icons-apple" class="w-4 h-4 mr-1 text-white" />
        </template>
        Đăng ký với Apple
      </UButton>
    </div>

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
  title: "Đăng ký tài khoản - Vistock Quants",
})

const { signup, loginSocial, isLoading } = useAuth()
const { registerWithEmailPassword, signInWithGoogle, signInWithApple } =
  useFirebase()
const { showErrorToast } = useCustomToast()
const showPassword = ref(false)
const isGoogleLoading = ref(false)
const isAppleLoading = ref(false)

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
    // Tự động đăng ký người dùng lên Firebase Authentication
    await registerWithEmailPassword(form.email, form.password, form.full_name)

    await signup({
      email: form.email,
      full_name: form.full_name,
      password: form.password,
    })
  } catch {}
}

const handleGoogleSignUp = async () => {
  try {
    isGoogleLoading.value = true
    const googleUser = await signInWithGoogle()
    await loginSocial({
      provider: "google",
      token: googleUser.idToken,
      email: googleUser.email,
      full_name: googleUser.displayName || undefined,
    })
  } catch (err: unknown) {
    const error = err as { code?: string; message?: string }
    if (error?.code !== "auth/popup-closed-by-user") {
      // Error handled by toast
    }
  } finally {
    isGoogleLoading.value = false
  }
}

const handleAppleSignUp = async () => {
  try {
    isAppleLoading.value = true
    const appleUser = await signInWithApple()
    await loginSocial({
      provider: "apple",
      token: appleUser.idToken,
      email: appleUser.email,
      full_name: appleUser.displayName || undefined,
    })
  } catch (err: unknown) {
    const error = err as { code?: string; message?: string }
    if (error?.code !== "auth/popup-closed-by-user") {
      // Error handled by toast
    }
  } finally {
    isAppleLoading.value = false
  }
}
</script>
