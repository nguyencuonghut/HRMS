<template>
  <div>
    <div class="page-header">
      <div>
        <h2>Sao lưu & khôi phục</h2>
        <span class="subtitle">Theo dõi cấu hình sao lưu database và file upload MinIO.</span>
      </div>
      <Button
        icon="pi pi-refresh"
        severity="secondary"
        outlined
        :loading="loading"
        v-tooltip.bottom="'Làm mới'"
        aria-label="Làm mới"
        @click="loadOverview"
      />
    </div>

    <div v-if="loading && !overview" class="backup-loading">
      <ProgressSpinner style="width: 42px; height: 42px" />
      <span>Đang tải dữ liệu sao lưu...</span>
    </div>

    <div v-else-if="error" class="backup-error">
      <i class="pi pi-exclamation-triangle" />
      <span>{{ error }}</span>
      <Button label="Thử lại" icon="pi pi-refresh" size="small" @click="loadOverview" />
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
          <span class="summary-label">Job gần nhất</span>
          <strong>{{ latestJobStatus }}</strong>
        </div>
      </section>

      <section class="backup-section">
        <div class="backup-section-header">
          <div>
            <h3>Cấu hình sao lưu</h3>
            <span>Thông tin đọc từ cấu hình hệ thống; secret được giữ trong biến môi trường server.</span>
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
                    <div class="muted-text">{{ data.kind }}</div>
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
                <div>{{ data.source_bucket || 'PostgreSQL application DB' }}</div>
                <div class="muted-text">{{ data.source_endpoint || 'DATABASE_URL' }}</div>
              </template>
            </Column>

            <Column header="Đích backup" style="min-width: 220px">
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
                    :value="data.source_configured ? 'Nguồn OK' : 'Thiếu nguồn'"
                    :severity="data.source_configured ? 'success' : 'warn'"
                    rounded
                  />
                  <Tag
                    :value="data.target_configured ? 'Đích OK' : 'Thiếu đích'"
                    :severity="data.target_configured ? 'success' : 'warn'"
                    rounded
                  />
                </div>
                <div class="muted-text">Secret: {{ data.secret_source }}</div>
              </template>
            </Column>

            <Column header="Validate gần nhất" style="min-width: 180px">
              <template #body="{ data }">
                <span>{{ data.last_validated_at ? formatDatetime(data.last_validated_at) : 'Chưa kiểm tra' }}</span>
                <div v-if="data.last_validation_status" class="muted-text">
                  {{ data.last_validation_status }}
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
              <h3>Lịch backup gần nhất</h3>
              <span>Tối đa 5 job mới nhất từ backend.</span>
            </div>
          </div>
          <div class="card">
            <DataTable :value="overview.latest_jobs" size="small" responsive-layout="scroll">
              <template #empty>
                <div class="empty-state compact-empty">
                  <i class="pi pi-clock" />
                  <span>Chưa có job backup nào.</span>
                </div>
              </template>
              <Column header="Loại" style="width: 140px">
                <template #body="{ data }">{{ kindLabel(data.kind) }}</template>
              </Column>
              <Column header="Trạng thái" style="width: 130px">
                <template #body="{ data }">
                  <Tag :value="statusLabel(data.status)" :severity="statusSeverity(data.status)" rounded />
                </template>
              </Column>
              <Column header="Artifact">
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
              <span>Tối đa 5 yêu cầu mới nhất từ backend.</span>
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
                <template #body="{ data }">{{ data.mode }}</template>
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
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import Button from 'primevue/button'
import Column from 'primevue/column'
import DataTable from 'primevue/datatable'
import ProgressSpinner from 'primevue/progressspinner'
import Tag from 'primevue/tag'
import backupService, { type BackupOverviewResponse } from '@/services/backupService'
import { formatDatetime } from '@/utils/format'

const overview = ref<BackupOverviewResponse | null>(null)
const loading = ref(false)
const error = ref('')

const enabledCount = computed(() => overview.value?.configs.filter((item) => item.enabled).length ?? 0)
const targetConfiguredCount = computed(() => overview.value?.configs.filter((item) => item.target_configured).length ?? 0)
const latestJobStatus = computed(() => {
  const status = overview.value?.latest_jobs[0]?.status
  return status ? statusLabel(status) : 'Chưa có'
})

async function loadOverview() {
  loading.value = true
  error.value = ''
  try {
    const resp = await backupService.getOverview()
    overview.value = resp.data
  } catch {
    error.value = 'Không tải được dữ liệu sao lưu. Vui lòng thử lại.'
  } finally {
    loading.value = false
  }
}

function kindLabel(kind: string): string {
  return overview.value?.configs.find((item) => item.kind === kind)?.kind_label ?? kind
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
  return 'Biểu thức cron tùy chỉnh'
}

function statusLabel(status: string): string {
  const labels: Record<string, string> = {
    queued: 'Đang chờ',
    running: 'Đang chạy',
    success: 'Thành công',
    failed: 'Thất bại',
    cancelled: 'Đã hủy',
  }
  return labels[status] ?? status
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
  return labels[status] ?? status
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

onMounted(loadOverview)
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

.compact-empty {
  padding: 2rem;
}

@media (max-width: 960px) {
  .backup-summary-grid,
  .backup-history-grid {
    grid-template-columns: 1fr;
  }
}
</style>
