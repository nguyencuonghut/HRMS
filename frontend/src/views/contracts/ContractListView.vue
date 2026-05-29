<template>
  <div>
    <!-- Page header -->
    <div class="page-header">
      <div>
        <h2>Hợp đồng lao động</h2>
        <span class="subtitle">Toàn bộ hợp đồng & phụ lục trong công ty</span>
      </div>
    </div>

    <!-- Toolbar -->
    <div class="toolbar">
      <IconField class="toolbar-search">
        <InputIcon class="pi pi-search" />
        <InputText
          v-model="filters.keyword"
          placeholder="Số HĐ hoặc tên nhân viên..."
          class="w-full"
          @keyup.enter="applyFilter"
        />
      </IconField>

      <Select
        v-model="filters.document_kind"
        :options="DOCUMENT_KIND_OPTIONS"
        option-label="label"
        option-value="value"
        placeholder="Loại tài liệu"
        show-clear
        filter
        class="toolbar-filter"
      />

      <Select
        v-model="filters.status"
        :options="CONTRACT_STATUS_OPTIONS"
        option-label="label"
        option-value="value"
        placeholder="Trạng thái"
        show-clear
        filter
        class="toolbar-filter"
      />

      <Select
        v-model="filters.expiring_within"
        :options="EXPIRING_OPTIONS"
        option-label="label"
        option-value="value"
        placeholder="Sắp hết hạn"
        show-clear
        filter
        class="toolbar-filter"
      />

      <Button label="Lọc" icon="pi pi-filter" @click="applyFilter" />
      <Button
        icon="pi pi-refresh"
        severity="secondary"
        text rounded
        v-tooltip.top="'Làm mới'"
        :loading="loading"
        @click="reset"
      />
    </div>

    <!-- DataTable -->
    <div class="card">
      <DataTable
        :value="items"
        :loading="loading"
        responsive-layout="scroll"
        :rows="pageSize"
        :total-records="total"
        :lazy="true"
        paginator
        paginator-template="RowsPerPageDropdown FirstPageLink PrevPageLink PageLinks NextPageLink LastPageLink CurrentPageReport"
        current-page-report-template="Hiển thị từ {first} đến {last} trên tổng số {totalRecords} dòng"
        :rows-per-page-options="[15, 25, 50]"
        @page="onPage"
      >
        <Column field="contract_number" header="Số hợp đồng" sortable style="min-width:160px;">
          <template #body="{ data }">
            <router-link
              :to="`/employees/${data.employee_id}`"
              class="contract-num-link"
            >{{ data.contract_number }}</router-link>
          </template>
        </Column>

        <Column header="Nhân viên" style="min-width:180px;">
          <template #body="{ data }">
            <router-link
              :to="`/employees/${data.employee_id}`"
              style="color:inherit; text-decoration:none;"
            >
              <div style="font-weight:500;">{{ data.employee_name ?? '—' }}</div>
              <div class="muted-text" style="font-size:0.78rem;">
                {{ data.employee_code ? data.employee_code : `#${data.employee_id}` }}
              </div>
            </router-link>
          </template>
        </Column>

        <Column field="category_name" header="Loại" style="min-width:160px;">
          <template #body="{ data }">
            <div>{{ data.category_name }}</div>
            <div class="muted-text" style="font-size:0.78rem;">
              {{ data.document_kind === 'labor_contract' ? 'Hợp đồng' : 'Phụ lục' }}
            </div>
          </template>
        </Column>

        <Column field="signed_date" header="Ngày ký" style="min-width:110px;">
          <template #body="{ data }">{{ formatDate(data.signed_date) }}</template>
        </Column>

        <Column field="effective_from" header="Hiệu lực từ" style="min-width:110px;">
          <template #body="{ data }">{{ formatDate(data.effective_from) }}</template>
        </Column>

        <Column field="effective_to" header="Hiệu lực đến" style="min-width:120px;">
          <template #body="{ data }">
            <span v-if="data.effective_to">{{ formatDate(data.effective_to) }}</span>
            <span v-else class="muted-text">Vô thời hạn</span>
          </template>
        </Column>

        <Column field="status_display" header="Trạng thái" style="min-width:160px;">
          <template #body="{ data }">
            <Tag :value="data.status_display" :severity="tagSeverity(data.status)" />
          </template>
        </Column>

        <Column header="Còn lại" style="width:110px;">
          <template #body="{ data }">
            <span
              v-if="data.days_until_expiry !== null && data.days_until_expiry !== undefined"
              :class="['days-badge', urgencyClass(data.days_until_expiry)]"
            >
              {{ data.days_until_expiry <= 0 ? 'Hết hạn' : `${data.days_until_expiry} ngày` }}
            </span>
            <span v-else class="muted-text">—</span>
          </template>
        </Column>

        <Column header="File" style="width:60px;" class="center-text">
          <template #body="{ data }">
            <i v-if="data.has_file" class="pi pi-paperclip" v-tooltip.top="data.file_name" />
          </template>
        </Column>

        <Column header="" style="width:100px;">
          <template #body="{ data }">
            <div style="display:flex; gap:0.25rem;">
              <Button
                v-if="data.days_until_expiry !== null && data.days_until_expiry !== undefined && data.days_until_expiry <= 30"
                icon="pi pi-replay"
                text rounded size="small"
                severity="warning"
                v-tooltip.top="'Tái ký — mở hồ sơ nhân viên'"
                @click="router.push(`/employees/${data.employee_id}?tab=contracts`)"
              />
              <router-link :to="`/employees/${data.employee_id}`">
                <Button icon="pi pi-arrow-right" text rounded size="small" v-tooltip.top="'Xem hồ sơ nhân viên'" />
              </router-link>
            </div>
          </template>
        </Column>

        <template #empty>
          <div class="empty-state">
            <i class="pi pi-file-edit" />
            <span>Không có hợp đồng nào</span>
          </div>
        </template>
      </DataTable>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import Button from 'primevue/button'
import Column from 'primevue/column'
import DataTable from 'primevue/datatable'
import IconField from 'primevue/iconfield'
import InputIcon from 'primevue/inputicon'
import InputText from 'primevue/inputtext'
import Select from 'primevue/select'
import Tag from 'primevue/tag'

import contractService, {
  type ContractRead,
  DOCUMENT_KIND_OPTIONS,
  CONTRACT_STATUS_OPTIONS,
  EXPIRING_OPTIONS,
  statusSeverity,
} from '@/services/contractService'

const router   = useRouter()
const route    = useRoute()
const loading  = ref(false)
const items    = ref<ContractRead[]>([])
const total    = ref(0)
const page     = ref(1)
const pageSize = ref(25)

const filters = ref({
  keyword:        '',
  document_kind:  null as string | null,
  status:         null as string | null,
  expiring_within: null as number | null,
})

function tagSeverity(status: string) { return statusSeverity(status) }

function urgencyClass(days: number): string {
  if (days <= 0)  return 'expired'
  if (days <= 7)  return 'critical'
  if (days <= 15) return 'warning'
  if (days <= 30) return 'soon'
  return 'ok'
}

function formatDate(iso: string | null): string {
  if (!iso) return '—'
  const [y, m, d] = iso.split('-')
  return `${d}/${m}/${y}`
}

async function load() {
  loading.value = true
  try {
    const params: Record<string, unknown> = {
      page: page.value,
      page_size: pageSize.value,
    }
    if (filters.value.keyword)        params.keyword        = filters.value.keyword
    if (filters.value.document_kind)  params.document_kind  = filters.value.document_kind
    if (filters.value.status)         params.status         = filters.value.status
    if (filters.value.expiring_within) params.expiring_within = filters.value.expiring_within

    const res = await contractService.listContractsGlobal(params)
    items.value = res.data.items
    total.value = res.data.total
  } finally {
    loading.value = false
  }
}

function applyFilter() {
  page.value = 1
  load()
}

function reset() {
  filters.value = { keyword: '', document_kind: null, status: null, expiring_within: null }
  page.value = 1
  load()
}

function onPage(e: { page: number; rows: number }) {
  page.value = e.page + 1
  pageSize.value = e.rows
  load()
}

onMounted(() => {
  const ew = route.query.expiring_within
  if (ew) {
    const n = parseInt(String(ew), 10)
    if (!isNaN(n)) filters.value.expiring_within = n
  }
  load()
})
</script>
