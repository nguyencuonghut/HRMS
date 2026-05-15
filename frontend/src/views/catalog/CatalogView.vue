<template>
  <div class="catalog-overview">
    <section class="hero-panel">
      <div class="hero-copy">
        <span class="eyebrow">Catalog Control Center</span>
        <h1>Tổng quan danh mục</h1>
        <p class="hero-text">
          Theo dõi độ sẵn sàng của dữ liệu nền, đi nhanh vào các màn quản trị chính và kiểm
          soát hai hệ địa chỉ cũ/mới trước khi tích hợp sâu với hồ sơ nhân sự.
        </p>
        <div class="hero-actions">
          <Button
            label="Mở danh mục hành chính"
            icon="pi pi-map"
            @click="router.push('/catalog/administrative-units')"
          />
          <Button
            label="Mở danh mục học vấn"
            icon="pi pi-graduation-cap"
            severity="secondary"
            @click="router.push('/catalog/education')"
          />
          <Button
            label="Mở danh mục nghiệp vụ khác"
            icon="pi pi-briefcase"
            severity="secondary"
            @click="router.push('/catalog/other-business')"
          />
          <Button
            label="Xem lịch sử import"
            icon="pi pi-history"
            severity="secondary"
            outlined
            @click="router.push('/catalog/administrative-imports')"
          />
        </div>
      </div>

      <div class="hero-side">
        <div class="signal-card">
          <div class="signal-head">
            <span class="signal-label">Trạng thái hiện tại</span>
            <Tag :value="importHealth.label" :severity="importHealth.severity" rounded />
          </div>
          <p class="signal-value">{{ importHeadline }}</p>
          <p class="signal-note">{{ importSubline }}</p>
        </div>

        <div class="signal-card muted">
          <div class="signal-head">
            <span class="signal-label">Phạm vi quản trị</span>
          </div>
          <ul class="scope-list">
            <li>Danh mục hành chính hệ mới 2 cấp</li>
            <li>Danh mục hành chính hệ cũ 3 cấp</li>
            <li>Danh mục học vấn cho hồ sơ nhân sự</li>
            <li>Danh mục nghiệp vụ khác cho hợp đồng và nghỉ phép</li>
            <li>Lịch sử import và rà soát batch lỗi</li>
          </ul>
        </div>
      </div>
    </section>

    <section class="stats-grid">
      <article v-for="stat in stats" :key="stat.label" class="stat-card">
        <div class="stat-icon" :class="`tone-${stat.tone}`">
          <i :class="['pi', stat.icon]" />
        </div>
        <div class="stat-body">
          <span class="stat-label">{{ stat.label }}</span>
          <strong class="stat-value">{{ stat.value }}</strong>
          <span class="stat-footnote">{{ stat.footnote }}</span>
        </div>
      </article>
    </section>

    <div v-if="errorMessage" class="status-banner danger">
      <i class="pi pi-exclamation-triangle" />
      <span>{{ errorMessage }}</span>
    </div>

    <section class="content-grid">
      <article class="feature-card">
        <div class="section-head">
          <div>
            <span class="section-kicker">Điểm vào chính</span>
            <h2>Module đang vận hành</h2>
          </div>
          <Button
            icon="pi pi-refresh"
            severity="secondary"
            text
            rounded
            :loading="loading"
            v-tooltip.top="'Làm mới dữ liệu'"
            @click="loadOverview"
          />
        </div>

        <div class="module-list">
          <RouterLink to="/catalog/administrative-units" class="module-card primary">
            <div class="module-meta">
              <div class="module-icon">
                <i class="pi pi-map" />
              </div>
              <div>
                <h3>Danh mục hành chính</h3>
                <p>Quản trị cây địa chỉ cũ/mới, khóa dữ liệu và thao tác CRUD trực tiếp.</p>
              </div>
            </div>
            <div class="module-tail">
              <div class="module-stat">
                <span>Đơn vị active</span>
                <strong>{{ formatNumber(statsSnapshot.newUnits + statsSnapshot.oldUnits) }}</strong>
              </div>
              <span class="module-link">Mở màn quản trị</span>
            </div>
          </RouterLink>

          <RouterLink to="/catalog/administrative-imports" class="module-card secondary">
            <div class="module-meta">
              <div class="module-icon secondary">
                <i class="pi pi-download" />
              </div>
              <div>
                <h3>Lịch sử import địa chỉ</h3>
                <p>Theo dõi batch, kết quả xử lý, lỗi dữ liệu và trạng thái đồng bộ nguồn.</p>
              </div>
            </div>
            <div class="module-tail">
              <div class="module-stat">
                <span>Tổng batch</span>
                <strong>{{ formatNumber(statsSnapshot.importBatches) }}</strong>
              </div>
              <span class="module-link">Xem lịch sử</span>
            </div>
          </RouterLink>

          <RouterLink to="/catalog/education" class="module-card tertiary">
            <div class="module-meta">
              <div class="module-icon tertiary">
                <i class="pi pi-graduation-cap" />
              </div>
              <div>
                <h3>Danh mục học vấn</h3>
                <p>Quản trị trình độ, trường học và chuyên ngành cho phần học vấn nhân sự.</p>
              </div>
            </div>
            <div class="module-tail">
              <div class="module-stat">
                <span>Bản ghi active</span>
                <strong>{{ formatNumber(statsSnapshot.educationLevels + statsSnapshot.educationInstitutions + statsSnapshot.educationMajors) }}</strong>
              </div>
              <span class="module-link">Mở workspace học vấn</span>
            </div>
          </RouterLink>

          <RouterLink to="/catalog/other-business" class="module-card quaternary">
            <div class="module-meta">
              <div class="module-icon quaternary">
                <i class="pi pi-briefcase" />
              </div>
              <div>
                <h3>Danh mục nghiệp vụ khác</h3>
                <p>Quản trị loại hợp đồng, nhân thân, ngân hàng, nghỉ phép, kỹ năng và mẫu hợp đồng.</p>
              </div>
            </div>
            <div class="module-tail">
              <div class="module-stat">
                <span>Nhóm dữ liệu</span>
                <strong>2.3</strong>
              </div>
              <span class="module-link">Mở workspace nghiệp vụ</span>
            </div>
          </RouterLink>
        </div>
      </article>

      <article class="feature-card">
        <div class="section-head">
          <div>
            <span class="section-kicker">Dữ liệu nền</span>
            <h2>Độ phủ danh mục</h2>
          </div>
        </div>

        <div class="coverage-list">
          <div class="coverage-row">
            <div>
              <strong>Hệ mới</strong>
              <span>{{ formatNumber(statsSnapshot.newProvinces) }} tỉnh/thành đang hoạt động</span>
            </div>
            <Tag value="2 cấp" severity="info" rounded />
          </div>
          <div class="coverage-row">
            <div>
              <strong>Hệ cũ</strong>
              <span>{{ formatNumber(statsSnapshot.oldProvinces) }} tỉnh/thành đang hoạt động</span>
            </div>
            <Tag value="3 cấp" severity="contrast" rounded />
          </div>
          <div class="coverage-row">
            <div>
              <strong>Batch import thành công</strong>
              <span>{{ formatNumber(successfulImportCount) }} batch đã hoàn tất không lỗi hệ thống</span>
            </div>
            <Tag value="Import" severity="success" rounded />
          </div>
        </div>

        <div class="guidance-callout">
          <i class="pi pi-info-circle" />
          <p>
            Màn này dùng số liệu runtime từ API hiện tại. Khi import mới hoặc khóa đơn vị,
            các chỉ số sẽ đổi theo dữ liệu thật thay vì mô tả tĩnh.
          </p>
        </div>
      </article>
    </section>

    <section class="timeline-card">
      <div class="section-head">
        <div>
          <span class="section-kicker">Lần đồng bộ gần nhất</span>
          <h2>Dấu vết import gần đây</h2>
        </div>
      </div>

      <div v-if="latestBatch" class="timeline-grid">
        <div class="timeline-block">
          <span class="timeline-label">Nguồn</span>
          <strong>{{ latestBatch.source_name }}</strong>
          <small>{{ latestBatch.source_version }}</small>
        </div>
        <div class="timeline-block">
          <span class="timeline-label">Kết quả</span>
          <strong>{{ formatNumber(latestBatch.success_rows) }} / {{ formatNumber(latestBatch.total_rows) }}</strong>
          <small>{{ latestBatch.failed_rows }} lỗi dữ liệu</small>
        </div>
        <div class="timeline-block">
          <span class="timeline-label">Thời gian</span>
          <strong>{{ formatDateTime(latestBatch.imported_at) }}</strong>
          <small>{{ latestBatch.file_name || 'Không có tên file' }}</small>
        </div>
      </div>
      <div v-else class="empty-panel">
        <i class="pi pi-inbox" />
        <span>Chưa có batch import nào để hiển thị.</span>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import Button from 'primevue/button'
import Tag from 'primevue/tag'

import administrativeUnitService, {
  type AdministrativeImportBatchRead,
} from '@/services/administrativeUnitService'
import educationCatalogService from '@/services/educationCatalogService'

type Severity = 'success' | 'info' | 'warning' | 'danger' | 'contrast'
type Tone = 'teal' | 'amber' | 'slate' | 'rose'

interface OverviewStats {
  newUnits: number
  oldUnits: number
  newProvinces: number
  oldProvinces: number
  importBatches: number
  educationLevels: number
  educationInstitutions: number
  educationMajors: number
}

interface StatItem {
  label: string
  value: string
  footnote: string
  icon: string
  tone: Tone
}

const router = useRouter()

const loading = ref(false)
const errorMessage = ref('')
const batches = ref<AdministrativeImportBatchRead[]>([])
const statsSnapshot = ref<OverviewStats>({
  newUnits: 0,
  oldUnits: 0,
  newProvinces: 0,
  oldProvinces: 0,
  importBatches: 0,
  educationLevels: 0,
  educationInstitutions: 0,
  educationMajors: 0,
})

function formatNumber(value: number) {
  return new Intl.NumberFormat('vi-VN').format(value)
}

function formatDateTime(value: string) {
  return new Date(value).toLocaleString('vi-VN')
}

const latestBatch = computed(() =>
  [...batches.value].sort((a, b) => Date.parse(b.imported_at) - Date.parse(a.imported_at))[0] ?? null,
)

const successfulImportCount = computed(
  () => batches.value.filter((batch) => batch.status === 'success').length,
)

const importHealth = computed<{ label: string; severity: Severity }>(() => {
  if (!latestBatch.value) return { label: 'Chưa có batch', severity: 'contrast' }
  if (latestBatch.value.status === 'failed') return { label: 'Có lỗi import', severity: 'danger' }
  if (latestBatch.value.failed_rows > 0) return { label: 'Cần rà soát dữ liệu', severity: 'warning' }
  return { label: 'Ổn định', severity: 'success' }
})

const importHeadline = computed(() => {
  if (!latestBatch.value) return 'Hệ thống chưa có lịch sử đồng bộ địa chỉ.'
  return `Batch gần nhất: ${latestBatch.value.source_name} (${latestBatch.value.source_version})`
})

const importSubline = computed(() => {
  if (!latestBatch.value) return 'Chạy import đầu tiên để tạo baseline cho dữ liệu danh mục.'
  return `Thành công ${formatNumber(latestBatch.value.success_rows)} / ${formatNumber(latestBatch.value.total_rows)} dòng, lỗi ${formatNumber(latestBatch.value.failed_rows)} dòng.`
})

const stats = computed<StatItem[]>(() => [
  {
    label: 'Đơn vị active hệ mới',
    value: formatNumber(statsSnapshot.value.newUnits),
    footnote: `${formatNumber(statsSnapshot.value.newProvinces)} tỉnh/thành đã seed`,
    icon: 'pi-sitemap',
    tone: 'teal',
  },
  {
    label: 'Đơn vị active hệ cũ',
    value: formatNumber(statsSnapshot.value.oldUnits),
    footnote: `${formatNumber(statsSnapshot.value.oldProvinces)} tỉnh/thành đã seed`,
    icon: 'pi-building-columns',
    tone: 'amber',
  },
  {
    label: 'Batch import đã ghi nhận',
    value: formatNumber(statsSnapshot.value.importBatches),
    footnote: `${formatNumber(successfulImportCount.value)} batch trạng thái success`,
    icon: 'pi-history',
    tone: 'slate',
  },
  {
    label: 'Mức sẵn sàng',
    value: importHealth.value.label,
    footnote: latestBatch.value ? 'Dựa trên batch import gần nhất' : 'Chưa có dữ liệu import',
    icon: 'pi-shield',
    tone: 'rose',
  },
])

async function loadOverview() {
  loading.value = true
  errorMessage.value = ''
  try {
    const [
      newUnitsRes,
      oldUnitsRes,
      newProvincesRes,
      oldProvincesRes,
      importBatchesRes,
      educationLevelsRes,
      educationInstitutionsRes,
      educationMajorsRes,
    ] = await Promise.all([
      administrativeUnitService.getList({
        system_type: 'new',
        is_active: true,
        page: 1,
        page_size: 1,
      }),
      administrativeUnitService.getList({
        system_type: 'old',
        is_active: true,
        page: 1,
        page_size: 1,
      }),
      administrativeUnitService.listProvinces({
        system_type: 'new',
        is_active: true,
      }),
      administrativeUnitService.listProvinces({
        system_type: 'old',
        is_active: true,
      }),
      administrativeUnitService.listImportBatches(),
      educationCatalogService.getEducationLevels({ is_active: true, page: 1, page_size: 1 }),
      educationCatalogService.getEducationalInstitutions({ is_active: true, page: 1, page_size: 1 }),
      educationCatalogService.getEducationMajors({ is_active: true, page: 1, page_size: 1 }),
    ])

    batches.value = importBatchesRes.data
    statsSnapshot.value = {
      newUnits: newUnitsRes.data.total,
      oldUnits: oldUnitsRes.data.total,
      newProvinces: newProvincesRes.data.length,
      oldProvinces: oldProvincesRes.data.length,
      importBatches: importBatchesRes.data.length,
      educationLevels: educationLevelsRes.data.total,
      educationInstitutions: educationInstitutionsRes.data.total,
      educationMajors: educationMajorsRes.data.total,
    }
  } catch {
    errorMessage.value = 'Không tải được dữ liệu tổng quan danh mục. Vui lòng thử lại.'
  } finally {
    loading.value = false
  }
}

onMounted(loadOverview)
</script>

<style scoped>
.catalog-overview {
  --catalog-surface: var(--l-surface);
  --catalog-surface-soft: color-mix(in srgb, var(--l-surface) 88%, var(--l-bg) 12%);
  --catalog-surface-hero: color-mix(in srgb, var(--l-surface) 92%, var(--l-bg) 8%);
  --catalog-border: var(--l-border);
  --catalog-text: var(--l-text);
  --catalog-text-muted: var(--l-text-muted);
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
  color: var(--catalog-text);
}

.hero-panel {
  display: grid;
  grid-template-columns: minmax(0, 1.5fr) minmax(320px, 0.9fr);
  gap: 1rem;
  padding: 1.5rem;
  border-radius: 28px;
  border: 1px solid color-mix(in srgb, var(--p-primary-color) 22%, var(--catalog-border));
  background:
    radial-gradient(circle at top left, color-mix(in srgb, var(--p-primary-color) 14%, transparent), transparent 38%),
    linear-gradient(
      145deg,
      color-mix(in srgb, var(--catalog-surface-hero) 92%, var(--p-primary-color) 8%),
      color-mix(in srgb, var(--catalog-surface) 84%, var(--l-bg) 16%)
    );
  box-shadow: var(--l-shadow-lg);
}

.eyebrow,
.section-kicker,
.signal-label,
.timeline-label,
.stat-label {
  letter-spacing: 0.08em;
  text-transform: uppercase;
  font-size: 0.73rem;
  font-weight: 700;
}

.eyebrow,
.section-kicker,
.signal-label,
.timeline-label {
  color: color-mix(in srgb, var(--p-primary-color) 72%, var(--p-text-muted-color));
}

.hero-copy {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.hero-copy h1 {
  margin: 0;
  font-size: clamp(2rem, 3vw, 2.75rem);
  line-height: 1.05;
}

.hero-text {
  max-width: 62ch;
  margin: 0;
  color: var(--catalog-text-muted);
  font-size: 1rem;
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
.feature-card,
.timeline-card,
.stat-card {
  border-radius: 22px;
  border: 1px solid color-mix(in srgb, var(--catalog-border) 86%, var(--p-primary-color) 14%);
  background: var(--catalog-surface);
  color: var(--catalog-text);
}

.signal-card {
  padding: 1rem 1.1rem;
}

.signal-card.muted {
  background: var(--catalog-surface-soft);
}

.signal-head,
.section-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1rem;
}

.signal-value {
  margin: 0.85rem 0 0.35rem;
  font-size: 1.05rem;
  font-weight: 700;
  line-height: 1.4;
}

.signal-note {
  margin: 0;
  color: var(--catalog-text-muted);
  line-height: 1.55;
}

.scope-list {
  margin: 0.85rem 0 0;
  padding-left: 1rem;
  color: var(--catalog-text-muted);
  display: grid;
  gap: 0.45rem;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 1rem;
}

.stat-card {
  display: flex;
  gap: 1rem;
  align-items: flex-start;
  padding: 1rem 1.05rem;
  min-height: 128px;
}

.stat-icon {
  width: 3rem;
  height: 3rem;
  border-radius: 16px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  font-size: 1.25rem;
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
  background: color-mix(in srgb, var(--catalog-border) 25%, var(--catalog-surface));
  color: var(--catalog-text);
}

.tone-rose {
  background: color-mix(in srgb, var(--p-pink-500) 16%, var(--catalog-surface));
  color: var(--p-pink-600);
}

.stat-body {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}

.stat-value {
  font-size: 1.65rem;
  line-height: 1.05;
}

.stat-footnote {
  color: var(--catalog-text-muted);
  line-height: 1.45;
  font-size: 0.92rem;
}

.status-banner {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.95rem 1rem;
  border-radius: 18px;
  border: 1px solid;
}

.status-banner.danger {
  color: color-mix(in srgb, var(--p-red-600) 85%, var(--p-text-color));
  background: color-mix(in srgb, var(--p-red-500) 10%, var(--catalog-surface));
  border-color: color-mix(in srgb, var(--p-red-500) 22%, var(--catalog-border));
}

.content-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.3fr) minmax(320px, 0.9fr);
  gap: 1rem;
}

.feature-card,
.timeline-card {
  padding: 1.25rem;
}

.section-head h2 {
  margin: 0.2rem 0 0;
  font-size: 1.35rem;
}

.module-list,
.coverage-list {
  display: grid;
  gap: 0.9rem;
  margin-top: 1rem;
}

.module-card {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
  padding: 1rem;
  border-radius: 20px;
  border: 1px solid color-mix(in srgb, var(--catalog-border) 82%, var(--p-primary-color) 18%);
  background:
    linear-gradient(
      180deg,
      color-mix(in srgb, var(--catalog-surface) 94%, var(--l-bg) 6%),
      color-mix(in srgb, var(--catalog-surface) 88%, var(--l-bg) 12%)
    );
  color: inherit;
  text-decoration: none;
  transition: transform 0.18s ease, border-color 0.18s ease, box-shadow 0.18s ease;
}

.module-card:hover {
  transform: translateY(-2px);
  border-color: color-mix(in srgb, var(--p-primary-color) 32%, var(--catalog-border));
  box-shadow: var(--l-shadow);
}

.module-meta {
  display: flex;
  gap: 0.9rem;
  align-items: flex-start;
}

.module-icon {
  width: 2.75rem;
  height: 2.75rem;
  border-radius: 14px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  background: color-mix(in srgb, var(--p-primary-color) 18%, var(--catalog-surface));
  color: var(--p-primary-color);
}

.module-icon.secondary {
  background: color-mix(in srgb, var(--p-orange-500) 16%, var(--catalog-surface));
  color: var(--p-orange-600);
}

.module-icon.tertiary {
  background: color-mix(in srgb, var(--p-blue-500) 14%, var(--catalog-surface));
  color: var(--p-blue-600);
}

.module-meta h3,
.coverage-row strong,
.timeline-block strong {
  margin: 0;
}

.module-meta p {
  margin: 0.35rem 0 0;
  color: var(--catalog-text-muted);
  line-height: 1.55;
}

.module-tail {
  min-width: 150px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  align-items: flex-end;
  gap: 0.75rem;
}

.module-stat {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 0.2rem;
}

.module-stat span,
.coverage-row span,
.timeline-block small,
.module-link {
  color: var(--catalog-text-muted);
}

.module-stat strong,
.timeline-block strong {
  font-size: 1.2rem;
}

.module-link {
  font-weight: 700;
}

.coverage-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 1rem;
  padding: 0.95rem 1rem;
  border-radius: 18px;
  background: var(--catalog-surface-soft);
}

.coverage-row > div {
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
}

.guidance-callout {
  margin-top: 1rem;
  display: flex;
  gap: 0.8rem;
  padding: 0.95rem 1rem;
  border-radius: 18px;
  background: color-mix(in srgb, var(--p-primary-color) 8%, var(--catalog-surface));
  color: var(--catalog-text-muted);
}

.guidance-callout p {
  margin: 0;
  line-height: 1.55;
}

.timeline-grid {
  margin-top: 1rem;
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 0.9rem;
}

.timeline-block {
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
  padding: 1rem;
  border-radius: 18px;
  background: var(--catalog-surface-soft);
}

.empty-panel {
  margin-top: 1rem;
  min-height: 140px;
  border-radius: 20px;
  border: 1px dashed var(--catalog-border);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 0.75rem;
  color: var(--catalog-text-muted);
}

@media (max-width: 1200px) {
  .stats-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .content-grid,
  .hero-panel,
  .timeline-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .catalog-overview {
    gap: 1rem;
  }

  .hero-panel,
  .feature-card,
  .timeline-card {
    padding: 1rem;
  }

  .hero-actions,
  .module-card,
  .coverage-row,
  .section-head {
    flex-direction: column;
  }

  .stats-grid {
    grid-template-columns: 1fr;
  }

  .module-tail,
  .module-stat {
    align-items: flex-start;
  }
}
</style>
