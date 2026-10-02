<template>
  <div class="space-y-6 max-w-4xl">
    <!-- Header -->
    <div>
      <h1 class="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
        <UIcon name="i-heroicons-cog-6-tooth" class="w-7 h-7 text-emerald-400" />
        Cài đặt tài khoản (User Settings)
      </h1>
      <p class="text-xs sm:text-sm text-slate-400 mt-1">
        Quản lý thông tin hồ sơ, mật khẩu và tùy chọn bảo mật cá nhân
      </p>
    </div>

    <!-- Tabs Navigation -->
    <div class="flex border-b border-slate-800 gap-4">
      <button
        type="button"
        class="pb-2.5 text-xs font-bold transition-colors border-b-2 flex items-center gap-2"
        :class="activeTab === 'profile' ? 'border-emerald-400 text-emerald-400' : 'border-transparent text-slate-400 hover:text-slate-200'"
        @click="activeTab = 'profile'"
      >
        <UIcon name="i-heroicons-user" class="w-4 h-4" />
        Hồ sơ cá nhân
      </button>
      <button
        type="button"
        class="pb-2.5 text-xs font-bold transition-colors border-b-2 flex items-center gap-2"
        :class="activeTab === 'password' ? 'border-emerald-400 text-emerald-400' : 'border-transparent text-slate-400 hover:text-slate-200'"
        @click="activeTab = 'password'"
      >
        <UIcon name="i-heroicons-key" class="w-4 h-4" />
        Đổi mật khẩu
      </button>
      <button
        type="button"
        class="pb-2.5 text-xs font-bold transition-colors border-b-2 flex items-center gap-2"
        :class="activeTab === 'danger' ? 'border-rose-400 text-rose-400' : 'border-transparent text-slate-400 hover:text-slate-200'"
        @click="activeTab = 'danger'"
      >
        <UIcon name="i-heroicons-exclamation-triangle" class="w-4 h-4" />
        Vùng nguy hiểm
      </button>
    </div>

    <!-- Tab 1: Profile Information -->
    <div v-if="activeTab === 'profile'" class="p-6 rounded-2xl bg-[#090d16]/80 border border-white/[0.08] shadow-xl space-y-4">
      <div>
        <h3 class="text-sm font-bold text-white font-mono">Thông tin cơ bản</h3>
        <p class="text-xs text-slate-400">Cập nhật họ tên và địa chỉ email đăng nhập</p>
      </div>

      <form class="space-y-4 max-w-md font-mono" @submit.prevent="updateProfile">
        <div>
          <label class="block text-xs font-medium text-slate-300 mb-1 font-sans">Họ và tên</label>
          <UInput v-model="profileForm.full_name" size="md" class="w-full text-xs font-mono" />
        </div>

        <div>
          <label class="block text-xs font-medium text-slate-300 mb-1 font-sans">Email</label>
          <UInput v-model="profileForm.email" type="email" required size="md" class="w-full text-xs font-mono" />
        </div>

        <div class="pt-2">
          <UButton type="submit" color="emerald" :loading="isSavingProfile" class="text-xs font-mono font-semibold">
            Lưu thay đổi
          </UButton>
        </div>
      </form>
    </div>

    <!-- Tab 2: Change Password -->
    <div v-else-if="activeTab === 'password'" class="p-6 rounded-2xl bg-[#090d16]/80 border border-white/[0.08] shadow-xl space-y-4">
      <div>
        <h3 class="text-sm font-bold text-white font-mono">Đổi mật khẩu</h3>
        <p class="text-xs text-slate-400">Đảm bảo mật khẩu mới có ít nhất 8 ký tự và độ phức tạp cao</p>
      </div>

      <form class="space-y-4 max-w-md font-mono" @submit.prevent="changePassword">
        <div>
          <label class="block text-xs font-medium text-slate-300 mb-1 font-sans">Mật khẩu hiện tại *</label>
          <UInput
            v-model="passwordForm.current_password"
            type="password"
            required
            size="md"
            class="w-full text-xs font-mono"
          />
        </div>

        <div>
          <label class="block text-xs font-medium text-slate-300 mb-1 font-sans">Mật khẩu mới *</label>
          <UInput
            v-model="passwordForm.new_password"
            type="password"
            required
            minlength="8"
            size="md"
            class="w-full text-xs font-mono"
          />
        </div>

        <div>
          <label class="block text-xs font-medium text-slate-300 mb-1 font-sans">Xác nhận mật khẩu mới *</label>
          <UInput
            v-model="passwordForm.confirm_password"
            type="password"
            required
            minlength="8"
            size="md"
            class="w-full text-xs font-mono"
          />
        </div>

        <div v-if="passwordMismatch" class="text-xs text-rose-400 font-mono">
          Mật khẩu mới xác nhận không khớp!
        </div>

        <div class="pt-2">
          <UButton
            type="submit"
            color="emerald"
            :loading="isSavingPassword"
            :disabled="passwordMismatch || !passwordForm.new_password"
            class="text-xs font-mono font-semibold"
          >
            Cập nhật mật khẩu
          </UButton>
        </div>
      </form>
    </div>

    <!-- Tab 3: Danger Zone -->
    <div v-else-if="activeTab === 'danger'" class="p-6 rounded-2xl bg-[#090d16]/80 border border-rose-500/20 shadow-xl space-y-4">
      <div>
        <h3 class="text-sm font-bold text-rose-400 flex items-center gap-2 font-mono">
          <UIcon name="i-heroicons-exclamation-triangle" class="w-5 h-5 text-rose-400" />
          Xóa tài khoản vĩnh viễn
        </h3>
        <p class="text-xs text-slate-400 leading-relaxed font-sans">
          Khi bạn xóa tài khoản, tất cả dữ liệu danh mục, mô phỏng cá nhân và thiết lập sẽ bị xóa vĩnh viễn. Hành động này không thể hoàn tác.
        </p>
      </div>

      <div class="pt-2">
        <UButton color="red" class="text-xs font-mono" @click="deleteAccountModal = true">
          Xóa tài khoản của tôi
        </UButton>
      </div>

      <!-- Delete Account Confirmation Modal -->
      <UModal v-model="deleteAccountModal">
        <div class="p-6 bg-[#090d16] text-slate-100 rounded-2xl border border-white/[0.08] space-y-4">
          <h3 class="text-base font-bold text-rose-400 font-mono">Bạn có chắc chắn muốn xóa tài khoản?</h3>
          <p class="text-xs text-slate-300">
            Hành động này sẽ hủy kích hoạt tài khoản của bạn ngay lập tức. Bạn sẽ bị đăng xuất và không thể truy cập lại.
          </p>
          <div class="flex items-center justify-end gap-2 pt-2">
            <UButton color="gray" variant="ghost" class="text-xs font-mono" @click="deleteAccountModal = false">
              Hủy
            </UButton>
            <UButton color="red" :loading="isDeletingAccount" class="text-xs font-mono" @click="handleDeleteAccount">
              Xác nhận xóa tài khoản
            </UButton>
          </div>
        </div>
      </UModal>
    </div>
  </div>
</template>

<script setup lang="ts">
import { UsersService } from "~/client"

useHead({
  title: "Cài đặt tài khoản - Vnstock Quants",
})

const { user, fetchUser, logout } = useAuth()
const { showSuccessToast, showErrorToast } = useCustomToast()

const activeTab = ref<"profile" | "password" | "danger">("profile")

const profileForm = reactive({
  full_name: "",
  email: "",
})

const isSavingProfile = ref(false)

const passwordForm = reactive({
  current_password: "",
  new_password: "",
  confirm_password: "",
})

const isSavingPassword = ref(false)
const deleteAccountModal = ref(false)
const isDeletingAccount = ref(false)

const passwordMismatch = computed(() => {
  return (
    passwordForm.confirm_password.length > 0 &&
    passwordForm.new_password !== passwordForm.confirm_password
  )
})

watch(
  user,
  (newUser) => {
    if (newUser) {
      profileForm.full_name = newUser.full_name || ""
      profileForm.email = newUser.email || ""
    }
  },
  { immediate: true },
)

const updateProfile = async () => {
  if (!profileForm.email.trim()) return
  isSavingProfile.value = true
  try {
    await UsersService.updateUserMe({
      body: {
        full_name: profileForm.full_name || undefined,
        email: profileForm.email,
      },
    })
    await fetchUser()
    showSuccessToast("Cập nhật thành công!", "Thông tin cá nhân đã được lưu.")
  } catch (err: unknown) {
    const error = err as { body?: { detail?: string }; message?: string }
    showErrorToast(
      "Lỗi cập nhật",
      error?.body?.detail || error?.message || "Không thể cập nhật hồ sơ.",
    )
  } finally {
    isSavingProfile.value = false
  }
}

const changePassword = async () => {
  if (passwordForm.new_password !== passwordForm.confirm_password) {
    showErrorToast("Lỗi nhập liệu", "Mật khẩu xác nhận không khớp.")
    return
  }
  isSavingPassword.value = true
  try {
    await UsersService.updatePasswordMe({
      body: {
        current_password: passwordForm.current_password,
        new_password: passwordForm.new_password,
      },
    })
    showSuccessToast(
      "Đổi mật khẩu thành công!",
      "Mật khẩu mới của bạn đã có hiệu lực.",
    )
    passwordForm.current_password = ""
    passwordForm.new_password = ""
    passwordForm.confirm_password = ""
  } catch (err: unknown) {
    const error = err as { body?: { detail?: string }; message?: string }
    showErrorToast(
      "Lỗi đổi mật khẩu",
      error?.body?.detail || error?.message || "Mật khẩu hiện tại không đúng.",
    )
  } finally {
    isSavingPassword.value = false
  }
}

const handleDeleteAccount = async () => {
  isDeletingAccount.value = true
  try {
    await UsersService.deleteUserMe()
    showSuccessToast(
      "Đã xóa tài khoản",
      "Tài khoản của bạn đã được xóa thành công.",
    )
    deleteAccountModal.value = false
    logout()
  } catch (err: unknown) {
    const error = err as { body?: { detail?: string }; message?: string }
    showErrorToast(
      "Lỗi xóa tài khoản",
      error?.body?.detail || error?.message || "Không thể xóa tài khoản.",
    )
  } finally {
    isDeletingAccount.value = false
  }
}
</script>
