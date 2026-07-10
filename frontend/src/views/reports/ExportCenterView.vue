<template>
  <div class="export-center-view">
    <Toast />

    <div class="page-header">
      <div>
        <h2>Xuất báo cáo</h2>
        <div class="subtitle">
          Trung tâm xuất file dùng chung cho dashboard, báo cáo nhân sự, nghỉ phép, bảo hiểm, hợp đồng và tuyển dụng.
        </div>
      </div>
    </div>

    <Tabs v-model:value="activeTab">
      <TabList>
        <Tab value="quick">Xuất nhanh</Tab>
        <Tab value="history">Lịch sử</Tab>
        <Tab value="templates">Mẫu</Tab>
        <Tab v-if="canViewInsuranceExports" value="bhxh">Biểu mẫu BHXH</Tab>
      </TabList>

      <TabPanels>
        <TabPanel value="quick">
          <div class="export-center-grid">
            <div class="card export-main-card card-content-padding">
              <div class="export-section-header">
                <div>
                  <h3 class="section-title">Tạo export</h3>
                  <span class="export-section-subtitle">Chọn loại báo cáo, bộ lọc và định dạng xuất.</span>
                </div>
              </div>

              <ExportFilterPanel
                :draft="quickDraft"
                :departments="departments"
                :report-type-options="reportTypeOptions"
                :format-options="formatOptions"
                @report-type-change="handleReportTypeChange"
              />

              <div class="export-main-actions">
                <Button
                  v-can:export="'reports'"
                  label="Xuất báo cáo"
                  icon="pi pi-file-export"
                  :loading="submitting"
                  @click="submitExport"
                />
                <Button
                  v-can:export="'reports'"
                  label="Lưu thành mẫu"
                  icon="pi pi-bookmark"
                  severity="secondary"
                  outlined
                  @click="openSaveTemplateDialog"
                />
                <Button
                  v-if="canExportReports && selectedTemplateId"
                  label="Ghi đè mẫu đang dùng"
                  icon="pi pi-save"
                  severity="contrast"
                  outlined
                  :loading="templateSaving"
                  @click="overwriteSelectedTemplate"
                />
              </div>
            </div>

            <div class="card export-side-card card-content-padding">
              <div class="export-section-header">
                <div>
                  <h3 class="section-title">Trạng thái hiện tại</h3>
                  <span class="export-section-subtitle">Theo dõi export đang xử lý và tải file ngay khi hoàn tất.</span>
                </div>
              </div>

              <div v-if="currentJob" class="export-current-job">
                <div class="export-current-row">
                  <span>Job</span>
                  <strong>{{ currentJob.filename || currentJob.report_type }}</strong>
                </div>
                <div class="export-current-row">
                  <span>Trạng thái</span>
                  <Tag :value="statusLabel(currentJob.status)" :severity="statusSeverity(currentJob.status)" rounded />
                </div>
                <div class="export-current-row">
                  <span>Số dòng</span>
                  <strong>{{ currentJob.row_count ?? '—' }}</strong>
                </div>
                <div class="export-current-row">
                  <span>File</span>
                  <strong>{{ currentJob.format.toUpperCase() }}</strong>
                </div>
                <div v-if="currentJob.error_message" class="export-error-copy">
                  {{ currentJob.error_message }}
                </div>
                <div class="export-current-actions">
                  <Button
                    v-can:export="'reports'"
                    v-if="currentJob.status === 'done'"
                    label="Tải file"
                    icon="pi pi-download"
                    severity="success"
                    outlined
                    @click="downloadJob(currentJob)"
                  />
                  <Button
                    v-if="currentJob.status !== 'done' && isPolling"
                    label="Đang polling"
                    icon="pi pi-spin pi-spinner"
                    severity="secondary"
                    disabled
                  />
                </div>
              </div>
              <div v-else class="export-empty">
                Chưa có export nào trong phiên làm việc này.
              </div>
            </div>
          </div>
        </TabPanel>

        <TabPanel value="history">
          <div class="card export-history-card card-content-padding">
            <div class="export-section-header">
              <div>
                <h3 class="section-title">Lịch sử xuất</h3>
                <span class="export-section-subtitle">Tải lại file cũ hoặc xóa job không còn cần thiết.</span>
              </div>
              <Button
                icon="pi pi-refresh"
                label="Làm mới"
                severity="secondary"
                outlined
                :loading="historyLoading"
                @click="loadHistory(historyPage.page)"
              />
            </div>

            <DataTable
              :value="historyPage.items"
              :loading="historyLoading"
              lazy
              paginator
              paginator-template="RowsPerPageDropdown FirstPageLink PrevPageLink PageLinks NextPageLink LastPageLink CurrentPageReport"
              current-page-report-template="Hiển thị từ {first} đến {last} trên tổng số {totalRecords} dòng"
              striped-rows
              responsive-layout="scroll"
              :rows="historyPage.page_size"
              :first="(historyPage.page - 1) * historyPage.page_size"
              :total-records="historyPage.total"
              :rows-per-page-options="[5, 10, 20]"
              @page="onHistoryPage"
            >
              <template #empty>
                <div class="export-empty">Chưa có lịch sử export.</div>
              </template>

              <Column field="filename" header="Tên file" style="min-width: 210px">
                <template #body="{ data }">
                  <div class="export-history-name">
                    <strong>{{ data.filename || data.report_type }}</strong>
                    <span>{{ data.report_type_label }}</span>
                  </div>
                </template>
              </Column>
              <Column header="Định dạng" style="width: 100px">
                <template #body="{ data }">{{ data.format_label }}</template>
              </Column>
              <Column header="Trạng thái" style="width: 140px">
                <template #body="{ data }">
                  <Tag :value="data.status_label" :severity="data.status_severity" rounded />
                </template>
              </Column>
              <Column header="Số dòng" style="width: 110px">
                <template #body="{ data }">{{ data.row_count ?? '—' }}</template>
              </Column>
              <Column header="Tạo lúc" style="min-width: 170px">
                <template #body="{ data }">{{ formatDateTime(data.created_at) }}</template>
              </Column>
              <Column header="" style="width: 150px">
                <template #body="{ data }">
                  <div class="export-row-actions">
                    <Button
                      v-can:export="'reports'"
                      v-if="data.status === 'done'"
                      icon="pi pi-download"
                      text
                      rounded
                      severity="success"
                      size="small"
                      @click="downloadJob(data)"
                    />
                    <Button
                      v-can:export="'reports'"
                      icon="pi pi-trash"
                      text
                      rounded
                      severity="danger"
                      size="small"
                      @click="deleteHistoryJob(data.id)"
                    />
                  </div>
                </template>
              </Column>
            </DataTable>
          </div>
        </TabPanel>

        <TabPanel value="templates">
          <div class="card export-template-card card-content-padding">
            <div class="export-section-header">
              <div>
                <h3 class="section-title">Mẫu báo cáo</h3>
                <span class="export-section-subtitle">Lưu bộ lọc hay dùng để tái sử dụng nhanh trong các lần xuất sau.</span>
              </div>
            </div>

            <DataTable
              :value="templates"
              :loading="templateLoading"
              responsive-layout="scroll"
              striped-rows
            >
              <template #empty>
                <div class="export-empty">Chưa có mẫu báo cáo nào.</div>
              </template>

              <Column field="name" header="Tên mẫu" style="min-width: 190px">
                <template #body="{ data }">
                  <div class="export-template-name">
                    <strong>{{ data.name }}</strong>
                    <span>{{ data.report_type_label }}</span>
                  </div>
                </template>
              </Column>
              <Column field="description" header="Mô tả" style="min-width: 220px">
                <template #body="{ data }">{{ data.description || '—' }}</template>
              </Column>
              <Column header="Mặc định" style="width: 110px">
                <template #body="{ data }">
                  <Tag :value="data.is_default ? 'Mặc định' : 'Thường'" :severity="data.is_default ? 'info' : 'secondary'" rounded />
                </template>
              </Column>
              <Column header="Cập nhật" style="min-width: 170px">
                <template #body="{ data }">{{ formatDateTime(data.updated_at) }}</template>
              </Column>
              <Column header="" style="width: 180px">
                <template #body="{ data }">
                  <div class="export-row-actions">
                    <Button
                      icon="pi pi-play"
                      text
                      rounded
                      severity="info"
                      size="small"
                      @click="applyTemplate(data)"
                    />
                    <Button
                      v-can:export="'reports'"
                      icon="pi pi-pencil"
                      text
                      rounded
                      severity="contrast"
                      size="small"
                      @click="openEditTemplateDialog(data)"
                    />
                    <Button
                      v-can:export="'reports'"
                      icon="pi pi-trash"
                      text
                      rounded
                      severity="danger"
                      size="small"
                      @click="deleteTemplate(data.id)"
                    />
                  </div>
                </template>
              </Column>
            </DataTable>
          </div>
        </TabPanel>
        <TabPanel v-if="canViewInsuranceExports" value="bhxh">
          <div class="bhxh-panel">
            <!-- Filter row -->
            <div class="card bhxh-filter-card">
              <div class="bhxh-filter-row">
                <div class="bhxh-field">
                  <label>Tháng</label>
                  <Select
                    v-model="bhxhMonth"
                    :options="monthOptions"
                    option-label="label"
                    option-value="value"
                  />
                </div>
                <div class="bhxh-field">
                  <label>Năm</label>
                  <Select
                    v-model="bhxhYear"
                    :options="bhxhYearOptions"
                    option-label="label"
                    option-value="value"
                  />
                </div>
                <div class="bhxh-field">
                  <label>Phòng ban</label>
                  <Select
                    v-model="bhxhDeptId"
                    :options="departments"
                    option-label="name"
                    option-value="id"
                    placeholder="Toàn công ty"
                    show-clear
                    filter
                  />
                </div>
              </div>
            </div>

            <!-- D02-LT card -->
            <div class="card bhxh-form-card">
              <div class="bhxh-form-info">
                <div class="bhxh-form-title">D02-LT</div>
                <div class="bhxh-form-desc">Danh sách lao động tham gia BHXH, BHYT, BHTN</div>
              </div>
              <Button
                v-can:view="'insurance'"
                label="Xuất Excel"
                icon="pi pi-file-excel"
                severity="success"
                outlined
                :loading="exportingD02"
                @click="doExportD02"
              />
            </div>

            <!-- D03-TS card -->
            <div class="card bhxh-form-card">
              <div class="bhxh-form-info">
                <div class="bhxh-form-title">D03-TS</div>
                <div class="bhxh-form-desc">Bảng tổng hợp mức đóng BHXH, BHYT, BHTN</div>
              </div>
              <Button
                v-can:view="'insurance'"
                label="Xuất Excel"
                icon="pi pi-file-excel"
                severity="success"
                outlined
                :loading="exportingD03"
                @click="doExportD03"
              />
            </div>
          </div>
        </TabPanel>
      </TabPanels>
    </Tabs>

    <Dialog
      v-model:visible="saveTemplateVisible"
      header="Lưu mẫu báo cáo"
      modal
      :style="{ width: '34rem' }"
    >
      <div class="export-dialog-body">
        <div class="export-field">
          <label for="export-template-name">Tên mẫu</label>
          <InputText id="export-template-name" v-model.trim="templateForm.name" />
        </div>
        <div class="export-field">
          <label for="export-template-desc">Mô tả</label>
          <Textarea id="export-template-desc" v-model="templateForm.description" rows="3" auto-resize />
        </div>
        <div class="export-field">
          <label>Định dạng</label>
          <Select
            v-model="templateForm.format"
            :options="formatOptions"
            option-label="label"
            option-value="code"
          />
        </div>
        <div class="export-check">
          <Checkbox v-model="templateForm.is_default" binary input-id="template-default" />
          <label for="template-default">Đặt làm mẫu mặc định cho loại báo cáo này</label>
        </div>
      </div>
      <template #footer>
        <Button label="Hủy" text @click="saveTemplateVisible = false" />
        <Button v-can:export="'reports'" label="Lưu mẫu" :loading="templateSaving" @click="saveTemplate" />
      </template>
    </Dialog>

    <Dialog
      v-model:visible="editTemplateVisible"
      header="Cập nhật mẫu báo cáo"
      modal
      :style="{ width: '34rem' }"
    >
      <div class="export-dialog-body">
        <div class="export-field">
          <label for="edit-template-name">Tên mẫu</label>
          <InputText id="edit-template-name" v-model.trim="editTemplateForm.name" />
        </div>
        <div class="export-field">
          <label for="edit-template-desc">Mô tả</label>
          <Textarea id="edit-template-desc" v-model="editTemplateForm.description" rows="3" auto-resize />
        </div>
        <div class="export-field">
          <label>Định dạng</label>
          <Select
            v-model="editTemplateForm.format"
            :options="formatOptions"
            option-label="label"
            option-value="code"
          />
        </div>
        <div class="export-check">
          <Checkbox v-model="editTemplateForm.is_default" binary input-id="template-edit-default" />
          <label for="template-edit-default">Đặt làm mặc định</label>
        </div>
      </div>
      <template #footer>
        <Button label="Hủy" text @click="editTemplateVisible = false" />
        <Button v-can:export="'reports'" label="Cập nhật" :loading="templateSaving" @click="updateTemplateMeta" />
      </template>
    </Dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import Button from 'primevue/button'
import Checkbox from 'primevue/checkbox'
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
import Toast from 'primevue/toast'
import { useToast } from 'primevue/usetoast'

import { useExportPolling } from '@/composables/useExportPolling'
import departmentService, { type DepartmentRead } from '@/services/departmentService'
import exportService, {
  type ExportFormatOption,
  type ExportFormat,
  type ExportJobResponse,
  type ExportReportTypeOption,
  type ExportReportType,
  type ReportTemplateResponse,
  type ExportStatusOption,
} from '@/services/exportService'
import bhxhExportService from '@/services/bhxhExportService'
import ExportFilterPanel from './components/export/ExportFilterPanel.vue'
import { usePermissionGate } from '@/composables/usePermissionGate'

const toast = useToast()
const { isPolling, start } = useExportPolling()
const permissionGate = usePermissionGate()
const canExportReports = computed(() => permissionGate.canExport('reports'))
const canViewInsuranceExports = computed(() => permissionGate.canView('insurance'))
const canLoadDepartments = computed(() => permissionGate.canAccessRoute('/org/departments'))

const activeTab = ref('quick')
const departments = ref<DepartmentRead[]>([])
const templates = ref<ReportTemplateResponse[]>([])
const currentJob = ref<ExportJobResponse | null>(null)
const reportTypeOptions = ref<ExportReportTypeOption[]>([])
const formatOptions = ref<ExportFormatOption[]>([])
const statusOptions = ref<ExportStatusOption[]>([])
const statusMetaMap = ref<Record<string, ExportStatusOption>>({})

const submitting = ref(false)
const historyLoading = ref(false)
const templateLoading = ref(false)
const templateSaving = ref(false)

const saveTemplateVisible = ref(false)
const editTemplateVisible = ref(false)
const selectedTemplateId = ref<number | null>(null)

const historyPage = reactive({
  items: [] as ExportJobResponse[],
  total: 0,
  page: 1,
  page_size: 10,
})

const quickDraft = reactive({
  report_type: 'hr-employee-list' as ExportReportType,
  format: 'xlsx' as ExportFormat,
  filename: '',
  filters: {
    page_size: 20,
  } as Record<string, unknown>,
})

const templateForm = reactive({
  name: '',
  description: '',
  format: 'xlsx' as ExportFormat,
  is_default: false,
})

const editTemplateTarget = ref<ReportTemplateResponse | null>(null)
const editTemplateForm = reactive({
  name: '',
  description: '',
  format: 'xlsx' as ExportFormat,
  is_default: false,
})

function resetFiltersForReportType(reportType: ExportReportType) {
  const currentYear = new Date().getFullYear()
  const currentMonth = new Date().getMonth() + 1

  const next: Record<string, unknown> = {}
  if (['dashboard', 'leaves', 'insurance', 'contracts', 'hr-employee-list', 'hr-movement', 'hr-tenure', 'hr-org-structure', 'recruitment', 'probation'].includes(reportType)) {
    next.department_id = null
  }

  if (reportType === 'dashboard') {
    next.year = currentYear
    next.month = currentMonth
  }
  if (reportType === 'hr-employee-list') {
    next.page_size = 20
  }
  if (reportType === 'hr-movement') {
    next.start_date = `${currentYear}-01-01`
    next.end_date = `${currentYear}-12-31`
    next.group_by = 'month'
  }
  if (reportType === 'leaves') {
    next.year = currentYear
  }
  if (reportType === 'insurance') {
    next.year = currentYear
    next.month = currentMonth
  }
  if (reportType === 'contracts') {
    next.status = 'active'
    next.days_ahead = 90
  }
  if (reportType === 'recruitment' || reportType === 'probation') {
    next.start_date = `${currentYear}-01-01`
    next.end_date = `${currentYear}-12-31`
  }

  quickDraft.filters = next
}

function handleReportTypeChange(reportType: ExportReportType) {
  quickDraft.report_type = reportType
  resetFiltersForReportType(reportType)
}

function statusLabel(status: string) {
  return statusMetaMap.value[status]?.label ?? status
}

function statusSeverity(status: string) {
  return statusMetaMap.value[status]?.severity ?? 'secondary'
}

function formatDateTime(value?: string | null) {
  if (!value) return '—'
  return new Intl.DateTimeFormat('vi-VN', {
    dateStyle: 'short',
    timeStyle: 'short',
  }).format(new Date(value))
}

async function loadDepartments() {
  if (!canLoadDepartments.value) {
    departments.value = []
    return
  }
  try {
    const res = await departmentService.getList(true)
    departments.value = res.data
  } catch {
    departments.value = []
  }
}

async function loadMeta() {
  const res = await exportService.getMeta()
  reportTypeOptions.value = [...res.data.report_types].sort((a, b) => a.order - b.order)
  formatOptions.value = [...res.data.formats].sort((a, b) => a.order - b.order)
  statusOptions.value = [...res.data.statuses].sort((a, b) => a.order - b.order)
  statusMetaMap.value = Object.fromEntries(statusOptions.value.map((item) => [item.code, item]))
}

async function loadHistory(page = historyPage.page) {
  historyLoading.value = true
  try {
    const res = await exportService.getHistory({
      page,
      page_size: historyPage.page_size,
    })
    historyPage.items = res.data.items
    historyPage.total = res.data.total
    historyPage.page = res.data.page
    historyPage.page_size = res.data.page_size
  } finally {
    historyLoading.value = false
  }
}

async function loadTemplates() {
  templateLoading.value = true
  try {
    const res = await exportService.listTemplates()
    templates.value = res.data
  } finally {
    templateLoading.value = false
  }
}

function normalizedFilters() {
  return Object.fromEntries(
    Object.entries(quickDraft.filters).filter(
      ([, value]) => value !== null && value !== undefined && value !== '',
    ),
  )
}

async function downloadJob(job: Pick<ExportJobResponse, 'id' | 'filename'>) {
  await exportService.downloadJob(job.id, job.filename || 'bao_cao.xlsx')
}

async function submitExport() {
  submitting.value = true
  try {
    const res = await exportService.createJob({
      report_type: quickDraft.report_type,
      format: quickDraft.format,
      filename: quickDraft.filename || null,
      filters: normalizedFilters(),
    })
    currentJob.value = res.data
    activeTab.value = 'quick'

    if (res.data.status === 'done') {
      await downloadJob(res.data)
      toast.add({
        severity: 'success',
        summary: 'Xuất báo cáo thành công',
        detail: 'File đã sẵn sàng để tải.',
        life: 3000,
      })
      await loadHistory(1)
      return
    }

    toast.add({
      severity: 'info',
      summary: 'Đã tạo export nền',
      detail: 'Hệ thống sẽ tự tải file khi job hoàn tất.',
      life: 3000,
    })
    await start(res.data.id, {
      onDone: async () => {
        const latest = await exportService.getHistory({ page: 1, page_size: historyPage.page_size })
        const fresh = latest.data.items.find((item) => item.id === res.data.id)
        if (fresh) currentJob.value = fresh
        await loadHistory(1)
        if (fresh) {
          await downloadJob(fresh)
        }
        toast.add({
          severity: 'success',
          summary: 'Export đã hoàn tất',
          detail: 'File đã được tải xuống.',
          life: 3000,
        })
      },
      onFailed: async (status) => {
        await loadHistory(1)
        toast.add({
          severity: 'error',
          summary: 'Export thất bại',
          detail: status.error_message || 'Không thể tạo file báo cáo.',
          life: 4000,
        })
      },
    })
  } catch (error: any) {
    toast.add({
      severity: 'error',
      summary: 'Không tạo được export',
      detail: error?.response?.data?.detail || 'Vui lòng kiểm tra lại bộ lọc.',
      life: 4000,
    })
  } finally {
    submitting.value = false
  }
}

function openSaveTemplateDialog() {
  templateForm.name = ''
  templateForm.description = ''
  templateForm.format = quickDraft.format
  templateForm.is_default = false
  saveTemplateVisible.value = true
}

async function saveTemplate() {
  if (!templateForm.name.trim()) {
    toast.add({ severity: 'warn', summary: 'Thiếu tên mẫu', detail: 'Nhập tên mẫu trước khi lưu.', life: 2500 })
    return
  }
  templateSaving.value = true
  try {
    await exportService.createTemplate({
      name: templateForm.name.trim(),
      description: templateForm.description || null,
      report_type: quickDraft.report_type,
      format: templateForm.format,
      filters: normalizedFilters(),
      is_default: templateForm.is_default,
    })
    saveTemplateVisible.value = false
    await loadTemplates()
    toast.add({
      severity: 'success',
      summary: 'Đã lưu mẫu',
      detail: 'Mẫu báo cáo đã được lưu.',
      life: 2500,
    })
  } catch (error: any) {
    toast.add({
      severity: 'error',
      summary: 'Lưu mẫu thất bại',
      detail: error?.response?.data?.detail || 'Không thể lưu mẫu.',
      life: 3500,
    })
  } finally {
    templateSaving.value = false
  }
}

function applyTemplate(template: ReportTemplateResponse) {
  selectedTemplateId.value = template.id
  quickDraft.report_type = template.report_type
  quickDraft.format = template.format
  quickDraft.filename = template.name
  quickDraft.filters = { ...template.filters }
  activeTab.value = 'quick'
  toast.add({
    severity: 'info',
    summary: 'Đã áp dụng mẫu',
    detail: `Mẫu "${template.name}" đã được nạp vào bộ lọc.`,
    life: 2500,
  })
}

function openEditTemplateDialog(template: ReportTemplateResponse) {
  editTemplateTarget.value = template
  editTemplateForm.name = template.name
  editTemplateForm.description = template.description || ''
  editTemplateForm.format = template.format
  editTemplateForm.is_default = template.is_default
  editTemplateVisible.value = true
}

async function updateTemplateMeta() {
  if (!editTemplateTarget.value) return
  templateSaving.value = true
  try {
    await exportService.updateTemplate(editTemplateTarget.value.id, {
      name: editTemplateForm.name.trim(),
      description: editTemplateForm.description || null,
      format: editTemplateForm.format,
      is_default: editTemplateForm.is_default,
    })
    editTemplateVisible.value = false
    await loadTemplates()
    toast.add({
      severity: 'success',
      summary: 'Đã cập nhật mẫu',
      detail: 'Thông tin mẫu đã được cập nhật.',
      life: 2500,
    })
  } catch (error: any) {
    toast.add({
      severity: 'error',
      summary: 'Cập nhật mẫu thất bại',
      detail: error?.response?.data?.detail || 'Không thể cập nhật mẫu.',
      life: 3500,
    })
  } finally {
    templateSaving.value = false
  }
}

async function overwriteSelectedTemplate() {
  if (!selectedTemplateId.value) return
  templateSaving.value = true
  try {
    await exportService.updateTemplate(selectedTemplateId.value, {
      format: quickDraft.format,
      filters: normalizedFilters(),
    })
    await loadTemplates()
    toast.add({
      severity: 'success',
      summary: 'Đã ghi đè mẫu',
      detail: 'Bộ lọc hiện tại đã được lưu lại vào mẫu đang dùng.',
      life: 2500,
    })
  } catch (error: any) {
    toast.add({
      severity: 'error',
      summary: 'Ghi đè mẫu thất bại',
      detail: error?.response?.data?.detail || 'Không thể cập nhật mẫu.',
      life: 3500,
    })
  } finally {
    templateSaving.value = false
  }
}

async function deleteTemplate(templateId: number) {
  try {
    await exportService.deleteTemplate(templateId)
    if (selectedTemplateId.value === templateId) {
      selectedTemplateId.value = null
    }
    await loadTemplates()
  } catch (error: any) {
    toast.add({
      severity: 'error',
      summary: 'Xóa mẫu thất bại',
      detail: error?.response?.data?.detail || 'Không thể xóa mẫu.',
      life: 3500,
    })
  }
}

async function deleteHistoryJob(jobId: string) {
  try {
    await exportService.deleteJob(jobId)
    if (currentJob.value?.id === jobId) {
      currentJob.value = null
    }
    await loadHistory(historyPage.page)
  } catch (error: any) {
    toast.add({
      severity: 'error',
      summary: 'Xóa lịch sử thất bại',
      detail: error?.response?.data?.detail || 'Không thể xóa export job.',
      life: 3500,
    })
  }
}

function onHistoryPage(event: { page: number; rows: number }) {
  historyPage.page = event.page + 1
  historyPage.page_size = event.rows
  void loadHistory(historyPage.page)
}

// BHXH export state
const _now = new Date()
const bhxhMonth = ref(_now.getMonth() + 1)
const bhxhYear = ref(_now.getFullYear())
const bhxhDeptId = ref<number | null>(null)
const exportingD02 = ref(false)
const exportingD03 = ref(false)

const monthOptions = Array.from({ length: 12 }, (_, i) => ({ label: `Tháng ${i + 1}`, value: i + 1 }))
const bhxhYearOptions = computed(() =>
  Array.from({ length: 6 }, (_, i) => {
    const y = _now.getFullYear() - 2 + i
    return { label: String(y), value: y }
  }),
)

async function doExportD02() {
  exportingD02.value = true
  try {
    await bhxhExportService.exportD02Lt({ year: bhxhYear.value, month: bhxhMonth.value, department_id: bhxhDeptId.value })
  } catch {
    toast.add({ severity: 'error', summary: 'Xuất D02-LT thất bại', life: 4000 })
  } finally {
    exportingD02.value = false
  }
}

async function doExportD03() {
  exportingD03.value = true
  try {
    await bhxhExportService.exportD03Ts({ year: bhxhYear.value, month: bhxhMonth.value, department_id: bhxhDeptId.value })
  } catch {
    toast.add({ severity: 'error', summary: 'Xuất D03-TS thất bại', life: 4000 })
  } finally {
    exportingD03.value = false
  }
}

onMounted(async () => {
  await Promise.all([
    loadMeta(),
    loadDepartments(),
    loadHistory(1),
    loadTemplates(),
  ])
})
</script>

<style>
.export-center-view {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.export-center-grid {
  display: grid;
  grid-template-columns: 1.7fr 1fr;
  gap: 1rem;
}

.export-main-card,
.export-side-card,
.export-history-card,
.export-template-card {
  border: 1px solid var(--l-border);
  background: var(--l-surface);
  box-shadow: var(--l-shadow);
}

.export-section-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1rem;
  margin-bottom: 1rem;
}

.export-section-subtitle {
  display: inline-block;
  margin-top: 0.2rem;
  font-size: 0.88rem;
  color: var(--l-text-muted);
}

.export-main-actions {
  display: flex;
  gap: 0.75rem;
  flex-wrap: wrap;
  margin-top: 1.25rem;
}

.export-current-job {
  display: flex;
  flex-direction: column;
  gap: 0.9rem;
}

.export-current-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
}

.export-current-row span {
  color: var(--l-text-muted);
  font-size: 0.86rem;
}

.export-current-row strong {
  color: var(--l-text);
  text-align: right;
}

.export-current-actions {
  display: flex;
  gap: 0.75rem;
  flex-wrap: wrap;
}

.export-error-copy {
  padding: 0.85rem 1rem;
  border-radius: 0.85rem;
  background: color-mix(in srgb, var(--p-red-500) 8%, var(--l-surface));
  border: 1px solid color-mix(in srgb, var(--p-red-500) 25%, transparent);
  color: var(--l-text);
  font-size: 0.88rem;
}

.export-empty {
  padding: 1.5rem 0.5rem;
  text-align: center;
  color: var(--l-text-muted);
}

.export-history-name,
.export-template-name {
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
}

.export-history-name span,
.export-template-name span {
  color: var(--l-text-muted);
  font-size: 0.82rem;
}

.export-row-actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.15rem;
}

.export-dialog-body {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.export-field {
  display: flex;
  flex-direction: column;
  gap: 0.45rem;
}

.export-field label {
  font-size: 0.82rem;
  font-weight: 600;
  color: var(--l-text-muted);
}

.export-check {
  display: flex;
  align-items: center;
  gap: 0.65rem;
}

@media (max-width: 1023px) {
  .export-center-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 767px) {
  .export-main-actions {
    flex-direction: column;
  }

  .export-main-actions .p-button,
  .export-current-actions .p-button {
    width: 100%;
  }

  .export-current-row {
    align-items: flex-start;
    flex-direction: column;
  }
}

.bhxh-panel {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  padding-top: 0.5rem;
}

.bhxh-filter-card {
  padding: var(--hh-card-content-padding);
  border: 1px solid var(--l-border);
  background: var(--l-surface);
}

.bhxh-filter-row {
  display: flex;
  gap: 1rem;
  flex-wrap: wrap;
}

.bhxh-field {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
  min-width: 160px;
}

.bhxh-field label {
  font-size: 0.82rem;
  font-weight: 600;
  color: var(--l-text-muted);
}

.bhxh-form-card {
  padding: var(--hh-card-content-padding);
  border: 1px solid var(--l-border);
  background: var(--l-surface);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  flex-wrap: wrap;
}

.bhxh-form-title {
  font-weight: 700;
  font-size: 1rem;
}

.bhxh-form-desc {
  font-size: 0.85rem;
  color: var(--l-text-muted);
  margin-top: 0.2rem;
}
</style>
