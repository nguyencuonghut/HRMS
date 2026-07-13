<template>
  <div class="backup-center">
    <div class="page-header">
      <div>
        <h2>Sao lưu & khôi phục</h2>
        <span class="subtitle">Theo dõi cấu hình sao lưu cơ sở dữ liệu và tệp tải lên trên MinIO.</span>
      </div>
      <Button
        icon="pi pi-refresh"
        severity="secondary"
        outlined
        :loading="loading"
        v-tooltip.bottom="'Làm mới'"
        aria-label="Làm mới"
        @click="() => loadOverview()"
      />
    </div>

    <div v-if="loading && !overview" class="backup-loading">
      <ProgressSpinner style="width: 42px; height: 42px" />
      <span>Đang tải dữ liệu sao lưu...</span>
    </div>

    <div v-else-if="error" class="backup-error">
      <i class="pi pi-exclamation-triangle" />
      <span>{{ error }}</span>
      <Button label="Thử lại" icon="pi pi-refresh" size="small" @click="() => loadOverview()" />
    </div>

    <template v-else-if="overview">
      <section class="backup-summary-grid" aria-label="Tổng quan sao lưu">
        <div class="backup-summary-item">
          <span class="summary-label">Tổng cấu hình</span>
          <strong data-testid="backup-config-count">{{ overview.config_count }}</strong>
        </div>
        <div class="backup-summary-item">
          <span class="summary-label">Đang bật</span>
          <strong>{{ enabledCount }}</strong>
        </div>
        <div class="backup-summary-item">
          <span class="summary-label">Đích đã cấu hình</span>
          <strong>{{ targetConfiguredCount }}/{{ overview.config_count }}</strong>
        </div>
        <div class="backup-summary-item">
          <span class="summary-label">Tác vụ gần nhất</span>
          <strong>{{ latestJobStatus }}</strong>
        </div>
      </section>

      <section class="backup-section">
        <div class="backup-section-header">
          <div>
            <h3>Cấu hình sao lưu</h3>
            <span>Thông tin đọc từ cấu hình hệ thống; thông tin bí mật được giữ trong biến môi trường máy chủ.</span>
          </div>
        </div>

        <div class="card" data-testid="backup-config-table">
          <DataTable
            :value="overview.configs"
            :loading="loading"
            striped-rows
            responsive-layout="scroll"
          >
            <template #empty>
              <div class="empty-state">
                <i class="pi pi-database" />
                <span>Chưa có cấu hình sao lưu.</span>
              </div>
            </template>

            <Column header="Loại dữ liệu" style="min-width: 210px">
              <template #body="{ data }">
                <div class="backup-kind-cell">
                  <i :class="['pi', data.kind === 'db' ? 'pi-database' : 'pi-folder-open']" />
                  <div>
                    <div class="strong-text">{{ data.kind_label }}</div>
                    <div class="muted-text">{{ kindCodeLabel(data.kind) }}</div>
                  </div>
                </div>
              </template>
            </Column>

            <Column header="Lịch chạy" style="min-width: 160px">
              <template #body="{ data }">
                <div class="cron-cell">
                  <code class="backup-code">{{ data.cron_expression }}</code>
                  <span class="muted-text">{{ cronDescription(data.cron_expression) }}</span>
                </div>
                <div class="muted-text">Giữ {{ data.retention_days }} ngày</div>
              </template>
            </Column>

            <Column header="Nguồn" style="min-width: 220px">
              <template #body="{ data }">
                <div>{{ sourceName(data) }}</div>
                <div class="muted-text">{{ sourceLocation(data) }}</div>
              </template>
            </Column>

            <Column header="Đích sao lưu" style="min-width: 220px">
              <template #body="{ data }">
                <div>{{ data.target_bucket }}</div>
                <div class="muted-text">
                  {{ data.target_prefix || '—' }}
                  <span v-if="data.target_endpoint"> · {{ data.target_endpoint }}</span>
                </div>
              </template>
            </Column>

            <Column header="Trạng thái" style="min-width: 190px">
              <template #body="{ data }">
                <div class="backup-tag-stack">
                  <Tag :value="data.enabled ? 'Đang bật' : 'Tắt'" :severity="data.enabled ? 'success' : 'secondary'" rounded />
                  <Tag
                    :value="data.source_configured ? 'Nguồn đã sẵn sàng' : 'Thiếu nguồn'"
                    :severity="data.source_configured ? 'success' : 'warn'"
                    rounded
                  />
                  <Tag
                    :value="data.target_configured ? 'Đích đã sẵn sàng' : 'Thiếu đích'"
                    :severity="data.target_configured ? 'success' : 'warn'"
                    rounded
                  />
                </div>
                <div class="muted-text">Nguồn thông tin bí mật: {{ secretSourceLabel(data.secret_source) }}</div>
              </template>
            </Column>

            <Column header="Lần kiểm tra gần nhất" style="min-width: 180px">
              <template #body="{ data }">
                <span>{{ data.last_validated_at ? formatDatetime(data.last_validated_at) : 'Chưa kiểm tra' }}</span>
                <div v-if="data.last_validation_status" class="backup-validation-state">
                  <Tag
                    :value="validationStatusLabel(data.last_validation_status)"
                    :severity="validationStatusSeverity(data.last_validation_status)"
                    rounded
                  />
                </div>
                <div v-if="data.last_validation_error" class="muted-text">
                  {{ data.last_validation_error }}
                </div>
              </template>
            </Column>

            <Column header="" style="width: 140px">
              <template #body="{ data }">
                <div class="backup-actions">
                  <Button
                    v-can:create="'backups'"
                    icon="pi pi-play"
                    severity="success"
                    text
                    rounded
                    size="small"
                    :loading="creatingJobKind === data.kind"
                    :aria-label="`Chạy sao lưu ${data.kind_label}`"
                    v-tooltip.top="'Chạy sao lưu ngay'"
                    @click="createManualBackup(data)"
                  />
                  <Button
                    v-can:edit="'backups'"
                    icon="pi pi-pencil"
                    severity="secondary"
                    text
                    rounded
                    size="small"
                    :aria-label="`Sửa cấu hình ${data.kind_label}`"
                    v-tooltip.top="'Sửa cấu hình'"
                    @click="openEditDialog(data)"
                  />
                  <Button
                    v-can:edit="'backups'"
                    icon="pi pi-check-circle"
                    severity="info"
                    text
                    rounded
                    size="small"
                    :loading="validatingKind === data.kind"
                    :aria-label="`Kiểm tra đích sao lưu ${data.kind_label}`"
                    v-tooltip.top="'Kiểm tra đích sao lưu'"
                    @click="validateTarget(data)"
                  />
                </div>
              </template>
            </Column>
          </DataTable>
        </div>
      </section>

      <section class="backup-history-grid">
        <div class="backup-section">
          <div class="backup-section-header">
            <div>
              <h3>Lịch sao lưu gần nhất</h3>
              <span>Tối đa 5 tác vụ mới nhất từ máy chủ.</span>
            </div>
          </div>
          <div class="card">
            <DataTable :value="overview.latest_jobs" size="small" responsive-layout="scroll">
              <template #empty>
                <div class="empty-state compact-empty">
                  <i class="pi pi-clock" />
                  <span>Chưa có tác vụ sao lưu nào.</span>
                </div>
              </template>
              <Column header="Loại" style="width: 140px">
                <template #body="{ data }">{{ kindLabel(data.kind) }}</template>
              </Column>
              <Column header="Kiểu chạy" style="width: 120px">
                <template #body="{ data }">{{ triggerLabel(data.trigger) }}</template>
              </Column>
              <Column header="Trạng thái" style="width: 130px">
                <template #body="{ data }">
                  <Tag :value="statusLabel(data.status)" :severity="statusSeverity(data.status)" rounded />
                </template>
              </Column>
              <Column header="Tệp kết quả">
                <template #body="{ data }">
                  <span>{{ data.artifact_key || '—' }}</span>
                  <div v-if="data.artifact_bucket" class="muted-text">{{ data.artifact_bucket }}</div>
                </template>
              </Column>
              <Column header="Thời gian" style="width: 170px">
                <template #body="{ data }">{{ formatDatetime(data.created_at) }}</template>
              </Column>
            </DataTable>
          </div>
        </div>

        <div class="backup-section">
          <div class="backup-section-header">
            <div>
              <h3>Yêu cầu khôi phục gần nhất</h3>
              <span>Tối đa 5 yêu cầu mới nhất từ máy chủ.</span>
            </div>
          </div>
          <div class="card">
            <DataTable :value="overview.latest_restore_requests" size="small" responsive-layout="scroll">
              <template #empty>
                <div class="empty-state compact-empty">
                  <i class="pi pi-history" />
                  <span>Chưa có yêu cầu khôi phục nào.</span>
                </div>
              </template>
              <Column header="Loại" style="width: 140px">
                <template #body="{ data }">{{ kindLabel(data.kind) }}</template>
              </Column>
              <Column header="Chế độ" style="width: 150px">
                <template #body="{ data }">{{ restoreModeLabel(data.mode) }}</template>
              </Column>
              <Column header="Trạng thái" style="width: 130px">
                <template #body="{ data }">
                  <Tag :value="restoreStatusLabel(data.status)" :severity="restoreStatusSeverity(data.status)" rounded />
                </template>
              </Column>
              <Column header="Đích">
                <template #body="{ data }">{{ data.target_db_name || data.target_bucket || '—' }}</template>
              </Column>
              <Column header="Thời gian" style="width: 170px">
                <template #body="{ data }">{{ formatDatetime(data.created_at) }}</template>
              </Column>
            </DataTable>
          </div>
        </div>
      </section>
    </template>

    <Dialog
      v-model:visible="editDialogVisible"
      modal
      :header="editDialogTitle"
      :style="{ width: '720px', maxWidth: '94vw' }"
      :closable="!savingConfig"
    >
      <form class="backup-config-form" @submit.prevent="saveConfig">
        <div class="backup-form-grid">
          <div class="backup-field backup-toggle-field">
            <label for="backup-enabled">Kích hoạt</label>
            <ToggleSwitch input-id="backup-enabled" v-model="configForm.enabled" />
          </div>

          <div class="backup-field">
            <label for="backup-cron">Lịch chạy</label>
            <InputText id="backup-cron" v-model.trim="configForm.cron_expression" class="w-full" />
            <small>{{ cronDescription(configForm.cron_expression) }}</small>
          </div>

          <div class="backup-field">
            <label for="backup-retention">Số ngày giữ</label>
            <InputNumber
              input-id="backup-retention"
              v-model="configForm.retention_days"
              class="w-full"
              :min="1"
              :max="3650"
              :use-grouping="false"
            />
          </div>

          <div class="backup-field">
            <label for="backup-target-endpoint">Địa chỉ kết nối đích</label>
            <InputText id="backup-target-endpoint" v-model.trim="configForm.target_endpoint" class="w-full" />
          </div>

          <div class="backup-field">
            <label for="backup-target-bucket">Kho lưu trữ đích</label>
            <InputText id="backup-target-bucket" v-model.trim="configForm.target_bucket" class="w-full" />
          </div>

          <div class="backup-field">
            <label for="backup-target-prefix">Thư mục đích</label>
            <InputText id="backup-target-prefix" v-model.trim="configForm.target_prefix" class="w-full" />
          </div>

          <div class="backup-field backup-toggle-field">
            <label for="backup-target-secure">Kết nối bảo mật đích</label>
            <ToggleSwitch input-id="backup-target-secure" v-model="configForm.target_secure" />
          </div>

          <template v-if="editingConfig?.kind === 'object_storage'">
            <div class="backup-field">
              <label for="backup-source-endpoint">Địa chỉ kết nối nguồn</label>
              <InputText id="backup-source-endpoint" v-model.trim="configForm.source_endpoint" class="w-full" />
            </div>

            <div class="backup-field">
              <label for="backup-source-bucket">Kho lưu trữ nguồn</label>
              <InputText id="backup-source-bucket" v-model.trim="configForm.source_bucket" class="w-full" />
            </div>

            <div class="backup-field backup-toggle-field">
              <label for="backup-source-secure">Kết nối bảo mật nguồn</label>
              <ToggleSwitch input-id="backup-source-secure" v-model="sourceSecureValue" />
            </div>
          </template>

          <div class="backup-field backup-field-wide">
            <label for="backup-notify-emails">Thư điện tử nhận thông báo</label>
            <InputText id="backup-notify-emails" v-model.trim="configForm.notify_emails" class="w-full" />
          </div>
        </div>

        <p v-if="configFormError" class="backup-form-error">{{ configFormError }}</p>

        <div class="backup-dialog-footer">
          <Button label="Hủy" severity="secondary" outlined :disabled="savingConfig" @click="editDialogVisible = false" />
          <Button type="submit" label="Lưu" icon="pi pi-check" :loading="savingConfig" />
        </div>
      </form>
    </Dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import Button from 'primevue/button'
import Column from 'primevue/column'
import DataTable from 'primevue/datatable'
import Dialog from 'primevue/dialog'
import InputNumber from 'primevue/inputnumber'
import InputText from 'primevue/inputtext'
import ProgressSpinner from 'primevue/progressspinner'
import Tag from 'primevue/tag'
import ToggleSwitch from 'primevue/toggleswitch'
import { useToast } from 'primevue/usetoast'
import backupService, {
  type BackupConfigRead,
  type BackupConfigUpdatePayload,
  type BackupJobSummary,
  type BackupOverviewResponse,
} from '@/services/backupService'
import { formatDatetime } from '@/utils/format'

interface BackupConfigForm {
  enabled: boolean
  cron_expression: string
  retention_days: number | null
  source_endpoint: string
  source_bucket: string
  source_secure: boolean | null
  target_endpoint: string
  target_bucket: string
  target_prefix: string
  target_secure: boolean
  notify_emails: string
}

const overview = ref<BackupOverviewResponse | null>(null)
const loading = ref(false)
const error = ref('')
const editDialogVisible = ref(false)
const editingConfig = ref<BackupConfigRead | null>(null)
const savingConfig = ref(false)
const validatingKind = ref('')
const creatingJobKind = ref('')
const configFormError = ref('')
const toast = useToast()
let overviewPollTimer: number | undefined

const configForm = ref<BackupConfigForm>({
  enabled: true,
  cron_expression: '0 2 * * *',
  retention_days: 90,
  source_endpoint: '',
  source_bucket: '',
  source_secure: null,
  target_endpoint: '',
  target_bucket: 'hrms-backup',
  target_prefix: '',
  target_secure: true,
  notify_emails: '',
})

const enabledCount = computed(() => overview.value?.configs.filter((item) => item.enabled).length ?? 0)
const targetConfiguredCount = computed(() => overview.value?.configs.filter((item) => item.target_configured).length ?? 0)
const latestJobStatus = computed(() => {
  const status = overview.value?.latest_jobs[0]?.status
  return status ? statusLabel(status) : 'Chưa có'
})
const editDialogTitle = computed(() => (
  editingConfig.value ? `Sửa cấu hình ${editingConfig.value.kind_label}` : 'Sửa cấu hình sao lưu'
))
const sourceSecureValue = computed({
  get: () => configForm.value.source_secure ?? false,
  set: (value: boolean) => {
    configForm.value.source_secure = value
  },
})

async function loadOverview(options: { silent?: boolean } = {}) {
  if (!options.silent) loading.value = true
  error.value = ''
  try {
    const resp = await backupService.getOverview()
    overview.value = resp.data
    syncOverviewPolling()
  } catch {
    if (!options.silent) {
      error.value = 'Không tải được dữ liệu sao lưu. Vui lòng thử lại.'
    }
  } finally {
    if (!options.silent) loading.value = false
  }
}

function hasActiveBackupJob(): boolean {
  return overview.value?.latest_jobs.some((item) => ['queued', 'running'].includes(item.status)) ?? false
}

function startOverviewPolling() {
  if (overviewPollTimer !== undefined) return
  overviewPollTimer = window.setInterval(() => {
    void loadOverview({ silent: true })
  }, 5000)
}

function stopOverviewPolling() {
  if (overviewPollTimer === undefined) return
  window.clearInterval(overviewPollTimer)
  overviewPollTimer = undefined
}

function syncOverviewPolling() {
  if (hasActiveBackupJob()) {
    startOverviewPolling()
  } else {
    stopOverviewPolling()
  }
}

function kindLabel(kind: string): string {
  return overview.value?.configs.find((item) => item.kind === kind)?.kind_label ?? kindCodeLabel(kind)
}

function kindCodeLabel(kind: string): string {
  const labels: Record<string, string> = {
    db: 'Cấu hình cơ sở dữ liệu',
    object_storage: 'Cấu hình kho tệp tải lên',
  }
  return labels[kind] ?? 'Cấu hình sao lưu'
}

function sourceName(config: BackupConfigRead): string {
  if (config.kind === 'db') return 'Cơ sở dữ liệu ứng dụng PostgreSQL'
  return config.source_bucket || 'Kho tệp tải lên MinIO'
}

function sourceLocation(config: BackupConfigRead): string {
  if (config.kind === 'db') return 'Biến môi trường cơ sở dữ liệu'
  return config.source_endpoint || 'Địa chỉ kết nối MinIO'
}

function secretSourceLabel(source: string): string {
  const labels: Record<string, string> = {
    env: 'biến môi trường',
  }
  return labels[source] ?? 'nguồn cấu hình khác'
}

function nullableText(value: string): string | null {
  const cleaned = value.trim()
  return cleaned ? cleaned : null
}

function parseNotifyEmails(value: string): string[] | null {
  const emails = value
    .split(',')
    .map((item) => item.trim())
    .filter(Boolean)
  return emails.length ? emails : null
}

function openEditDialog(config: BackupConfigRead) {
  editingConfig.value = config
  configForm.value = {
    enabled: config.enabled,
    cron_expression: config.cron_expression,
    retention_days: config.retention_days,
    source_endpoint: config.source_endpoint ?? '',
    source_bucket: config.source_bucket ?? '',
    source_secure: config.source_secure,
    target_endpoint: config.target_endpoint ?? '',
    target_bucket: config.target_bucket,
    target_prefix: config.target_prefix ?? '',
    target_secure: config.target_secure,
    notify_emails: config.notify_emails?.join(', ') ?? '',
  }
  configFormError.value = ''
  editDialogVisible.value = true
}

function buildUpdatePayload(): BackupConfigUpdatePayload {
  return {
    enabled: configForm.value.enabled,
    cron_expression: configForm.value.cron_expression,
    retention_days: configForm.value.retention_days ?? 1,
    source_endpoint: nullableText(configForm.value.source_endpoint),
    source_bucket: nullableText(configForm.value.source_bucket),
    source_secure: configForm.value.source_secure,
    target_endpoint: nullableText(configForm.value.target_endpoint),
    target_bucket: configForm.value.target_bucket.trim(),
    target_prefix: nullableText(configForm.value.target_prefix),
    target_secure: configForm.value.target_secure,
    notify_emails: parseNotifyEmails(configForm.value.notify_emails),
  }
}

function replaceConfig(config: BackupConfigRead) {
  if (!overview.value) return
  overview.value = {
    ...overview.value,
    configs: overview.value.configs.map((item) => (
      item.kind === config.kind ? config : item
    )),
  }
}

function prependJob(job: BackupJobSummary) {
  if (!overview.value) return
  overview.value = {
    ...overview.value,
    latest_jobs: [
      job,
      ...overview.value.latest_jobs.filter((item) => item.id !== job.id),
    ].slice(0, 5),
  }
  syncOverviewPolling()
}

function apiErrorMessage(error: unknown, fallback: string): string {
  const response = (error as { response?: { data?: { detail?: unknown } } }).response
  const detail = response?.data?.detail
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) {
    return detail
      .map((item) => translateApiDetailItem(item))
      .join('; ')
  }
  return fallback
}

function translateApiDetailItem(item: unknown): string {
  if (typeof item !== 'object' || !item) return String(item)
  const detail = item as { loc?: unknown[]; msg?: unknown; type?: unknown; ctx?: Record<string, unknown> }
  const lastLocation = detail.loc?.[detail.loc.length - 1]
  const field = typeof lastLocation === 'string' ? fieldLabel(lastLocation) : 'Giá trị'
  const message = String(detail.msg ?? '')
  const cleanedMessage = message.replace(/^Value error,\s*/i, '')

  if (!message || message === 'Field required') return `${field} là bắt buộc.`
  if (cleanedMessage !== message) return cleanedMessage
  if (message.startsWith('String should have at least')) return `${field} phải có ít nhất ${detail.ctx?.min_length ?? ''} ký tự.`
  if (message.startsWith('String should have at most')) return `${field} không được quá ${detail.ctx?.max_length ?? ''} ký tự.`
  if (message.startsWith('Input should be greater than or equal to')) return `${field} phải lớn hơn hoặc bằng ${detail.ctx?.ge ?? ''}.`
  if (message.startsWith('Input should be less than or equal to')) return `${field} phải nhỏ hơn hoặc bằng ${detail.ctx?.le ?? ''}.`
  if (message.startsWith('Input should be a valid integer')) return `${field} phải là số nguyên.`
  if (message.startsWith('Input should be a valid boolean')) return `${field} phải là bật hoặc tắt.`
  if (message.startsWith('Input should be a valid list')) return `${field} phải là danh sách hợp lệ.`
  return cleanedMessage
}

function fieldLabel(field: string): string {
  const labels: Record<string, string> = {
    enabled: 'Trạng thái kích hoạt',
    cron_expression: 'Lịch chạy',
    retention_days: 'Số ngày giữ',
    source_endpoint: 'Địa chỉ kết nối nguồn',
    source_bucket: 'Kho lưu trữ nguồn',
    source_secure: 'Kết nối bảo mật nguồn',
    target_endpoint: 'Địa chỉ kết nối đích',
    target_bucket: 'Kho lưu trữ đích',
    target_prefix: 'Thư mục đích',
    target_secure: 'Kết nối bảo mật đích',
    notify_emails: 'Thư điện tử nhận thông báo',
    kind: 'Loại cấu hình sao lưu',
  }
  return labels[field] ?? 'Giá trị'
}

async function saveConfig() {
  if (!editingConfig.value) return
  savingConfig.value = true
  configFormError.value = ''
  try {
    const resp = await backupService.updateConfig(editingConfig.value.kind, buildUpdatePayload())
    replaceConfig(resp.data)
    editDialogVisible.value = false
    toast.add({
      severity: 'success',
      summary: 'Đã lưu cấu hình',
      detail: resp.data.kind_label,
      life: 3500,
    })
  } catch (err) {
    configFormError.value = apiErrorMessage(err, 'Không lưu được cấu hình sao lưu.')
  } finally {
    savingConfig.value = false
  }
}

async function validateTarget(config: BackupConfigRead) {
  validatingKind.value = config.kind
  try {
    const resp = await backupService.validateTarget({ kind: config.kind })
    replaceConfig({
      ...config,
      target_configured: resp.data.target_configured,
      last_validated_at: resp.data.checked_at,
      last_validation_status: resp.data.status,
      last_validation_error: resp.data.status === 'success' ? null : resp.data.message,
    })
    toast.add({
      severity: resp.data.status === 'success' ? 'success' : 'warn',
      summary: 'Đã kiểm tra đích sao lưu',
      detail: resp.data.message,
      life: 5000,
    })
  } catch (err) {
    toast.add({
      severity: 'error',
      summary: 'Không kiểm tra được đích sao lưu',
      detail: apiErrorMessage(err, 'Không kiểm tra được đích sao lưu.'),
      life: 5000,
    })
  } finally {
    validatingKind.value = ''
  }
}

async function createManualBackup(config: BackupConfigRead) {
  creatingJobKind.value = config.kind
  try {
    const resp = await backupService.createJob({ kind: config.kind })
    prependJob(resp.data)
    toast.add({
      severity: 'success',
      summary: 'Đã đưa vào hàng chờ sao lưu',
      detail: config.kind_label,
      life: 4500,
    })
  } catch (err) {
    toast.add({
      severity: 'error',
      summary: 'Không tạo được tác vụ sao lưu',
      detail: apiErrorMessage(err, 'Không tạo được tác vụ sao lưu.'),
      life: 5000,
    })
  } finally {
    creatingJobKind.value = ''
  }
}

function cronDescription(expression: string): string {
  const [minute, hour, dayOfMonth, month, dayOfWeek] = expression.trim().split(/\s+/)
  if ([minute, hour, dayOfMonth, month, dayOfWeek].every((part) => part !== undefined)) {
    if (dayOfMonth === '*' && month === '*' && dayOfWeek === '*') {
      return `Hằng ngày lúc ${hour.padStart(2, '0')}:${minute.padStart(2, '0')}`
    }
    if (dayOfMonth === '*' && month === '*' && dayOfWeek !== '*') {
      return `Hằng tuần lúc ${hour.padStart(2, '0')}:${minute.padStart(2, '0')}`
    }
    if (dayOfMonth !== '*' && month === '*' && dayOfWeek === '*') {
      return `Hằng tháng ngày ${dayOfMonth}, lúc ${hour.padStart(2, '0')}:${minute.padStart(2, '0')}`
    }
  }
  return 'Biểu thức lịch chạy tùy chỉnh'
}

function validationStatusLabel(status: string): string {
  const labels: Record<string, string> = {
    success: 'Thành công',
    failed: 'Thất bại',
  }
  return labels[status] ?? 'Trạng thái khác'
}

function validationStatusSeverity(status: string): string {
  const severities: Record<string, string> = {
    success: 'success',
    failed: 'danger',
  }
  return severities[status] ?? 'secondary'
}

function statusLabel(status: string): string {
  const labels: Record<string, string> = {
    queued: 'Đang chờ',
    running: 'Đang chạy',
    success: 'Thành công',
    failed: 'Thất bại',
    cancelled: 'Đã hủy',
  }
  return labels[status] ?? 'Trạng thái khác'
}

function triggerLabel(trigger: string): string {
  const labels: Record<string, string> = {
    schedule: 'Theo lịch',
    manual: 'Thủ công',
    restore_request: 'Yêu cầu khôi phục',
    system: 'Hệ thống',
  }
  return labels[trigger] ?? 'Kiểu khác'
}

function statusSeverity(status: string): string {
  const severities: Record<string, string> = {
    queued: 'secondary',
    running: 'info',
    success: 'success',
    failed: 'danger',
    cancelled: 'warn',
  }
  return severities[status] ?? 'secondary'
}

function restoreStatusLabel(status: string): string {
  const labels: Record<string, string> = {
    draft: 'Bản nháp',
    queued: 'Đang chờ',
    running: 'Đang chạy',
    verified: 'Đã kiểm tra',
    restored: 'Đã khôi phục',
    failed: 'Thất bại',
    cancelled: 'Đã hủy',
  }
  return labels[status] ?? 'Trạng thái khác'
}

function restoreModeLabel(mode: string): string {
  const labels: Record<string, string> = {
    verify_only: 'Chỉ kiểm tra',
    restore_to_new_target: 'Khôi phục sang đích mới',
    production_swap_pending_operator: 'Chờ vận hành chuyển đổi',
  }
  return labels[mode] ?? 'Chế độ khôi phục'
}

function restoreStatusSeverity(status: string): string {
  const severities: Record<string, string> = {
    draft: 'secondary',
    queued: 'secondary',
    running: 'info',
    verified: 'success',
    restored: 'success',
    failed: 'danger',
    cancelled: 'warn',
  }
  return severities[status] ?? 'secondary'
}

onMounted(() => {
  void loadOverview()
})
onBeforeUnmount(stopOverviewPolling)
</script>

<style scoped>
.backup-loading,
.backup-error {
  min-height: 220px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.75rem;
  color: var(--p-text-muted-color);
}

.backup-error {
  color: var(--p-red-600);
}

.backup-summary-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 0.75rem;
  margin-bottom: 1rem;
}

.backup-summary-item {
  border: 1px solid var(--p-content-border-color);
  background: var(--p-content-background);
  border-radius: 8px;
  padding: 1rem;
  min-height: 86px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
}

.summary-label {
  color: var(--p-text-muted-color);
  font-size: 0.82rem;
}

.backup-summary-item strong {
  font-size: 1.45rem;
  line-height: 1.1;
}

.backup-section {
  margin-bottom: 1rem;
}

.backup-section-header {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
  align-items: flex-end;
  margin-bottom: 0.5rem;
}

.backup-section-header h3 {
  margin: 0;
  font-size: 1rem;
  font-weight: 700;
}

.backup-section-header span {
  color: var(--p-text-muted-color);
  font-size: 0.82rem;
}

.backup-history-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 1rem;
}

.backup-kind-cell {
  display: flex;
  align-items: center;
  gap: 0.7rem;
}

.backup-kind-cell i {
  color: var(--p-primary-color);
  font-size: 1.1rem;
}

.strong-text {
  font-weight: 600;
}

.cron-cell {
  display: flex;
  align-items: center;
  gap: 0.45rem;
  flex-wrap: wrap;
  margin-bottom: 0.15rem;
}

.backup-code {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace;
  font-size: 0.78rem;
  color: #334155;
  background: #f1f5f9;
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  padding: 0.15rem 0.35rem;
  white-space: nowrap;
}

:global(html.dark-mode) .backup-code {
  color: #e2e8f0;
  background: #1e293b;
  border-color: #475569;
}

.backup-tag-stack {
  display: flex;
  flex-wrap: wrap;
  gap: 0.25rem;
  margin-bottom: 0.25rem;
}

.backup-validation-state {
  margin-top: 0.25rem;
}

.backup-actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 0.25rem;
  min-width: 88px;
}

.backup-config-form {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.backup-form-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.9rem 1rem;
}

.backup-field {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}

.backup-field label {
  font-size: 0.82rem;
  font-weight: 600;
  color: var(--p-text-color);
}

.backup-field small {
  color: var(--p-text-muted-color);
}

.backup-field-wide {
  grid-column: 1 / -1;
}

.backup-toggle-field {
  justify-content: space-between;
  min-height: 68px;
}

.backup-form-error {
  margin: 0;
  color: var(--p-red-600);
  font-size: 0.88rem;
}

.backup-dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 0.5rem;
}

.compact-empty {
  padding: 2rem;
}

@media (max-width: 960px) {
  .backup-summary-grid,
  .backup-history-grid {
    grid-template-columns: 1fr;
  }

  .backup-form-grid {
    grid-template-columns: 1fr;
  }
}
</style>
