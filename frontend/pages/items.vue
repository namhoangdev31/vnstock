<template>
  <div class="space-y-6">
    <!-- Header -->
    <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
      <div>
        <div class="flex items-center gap-2 text-xs font-mono text-slate-500 mb-1">
          <span>WORKSPACE</span>
          <span>/</span>
          <span class="text-emerald-400">ITEMS CATALOG</span>
        </div>
        <h1 class="text-2xl font-bold tracking-tight text-white flex items-center gap-2.5">
          <div class="w-8 h-8 rounded-lg bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center">
            <UIcon name="i-heroicons-folder" class="w-4 h-4 text-emerald-400" />
          </div>
          Quản lý danh mục Items
        </h1>
        <p class="text-xs text-slate-400 mt-1">
          Danh mục định danh dữ liệu, cấu hình pipeline và tham số nghiên cứu định lượng
        </p>
      </div>

      <div class="flex items-center gap-2">
        <UButton
          color="gray"
          variant="solid"
          size="sm"
          :loading="isLoading"
          class="font-mono text-xs"
          @click="loadItems"
        >
          <template #leading>
            <UIcon name="i-heroicons-arrow-path" :class="{ 'animate-spin': isLoading }" class="w-3.5 h-3.5" />
          </template>
          Làm mới
        </UButton>

        <UButton
          color="emerald"
          size="sm"
          icon="i-heroicons-plus"
          class="font-mono text-xs shadow-lg shadow-emerald-500/10"
          @click="openAddModal"
        >
          Thêm Item
        </UButton>
      </div>
    </div>

    <!-- Items Table Card -->
    <div class="rounded-xl border border-white/[0.08] bg-[#090d16] overflow-hidden shadow-2xl">
      <div class="p-3.5 bg-[#0b101c] border-b border-white/[0.06] flex items-center justify-between">
        <div class="flex items-center gap-2 font-mono text-xs text-slate-300">
          <span class="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
          <span>BẢNG DANH MỤC THỰC THỂ</span>
          <span class="text-[10px] px-2 py-0.5 rounded bg-white/[0.04] text-slate-400 border border-white/[0.06]">
            {{ items.length }} records
          </span>
        </div>
        <div class="text-[11px] font-mono text-slate-400">
          ISO-8601 // POSTGRESQL TIER
        </div>
      </div>

      <div class="overflow-x-auto">
        <table class="w-full text-left text-xs">
          <thead class="bg-[#070a11] text-slate-400 uppercase font-mono text-[10px] tracking-wider border-b border-white/[0.06]">
            <tr>
              <th class="py-3 px-4 w-48">MÃ ĐỊNH DANH (UUID)</th>
              <th class="py-3 px-4">TIÊU ĐỀ (TITLE)</th>
              <th class="py-3 px-4">MÔ TẢ CHI TIẾT</th>
              <th class="py-3 px-4 w-28 text-right">THAO TÁC</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-white/[0.04]">
            <tr v-if="isLoading">
              <td colspan="4" class="py-14 text-center text-slate-400">
                <UIcon name="i-heroicons-arrow-path" class="w-7 h-7 animate-spin mx-auto text-emerald-400 mb-2" />
                <p class="font-mono text-xs text-slate-400">Đang đồng bộ danh sách items từ server...</p>
              </td>
            </tr>

            <tr v-else-if="items.length === 0">
              <td colspan="4" class="py-14 text-center text-slate-400">
                <UIcon name="i-heroicons-inbox" class="w-8 h-8 mx-auto text-slate-600 mb-2" />
                <p class="font-mono text-xs text-slate-300">Chưa có item nào được lưu trữ</p>
                <p class="text-[11px] text-slate-500 mt-1">Nhấn "Thêm Item" ở góc trên để tạo bản ghi đầu tiên.</p>
              </td>
            </tr>

            <tr
              v-for="item in items"
              :key="item.id"
              class="hover:bg-white/[0.02] transition-colors group"
            >
              <td class="py-3 px-4 font-mono text-slate-400 text-[11px] truncate max-w-[180px]">
                <span class="px-1.5 py-0.5 rounded bg-white/[0.03] border border-white/[0.06] text-slate-300">
                  {{ item.id }}
                </span>
              </td>
              <td class="py-3 px-4 font-semibold text-white">
                {{ item.title }}
              </td>
              <td class="py-3 px-4 text-slate-400">
                {{ item.description || 'N/A' }}
              </td>
              <td class="py-3 px-4 text-right space-x-1">
                <button
                  type="button"
                  class="p-1.5 text-slate-400 hover:text-emerald-400 hover:bg-emerald-500/10 rounded transition-colors"
                  title="Chỉnh sửa"
                  @click="openEditModal(item)"
                >
                  <UIcon name="i-heroicons-pencil-square" class="w-4 h-4" />
                </button>
                <button
                  type="button"
                  class="p-1.5 text-slate-400 hover:text-rose-400 hover:bg-rose-500/10 rounded transition-colors"
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
      <div class="p-6 bg-[#090d16] text-slate-100 rounded-xl border border-white/[0.1] space-y-4 shadow-2xl">
        <div class="flex items-center justify-between pb-3 border-b border-white/[0.06]">
          <h3 class="text-sm font-bold text-white flex items-center gap-2 font-mono">
            <UIcon :name="isEditing ? 'i-heroicons-pencil-square' : 'i-heroicons-plus-circle'" class="w-4 h-4 text-emerald-400" />
            {{ isEditing ? 'CẬP NHẬT ITEM' : 'KHỞI TẠO ITEM MỚI' }}
          </h3>
          <span class="text-[10px] font-mono text-slate-500">ID: {{ currentItemId || 'AUTO_GEN' }}</span>
        </div>

        <form class="space-y-4" @submit.prevent="saveItem">
          <div>
            <label class="block text-xs font-mono text-slate-300 mb-1.5">Tiêu đề (Title) *</label>
            <UInput v-model="form.title" placeholder="Nhập tiêu đề item" required size="md" class="w-full font-mono text-xs" />
          </div>

          <div>
            <label class="block text-xs font-mono text-slate-300 mb-1.5">Mô tả (Description)</label>
            <UTextarea v-model="form.description" placeholder="Nhập mô tả chi tiết danh mục..." :rows="3" class="w-full text-xs" />
          </div>

          <div class="flex items-center justify-end gap-2 pt-3 border-t border-white/[0.06]">
            <UButton color="gray" variant="ghost" size="sm" class="font-mono text-xs" @click="modalOpen = false">
              Hủy bỏ
            </UButton>
            <UButton type="submit" color="emerald" size="sm" :loading="isSaving" class="font-mono text-xs">
              {{ isEditing ? 'Lưu thay đổi' : 'Thêm mới' }}
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
          XÁC NHẬN XÓA ITEM
        </h3>
        <p class="text-xs text-slate-300 leading-relaxed">
          Bạn có chắc chắn muốn xóa vĩnh viễn item "<span class="font-bold text-white font-mono">{{ itemToDelete?.title }}</span>"? Thao tác này không thể hoàn tác.
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
