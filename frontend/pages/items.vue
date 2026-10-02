<template>
  <div class="space-y-6">
    <!-- Header -->
    <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
      <div>
        <h1 class="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
          <UIcon name="i-heroicons-folder" class="w-7 h-7 text-emerald-400" />
          Quản lý danh mục Items
        </h1>
        <p class="text-xs sm:text-sm text-slate-400 mt-1">
          Danh sách các hạng mục dữ liệu và cấu hình danh mục nghiên cứu
        </p>
      </div>

      <div class="flex items-center gap-2">
        <UButton
          color="gray"
          variant="solid"
          size="sm"
          :loading="isLoading"
          @click="loadItems"
        >
          <template #leading>
            <UIcon name="i-heroicons-arrow-path" :class="{ 'animate-spin': isLoading }" class="w-4 h-4" />
          </template>
          Làm mới
        </UButton>

        <UButton
          color="emerald"
          size="sm"
          icon="i-heroicons-plus"
          @click="openAddModal"
        >
          Thêm Item
        </UButton>
      </div>
    </div>

    <!-- Items Table Card -->
    <div class="rounded-xl border border-slate-800 bg-slate-900/60 overflow-hidden shadow-xl">
      <div class="overflow-x-auto">
        <table class="w-full text-left text-xs">
          <thead class="bg-slate-950 text-slate-400 uppercase font-mono text-[11px] border-b border-slate-800">
            <tr>
              <th class="py-3 px-4 w-44">ID</th>
              <th class="py-3 px-4">Tiêu đề (Title)</th>
              <th class="py-3 px-4">Mô tả (Description)</th>
              <th class="py-3 px-4 w-28 text-right">Thao tác</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-800/60">
            <tr v-if="isLoading">
              <td colspan="4" class="py-12 text-center text-slate-400">
                <UIcon name="i-heroicons-arrow-path" class="w-8 h-8 animate-spin mx-auto text-emerald-400 mb-2" />
                <p>Đang tải danh sách items...</p>
              </td>
            </tr>

            <tr v-else-if="items.length === 0">
              <td colspan="4" class="py-12 text-center text-slate-400">
                <UIcon name="i-heroicons-inbox" class="w-8 h-8 mx-auto text-slate-600 mb-2" />
                <p class="font-medium text-slate-300">Chưa có item nào</p>
                <p class="text-xs text-slate-500 mt-1">Nhấn "Thêm Item" để bắt đầu tạo mới.</p>
              </td>
            </tr>

            <tr
              v-for="item in items"
              :key="item.id"
              class="hover:bg-slate-800/40 transition-colors"
            >
              <td class="py-3 px-4 font-mono text-slate-400 text-[11px] truncate max-w-[160px]">
                {{ item.id }}
              </td>
              <td class="py-3 px-4 font-semibold text-white">
                {{ item.title }}
              </td>
              <td class="py-3 px-4 text-slate-300">
                {{ item.description || '—' }}
              </td>
              <td class="py-3 px-4 text-right space-x-1">
                <button
                  type="button"
                  class="p-1.5 text-slate-400 hover:text-emerald-400 hover:bg-slate-800 rounded transition-colors"
                  title="Chỉnh sửa"
                  @click="openEditModal(item)"
                >
                  <UIcon name="i-heroicons-pencil-square" class="w-4 h-4" />
                </button>
                <button
                  type="button"
                  class="p-1.5 text-slate-400 hover:text-rose-400 hover:bg-slate-800 rounded transition-colors"
                  title="Xóa"
                  @click="confirmDelete(item)"
                >
                  <UIcon name="i-heroicons-trash" class="w-4 h-4" />
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Add / Edit Modal -->
    <UModal v-model="modalOpen">
      <div class="p-6 bg-slate-900 text-slate-100 rounded-xl space-y-4">
        <h3 class="text-base font-bold text-white flex items-center gap-2">
          <UIcon :name="isEditing ? 'i-heroicons-pencil-square' : 'i-heroicons-plus-circle'" class="w-5 h-5 text-emerald-400" />
          {{ isEditing ? 'Chỉnh sửa Item' : 'Thêm Item mới' }}
        </h3>

        <form class="space-y-4" @submit.prevent="saveItem">
          <div>
            <label class="block text-xs font-medium text-slate-300 mb-1">Tiêu đề (Title) *</label>
            <UInput v-model="form.title" placeholder="Nhập tiêu đề item" required size="md" class="w-full" />
          </div>

          <div>
            <label class="block text-xs font-medium text-slate-300 mb-1">Mô tả (Description)</label>
            <UTextarea v-model="form.description" placeholder="Nhập mô tả chi tiết..." :rows="3" class="w-full" />
          </div>

          <div class="flex items-center justify-end gap-2 pt-2">
            <UButton color="gray" variant="ghost" @click="modalOpen = false">
              Hủy
            </UButton>
            <UButton type="submit" color="emerald" :loading="isSaving">
              {{ isEditing ? 'Lưu thay đổi' : 'Thêm mới' }}
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
          Xác nhận xóa Item
        </h3>
        <p class="text-xs text-slate-300">
          Bạn có chắc chắn muốn xóa item "<span class="font-bold text-white">{{ itemToDelete?.title }}</span>"? Thao tác này không thể hoàn tác.
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
import type { ItemPublic } from "~/client"
import { ItemsService } from "~/client"

useHead({
  title: "Quản lý Items - Vnstock Quants",
})

const { showSuccessToast, showErrorToast } = useCustomToast()

const items = ref<ItemPublic[]>([])
const isLoading = ref(false)

const modalOpen = ref(false)
const isEditing = ref(false)
const isSaving = ref(false)
const currentItemId = ref<string | null>(null)
const form = reactive({
  title: "",
  description: "",
})

const deleteModalOpen = ref(false)
const itemToDelete = ref<ItemPublic | null>(null)
const isDeleting = ref(false)

const loadItems = async () => {
  isLoading.value = true
  try {
    const res = await ItemsService.readItems({
      query: { skip: 0, limit: 100 },
    })
    items.value = res.data?.data ?? []
  } catch (err: unknown) {
    const error = err as { message?: string }
    showErrorToast(
      "Lỗi tải danh sách",
      error?.message || "Không thể tải danh sách items.",
    )
  } finally {
    isLoading.value = false
  }
}

const openAddModal = () => {
  isEditing.value = false
  currentItemId.value = null
  form.title = ""
  form.description = ""
  modalOpen.value = true
}

const openEditModal = (item: ItemPublic) => {
  isEditing.value = true
  currentItemId.value = item.id
  form.title = item.title
  form.description = item.description || ""
  modalOpen.value = true
}

const saveItem = async () => {
  if (!form.title.trim()) return
  isSaving.value = true
  try {
    if (isEditing.value && currentItemId.value) {
      await ItemsService.updateItem({
        path: { id: currentItemId.value },
        body: {
          title: form.title,
          description: form.description || undefined,
        },
      })
      showSuccessToast("Cập nhật thành công!", "Item đã được lưu thay đổi.")
    } else {
      await ItemsService.createItem({
        body: {
          title: form.title,
          description: form.description || undefined,
        },
      })
      showSuccessToast("Thêm mới thành công!", "Item mới đã được tạo.")
    }
    modalOpen.value = false
    await loadItems()
  } catch (err: unknown) {
    const error = err as { body?: { detail?: string }; message?: string }
    showErrorToast(
      "Lỗi lưu item",
      error?.body?.detail || error?.message || "Không thể lưu item.",
    )
  } finally {
    isSaving.value = false
  }
}

const confirmDelete = (item: ItemPublic) => {
  itemToDelete.value = item
  deleteModalOpen.value = true
}

const handleDelete = async () => {
  if (!itemToDelete.value) return
  isDeleting.value = true
  try {
    await ItemsService.deleteItem({
      path: { id: itemToDelete.value.id },
    })
    showSuccessToast(
      "Đã xóa item!",
      "Item đã được xóa vĩnh viễn khỏi hệ thống.",
    )
    deleteModalOpen.value = false
    await loadItems()
  } catch (err: unknown) {
    const error = err as { message?: string }
    showErrorToast("Lỗi xóa item", error?.message || "Không thể xóa item.")
  } finally {
    isDeleting.value = false
  }
}

onMounted(() => {
  loadItems()
})
</script>
