<template>
  <div class="section-stack" style="padding-top: 0.75rem">
    <div class="section-card">
      <div class="section-header">
        <span class="section-title">Lịch sử giao tiếp</span>
        <Button
          label="Gửi email"
          icon="pi pi-send"
          size="small"
          @click="showSendDialog = true"
        />
      </div>

      <div v-if="loading" class="rc-jd-empty">Đang tải...</div>
      <div v-else-if="!items.length" class="rc-jd-empty">Chưa có lịch sử giao tiếp.</div>

      <div v-else class="comm-timeline">
        <div
          v-for="item in items"
          :key="item.id"
          class="comm-item"
          :class="{ 'comm-item--expanded': expandedId === item.id }"
        >
          <div class="comm-item-header" @click="toggle(item)">
            <div class="comm-item-left">
              <i class="pi pi-envelope comm-icon" />
              <div>
                <div class="comm-subject">{{ item.subject ?? '(Không có tiêu đề)' }}</div>
                <div class="comm-meta">
                  <Tag :value="statusLabel(item.status)" :severity="statusSeverity(item.status)" style="font-size: 0.72rem" />
                  <span class="rc-muted" style="font-size: 0.78rem">
                    {{ item.sent_by_name ? `Gửi bởi ${item.sent_by_name}` : 'Tự động' }}
                  </span>
                  <span v-if="item.sent_at" class="rc-muted" style="font-size: 0.78rem">
                    · {{ formatDatetime(item.sent_at) }}
                  </span>
                  <span v-else class="rc-muted" style="font-size: 0.78rem">
                    · {{ formatDatetime(item.created_at) }}
                  </span>
                  <Button
                    v-if="item.status === 'failed'"
                    icon="pi pi-info-circle"
                    text
                    rounded
                    size="small"
                    severity="danger"
                    style="width: 1.4rem; height: 1.4rem; padding: 0"
                    v-tooltip.top="'Xem lý do lỗi'"
                    @click.stop="showError(item)"
                  />
                </div>
              </div>
            </div>
            <i :class="expandedId === item.id ? 'pi pi-chevron-up' : 'pi pi-chevron-down'" style="color: var(--p-surface-400)" />
          </div>
          <div v-if="expandedId === item.id && item.body_html" class="comm-body">
            <!-- eslint-disable-next-line vue/no-v-html -->
            <div class="comm-html-preview" v-html="item.body_html" />
          </div>
        </div>
      </div>
    </div>
  </div>

  <SendEmailDialog
    v-model:visible="showSendDialog"
    :candidate-id="candidateId"
    @sent="onSent"
  />

  <!-- Error detail dialog -->
  <Dialog
    v-model:visible="showErrorDialog"
    header="Chi tiết lỗi gửi email"
    modal
    :style="{ width: '480px' }"
  >
    <div v-if="errorItem" style="display: flex; flex-direction: column; gap: 0.75rem; margin-top: 0.25rem">
      <div style="display: flex; align-items: flex-start; gap: 0.6rem; padding: 0.75rem; border-radius: 6px; background: color-mix(in srgb, var(--p-red-500) 8%, var(--l-bg))">
        <i class="pi pi-exclamation-triangle" style="color: var(--p-red-500); margin-top: 0.15rem; flex-shrink: 0" />
        <span style="font-size: 0.9rem; line-height: 1.5">{{ errorItem.error_friendly }}</span>
      </div>
      <div v-if="showRawError" style="font-size: 0.78rem; color: var(--l-text-muted); font-family: monospace; white-space: pre-wrap; background: var(--l-surface); padding: 0.6rem; border-radius: 4px; border: 1px solid var(--l-border)">{{ errorItem.error_message }}</div>
      <Button
        :label="showRawError ? 'Ẩn chi tiết kỹ thuật' : 'Xem chi tiết kỹ thuật'"
        text
        size="small"
        severity="secondary"
        style="align-self: flex-start; padding: 0"
        @click="showRawError = !showRawError"
      />
    </div>
    <template #footer>
      <Button label="Đóng" severity="secondary" outlined @click="showErrorDialog = false" />
    </template>
  </Dialog>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import Button from 'primevue/button'
import Dialog from 'primevue/dialog'
import Tag from 'primevue/tag'
import { communicationService, type CommunicationRead } from '@/services/recruitmentService'
import SendEmailDialog from './SendEmailDialog.vue'
import { formatDatetime } from '@/utils/format'

const props = defineProps<{ candidateId: number }>()

const items = ref<CommunicationRead[]>([])
const loading = ref(false)
const expandedId = ref<number | null>(null)
const showSendDialog = ref(false)

const showErrorDialog = ref(false)
const errorItem = ref<CommunicationRead | null>(null)
const showRawError = ref(false)

function showError(item: CommunicationRead) {
  errorItem.value = item
  showRawError.value = false
  showErrorDialog.value = true
}

function toggle(item: CommunicationRead) {
  expandedId.value = expandedId.value === item.id ? null : item.id
}

function statusLabel(status: string) {
  const map: Record<string, string> = {
    pending: 'Chờ',
    sent: 'Đã gửi',
    failed: 'Lỗi',
    bounced: 'Trả lại',
  }
  return map[status] ?? status
}

function statusSeverity(status: string) {
  const map: Record<string, string> = {
    pending: 'warn',
    sent: 'success',
    failed: 'danger',
    bounced: 'danger',
  }
  return map[status] ?? 'secondary'
}


async function load() {
  loading.value = true
  try {
    items.value = await communicationService.listForCandidate(props.candidateId)
  } catch {
    items.value = []
  } finally {
    loading.value = false
  }
}

async function onSent() {
  showSendDialog.value = false
  await load()
}

onMounted(load)
</script>
