<template>
  <div class="space-y-6">
    <!-- Header -->
    <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
      <div>
        <h1 class="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
          <UIcon name="i-heroicons-users" class="w-7 h-7 text-amber-400" />
          Quản lý người dùng hệ thống (Admin)
        </h1>
        <p class="text-xs sm:text-sm text-slate-400 mt-1">
          Quản lý danh sách tài khoản, phân quyền quản trị viên và trạng thái kích hoạt
        </p>
      </div>

      <div class="flex items-center gap-2">
        <UButton
          color="gray"
          variant="solid"
          size="sm"
          :loading="isLoading"
          @click="loadUsers"
        >
          <template #leading>
            <UIcon name="i-heroicons-arrow-path" :class="{ 'animate-spin': isLoading }" class="w-4 h-4" />
          </template>
          Làm mới
        </UButton>

        <UButton
          color="amber"
          size="sm"
          icon="i-heroicons-user-plus"
          @click="openAddModal"
        >
          Thêm người dùng
        </UButton>
      </div>
    </div>

    <!-- Users Table Card -->
    <div class="rounded-xl border border-slate-800 bg-slate-900/60 overflow-hidden shadow-xl">
      <div class="overflow-x-auto">
        <table class="w-full text-left text-xs">
          <thead class="bg-slate-950 text-slate-400 uppercase font-mono text-[11px] border-b border-slate-800">
            <tr>
              <th class="py-3 px-4">Họ và tên</th>
              <th class="py-3 px-4">Email</th>
              <th class="py-3 px-4 w-32 text-center">Vai trò</th>
              <th class="py-3 px-4 w-32 text-center">Trạng thái</th>
              <th class="py-3 px-4 w-28 text-right">Thao tác</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-800/60">
            <tr v-if="isLoading">
              <td colspan="5" class="py-12 text-center text-slate-400">
                <UIcon name="i-heroicons-arrow-path" class="w-8 h-8 animate-spin mx-auto text-amber-400 mb-2" />
                <p>Đang tải danh sách người dùng...</p>
              </td>
            </tr>

            <tr
              v-for="u in users"
              :key="u.id"
              class="hover:bg-slate-800/40 transition-colors"
            >
              <td class="py-3 px-4 font-semibold text-white flex items-center gap-2">
                <span>{{ u.full_name || '—' }}</span>
                <span
                  v-if="u.id === currentUser?.id"
                  class="text-[10px] font-mono px-1.5 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                >
                  Tôi
                </span>
              </td>
              <td class="py-3 px-4 text-slate-300 font-mono">
                {{ u.email }}
              </td>
              <td class="py-3 px-4 text-center">
                <span
                  v-if="u.is_superuser"
                  class="inline-block px-2 py-0.5 rounded text-[10px] font-bold bg-amber-500/10 text-amber-400 border border-amber-500/20 uppercase"
                >
                  Superuser
                </span>
                <span
                  v-else
                  class="inline-block px-2 py-0.5 rounded text-[10px] font-medium bg-slate-800 text-slate-400"
                >
                  User
                </span>
              </td>
              <td class="py-3 px-4 text-center">
                <span
                  v-if="u.is_active"
                  class="inline-flex items-center gap-1 text-[11px] text-emerald-400 font-semibold"
                >
                  <UIcon name="i-heroicons-check-circle" class="w-4 h-4" />
                  Hoạt động
                </span>
                <span
                  v-else
                  class="inline-flex items-center gap-1 text-[11px] text-rose-400 font-semibold"
                >
                  <UIcon name="i-heroicons-x-circle" class="w-4 h-4" />
                  Đã khóa
                </span>
              </td>
              <td class="py-3 px-4 text-right space-x-1">
                <button
                  type="button"
                  class="p-1.5 text-slate-400 hover:text-amber-400 hover:bg-slate-800 rounded transition-colors"
                  title="Chỉnh sửa"
                  @click="openEditModal(u)"
                >
                  <UIcon name="i-heroicons-pencil-square" class="w-4 h-4" />
                </button>
                <button
                  type="button"
                  class="p-1.5 text-slate-400 hover:text-rose-400 hover:bg-slate-800 rounded transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
                  title="Xóa"
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
      <div class="p-6 bg-slate-900 text-slate-100 rounded-xl space-y-4">
        <h3 class="text-base font-bold text-white flex items-center gap-2">
          <UIcon :name="isEditing ? 'i-heroicons-pencil-square' : 'i-heroicons-user-plus'" class="w-5 h-5 text-amber-400" />
          {{ isEditing ? 'Chỉnh sửa Người dùng' : 'Thêm Người dùng mới' }}
        </h3>

        <form class="space-y-4" @submit.prevent="saveUser">
          <div>
            <label class="block text-xs font-medium text-slate-300 mb-1">Email *</label>
            <UInput v-model="form.email" type="email" placeholder="user@example.com" required size="md" class="w-full" />
          </div>

          <div>
            <label class="block text-xs font-medium text-slate-300 mb-1">Họ và tên</label>
            <UInput v-model="form.full_name" placeholder="Nguyễn Văn A" size="md" class="w-full" />
          </div>

          <div>
            <label class="block text-xs font-medium text-slate-300 mb-1">
              {{ isEditing ? 'Mật khẩu mới (để trống nếu không đổi)' : 'Mật khẩu ban đầu *' }}
            </label>
            <UInput
              v-model="form.password"
              type="password"
              placeholder="Mật khẩu"
              :required="!isEditing"
              minlength="8"
              size="md"
              class="w-full"
            />
          </div>

          <div class="space-y-2 pt-1">
            <label class="flex items-center gap-2 text-xs text-slate-300 cursor-pointer">
              <input v-model="form.is_superuser" type="checkbox" class="rounded accent-amber-500">
              <span>Quyền Quản trị viên (Superuser)</span>
            </label>

            <label class="flex items-center gap-2 text-xs text-slate-300 cursor-pointer">
              <input v-model="form.is_active" type="checkbox" class="rounded accent-emerald-500">
              <span>Kích hoạt tài khoản (Active)</span>
            </label>
          </div>

          <div class="flex items-center justify-end gap-2 pt-2">
            <UButton color="gray" variant="ghost" @click="modalOpen = false">
              Hủy
            </UButton>
            <UButton type="submit" color="amber" :loading="isSaving">
              {{ isEditing ? 'Lưu thay đổi' : 'Tạo tài khoản' }}
            </UButton>
          </div>
        </form>
      </div>
    </UModal>

    <!-- Delete Confirmation Modal -->
    <UModal v-model="deleteModalOpen">
      <div class="p-6 bg-slate-900 text-slate-100 rounded-xl space-y-4">
        <h3 class="text-base font-bold text-rose-400 flex items-center gap-2">
          <UIcon name="i-heroicons-exclamation-triangle" class="w-5 h-5 text-rose-400" />
          Xác nhận xóa tài khoản
        </h3>
        <p class="text-xs text-slate-300">
          Bạn có chắc chắn muốn xóa tài khoản "<span class="font-bold text-white">{{ userToDelete?.email }}</span>"? Hành động này không thể hoàn tác.
        </p>
        <div class="flex items-center justify-end gap-2 pt-2">
          <UButton color="gray" variant="ghost" @click="deleteModalOpen = false">
            Hủy
          </UButton>
          <UButton color="red" :loading="isDeleting" @click="handleDelete">
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
