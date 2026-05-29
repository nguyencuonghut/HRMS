<template>
  <div class="education-catalog">
    <section class="hero-panel">
      <div class="hero-copy">
        <span class="eyebrow">Education Catalog Workspace</span>
        <h1>Danh mục học vấn</h1>
        <p class="hero-text">
          Chuẩn hóa trình độ, trường học và chuyên ngành để dùng lại trực tiếp cho hồ sơ nhân sự,
          báo cáo năng lực và nhập dữ liệu lịch sử sau này.
        </p>
        <div class="hero-actions">
          <Button
            :label="createButtonLabel"
            icon="pi pi-plus"
            @click="openCreate(activeTab)"
          />
          <Button
            label="Về tổng quan danh mục"
            icon="pi pi-th-large"
            severity="secondary"
            outlined
            @click="router.push('/catalog')"
          />
          <Button
            label="Xem nhật ký hệ thống"
            icon="pi pi-list"
            severity="contrast"
            outlined
            @click="router.push('/admin/audit-logs')"
          />
        </div>
      </div>

      <div class="hero-side">
        <article class="signal-card">
          <div class="signal-head">
            <span class="signal-label">Phạm vi đang quản trị</span>
            <Tag :value="activeTabLabel" severity="info" rounded />
          </div>
          <p class="signal-value">{{ activeTabHeadline }}</p>
          <p class="signal-note">{{ activeTabSubline }}</p>
        </article>

        <article class="signal-card muted">
          <div class="signal-head">
            <span class="signal-label">Điểm dùng lại</span>
          </div>
          <ul class="scope-list">
            <li>Lookup cho học vấn trong hồ sơ nhân sự</li>
            <li>Chuẩn hóa tên trường và chuyên ngành nội bộ</li>
            <li>Khóa mềm thay vì xóa vật lý để giữ lịch sử tham chiếu</li>
            <li>CRUD được ghi audit log qua nhật ký hệ thống</li>
          </ul>
        </article>
      </div>
    </section>

    <section class="stats-grid">
      <article class="stat-card">
        <div class="stat-icon tone-teal">
          <i class="pi pi-sort-numeric-up" />
        </div>
        <div class="stat-body">
          <span class="stat-label">Trình độ học vấn</span>
          <strong class="stat-value">{{ formatNumber(levelState.total) }}</strong>
          <span class="stat-footnote">Thứ bậc học thuật chuẩn hóa</span>
        </div>
      </article>

      <article class="stat-card">
        <div class="stat-icon tone-amber">
          <i class="pi pi-building-columns" />
        </div>
        <div class="stat-body">
          <span class="stat-label">Trường học</span>
          <strong class="stat-value">{{ formatNumber(institutionState.total) }}</strong>
          <span class="stat-footnote">Cơ sở đào tạo đang có trong catalog</span>
        </div>
      </article>

      <article class="stat-card">
        <div class="stat-icon tone-slate">
          <i class="pi pi-book" />
        </div>
        <div class="stat-body">
          <span class="stat-label">Chuyên ngành</span>
          <strong class="stat-value">{{ formatNumber(majorState.total) }}</strong>
          <span class="stat-footnote">Nhóm học vấn sẵn sàng cho form nhân sự</span>
        </div>
      </article>
    </section>

    <div v-if="errorBanner" class="status-banner danger">
      <i class="pi pi-exclamation-triangle" />
      <span>{{ errorBanner }}</span>
    </div>

    <div class="card workspace-card">
      <Tabs v-model:value="activeTab">
        <div class="workspace-head">
          <div>
            <span class="section-kicker">Quản trị trực tiếp</span>
            <h2>{{ activeTabHeadline }}</h2>
          </div>
          <TabList>
            <Tab value="levels">Trình độ</Tab>
            <Tab value="institutions">Trường học</Tab>
            <Tab value="majors">Chuyên ngành</Tab>
          </TabList>
        </div>

        <TabPanels>
          <TabPanel value="levels">
            <div class="toolbar">
              <Select
                v-model="levelState.isActive"
                :options="activeFilterOptions"
                option-label="label"
                option-value="value"
                filter
                class="toolbar-filter"
                @change="handleLevelFilterChange"
              />
              <IconField class="toolbar-search">
                <InputIcon class="pi pi-search" />
                <InputText
                  v-model="levelState.keyword"
                  placeholder="Tìm theo mã hoặc tên trình độ..."
                  class="w-full"
                  @input="debounceLevels"
                  @keydown.enter="loadLevels"
                />
              </IconField>
              <Button
                icon="pi pi-refresh"
                severity="secondary"
                text
                rounded
                :loading="levelState.loading"
                v-tooltip.top="'Làm mới danh sách trình độ'"
                @click="loadLevels"
              />
            </div>

            <DataTable
              :value="levelState.items"
              :loading="levelState.loading"
              stripedRows
              paginator
              lazy
              responsive-layout="scroll"
              :rows="levelState.pageSize"
              :first="(levelState.page - 1) * levelState.pageSize"
              :total-records="levelState.total"
              :rows-per-page-options="[10, 20, 50]"
              paginator-template="RowsPerPageDropdown FirstPageLink PrevPageLink PageLinks NextPageLink LastPageLink CurrentPageReport"
              current-page-report-template="Hiển thị từ {first} đến {last} trên tổng số {totalRecords} dòng"
              @page="onLevelPage"
            >
              <template #paginatorstart>
                <span class="paginator-info" v-if="levelState.total > 0">
                  Hiển thị {{ (levelState.page - 1) * levelState.pageSize + 1 }}–{{ Math.min((levelState.page - 1) * levelState.pageSize + levelState.items.length, levelState.total) }}
                  trên tổng số {{ levelState.total }} dòng
                </span>
              </template>
              <template #empty>
                <div class="empty-state">
                  <i class="pi pi-inbox" />
                  <span>{{ levelState.keyword.trim() ? 'Không tìm thấy trình độ phù hợp' : 'Không có dữ liệu trình độ học vấn' }}</span>
                </div>
              </template>

              <Column field="rank_no" header="Bậc" style="width: 100px" />
              <Column field="code" header="Mã" style="width: 170px" />
              <Column field="name" header="Tên trình độ" style="min-width: 220px" />
              <Column field="is_active" header="Trạng thái" style="width: 130px">
                <template #body="{ data }">
                  <Tag :value="data.is_active ? 'Hoạt động' : 'Đã khóa'" :severity="data.is_active ? 'success' : 'danger'" />
                </template>
              </Column>
              <Column header="" style="width: 110px">
                <template #body="{ data }">
                  <div class="action-cell">
                    <Button icon="pi pi-pencil" severity="secondary" text rounded size="small" v-tooltip.top="'Chỉnh sửa'" @click="openEdit('levels', data)" />
                    <Button icon="pi pi-trash" severity="danger" text rounded size="small" v-tooltip.top="'Khóa'" @click="confirmDelete('levels', data)" />
                  </div>
                </template>
              </Column>
            </DataTable>
          </TabPanel>

          <TabPanel value="institutions">
            <div class="toolbar">
              <Select
                v-model="institutionState.isActive"
                :options="activeFilterOptions"
                option-label="label"
                option-value="value"
                filter
                class="toolbar-filter"
                @change="handleInstitutionFilterChange"
              />
              <Select
                v-model="institutionState.type"
                :options="institutionTypeOptions"
                option-label="label"
                option-value="value"
                filter
                class="toolbar-filter"
                @change="handleInstitutionFilterChange"
              />
              <InputText
                v-model="institutionState.countryCode"
                class="toolbar-filter"
                placeholder="Mã quốc gia"
                @keydown.enter="handleInstitutionFilterChange"
              />
              <IconField class="toolbar-search">
                <InputIcon class="pi pi-search" />
                <InputText
                  v-model="institutionState.keyword"
                  placeholder="Tìm theo tên trường, short name hoặc mã..."
                  class="w-full"
                  @input="debounceInstitutions"
                  @keydown.enter="loadInstitutions"
                />
              </IconField>
              <Button
                icon="pi pi-refresh"
                severity="secondary"
                text
                rounded
                :loading="institutionState.loading"
                v-tooltip.top="'Làm mới danh sách trường học'"
                @click="loadInstitutions"
              />
            </div>

            <DataTable
              :value="institutionState.items"
              :loading="institutionState.loading"
              stripedRows
              paginator
              lazy
              responsive-layout="scroll"
              :rows="institutionState.pageSize"
              :first="(institutionState.page - 1) * institutionState.pageSize"
              :total-records="institutionState.total"
              :rows-per-page-options="[10, 20, 50]"
              paginator-template="RowsPerPageDropdown FirstPageLink PrevPageLink PageLinks NextPageLink LastPageLink CurrentPageReport"
              current-page-report-template="Hiển thị từ {first} đến {last} trên tổng số {totalRecords} dòng"
              @page="onInstitutionPage"
            >
              <template #paginatorstart>
                <span class="paginator-info" v-if="institutionState.total > 0">
                  Hiển thị {{ (institutionState.page - 1) * institutionState.pageSize + 1 }}–{{ Math.min((institutionState.page - 1) * institutionState.pageSize + institutionState.items.length, institutionState.total) }}
                  trên tổng số {{ institutionState.total }} dòng
                </span>
              </template>
              <template #empty>
                <div class="empty-state">
                  <i class="pi pi-inbox" />
                  <span>{{ institutionState.keyword.trim() ? 'Không tìm thấy trường học phù hợp' : 'Không có dữ liệu trường học' }}</span>
                </div>
              </template>

              <Column field="name" header="Tên trường" style="min-width: 260px">
                <template #body="{ data }">
                  <div class="stacked-cell">
                    <strong>{{ data.name }}</strong>
                    <small v-if="data.short_name">{{ data.short_name }}</small>
                  </div>
                </template>
              </Column>
              <Column field="code" header="Mã" style="width: 130px">
                <template #body="{ data }">{{ data.code || '—' }}</template>
              </Column>
              <Column field="institution_type" header="Loại" style="width: 140px">
                <template #body="{ data }">{{ institutionTypeLabel(data.institution_type) }}</template>
              </Column>
              <Column field="country_code" header="Quốc gia" style="width: 110px">
                <template #body="{ data }">{{ data.country_code || '—' }}</template>
              </Column>
              <Column field="province_code" header="Mã tỉnh" style="width: 110px">
                <template #body="{ data }">{{ data.province_code || '—' }}</template>
              </Column>
              <Column field="is_active" header="Trạng thái" style="width: 130px">
                <template #body="{ data }">
                  <Tag :value="data.is_active ? 'Hoạt động' : 'Đã khóa'" :severity="data.is_active ? 'success' : 'danger'" />
                </template>
              </Column>
              <Column header="" style="width: 110px">
                <template #body="{ data }">
                  <div class="action-cell">
                    <Button icon="pi pi-pencil" severity="secondary" text rounded size="small" v-tooltip.top="'Chỉnh sửa'" @click="openEdit('institutions', data)" />
                    <Button icon="pi pi-trash" severity="danger" text rounded size="small" v-tooltip.top="'Khóa'" @click="confirmDelete('institutions', data)" />
                  </div>
                </template>
              </Column>
            </DataTable>
          </TabPanel>

          <TabPanel value="majors">
            <div class="toolbar">
              <Select
                v-model="majorState.isActive"
                :options="activeFilterOptions"
                option-label="label"
                option-value="value"
                filter
                class="toolbar-filter"
                @change="handleMajorFilterChange"
              />
              <Select
                v-model="majorState.group"
                :options="majorGroupOptions"
                option-label="label"
                option-value="value"
                filter
                class="toolbar-filter"
                @change="handleMajorFilterChange"
              />
              <IconField class="toolbar-search">
                <InputIcon class="pi pi-search" />
                <InputText
                  v-model="majorState.keyword"
                  placeholder="Tìm theo tên chuyên ngành hoặc mã..."
                  class="w-full"
                  @input="debounceMajors"
                  @keydown.enter="loadMajors"
                />
              </IconField>
              <Button
                icon="pi pi-refresh"
                severity="secondary"
                text
                rounded
                :loading="majorState.loading"
                v-tooltip.top="'Làm mới danh sách chuyên ngành'"
                @click="loadMajors"
              />
            </div>

            <DataTable
              :value="majorState.items"
              :loading="majorState.loading"
              stripedRows
              paginator
              lazy
              responsive-layout="scroll"
              :rows="majorState.pageSize"
              :first="(majorState.page - 1) * majorState.pageSize"
              :total-records="majorState.total"
              :rows-per-page-options="[10, 20, 50]"
              paginator-template="RowsPerPageDropdown FirstPageLink PrevPageLink PageLinks NextPageLink LastPageLink CurrentPageReport"
              current-page-report-template="Hiển thị từ {first} đến {last} trên tổng số {totalRecords} dòng"
              @page="onMajorPage"
            >
              <template #paginatorstart>
                <span class="paginator-info" v-if="majorState.total > 0">
                  Hiển thị {{ (majorState.page - 1) * majorState.pageSize + 1 }}–{{ Math.min((majorState.page - 1) * majorState.pageSize + majorState.items.length, majorState.total) }}
                  trên tổng số {{ majorState.total }} dòng
                </span>
              </template>
              <template #empty>
                <div class="empty-state">
                  <i class="pi pi-inbox" />
                  <span>{{ majorState.keyword.trim() ? 'Không tìm thấy chuyên ngành phù hợp' : 'Không có dữ liệu chuyên ngành' }}</span>
                </div>
              </template>

              <Column field="name" header="Tên chuyên ngành" style="min-width: 260px" />
              <Column field="code" header="Mã" style="width: 160px">
                <template #body="{ data }">{{ data.code || '—' }}</template>
              </Column>
              <Column field="major_group" header="Nhóm" style="width: 170px">
                <template #body="{ data }">{{ data.major_group || '—' }}</template>
              </Column>
              <Column field="is_active" header="Trạng thái" style="width: 130px">
                <template #body="{ data }">
                  <Tag :value="data.is_active ? 'Hoạt động' : 'Đã khóa'" :severity="data.is_active ? 'success' : 'danger'" />
                </template>
              </Column>
              <Column header="" style="width: 110px">
                <template #body="{ data }">
                  <div class="action-cell">
                    <Button icon="pi pi-pencil" severity="secondary" text rounded size="small" v-tooltip.top="'Chỉnh sửa'" @click="openEdit('majors', data)" />
                    <Button icon="pi pi-trash" severity="danger" text rounded size="small" v-tooltip.top="'Khóa'" @click="confirmDelete('majors', data)" />
                  </div>
                </template>
              </Column>
            </DataTable>
          </TabPanel>
        </TabPanels>
      </Tabs>
    </div>

    <Dialog
      v-model:visible="dialogVisible"
      :header="dialogHeader"
      :style="{ width: activeDialogKind === 'institutions' ? '640px' : '560px' }"
      modal
      :close-on-escape="!submitting"
      :closable="!submitting"
    >
      <form v-if="activeDialogKind === 'levels'" class="form-shell" @submit.prevent="submitLevelForm">
        <div v-if="!editingLevel" class="field">
          <label for="l-code">Mã trình độ <span class="req">*</span></label>
          <InputText id="l-code" v-model="levelForm.code" class="w-full" :invalid="!!levelErrors.code" />
          <small v-if="levelErrors.code" class="error-msg">{{ levelErrors.code }}</small>
        </div>

        <div class="field">
          <label for="l-name">Tên trình độ <span class="req">*</span></label>
          <InputText id="l-name" v-model="levelForm.name" class="w-full" :invalid="!!levelErrors.name" />
          <small v-if="levelErrors.name" class="error-msg">{{ levelErrors.name }}</small>
        </div>

        <div class="field">
          <label for="l-rank">Thứ bậc <span class="req">*</span></label>
          <InputNumber id="l-rank" v-model="levelForm.rank_no" :min="1" :max="999" :max-fraction-digits="0" class="w-full" :invalid="!!levelErrors.rank_no" />
          <small v-if="levelErrors.rank_no" class="error-msg">{{ levelErrors.rank_no }}</small>
        </div>

        <div v-if="editingLevel" class="field field-switch">
          <label>Trạng thái</label>
          <div class="switch-row">
            <ToggleSwitch v-model="levelForm.is_active" />
            <span :class="levelForm.is_active ? 'active-label' : 'inactive-label'">
              {{ levelForm.is_active ? 'Hoạt động' : 'Đã khóa' }}
            </span>
          </div>
        </div>
      </form>

      <form v-else-if="activeDialogKind === 'institutions'" class="form-shell" @submit.prevent="submitInstitutionForm">
        <div v-if="!editingInstitution" class="field">
          <label for="i-code">Mã trường</label>
          <InputText id="i-code" v-model="institutionForm.code" class="w-full" />
        </div>

        <div class="field">
          <label for="i-name">Tên trường <span class="req">*</span></label>
          <InputText id="i-name" v-model="institutionForm.name" class="w-full" :invalid="!!institutionErrors.name" />
          <small v-if="institutionErrors.name" class="error-msg">{{ institutionErrors.name }}</small>
        </div>

        <div class="field">
          <label for="i-short">Tên ngắn</label>
          <InputText id="i-short" v-model="institutionForm.short_name" class="w-full" />
        </div>

        <div class="field-row">
          <div class="field">
            <label for="i-type">Loại trường</label>
            <Select
              id="i-type"
              v-model="institutionForm.institution_type"
              :options="institutionTypeOptions"
              option-label="label"
              option-value="value"
              class="w-full"
              show-clear
              filter
            />
          </div>
          <div class="field">
            <label for="i-country">Mã quốc gia</label>
            <InputText id="i-country" v-model="institutionForm.country_code" class="w-full" placeholder="VN" />
          </div>
        </div>

        <div class="field">
          <label for="i-province">Mã tỉnh</label>
          <InputText id="i-province" v-model="institutionForm.province_code" class="w-full" placeholder="Ví dụ: 19" />
        </div>

        <div v-if="editingInstitution" class="field field-switch">
          <label>Trạng thái</label>
          <div class="switch-row">
            <ToggleSwitch v-model="institutionForm.is_active" />
            <span :class="institutionForm.is_active ? 'active-label' : 'inactive-label'">
              {{ institutionForm.is_active ? 'Hoạt động' : 'Đã khóa' }}
            </span>
          </div>
        </div>
      </form>

      <form v-else class="form-shell" @submit.prevent="submitMajorForm">
        <div v-if="!editingMajor" class="field">
          <label for="m-code">Mã chuyên ngành</label>
          <InputText id="m-code" v-model="majorForm.code" class="w-full" />
        </div>

        <div class="field">
          <label for="m-name">Tên chuyên ngành <span class="req">*</span></label>
          <InputText id="m-name" v-model="majorForm.name" class="w-full" :invalid="!!majorErrors.name" />
          <small v-if="majorErrors.name" class="error-msg">{{ majorErrors.name }}</small>
        </div>

        <div class="field">
          <label for="m-group">Nhóm chuyên ngành</label>
          <Select
            id="m-group"
            v-model="majorForm.major_group"
            :options="majorGroupOptions"
            option-label="label"
            option-value="value"
            class="w-full"
            show-clear
            filter
          />
        </div>

        <div v-if="editingMajor" class="field field-switch">
          <label>Trạng thái</label>
          <div class="switch-row">
            <ToggleSwitch v-model="majorForm.is_active" />
            <span :class="majorForm.is_active ? 'active-label' : 'inactive-label'">
              {{ majorForm.is_active ? 'Hoạt động' : 'Đã khóa' }}
            </span>
          </div>
        </div>
      </form>

      <template #footer>
        <Button label="Hủy" severity="secondary" outlined :disabled="submitting" @click="dialogVisible = false" />
        <Button :label="editingMode ? 'Lưu thay đổi' : 'Tạo mới'" icon="pi pi-check" :loading="submitting" @click="submitActiveForm" />
      </template>
    </Dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useConfirm } from 'primevue/useconfirm'
import { useToast } from 'primevue/usetoast'
import Button from 'primevue/button'
import Column from 'primevue/column'
import DataTable from 'primevue/datatable'
import Dialog from 'primevue/dialog'
import IconField from 'primevue/iconfield'
import InputIcon from 'primevue/inputicon'
import InputNumber from 'primevue/inputnumber'
import InputText from 'primevue/inputtext'
import Select from 'primevue/select'
import Tab from 'primevue/tab'
import TabList from 'primevue/tablist'
import TabPanel from 'primevue/tabpanel'
import TabPanels from 'primevue/tabpanels'
import Tabs from 'primevue/tabs'
import Tag from 'primevue/tag'
import ToggleSwitch from 'primevue/toggleswitch'

import educationCatalogService, {
  type EducationLevelRead,
  type EducationalInstitutionRead,
  type EducationMajorRead,
} from '@/services/educationCatalogService'

type TabKey = 'levels' | 'institutions' | 'majors'

interface BaseListState<T> {
  items: T[]
  total: number
  page: number
  pageSize: number
  keyword: string
  isActive: boolean | null
  loading: boolean
}

interface LevelFormState {
  code: string
  name: string
  rank_no: number | null
  is_active: boolean
}

interface InstitutionFormState {
  code: string
  name: string
  short_name: string
  institution_type: 'university' | 'college' | 'vocational' | 'high_school' | 'other' | null
  country_code: string
  province_code: string
  is_active: boolean
}

interface MajorFormState {
  code: string
  name: string
  major_group: string | null
  is_active: boolean
}

const router = useRouter()
const toast = useToast()
const confirm = useConfirm()

const activeTab = ref<TabKey>('levels')
const dialogVisible = ref(false)
const submitting = ref(false)
const errorBanner = ref('')

const levelState = ref<BaseListState<EducationLevelRead>>({
  items: [],
  total: 0,
  page: 1,
  pageSize: 10,
  keyword: '',
  isActive: true,
  loading: false,
})

const institutionState = ref<BaseListState<EducationalInstitutionRead> & {
  type: string | null
  countryCode: string
}>({
  items: [],
  total: 0,
  page: 1,
  pageSize: 10,
  keyword: '',
  isActive: true,
  loading: false,
  type: null,
  countryCode: '',
})

const majorState = ref<BaseListState<EducationMajorRead> & {
  group: string | null
}>({
  items: [],
  total: 0,
  page: 1,
  pageSize: 10,
  keyword: '',
  isActive: true,
  loading: false,
  group: null,
})

const levelForm = ref<LevelFormState>({
  code: '',
  name: '',
  rank_no: null,
  is_active: true,
})
const institutionForm = ref<InstitutionFormState>({
  code: '',
  name: '',
  short_name: '',
  institution_type: null,
  country_code: 'VN',
  province_code: '',
  is_active: true,
})
const majorForm = ref<MajorFormState>({
  code: '',
  name: '',
  major_group: null,
  is_active: true,
})

const levelErrors = ref<Partial<Record<keyof LevelFormState, string>>>({})
const institutionErrors = ref<Partial<Record<keyof InstitutionFormState, string>>>({})
const majorErrors = ref<Partial<Record<keyof MajorFormState, string>>>({})

const editingLevel = ref<EducationLevelRead | null>(null)
const editingInstitution = ref<EducationalInstitutionRead | null>(null)
const editingMajor = ref<EducationMajorRead | null>(null)
const activeDialogKind = ref<TabKey>('levels')

let levelSearchTimer: ReturnType<typeof setTimeout> | undefined
let institutionSearchTimer: ReturnType<typeof setTimeout> | undefined
let majorSearchTimer: ReturnType<typeof setTimeout> | undefined

const activeFilterOptions = [
  { label: 'Tất cả trạng thái', value: null },
  { label: 'Đang hoạt động', value: true },
  { label: 'Đã khóa', value: false },
]

const institutionTypeOptions = [
  { label: 'Tất cả loại trường', value: null },
  { label: 'Đại học', value: 'university' },
  { label: 'Cao đẳng', value: 'college' },
  { label: 'Nghề / trung cấp', value: 'vocational' },
  { label: 'THPT', value: 'high_school' },
  { label: 'Khác', value: 'other' },
]

const majorGroupOptions = [
  { label: 'Tất cả nhóm', value: null },
  { label: 'Nông nghiệp', value: 'agriculture' },
  { label: 'Chăn nuôi', value: 'animal_science' },
  { label: 'Nuôi trồng thủy sản', value: 'aquaculture' },
  { label: 'Kinh doanh', value: 'business' },
  { label: 'Kỹ thuật', value: 'engineering' },
  { label: 'Chế biến', value: 'processing' },
  { label: 'Quản lý chất lượng', value: 'quality' },
  { label: 'Khoa học', value: 'science' },
  { label: 'Chuỗi cung ứng', value: 'supply_chain' },
  { label: 'Thú y', value: 'veterinary' },
]

const activeTabLabel = computed(() => {
  if (activeTab.value === 'levels') return 'Trình độ học vấn'
  if (activeTab.value === 'institutions') return 'Trường học'
  return 'Chuyên ngành'
})

const activeTabHeadline = computed(() => {
  if (activeTab.value === 'levels') return 'Quản trị bậc học thuật nội bộ'
  if (activeTab.value === 'institutions') return 'Quản trị trường học và cơ sở đào tạo'
  return 'Quản trị chuyên ngành cho hồ sơ nhân sự'
})

const activeTabSubline = computed(() => {
  if (activeTab.value === 'levels') {
    return 'Dùng để ép thứ bậc học vấn, lọc báo cáo và chốt lookup chuẩn cho quá trình học.'
  }
  if (activeTab.value === 'institutions') {
    return 'Tối ưu cho các trường nông nghiệp, kỹ thuật, kinh doanh và các cơ sở đào tạo liên quan vận hành sản xuất.'
  }
  return 'Chuẩn hóa nhóm chuyên ngành để giảm nhập tay và gom báo cáo theo năng lực thực tế.'
})

const createButtonLabel = computed(() => {
  if (activeTab.value === 'levels') return 'Thêm trình độ'
  if (activeTab.value === 'institutions') return 'Thêm trường học'
  return 'Thêm chuyên ngành'
})

const dialogHeader = computed(() => {
  if (activeDialogKind.value === 'levels') return editingLevel.value ? 'Chỉnh sửa trình độ học vấn' : 'Thêm trình độ học vấn'
  if (activeDialogKind.value === 'institutions') return editingInstitution.value ? 'Chỉnh sửa trường học' : 'Thêm trường học'
  return editingMajor.value ? 'Chỉnh sửa chuyên ngành' : 'Thêm chuyên ngành'
})

const editingMode = computed(() => {
  if (activeDialogKind.value === 'levels') return !!editingLevel.value
  if (activeDialogKind.value === 'institutions') return !!editingInstitution.value
  return !!editingMajor.value
})

function formatNumber(value: number) {
  return new Intl.NumberFormat('vi-VN').format(value)
}

function institutionTypeLabel(value: string | null) {
  return institutionTypeOptions.find((item) => item.value === value)?.label ?? '—'
}

function apiError(error: unknown): string {
  const err = error as { response?: { data?: { detail?: unknown } } }
  const detail = err.response?.data?.detail
  if (Array.isArray(detail)) return detail.map((item: { msg: string }) => item.msg).join('; ')
  return typeof detail === 'string' ? detail : 'Đã xảy ra lỗi, vui lòng thử lại'
}

async function loadLevels() {
  levelState.value.loading = true
  try {
    const res = await educationCatalogService.getEducationLevels({
      keyword: levelState.value.keyword.trim() || null,
      is_active: levelState.value.isActive,
      page: levelState.value.page,
      page_size: levelState.value.pageSize,
    })
    levelState.value.items = res.data.items
    levelState.value.total = res.data.total
  } catch (error) {
    errorBanner.value = 'Không tải được dữ liệu trình độ học vấn.'
    toast.add({ severity: 'error', summary: 'Lỗi', detail: apiError(error), life: 4000 })
  } finally {
    levelState.value.loading = false
  }
}

async function loadInstitutions() {
  institutionState.value.loading = true
  try {
    const res = await educationCatalogService.getEducationalInstitutions({
      keyword: institutionState.value.keyword.trim() || null,
      institution_type: institutionState.value.type,
      country_code: institutionState.value.countryCode.trim() || null,
      is_active: institutionState.value.isActive,
      page: institutionState.value.page,
      page_size: institutionState.value.pageSize,
    })
    institutionState.value.items = res.data.items
    institutionState.value.total = res.data.total
  } catch (error) {
    errorBanner.value = 'Không tải được dữ liệu trường học.'
    toast.add({ severity: 'error', summary: 'Lỗi', detail: apiError(error), life: 4000 })
  } finally {
    institutionState.value.loading = false
  }
}

async function loadMajors() {
  majorState.value.loading = true
  try {
    const res = await educationCatalogService.getEducationMajors({
      keyword: majorState.value.keyword.trim() || null,
      major_group: majorState.value.group,
      is_active: majorState.value.isActive,
      page: majorState.value.page,
      page_size: majorState.value.pageSize,
    })
    majorState.value.items = res.data.items
    majorState.value.total = res.data.total
  } catch (error) {
    errorBanner.value = 'Không tải được dữ liệu chuyên ngành.'
    toast.add({ severity: 'error', summary: 'Lỗi', detail: apiError(error), life: 4000 })
  } finally {
    majorState.value.loading = false
  }
}

function debounceLevels() {
  if (levelSearchTimer) clearTimeout(levelSearchTimer)
  levelSearchTimer = setTimeout(() => {
    levelState.value.page = 1
    void loadLevels()
  }, 300)
}

function debounceInstitutions() {
  if (institutionSearchTimer) clearTimeout(institutionSearchTimer)
  institutionSearchTimer = setTimeout(() => {
    institutionState.value.page = 1
    void loadInstitutions()
  }, 300)
}

function debounceMajors() {
  if (majorSearchTimer) clearTimeout(majorSearchTimer)
  majorSearchTimer = setTimeout(() => {
    majorState.value.page = 1
    void loadMajors()
  }, 300)
}

function handleLevelFilterChange() {
  levelState.value.page = 1
  void loadLevels()
}

function handleInstitutionFilterChange() {
  institutionState.value.page = 1
  void loadInstitutions()
}

function handleMajorFilterChange() {
  majorState.value.page = 1
  void loadMajors()
}

function onLevelPage(event: { page?: number; rows?: number }) {
  levelState.value.page = (event.page ?? 0) + 1
  levelState.value.pageSize = event.rows ?? levelState.value.pageSize
  void loadLevels()
}

function onInstitutionPage(event: { page?: number; rows?: number }) {
  institutionState.value.page = (event.page ?? 0) + 1
  institutionState.value.pageSize = event.rows ?? institutionState.value.pageSize
  void loadInstitutions()
}

function onMajorPage(event: { page?: number; rows?: number }) {
  majorState.value.page = (event.page ?? 0) + 1
  majorState.value.pageSize = event.rows ?? majorState.value.pageSize
  void loadMajors()
}

function resetLevelForm() {
  levelForm.value = { code: '', name: '', rank_no: null, is_active: true }
  levelErrors.value = {}
  editingLevel.value = null
}

function resetInstitutionForm() {
  institutionForm.value = {
    code: '',
    name: '',
    short_name: '',
    institution_type: null,
    country_code: 'VN',
    province_code: '',
    is_active: true,
  }
  institutionErrors.value = {}
  editingInstitution.value = null
}

function resetMajorForm() {
  majorForm.value = { code: '', name: '', major_group: null, is_active: true }
  majorErrors.value = {}
  editingMajor.value = null
}

function openCreate(kind: TabKey) {
  activeDialogKind.value = kind
  dialogVisible.value = true
  if (kind === 'levels') {
    resetLevelForm()
    return
  }
  if (kind === 'institutions') {
    resetInstitutionForm()
    return
  }
  resetMajorForm()
}

function openEdit(kind: 'levels', row: EducationLevelRead): void
function openEdit(kind: 'institutions', row: EducationalInstitutionRead): void
function openEdit(kind: 'majors', row: EducationMajorRead): void
function openEdit(kind: TabKey, row: EducationLevelRead | EducationalInstitutionRead | EducationMajorRead) {
  activeDialogKind.value = kind
  dialogVisible.value = true

  if (kind === 'levels') {
    const level = row as EducationLevelRead
    editingLevel.value = level
    levelErrors.value = {}
    levelForm.value = {
      code: level.code,
      name: level.name,
      rank_no: level.rank_no,
      is_active: level.is_active,
    }
    return
  }

  if (kind === 'institutions') {
    const institution = row as EducationalInstitutionRead
    editingInstitution.value = institution
    institutionErrors.value = {}
    institutionForm.value = {
      code: institution.code || '',
      name: institution.name,
      short_name: institution.short_name || '',
      institution_type: (institution.institution_type as InstitutionFormState['institution_type']) || null,
      country_code: institution.country_code || 'VN',
      province_code: institution.province_code || '',
      is_active: institution.is_active,
    }
    return
  }

  const major = row as EducationMajorRead
  editingMajor.value = major
  majorErrors.value = {}
  majorForm.value = {
    code: major.code || '',
    name: major.name,
    major_group: major.major_group,
    is_active: major.is_active,
  }
}

function validateLevelForm() {
  levelErrors.value = {}
  if (!editingLevel.value && !levelForm.value.code.trim()) levelErrors.value.code = 'Mã trình độ không được để trống'
  if (!levelForm.value.name.trim()) levelErrors.value.name = 'Tên trình độ không được để trống'
  if (!levelForm.value.rank_no) levelErrors.value.rank_no = 'Thứ bậc không được để trống'
  return Object.keys(levelErrors.value).length === 0
}

function validateInstitutionForm() {
  institutionErrors.value = {}
  if (!institutionForm.value.name.trim()) institutionErrors.value.name = 'Tên trường không được để trống'
  return Object.keys(institutionErrors.value).length === 0
}

function validateMajorForm() {
  majorErrors.value = {}
  if (!majorForm.value.name.trim()) majorErrors.value.name = 'Tên chuyên ngành không được để trống'
  return Object.keys(majorErrors.value).length === 0
}

async function submitLevelForm() {
  if (!validateLevelForm()) return
  submitting.value = true
  try {
    if (editingLevel.value) {
      await educationCatalogService.updateEducationLevel(editingLevel.value.id, {
        name: levelForm.value.name.trim(),
        rank_no: levelForm.value.rank_no || undefined,
        is_active: levelForm.value.is_active,
      })
      toast.add({ severity: 'success', summary: 'Thành công', detail: 'Đã cập nhật trình độ học vấn', life: 3000 })
    } else {
      await educationCatalogService.createEducationLevel({
        code: levelForm.value.code.trim(),
        name: levelForm.value.name.trim(),
        rank_no: levelForm.value.rank_no || 0,
        is_active: levelForm.value.is_active,
      })
      toast.add({ severity: 'success', summary: 'Thành công', detail: 'Đã tạo trình độ học vấn mới', life: 3000 })
    }
    dialogVisible.value = false
    await loadLevels()
  } catch (error) {
    toast.add({ severity: 'error', summary: 'Lỗi', detail: apiError(error), life: 5000 })
  } finally {
    submitting.value = false
  }
}

async function submitInstitutionForm() {
  if (!validateInstitutionForm()) return
  submitting.value = true
  try {
    const payload = {
      name: institutionForm.value.name.trim(),
      short_name: institutionForm.value.short_name.trim() || null,
      institution_type: institutionForm.value.institution_type,
      country_code: institutionForm.value.country_code.trim() || null,
      province_code: institutionForm.value.province_code.trim() || null,
      is_active: institutionForm.value.is_active,
    }

    if (editingInstitution.value) {
      await educationCatalogService.updateEducationalInstitution(editingInstitution.value.id, payload)
      toast.add({ severity: 'success', summary: 'Thành công', detail: 'Đã cập nhật trường học', life: 3000 })
    } else {
      await educationCatalogService.createEducationalInstitution({
        code: institutionForm.value.code.trim() || null,
        ...payload,
      })
      toast.add({ severity: 'success', summary: 'Thành công', detail: 'Đã tạo trường học mới', life: 3000 })
    }
    dialogVisible.value = false
    await loadInstitutions()
  } catch (error) {
    toast.add({ severity: 'error', summary: 'Lỗi', detail: apiError(error), life: 5000 })
  } finally {
    submitting.value = false
  }
}

async function submitMajorForm() {
  if (!validateMajorForm()) return
  submitting.value = true
  try {
    const payload = {
      name: majorForm.value.name.trim(),
      major_group: majorForm.value.major_group,
      is_active: majorForm.value.is_active,
    }

    if (editingMajor.value) {
      await educationCatalogService.updateEducationMajor(editingMajor.value.id, payload)
      toast.add({ severity: 'success', summary: 'Thành công', detail: 'Đã cập nhật chuyên ngành', life: 3000 })
    } else {
      await educationCatalogService.createEducationMajor({
        code: majorForm.value.code.trim() || null,
        ...payload,
      })
      toast.add({ severity: 'success', summary: 'Thành công', detail: 'Đã tạo chuyên ngành mới', life: 3000 })
    }
    dialogVisible.value = false
    await loadMajors()
  } catch (error) {
    toast.add({ severity: 'error', summary: 'Lỗi', detail: apiError(error), life: 5000 })
  } finally {
    submitting.value = false
  }
}

function submitActiveForm() {
  if (activeDialogKind.value === 'levels') {
    void submitLevelForm()
    return
  }
  if (activeDialogKind.value === 'institutions') {
    void submitInstitutionForm()
    return
  }
  void submitMajorForm()
}

function confirmDelete(kind: 'levels', row: EducationLevelRead): void
function confirmDelete(kind: 'institutions', row: EducationalInstitutionRead): void
function confirmDelete(kind: 'majors', row: EducationMajorRead): void
function confirmDelete(kind: TabKey, row: EducationLevelRead | EducationalInstitutionRead | EducationMajorRead) {
  const label = kind === 'levels' ? 'trình độ học vấn' : kind === 'institutions' ? 'trường học' : 'chuyên ngành'
  const rowName = row.name
  confirm.require({
    message: `Bạn có chắc chắn muốn khóa ${label} "${rowName}"?`,
    header: 'Xác nhận thao tác',
    icon: 'pi pi-exclamation-triangle',
    acceptLabel: 'Khóa',
    rejectLabel: 'Hủy',
    acceptClass: 'p-button-danger',
    accept: async () => {
      try {
        if (kind === 'levels') {
          const res = await educationCatalogService.deleteEducationLevel((row as EducationLevelRead).id)
          toast.add({ severity: 'success', summary: 'Thành công', detail: res.data.message, life: 3000 })
          await loadLevels()
          return
        }
        if (kind === 'institutions') {
          const res = await educationCatalogService.deleteEducationalInstitution((row as EducationalInstitutionRead).id)
          toast.add({ severity: 'success', summary: 'Thành công', detail: res.data.message, life: 3000 })
          await loadInstitutions()
          return
        }
        const res = await educationCatalogService.deleteEducationMajor((row as EducationMajorRead).id)
        toast.add({ severity: 'success', summary: 'Thành công', detail: res.data.message, life: 3000 })
        await loadMajors()
      } catch (error) {
        toast.add({ severity: 'error', summary: 'Lỗi', detail: apiError(error), life: 5000 })
      }
    },
  })
}

watch(activeTab, (tab) => {
  if (tab === 'levels' && levelState.value.items.length === 0) {
    void loadLevels()
  }
  if (tab === 'institutions' && institutionState.value.items.length === 0) {
    void loadInstitutions()
  }
  if (tab === 'majors' && majorState.value.items.length === 0) {
    void loadMajors()
  }
})

onMounted(async () => {
  errorBanner.value = ''
  await Promise.all([loadLevels(), loadInstitutions(), loadMajors()])
})
</script>

<style scoped>
.education-catalog {
  --catalog-surface: var(--l-surface);
  --catalog-surface-soft: color-mix(in srgb, var(--l-surface) 90%, var(--l-bg) 10%);
  --catalog-border: var(--l-border);
  --catalog-text: var(--l-text);
  --catalog-text-muted: var(--l-text-muted);
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
  color: var(--catalog-text);
}

.hero-panel {
  display: grid;
  grid-template-columns: minmax(0, 1.6fr) minmax(320px, 0.95fr);
  gap: 1rem;
  padding: 1.5rem;
  border-radius: 28px;
  border: 1px solid color-mix(in srgb, var(--p-primary-color) 24%, var(--catalog-border));
  background:
    radial-gradient(circle at top left, color-mix(in srgb, var(--p-primary-color) 12%, transparent), transparent 40%),
    linear-gradient(
      140deg,
      color-mix(in srgb, var(--catalog-surface) 92%, var(--p-primary-color) 8%),
      color-mix(in srgb, var(--catalog-surface-soft) 88%, var(--l-bg) 12%)
    );
  box-shadow: var(--l-shadow-lg);
}

.hero-copy {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.hero-copy h1,
.workspace-head h2 {
  margin: 0;
}

.hero-copy h1 {
  font-size: clamp(1.9rem, 2.8vw, 2.6rem);
  line-height: 1.05;
}

.eyebrow,
.section-kicker,
.signal-label,
.stat-label {
  letter-spacing: 0.08em;
  text-transform: uppercase;
  font-size: 0.73rem;
  font-weight: 700;
  color: color-mix(in srgb, var(--p-primary-color) 72%, var(--catalog-text-muted));
}

.hero-text,
.signal-note,
.scope-list,
.stat-footnote {
  color: var(--catalog-text-muted);
}

.hero-text {
  max-width: 64ch;
  margin: 0;
  line-height: 1.7;
}

.hero-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
}

.hero-side {
  display: grid;
  gap: 0.9rem;
}

.signal-card,
.stat-card,
.workspace-card {
  border-radius: 22px;
  border: 1px solid color-mix(in srgb, var(--catalog-border) 86%, var(--p-primary-color) 14%);
  background: var(--catalog-surface);
}

.signal-card {
  padding: 1rem 1.1rem;
}

.signal-card.muted {
  background: var(--catalog-surface-soft);
}

.signal-head,
.workspace-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1rem;
}

.signal-value {
  margin: 0.8rem 0 0.35rem;
  font-size: 1.05rem;
  font-weight: 700;
  line-height: 1.45;
}

.signal-note {
  margin: 0;
  line-height: 1.55;
}

.scope-list {
  margin: 0.85rem 0 0;
  padding-left: 1rem;
  display: grid;
  gap: 0.45rem;
  line-height: 1.55;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 1rem;
}

.stat-card {
  display: flex;
  gap: 1rem;
  padding: 1rem 1.1rem;
  align-items: flex-start;
}

.stat-icon {
  width: 3rem;
  height: 3rem;
  border-radius: 16px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 1.2rem;
}

.stat-body {
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
}

.stat-value {
  font-size: 1.8rem;
  line-height: 1;
}

.tone-teal {
  background: color-mix(in srgb, var(--p-primary-color) 16%, var(--catalog-surface));
  color: var(--p-primary-color);
}

.tone-amber {
  background: color-mix(in srgb, var(--p-orange-500) 15%, var(--catalog-surface));
  color: var(--p-orange-600);
}

.tone-slate {
  background: color-mix(in srgb, var(--p-surface-400) 18%, var(--catalog-surface));
  color: var(--catalog-text);
}

.status-banner {
  display: flex;
  align-items: center;
  gap: 0.65rem;
  padding: 0.9rem 1rem;
  border-radius: 16px;
}

.status-banner.danger {
  border: 1px solid color-mix(in srgb, var(--p-red-500) 26%, var(--catalog-border));
  background: color-mix(in srgb, var(--p-red-500) 10%, var(--catalog-surface));
  color: color-mix(in srgb, var(--p-red-600) 65%, var(--catalog-text));
}

.workspace-card {
  padding: 1rem 1rem 1.15rem;
}

.workspace-head {
  padding-bottom: 1rem;
}

.toolbar {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
  align-items: center;
  margin-bottom: 1rem;
}

.toolbar-filter {
  min-width: 150px;
}

.toolbar-search {
  min-width: 240px;
  flex: 1;
}

.stacked-cell {
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
}

.stacked-cell small {
  color: var(--catalog-text-muted);
}

.action-cell {
  display: flex;
  justify-content: flex-end;
  gap: 0.15rem;
}

.form-shell {
  display: flex;
  flex-direction: column;
  gap: 0.85rem;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}

.field-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.85rem;
}

.field-switch {
  gap: 0.6rem;
}

.switch-row {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.req,
.error-msg {
  color: #dc2626;
}

.active-label {
  color: #15803d;
  font-weight: 500;
}

.inactive-label {
  color: #b91c1c;
  font-weight: 500;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.75rem;
  padding: 2rem 0;
  color: var(--catalog-text-muted);
}

@media (max-width: 1100px) {
  .hero-panel,
  .stats-grid {
    grid-template-columns: 1fr;
  }

  .workspace-head {
    flex-direction: column;
    align-items: stretch;
  }
}

@media (max-width: 768px) {
  .hero-actions,
  .toolbar {
    flex-direction: column;
    align-items: stretch;
  }

  .field-row {
    grid-template-columns: 1fr;
  }

  .toolbar-filter,
  .toolbar-search {
    min-width: 100%;
  }
}
</style>
