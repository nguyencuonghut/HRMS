<template>
  <div class="rc-detail" v-if="posting">
    <!-- Header -->
    <div class="rc-detail-header">
      <div class="rc-header-left">
        <Button icon="pi pi-arrow-left" text rounded severity="secondary" @click="$router.push('/recruitment?tab=postings')" />
        <div>
          <div style="display: flex; align-items: center; gap: 0.6rem; flex-wrap: wrap">
            <span class="rc-jr-code">{{ posting.title }}</span>
            <Tag :value="posting.status_label" :severity="statusSeverity(posting.status)" />
            <Tag :value="posting.posting_type_label" :severity="posting.posting_type === 'internal' ? 'info' : 'secondary'" />
          </div>
          <div class="rc-meta-row" style="margin-top: 0.2rem">
            <span>{{ posting.job_requisition_code }}</span>
            <span>·</span>
            <span>{{ posting.job_position_name }}</span>
            <span>·</span>
            <span>{{ posting.department_name }}</span>
            <span v-if="posting.created_by_name">·</span>
            <span v-if="posting.created_by_name">Tạo bởi {{ posting.created_by_name }}</span>
          </div>
        </div>
      </div>

      <div class="rc-header-right">
        <Button
          v-if="posting.status === 'draft' || posting.status === 'active'"
          label="Sửa"
          icon="pi pi-pencil"
          severity="secondary"
          outlined
          @click="openEdit"
        />
        <Button
          v-if="posting.status === 'draft'"
          label="Đăng tin"
          icon="pi pi-send"
          severity="success"
          @click="confirmPublish"
        />
        <Button
          v-if="posting.status === 'active'"
          label="Đóng tin"
          icon="pi pi-times-circle"
          severity="warn"
          outlined
          @click="confirmClose"
        />
        <Button
          v-if="posting.status === 'closed'"
          label="Mở lại"
          icon="pi pi-refresh"
          severity="info"
          @click="confirmReopen"
        />
      </div>
    </div>

    <!-- Info -->
    <div class="section-stack" style="margin-top: 0.75rem">
      <div class="section-card">
        <div class="section-header">
          <span class="section-title">Thông tin tin tuyển dụng</span>
        </div>
        <div class="info-grid">
          <div class="info-row">
            <span class="info-label">Vị trí</span>
            <span class="info-value">{{ posting.job_position_name }}</span>
          </div>
          <div class="info-row">
            <span class="info-label">Phòng ban</span>
            <span class="info-value">{{ posting.department_name }}</span>
          </div>
          <div class="info-row">
            <span class="info-label">Hạn nộp hồ sơ</span>
            <span class="info-value" :class="deadlineClass(posting.deadline)">
              {{ posting.deadline ? formatDate(posting.deadline) : '—' }}
            </span>
          </div>
          <div class="info-row">
            <span class="info-label">Mức lương</span>
            <span class="info-value">{{ posting.salary_display ?? 'Thỏa thuận' }}</span>
          </div>
          <div class="info-row" v-if="posting.work_location">
            <span class="info-label">Địa điểm</span>
            <span class="info-value">{{ posting.work_location }}</span>
          </div>
          <div class="info-row">
            <span class="info-label">Ứng viên đã ứng tuyển</span>
            <span class="info-value">{{ posting.candidate_count }}</span>
          </div>
          <div class="info-row" v-if="posting.channels.length">
            <span class="info-label">Kênh đăng</span>
            <span class="info-value">{{ posting.channels.map(c => c.name).join(', ') }}</span>
          </div>
          <div class="info-row" v-if="posting.opened_at">
            <span class="info-label">Đăng lúc</span>
            <span class="info-value">{{ formatDatetime(posting.opened_at) }}</span>
          </div>
          <div class="info-row" v-if="posting.closed_at">
            <span class="info-label">Đóng lúc</span>
            <span class="info-value">{{ formatDatetime(posting.closed_at) }}</span>
          </div>
        </div>
      </div>

      <!-- JD preview -->
      <div class="section-card">
        <div class="section-header">
          <span class="section-title">Mô tả công việc</span>
        </div>
        <div v-if="posting.description" class="rc-jd-block">{{ posting.description }}</div>
        <div v-else class="rc-jd-empty">—</div>

        <template v-if="posting.requirements">
          <div class="section-header" style="margin-top: 1.25rem">
            <span class="section-title">Yêu cầu ứng viên</span>
          </div>
          <div class="rc-jd-block">{{ posting.requirements }}</div>
        </template>

        <template v-if="posting.benefits">
          <div class="section-header" style="margin-top: 1.25rem">
            <span class="section-title">Phúc lợi</span>
          </div>
          <div class="rc-jd-block">{{ posting.benefits }}</div>
        </template>
      </div>

      <div class="section-card" v-if="posting.note">
        <div class="section-header"><span class="section-title">Ghi chú nội bộ</span></div>
        <div style="white-space: pre-wrap; font-size: 0.875rem">{{ posting.note }}</div>
      </div>
    </div>

    <!-- Edit dialog -->
    <JobPostingFormDialog
      v-model:visible="showEditDialog"
      :editing="posting"
      @saved="onSaved"
    />
  </div>

  <div v-else-if="pageLoading" class="loading-state">
    <i class="pi pi-spin pi-spinner" /><span>Đang tải...</span>
  </div>
  <div v-else class="error-state">
    <i class="pi pi-exclamation-triangle" /><span>Không tìm thấy tin tuyển dụng</span>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import Button from 'primevue/button'
import Tag from 'primevue/tag'
import { useConfirm } from 'primevue/useconfirm'
import { useToast } from 'primevue/usetoast'
import { formatDatetime } from '@/utils/format'

import recruitmentService, { type JobPostingRead } from '@/services/recruitmentService'
import JobPostingFormDialog from './components/JobPostingFormDialog.vue'

const route   = useRoute()
const confirm = useConfirm()
const toast   = useToast()

const posting     = ref<JobPostingRead | null>(null)
const pageLoading = ref(true)
const showEditDialog = ref(false)

const postingId = computed(() => Number(route.params.id))

function statusSeverity(st: string) {
  const map: Record<string, string> = { draft: 'secondary', active: 'success', closed: 'warn', expired: 'danger' }
  return map[st] ?? 'secondary'
}
function formatDate(d: string) { return new Date(d).toLocaleDateString('vi-VN') }

function deadlineClass(d: string | null) {
  if (!d) return ''
  const diff = (new Date(d).getTime() - Date.now()) / 86400000
  return diff < 0 ? 'rc-deadline-past' : diff < 7 ? 'rc-deadline-near' : ''
}

async function load() {
  pageLoading.value = true
  try {
    const res = await recruitmentService.getPosting(postingId.value)
    posting.value = res.data
  } catch { posting.value = null } finally { pageLoading.value = false }
}

function openEdit() { showEditDialog.value = true }
async function onSaved() { showEditDialog.value = false; await load() }

function confirmPublish() {
  confirm.require({
    message: `Đăng tin "${posting.value?.title}"?`,
    header: 'Xác nhận đăng tin',
    icon: 'pi pi-send',
    acceptLabel: 'Đăng',
    rejectLabel: 'Hủy',
    accept: async () => {
      try {
        await recruitmentService.publishPosting(postingId.value)
        await load()
        toast.add({ severity: 'success', summary: 'Đã đăng tin', life: 3000 })
      } catch { toast.add({ severity: 'error', summary: 'Lỗi', detail: 'Không thể đăng tin', life: 4000 }) }
    },
  })
}

function confirmClose() {
  confirm.require({
    message: `Đóng tin "${posting.value?.title}"?`,
    header: 'Xác nhận đóng tin',
    icon: 'pi pi-times-circle',
    acceptLabel: 'Đóng',
    rejectLabel: 'Hủy',
    accept: async () => {
      try {
        await recruitmentService.closePosting(postingId.value)
        await load()
        toast.add({ severity: 'warn', summary: 'Đã đóng tin', life: 3000 })
      } catch { toast.add({ severity: 'error', summary: 'Lỗi', detail: 'Không thể đóng tin', life: 4000 }) }
    },
  })
}

function confirmReopen() {
  confirm.require({
    message: `Mở lại tin "${posting.value?.title}"?`,
    header: 'Xác nhận mở lại',
    icon: 'pi pi-refresh',
    acceptLabel: 'Mở lại',
    rejectLabel: 'Hủy',
    accept: async () => {
      try {
        await recruitmentService.reopenPosting(postingId.value)
        await load()
        toast.add({ severity: 'success', summary: 'Đã mở lại tin', life: 3000 })
      } catch (err: unknown) {
        const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
        toast.add({ severity: 'error', summary: 'Lỗi', detail: typeof detail === 'string' ? detail : 'Không thể mở lại', life: 4000 })
      }
    },
  })
}

onMounted(load)
</script>
