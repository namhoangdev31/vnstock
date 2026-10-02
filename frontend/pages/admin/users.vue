<template>
  <div class="space-y-6">
    <!-- Header -->
    <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
      <div>
        <div class="flex items-center gap-2 text-xs font-mono text-slate-500 mb-1">
          <span>SECURITY & ACCESS</span>
          <span>/</span>
          <span class="text-amber-400">ROLE-BASED ACCESS CONTROL (RBAC)</span>
        </div>
        <h1 class="text-2xl font-bold tracking-tight text-white flex items-center gap-2.5">
          <div class="w-8 h-8 rounded-lg bg-amber-500/10 border border-amber-500/30 flex items-center justify-center">
            <UIcon name="i-heroicons-shield-check" class="w-4 h-4 text-amber-400" />
          </div>
          Quản trị tài khoản & Phân quyền
        </h1>
        <p class="text-xs text-slate-400 mt-1">
          Quản lý danh sách tài khoản định lượng, phân bổ quyền Superuser và kiểm soát trạng thái đăng nhập
        </p>
      </div>

      <div class="flex items-center gap-2">
        <UButton
          color="gray"
          variant="solid"
          size="sm"
          :loading="isLoading"
          class="font-mono text-xs"
          @click="loadUsers"
        >
          <template #leading>
            <UIcon name="i-heroicons-arrow-path" :class="{ 'animate-spin': isLoading }" class="w-3.5 h-3.5" />
          </template>
          Làm mới
        </UButton>

        <UButton
          color="amber"
          size="sm"
          icon="i-heroicons-user-plus"
          class="font-mono text-xs shadow-lg shadow-amber-500/10"
          @click="openAddModal"
        >
          Thêm người dùng
        </UButton>
      </div>
    </div>

    <!-- Users Table Card -->
    <div class="rounded-xl border border-white/[0.08] bg-[#090d16] overflow-hidden shadow-2xl">
      <div class="p-3.5 bg-[#0b101c] border-b border-white/[0.06] flex items-center justify-between">
        <div class="flex items-center gap-2 font-mono text-xs text-slate-300">
          <span class="w-2 h-2 rounded-full bg-amber-400 animate-pulse" />
          <span>DANH SÁCH NGƯỜI DÙNG HỆ THỐNG</span>
          <span class="text-[10px] px-2 py-0.5 rounded bg-white/[0.04] text-slate-400 border border-white/[0.06]">
            {{ users.length }} accounts
          </span>
        </div>
        <div class="text-[11px] font-mono text-slate-400">
          JWT AUTH // SCOPE: ADMIN
        </div>
      </div>

      <div class="overflow-x-auto">
        <table class="w-full text-left text-xs">
          <thead class="bg-[#070a11] text-slate-400 uppercase font-mono text-[10px] tracking-wider border-b border-white/[0.06]">
            <tr>
              <th class="py-3 px-4">HỌ VÀ TÊN</th>
              <th class="py-3 px-4">ĐỊA CHỈ EMAIL</th>
              <th class="py-3 px-4 w-32 text-center">VAI TRÒ (ROLE)</th>
              <th class="py-3 px-4 w-32 text-center">TRẠNG THÁI</th>
              <th class="py-3 px-4 w-28 text-right">THAO TÁC</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-white/[0.04]">
            <tr v-if="isLoading">
              <td colspan="5" class="py-14 text-center text-slate-400">
                <UIcon name="i-heroicons-arrow-path" class="w-7 h-7 animate-spin mx-auto text-amber-400 mb-2" />
                <p class="font-mono text-xs text-slate-400">Đang truy vấn danh sách tài khoản từ cơ sở dữ liệu...</p>
              </td>
            </tr>

            <tr
              v-for="u in users"
              :key="u.id"
              class="hover:bg-white/[0.02] transition-colors group"
            >
              <td class="py-3 px-4 font-semibold text-white flex items-center gap-2">
                <span>{{ u.full_name || 'N/A' }}</span>
                <span
                  v-if="u.id === currentUser?.id"
                  class="text-[10px] font-mono px-1.5 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                >
                  Current
                </span>
              </td>
              <td class="py-3 px-4 text-slate-300 font-mono text-[11px]">
                {{ u.email }}
              </td>
              <td class="py-3 px-4 text-center">
                <span
                  v-if="u.is_superuser"
                  class="inline-block px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-amber-500/10 text-amber-400 border border-amber-500/20 uppercase"
                >
                  Superuser
                </span>
                <span
                  v-else
                  class="inline-block px-2 py-0.5 rounded text-[10px] font-mono font-medium bg-white/[0.04] text-slate-400 border border-white/[0.06]"
                >
                  Quant User
                </span>
              </td>
              <td class="py-3 px-4 text-center">
                <span
                  v-if="u.is_active"
                  class="inline-flex items-center gap-1.5 text-[11px] font-mono text-emerald-400 font-medium"
                >
                  <span class="w-1.5 h-1.5 rounded-full bg-emerald-400" />
                  Active
                </span>
                <span
                  v-else
                  class="inline-flex items-center gap-1.5 text-[11px] font-mono text-rose-400 font-medium"
                >
                  <span class="w-1.5 h-1.5 rounded-full bg-rose-400" />
                  Locked
                </span>
              </td>
              <td class="py-3 px-4 text-right space-x-1">
                <button
                  type="button"
                  class="p-1.5 text-slate-400 hover:text-amber-400 hover:bg-amber-500/10 rounded transition-colors"
                  title="Chỉnh sửa tài khoản"
                  @click="openEditModal(u)"
                >
                  <UIcon name="i-heroicons-pencil-square" class="w-4 h-4" />
                </button>
                <button
                  type="button"
                  class="p-1.5 text-slate-400 hover:text-rose-400 hover:bg-rose-500/10 rounded transition-colors disabled:opacity-20 disabled:cursor-not-allowed"
                  title="Xóa tài khoản"
                  :disabled="u.id === currentUser?.id"
                  @click="confirmDelete(u)"
                >
                  <UIcon name="i-heroicons-trash" class="w-4 h-4" />
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Add / Edit User Modal -->
    <UModal v-model="modalOpen">
      <div class="p-6 bg-[#090d16] text-slate-100 rounded-xl border border-white/[0.1] space-y-4 shadow-2xl">
        <div class="flex items-center justify-between pb-3 border-b border-white/[0.06]">
          <h3 class="text-sm font-bold text-white flex items-center gap-2 font-mono">
            <UIcon :name="isEditing ? 'i-heroicons-pencil-square' : 'i-heroicons-user-plus'" class="w-4 h-4 text-amber-400" />
            {{ isEditing ? 'CẬP NHẬT THÔNG TIN NGƯỜI DÙNG' : 'TẠO TÀI KHOẢN MỚI' }}
          </h3>
          <span class="text-[10px] font-mono text-slate-500">ID: {{ currentUserId || 'AUTO_GEN' }}</span>
        </div>

        <form class="space-y-4" @submit.prevent="saveUser">
          <div>
            <label class="block text-xs font-mono text-slate-300 mb-1.5">Địa chỉ Email *</label>
            <UInput v-model="form.email" type="email" placeholder="user@example.com" required size="md" class="w-full font-mono text-xs" />
          </div>

          <div>
            <label class="block text-xs font-mono text-slate-300 mb-1.5">Họ và tên</label>
            <UInput v-model="form.full_name" placeholder="Nguyễn Văn A" size="md" class="w-full text-xs" />
          </div>

          <div>
            <label class="block text-xs font-mono text-slate-300 mb-1.5">
              {{ isEditing ? 'Mật khẩu mới (để trống nếu giữ nguyên)' : 'Mật khẩu khởi tạo *' }}
            </label>
            <UInput
              v-model="form.password"
              type="password"
              placeholder="Mật khẩu tối thiểu 8 ký tự"
              :required="!isEditing"
              minlength="8"
              size="md"
              class="w-full font-mono text-xs"
            />
          </div>

          <div class="space-y-2 pt-2 border-t border-white/[0.06]">
            <label class="flex items-center gap-2.5 text-xs text-slate-300 cursor-pointer">
              <input v-model="form.is_superuser" type="checkbox" class="rounded accent-amber-500 bg-slate-900 border-slate-700">
              <span class="font-mono">Quyền Quản trị viên (Superuser Flag)</span>
            </label>

            <label class="flex items-center gap-2.5 text-xs text-slate-300 cursor-pointer">
              <input v-model="form.is_active" type="checkbox" class="rounded accent-emerald-500 bg-slate-900 border-slate-700">
              <span class="font-mono">Kích hoạt tài khoản (Active Status)</span>
            </label>
          </div>

          <div class="flex items-center justify-end gap-2 pt-3 border-t border-white/[0.06]">
            <UButton color="gray" variant="ghost" size="sm" class="font-mono text-xs" @click="modalOpen = false">
              Hủy
            </UButton>
            <UButton type="submit" color="amber" size="sm" :loading="isSaving" class="font-mono text-xs">
              {{ isEditing ? 'Lưu thay đổi' : 'Tạo tài khoản' }}
            </UButton>
          </div>
        </form>
      </div>
    </UModal>

    <!-- Delete Confirmation Modal -->
    <UModal v-model="deleteModalOpen">
      <div class="p-6 bg-[#090d16] text-slate-100 rounded-xl border border-rose-500/20 space-y-4 shadow-2xl">
        <h3 class="text-sm font-bold text-rose-400 flex items-center gap-2 font-mono">
          <UIcon name="i-heroicons-exclamation-triangle" class="w-4 h-4 text-rose-400" />
          XÁC NHẬN XÓA TÀI KHOẢN
        </h3>
        <p class="text-xs text-slate-300 leading-relaxed">
          Bạn có chắc chắn muốn xóa vĩnh viễn tài khoản "<span class="font-bold text-white font-mono">{{ userToDelete?.email }}</span>"? Toàn bộ dữ liệu gắn liền với người dùng này sẽ bị hủy bỏ.
        </p>
        <div class="flex items-center justify-end gap-2 pt-3 border-t border-white/[0.06]">
          <UButton color="gray" variant="ghost" size="sm" class="font-mono text-xs" @click="deleteModalOpen = false">
            Hủy
          </UButton>
          <UButton color="red" size="sm" :loading="isDeleting" class="font-mono text-xs" @click="handleDelete">
            Xác nhận xóa
          </UButton>
        </div>
      </div>
    </UModal>
  </div>
</template>

<script setup lang="ts">
import type { UserPublic } from "~/client"
import { UsersService } from "~/client"

useHead({
  title: "Quản trị người dùng - Vnstock Quants",
})

const { user: currentUser } = useAuth()
const { showSuccessToast, showErrorToast } = useCustomToast()

const users = ref<UserPublic[]>([])
const isLoading = ref(false)

const modalOpen = ref(false)
const isEditing = ref(false)
const isSaving = ref(false)
const currentUserId = ref<string | null>(null)
const form = reactive({
  email: "",
  full_name: "",
  password: "",
  is_superuser: false,
  is_active: true,
})

const deleteModalOpen = ref(false)
const userToDelete = ref<UserPublic | null>(null)
const isDeleting = ref(false)

const loadUsers = async () => {
  isLoading.value = true
  try {
    const res = await UsersService.readUsers({
      query: { skip: 0, limit: 100 },
    })
    users.value = res.data?.data ?? []
  } catch (err: unknown) {
    const error = err as { message?: string }
    showErrorToast(
      "Lỗi tải danh sách",
      error?.message || "Không thể tải danh sách người dùng.",
    )
  } finally {
    isLoading.value = false
  }
}

const openAddModal = () => {
  isEditing.value = false
  currentUserId.value = null
  form.email = ""
  form.full_name = ""
  form.password = ""
  form.is_superuser = false
  form.is_active = true
  modalOpen.value = true
}

const openEditModal = (u: UserPublic) => {
  isEditing.value = true
  currentUserId.value = u.id
  form.email = u.email
  form.full_name = u.full_name || ""
  form.password = ""
  form.is_superuser = !!u.is_superuser
  form.is_active = u.is_active ?? true
  modalOpen.value = true
}

const saveUser = async () => {
  if (!form.email.trim()) return
  isSaving.value = true
  try {
    if (isEditing.value && currentUserId.value) {
      await UsersService.updateUser({
        path: { user_id: currentUserId.value },
        body: {
          email: form.email,
          full_name: form.full_name || undefined,
          password: form.password || undefined,
          is_superuser: form.is_superuser,
          is_active: form.is_active,
        },
      })
      showSuccessToast(
        "Cập nhật thành công!",
        "Thông tin tài khoản đã được lưu.",
      )
    } else {
      await UsersService.createUser({
        body: {
          email: form.email,
          full_name: form.full_name || undefined,
          password: form.password,
          is_superuser: form.is_superuser,
          is_active: form.is_active,
        },
      })
      showSuccessToast(
        "Tạo tài khoản thành công!",
        "Tài khoản mới đã được khởi tạo.",
      )
    }
    modalOpen.value = false
    await loadUsers()
  } catch (err: unknown) {
    const error = err as { body?: { detail?: string }; message?: string }
    showErrorToast(
      "Lỗi lưu người dùng",
      error?.body?.detail || error?.message || "Không thể lưu thông tin.",
    )
  } finally {
    isSaving.value = false
  }
}

const confirmDelete = (u: UserPublic) => {
  if (u.id === currentUser.value?.id) {
    showErrorToast("Cảnh báo", "Bạn không thể tự xóa tài khoản của chính mình.")
    return
  }
  userToDelete.value = u
  deleteModalOpen.value = true
}

const handleDelete = async () => {
  if (!userToDelete.value) return
  isDeleting.value = true
  try {
    await UsersService.deleteUser({
      path: { user_id: userToDelete.value.id },
    })
    showSuccessToast(
      "Đã xóa tài khoản!",
      "Tài khoản đã được gỡ bỏ khỏi hệ thống.",
    )
    deleteModalOpen.value = false
    await loadUsers()
  } catch (err: unknown) {
    const error = err as { message?: string }
    showErrorToast(
      "Lỗi xóa tài khoản",
      error?.message || "Không thể xóa tài khoản.",
    )
  } finally {
    isDeleting.value = false
  }
}

onMounted(() => {
  loadUsers()
})
</script>
