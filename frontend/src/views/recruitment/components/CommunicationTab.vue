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
                  <span v-if="item.trigger_event" class="rc-muted" style="font-size: 0.78rem">
                    · trigger: {{ item.trigger_event }}
                  </span>
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
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import Button from 'primevue/button'
import Tag from 'primevue/tag'
import { communicationService, type CommunicationRead } from '@/services/recruitmentService'
import SendEmailDialog from './SendEmailDialog.vue'

const props = defineProps<{ candidateId: number }>()

const items = ref<CommunicationRead[]>([])
const loading = ref(false)
const expandedId = ref<number | null>(null)
const showSendDialog = ref(false)

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

function formatDatetime(d: string) {
  return new Date(d).toLocaleString('vi-VN', { dateStyle: 'short', timeStyle: 'short' })
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
