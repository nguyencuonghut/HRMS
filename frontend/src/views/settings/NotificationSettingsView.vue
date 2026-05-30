<template>
  <div>
    <div class="page-header">
      <div>
        <h2>Cài đặt thông báo</h2>
        <div class="subtitle">Quản lý mẫu email và lịch gửi thông báo tự động.</div>
      </div>
    </div>
    <Toast />

    <Tabs v-model:value="activeTab">
      <TabList>
        <Tab value="templates">Mẫu email</Tab>
        <Tab value="config">Cấu hình sự kiện</Tab>
        <Tab value="logs">Lịch sử gửi</Tab>
      </TabList>
      <TabPanels>

        <!-- Tab Mẫu email -->
        <TabPanel value="templates">
          <div v-if="templatesLoading" class="notif-loading">Đang tải...</div>
          <div v-else class="notif-template-list">
            <div
              v-for="tpl in templates"
              :key="tpl.code"
              class="card notif-template-card"
              @click="openEdit(tpl)"
            >
              <div class="notif-template-header">
                <div>
                  <div class="notif-template-name">{{ tpl.name }}</div>
                  <div class="notif-template-subject">{{ tpl.subject }}</div>
                </div>
                <div class="notif-template-meta">
                  <Tag :value="tpl.is_active ? 'Đang bật' : 'Tắt'" :severity="tpl.is_active ? 'success' : 'secondary'" rounded />
                  <Tag v-if="tpl.days_before" :value="`${tpl.days_before} ngày`" severity="info" rounded />
                </div>
              </div>
              <div class="notif-template-fields">
                <span class="notif-field-label">Biến thay thế:</span>
                <code v-for="f in tpl.merge_fields" :key="f" class="notif-field-chip">{{ wrapField(f) }}</code>
              </div>
            </div>
          </div>
        </TabPanel>

        <!-- Tab Cấu hình -->
        <TabPanel value="config">
          <div class="card">
            <DataTable :value="configs" :loading="configLoading" striped-rows>
              <Column header="Sự kiện" style="width: 220px">
                <template #body="{ data }">{{ eventTypeLabel(data.event_type) }}</template>
              </Column>
              <Column header="Bật/Tắt" style="width: 120px">
                <template #body="{ data }">
                  <ToggleButton
                    v-model="data.is_enabled"
                    on-label="Bật" off-label="Tắt"
                    on-icon="pi pi-check" off-icon="pi pi-times"
                    @change="saveConfig(data)"
                  />
                </template>
              </Column>
              <Column header="Ngưỡng cảnh báo (ngày)">
                <template #body="{ data }">
                  <div class="notif-days-chips">
                    <Tag v-for="d in (data.days_before ?? [])" :key="d" :value="`${d} ngày`" severity="secondary" rounded />
                    <span v-if="!data.days_before?.length" class="notif-muted">—</span>
                  </div>
                </template>
              </Column>
            </DataTable>
          </div>
        </TabPanel>

        <!-- Tab Lịch sử -->
        <TabPanel value="logs">
          <div class="card notif-log-card">
            <div class="notif-log-filters">
              <Select
                v-model="logFilter.event_type"
                :options="eventTypeOptions"
                option-label="label"
                option-value="value"
                placeholder="Tất cả sự kiện"
                show-clear
              />
              <Select
                v-model="logFilter.status"
                :options="statusOptions"
                option-label="label"
                option-value="value"
                placeholder="Tất cả trạng thái"
                show-clear
              />
              <Button label="Tìm kiếm" icon="pi pi-search" @click="loadLogs" />
            </div>

            <DataTable
              :value="logs.items"
              :loading="logLoading"
              striped-rows
              paginator
              :rows="20"
              :total-records="logs.total"
              lazy
              @page="onLogPage"
            >
              <template #empty><div class="notif-empty">Chưa có lịch sử gửi email.</div></template>
              <Column field="event_type" header="Sự kiện" style="width: 160px" />
              <Column field="recipient_email" header="Người nhận" />
              <Column field="subject" header="Tiêu đề" />
              <Column header="Trạng thái" style="width: 110px">
                <template #body="{ data }">
                  <Tag :value="data.status" :severity="logStatusSeverity(data.status)" rounded />
                </template>
              </Column>
              <Column header="Thời gian" style="width: 160px">
                <template #body="{ data }">{{ formatDatetime(data.sent_at) }}</template>
              </Column>
            </DataTable>
          </div>
        </TabPanel>
      </TabPanels>
    </Tabs>

    <!-- Dialog chỉnh sửa template -->
    <Dialog
      v-model:visible="editVisible"
      :header="editTpl?.name ?? 'Chỉnh sửa mẫu'"
      modal
      :style="{ width: '680px' }"
    >
      <div v-if="editTpl" class="notif-edit-form">
        <div class="notif-edit-field">
          <label>Tiêu đề email</label>
          <InputText v-model="editForm.subject" class="notif-full-width" />
        </div>
        <div class="notif-edit-field">
          <label>Nội dung HTML</label>
          <Textarea v-model="editForm.body_html" rows="10" auto-resize class="notif-full-width notif-body-textarea" />
        </div>
        <div class="notif-edit-field notif-active-toggle">
          <label>Trạng thái</label>
          <ToggleButton v-model="editForm.is_active" on-label="Đang bật" off-label="Tắt" on-icon="pi pi-check" off-icon="pi pi-times" />
        </div>

        <!-- Preview -->
        <div v-if="previewHtml" class="notif-preview-box">
          <div class="notif-preview-label">Xem trước:</div>
          <div class="notif-preview-content" v-html="sanitizeHtml(previewHtml)" />
        </div>
      </div>

      <template #footer>
        <Button label="Xem trước" icon="pi pi-eye" severity="secondary" outlined :loading="previewing" @click="doPreview" />
        <Button label="Gửi test" icon="pi pi-send" severity="secondary" outlined @click="openTestSend" />
        <Button label="Lưu" icon="pi pi-check" :loading="saving" @click="doSave" />
      </template>
    </Dialog>

    <!-- Dialog test send -->
    <Dialog v-model:visible="testSendVisible" header="Gửi email thử" modal :style="{ width: '400px' }">
      <div class="notif-edit-field">
        <label>Email nhận</label>
        <InputText v-model="testSendEmail" class="notif-full-width" placeholder="your@email.com" />
      </div>
      <template #footer>
        <Button label="Hủy" text @click="testSendVisible = false" />
        <Button label="Gửi" icon="pi pi-send" :loading="testSending" @click="doTestSend" />
      </template>
    </Dialog>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { useSanitize } from '@/composables/useSanitize'
import Button from 'primevue/button'
import Column from 'primevue/column'
import DataTable from 'primevue/datatable'
import Dialog from 'primevue/dialog'
import InputText from 'primevue/inputtext'
import Select from 'primevue/select'
import Tab from 'primevue/tab'
import TabList from 'primevue/tablist'
import TabPanel from 'primevue/tabpanel'
import TabPanels from 'primevue/tabpanels'
import Tabs from 'primevue/tabs'
import Tag from 'primevue/tag'
import Textarea from 'primevue/textarea'
import ToggleButton from 'primevue/togglebutton'
import Toast from 'primevue/toast'
import { useToast } from 'primevue/usetoast'

import notificationService, { type NotifConfig, type NotifTemplate, type EmailLogListResponse } from '@/services/notificationService'

const toast = useToast()
const { sanitizeHtml } = useSanitize()
const activeTab = ref('templates')

// Templates
const templates = ref<NotifTemplate[]>([])
const templatesLoading = ref(false)

// Edit dialog
const editVisible = ref(false)
const editTpl = ref<NotifTemplate | null>(null)
const editForm = reactive({ subject: '', body_html: '', is_active: true })
const saving = ref(false)
const previewing = ref(false)
const previewHtml = ref('')

// Test send
const testSendVisible = ref(false)
const testSendEmail = ref('')
const testSending = ref(false)

// Config
const configs = ref<NotifConfig[]>([])
const configLoading = ref(false)

// Logs
const logs = ref<EmailLogListResponse>({ items: [], total: 0, page: 1, page_size: 20, total_pages: 0 })
const logLoading = ref(false)
const logFilter = reactive<{ event_type: string | null; status: string | null }>({ event_type: null, status: null })
const logPage = ref(1)

const eventTypeOptions = [
  { label: 'Hợp đồng hết hạn', value: 'contract_expiry' },
  { label: 'Thử việc kết thúc', value: 'probation_end' },
  { label: 'Sinh nhật', value: 'birthday' },
  { label: 'Chứng chỉ hết hạn', value: 'certificate_expiry' },
  { label: 'Tồn phép hết hạn', value: 'carryover_expiry' },
]

const statusOptions = [
  { label: 'Đã gửi', value: 'sent' },
  { label: 'Thất bại', value: 'failed' },
  { label: 'Bỏ qua', value: 'skipped' },
]

function logStatusSeverity(status: string) {
  if (status === 'sent') return 'success'
  if (status === 'failed') return 'danger'
  return 'warn'
}

const EVENT_TYPE_LABELS: Record<string, string> = {
  contract_expiry: 'Hợp đồng sắp hết hạn',
  probation_end: 'Thử việc sắp kết thúc',
  birthday: 'Sinh nhật nhân viên',
  certificate_expiry: 'Chứng chỉ sắp hết hạn',
  carryover_expiry: 'Tồn phép sắp hết hạn',
}

function eventTypeLabel(code: string) {
  return EVENT_TYPE_LABELS[code] ?? code
}

function wrapField(f: string) {
  return '{{' + f + '}}'
}

function formatDatetime(value: string) {
  return new Intl.DateTimeFormat('vi-VN', { dateStyle: 'short', timeStyle: 'short' }).format(new Date(value))
}

async function loadTemplates() {
  templatesLoading.value = true
  try {
    const res = await notificationService.getTemplates()
    templates.value = res.data
  } catch {
    toast.add({ severity: 'error', summary: 'Không tải được mẫu email', life: 3000 })
  } finally {
    templatesLoading.value = false
  }
}

function openEdit(tpl: NotifTemplate) {
  editTpl.value = tpl
  editForm.subject = tpl.subject
  editForm.body_html = tpl.body_html
  editForm.is_active = tpl.is_active
  previewHtml.value = ''
  editVisible.value = true
}

async function doSave() {
  if (!editTpl.value) return
  saving.value = true
  try {
    const res = await notificationService.updateTemplate(editTpl.value.code, {
      subject: editForm.subject,
      body_html: editForm.body_html,
      is_active: editForm.is_active,
    })
    const idx = templates.value.findIndex(t => t.code === editTpl.value!.code)
    if (idx >= 0) templates.value[idx] = res.data
    toast.add({ severity: 'success', summary: 'Đã lưu mẫu email', life: 3000 })
    editVisible.value = false
  } catch {
    toast.add({ severity: 'error', summary: 'Lưu thất bại', life: 3000 })
  } finally {
    saving.value = false
  }
}

async function doPreview() {
  if (!editTpl.value) return
  previewing.value = true
  try {
    const res = await notificationService.previewTemplate(editTpl.value.code)
    previewHtml.value = res.data.html
  } catch {
    toast.add({ severity: 'error', summary: 'Xem trước thất bại', life: 3000 })
  } finally {
    previewing.value = false
  }
}

function openTestSend() {
  testSendEmail.value = ''
  testSendVisible.value = true
}

async function doTestSend() {
  if (!editTpl.value || !testSendEmail.value) return
  testSending.value = true
  try {
    const res = await notificationService.testSend(editTpl.value.code, testSendEmail.value)
    toast.add({
      severity: res.data.sent ? 'success' : 'warn',
      summary: res.data.sent ? 'Email đã gửi' : 'Không thể gửi (SMTP chưa cấu hình)',
      life: 4000,
    })
    testSendVisible.value = false
  } catch {
    toast.add({ severity: 'error', summary: 'Gửi thất bại', life: 3000 })
  } finally {
    testSending.value = false
  }
}

async function loadConfig() {
  configLoading.value = true
  try {
    const res = await notificationService.getConfig()
    configs.value = res.data
  } catch {
    toast.add({ severity: 'error', summary: 'Không tải được cấu hình', life: 3000 })
  } finally {
    configLoading.value = false
  }
}

async function saveConfig(cfg: NotifConfig) {
  try {
    await notificationService.updateConfig(cfg.event_type, { is_enabled: cfg.is_enabled })
    toast.add({ severity: 'success', summary: 'Đã cập nhật cấu hình', life: 2000 })
  } catch {
    toast.add({ severity: 'error', summary: 'Cập nhật thất bại', life: 3000 })
  }
}

async function loadLogs() {
  logLoading.value = true
  try {
    const params: Record<string, unknown> = { page: logPage.value, page_size: 20 }
    if (logFilter.event_type) params.event_type = logFilter.event_type
    if (logFilter.status) params.status = logFilter.status
    const res = await notificationService.getLogs(params as Parameters<typeof notificationService.getLogs>[0])
    logs.value = res.data
  } catch {
    toast.add({ severity: 'error', summary: 'Không tải được lịch sử', life: 3000 })
  } finally {
    logLoading.value = false
  }
}

function onLogPage(event: { page: number }) {
  logPage.value = event.page + 1
  loadLogs()
}

onMounted(() => {
  loadTemplates()
  loadConfig()
  loadLogs()
})
</script>

<style>
.notif-template-list {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  padding-top: 0.5rem;
}

.notif-template-card {
  padding: 1rem 1.25rem;
  border: 1px solid var(--l-border);
  background: var(--l-surface);
  cursor: pointer;
  transition: border-color 0.15s;
}

.notif-template-card:hover {
  border-color: var(--p-primary-color);
}

.notif-template-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 1rem;
  flex-wrap: wrap;
}

.notif-template-name {
  font-weight: 600;
  font-size: 0.95rem;
}

.notif-template-subject {
  font-size: 0.82rem;
  color: var(--l-text-muted);
  margin-top: 0.2rem;
}

.notif-template-meta {
  display: flex;
  gap: 0.4rem;
  flex-wrap: wrap;
}

.notif-template-fields {
  margin-top: 0.6rem;
  display: flex;
  align-items: center;
  gap: 0.4rem;
  flex-wrap: wrap;
}

.notif-field-label {
  font-size: 0.78rem;
  color: var(--l-text-muted);
}

.notif-field-chip {
  font-size: 0.75rem;
  background: color-mix(in srgb, var(--p-primary-color) 18%, transparent);
  border: 1px solid color-mix(in srgb, var(--p-primary-color) 50%, transparent);
  border-radius: 4px;
  padding: 0.15rem 0.5rem;
  color: var(--l-text);
  font-family: monospace;
}

.notif-log-card {
  padding: 1rem 1.25rem;
  border: 1px solid var(--l-border);
  background: var(--l-surface);
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.notif-log-filters {
  display: flex;
  gap: 0.75rem;
  flex-wrap: wrap;
  align-items: flex-end;
}

.notif-days-chips {
  display: flex;
  gap: 0.3rem;
  flex-wrap: wrap;
}

.notif-muted {
  color: var(--l-text-muted);
  font-size: 0.85rem;
}

.notif-loading, .notif-empty {
  padding: 2rem;
  text-align: center;
  color: var(--l-text-muted);
}

.notif-edit-form {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.notif-edit-field {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
}

.notif-edit-field label {
  font-size: 0.82rem;
  font-weight: 600;
  color: var(--l-text-muted);
}

.notif-full-width {
  width: 100%;
}

.notif-body-textarea {
  font-family: monospace;
  font-size: 0.82rem;
}

.notif-active-toggle {
  flex-direction: row;
  align-items: center;
  gap: 0.75rem;
}

.notif-preview-box {
  border: 1px solid var(--l-border);
  border-radius: 0.5rem;
  overflow: hidden;
}

.notif-preview-label {
  padding: 0.4rem 0.75rem;
  font-size: 0.78rem;
  font-weight: 600;
  background: var(--l-surface-raised, #f3f4f6);
  border-bottom: 1px solid var(--l-border);
  color: var(--l-text-muted);
}

.notif-preview-content {
  padding: 1rem;
  font-size: 0.88rem;
  line-height: 1.6;
}
</style>
