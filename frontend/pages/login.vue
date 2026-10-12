<template>
  <div>
    <div class="mb-6 text-center">
      <h2 class="text-xl font-bold text-slate-100">Đăng nhập tài khoản</h2>
      <p class="text-xs text-slate-400 mt-1">Truy cập vào hệ thống mô phỏng & phân tích dữ liệu</p>
    </div>

    <form class="space-y-4" @submit.prevent="handleLogin">
      <div>
        <label class="block text-xs font-medium text-slate-300 mb-1.5">Email</label>
        <UInput
          v-model="form.username"
          type="email"
          placeholder="user@example.com"
          icon="i-heroicons-envelope"
          size="md"
          required
          autofocus
          class="w-full"
        />
      </div>

      <div>
        <div class="flex items-center justify-between mb-1.5">
          <label class="block text-xs font-medium text-slate-300">Mật khẩu</label>
          <NuxtLink to="/recover-password" class="text-xs text-aave-violet hover:underline">
            Quên mật khẩu?
          </NuxtLink>
        </div>
        <UInput
          v-model="form.password"
          :type="showPassword ? 'text' : 'password'"
          placeholder="Nhập mật khẩu của bạn"
          icon="i-heroicons-lock-closed"
          size="md"
          required
          class="w-full"
          :ui="{ icon: { trailing: { pointer: '' } } }"
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

      <UButton
        type="submit"
        block
        size="md"
        color="primary"
        :loading="isLoading"
        class="mt-2 font-medium !rounded-full !bg-aave-violet !text-aave-charcoal hover:brightness-105 active:scale-[0.99] transition-all"
      >
        Đăng nhập
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
        @click="handleGoogleSignIn"
      >
        <template #leading>
          <UIcon name="i-logos-google-icon" class="w-4 h-4 mr-1" />
        </template>
        Đăng nhập bằng Google
      </UButton>

      <UButton
        type="button"
        block
        size="md"
        variant="outline"
        :loading="isAppleLoading"
        class="font-medium !rounded-full border-slate-700 text-slate-200 hover:bg-slate-800 active:scale-[0.99] transition-all"
        @click="handleAppleSignIn"
      >
        <template #leading>
          <UIcon name="i-simple-icons-apple" class="w-4 h-4 mr-1 text-white" />
        </template>
        Đăng nhập bằng Apple
      </UButton>
    </div>

    <div class="mt-6 text-center text-xs text-slate-400">
      Chưa có tài khoản?
      <NuxtLink to="/signup" class="text-aave-violet font-medium hover:underline ml-1">
        Đăng ký ngay
      </NuxtLink>
    </div>
  </div>
</template>

<script setup lang="ts">
definePageMeta({
  layout: "auth",
})

useHead({
  title: "Đăng nhập - Vistock Quants",
})

const { login, loginSocial, isLoading } = useAuth()
const { signInWithGoogle, signInWithApple } = useFirebase()
const showPassword = ref(false)
const isGoogleLoading = ref(false)
const isAppleLoading = ref(false)

const form = reactive({
  username: "",
  password: "",
})

const handleLogin = async () => {
  if (!form.username || !form.password) return
  try {
    await login({
      username: form.username,
      password: form.password,
    })
  } catch {}
}

const handleGoogleSignIn = async () => {
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
      // Error handling is managed by loginSocial toast
    }
  } finally {
    isGoogleLoading.value = false
  }
}

const handleAppleSignIn = async () => {
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
      // Error handling is managed by loginSocial toast
    }
  } finally {
    isAppleLoading.value = false
  }
}
</script>
