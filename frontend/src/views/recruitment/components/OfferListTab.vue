<template>
  <div class="section-stack" style="padding-top: 0.75rem">
    <div class="section-card">
      <div class="section-header">
        <span class="section-title">Danh sách Offer</span>
        <Button
          v-if="canCreate"
          label="Tạo Offer"
          icon="pi pi-plus"
          size="small"
          @click="openCreate"
        />
      </div>

      <div v-if="loading" class="rc-jd-empty">Đang tải...</div>
      <div v-else-if="!offers.length" class="rc-jd-empty">Chưa có offer nào.</div>

      <DataTable v-else :value="offers" size="small" class="p-datatable-sm">
        <Column header="Trạng thái" style="width: 130px">
          <template #body="{ data }">
            <Tag :value="data.status_label" :severity="statusSeverity(data.status)" />
          </template>
        </Column>
        <Column header="Lương chính thức" style="width: 160px">
          <template #body="{ data }">
            <span>{{ formatCurrency(data.official_salary) }}</span>
          </template>
        </Column>
        <Column header="Lương thử việc" style="width: 180px">
          <template #body="{ data }">
            <div>
              <span :class="{ 'rc-warning-text': data.probation_salary_warning }">
                {{ formatCurrency(data.probation_salary) }}
              </span>
              <div v-if="data.probation_salary_warning" class="rc-warning-note">
                <i class="pi pi-exclamation-triangle" /> Dưới 85% lương chính thức (vi phạm Điều 24 BLLĐ 2019)
              </div>
            </div>
          </template>
        </Column>
        <Column header="Thử việc (ngày)" style="width: 150px">
          <template #body="{ data }">
            <div>
              <span :class="{ 'rc-warning-text': data.probation_days_warning }">
                {{ data.probation_days }} ngày
              </span>
              <div v-if="data.probation_days_warning" class="rc-warning-note">
                <i class="pi pi-exclamation-triangle" /> Vượt giới hạn {{ data.probation_days_limit }} ngày (Điều 24 BLLĐ 2019)
              </div>
            </div>
          </template>
        </Column>
        <Column header="Ngày bắt đầu" style="width: 130px">
          <template #body="{ data }">{{ data.proposed_start_date }}</template>
        </Column>
        <Column header="Hạn phản hồi" style="width: 120px">
          <template #body="{ data }">{{ data.expires_at ?? '—' }}</template>
        </Column>
        <Column header="" style="width: 200px">
          <template #body="{ data }">
            <div class="rc-action-btns">
              <Button
                v-if="data.status === 'draft'"
                label="Gửi"
                icon="pi pi-send"
                size="small"
                severity="warn"
                outlined
                :loading="actionLoading === `send-${data.id}`"
                @click="sendOffer(data)"
              />
              <Button
                v-if="data.status === 'draft' || data.status === 'negotiating'"
                icon="pi pi-pencil"
                size="small"
                severity="secondary"
                outlined
                @click="openEdit(data)"
              />
              <Button
                v-if="data.status === 'sent' || data.status === 'waiting' || data.status === 'negotiating'"
                label="Chấp nhận"
                size="small"
                severity="success"
                outlined
                :loading="actionLoading === `accept-${data.id}`"
                @click="acceptOffer(data)"
              />
              <Button
                v-if="data.status === 'sent' || data.status === 'waiting' || data.status === 'negotiating'"
                label="Từ chối"
                size="small"
                severity="danger"
                outlined
                @click="openReject(data)"
              />
              <Button
                v-if="data.status === 'accepted' || data.status === 'rejected'"
                label="Quyết định"
                icon="pi pi-file-edit"
                size="small"
                severity="info"
                outlined
                @click="openDecision(data)"
              />
            </div>
          </template>
        </Column>
      </DataTable>
    </div>
  </div>

  <!-- Offer form dialog -->
  <OfferFormDialog
    v-model:visible="showOfferForm"
    :application-id="applicationId"
    :offer="editingOffer"
    :jr-job-position-id="props.jrJobPositionId"
    :jr-dept-id="props.jrDeptId"
    :jr-job-position-name="props.jrJobPositionName"
    :jr-dept-name="props.jrDeptName"
    @saved="onOfferSaved"
  />

  <!-- Reject dialog -->
  <Dialog v-model:visible="showRejectDialog" header="Từ chối Offer" modal :style="{ width: '420px' }">
    <div class="rc-field" style="margin-top: 0.5rem">
      <label class="rc-label">Lý do từ chối <span class="req">*</span></label>
      <Textarea v-model="rejectReason" rows="3" class="w-full" auto-resize />
    </div>
    <template #footer>
      <Button label="Hủy" severity="secondary" outlined @click="showRejectDialog = false" />
      <Button label="Từ chối" severity="danger" :loading="rejectLoading" @click="confirmReject" />
    </template>
  </Dialog>

  <!-- Hiring decision dialog -->
  <HiringDecisionDialog
    v-if="decisionOffer"
    v-model:visible="showDecisionDialog"
    :offer-id="decisionOffer.id"
    :decision="currentDecision"
    :default-dept-id="decisionOffer.department_id"
    :default-pos-id="decisionOffer.job_position_id"
    :default-start-date="decisionOffer.proposed_start_date"
    :default-official-salary="decisionOffer.official_salary"
    :default-probation-salary="decisionOffer.probation_salary"
    :default-probation-days="decisionOffer.probation_days"
    @saved="onDecisionSaved"
    @converted="onConverted"
  />
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import Button from 'primevue/button'
import Column from 'primevue/column'
import DataTable from 'primevue/datatable'
import Dialog from 'primevue/dialog'
import Tag from 'primevue/tag'
import Textarea from 'primevue/textarea'
import { useToast } from 'primevue/usetoast'

import {
  offerService,
  hiringDecisionService,
  type OfferRead,
  type HiringDecisionRead,
  type ConvertToEmployeeResult,
} from '@/services/recruitmentService'
import OfferFormDialog from './OfferFormDialog.vue'
import HiringDecisionDialog from './HiringDecisionDialog.vue'

const props = defineProps<{
  applicationId: number
  canCreate?: boolean
  jrJobPositionId?: number | null
  jrDeptId?: number | null
  jrJobPositionName?: string | null
  jrDeptName?: string | null
}>()

const emit = defineEmits<{
  (e: 'converted', result: ConvertToEmployeeResult): void
}>()

const toast = useToast()
const loading = ref(false)
const offers = ref<OfferRead[]>([])
const actionLoading = ref<string | null>(null)

const showOfferForm = ref(false)
const editingOffer = ref<OfferRead | null>(null)

const showRejectDialog = ref(false)
const rejectingOffer = ref<OfferRead | null>(null)
const rejectReason = ref('')
const rejectLoading = ref(false)

const showDecisionDialog = ref(false)
const decisionOffer = ref<OfferRead | null>(null)
const currentDecision = ref<HiringDecisionRead | null>(null)

function statusSeverity(status: string) {
  const map: Record<string, string> = {
    draft: 'secondary',
    sent: 'info',
    waiting: 'warn',
    negotiating: 'warn',
    accepted: 'success',
    rejected: 'danger',
  }
  return map[status] ?? 'secondary'
}

function formatCurrency(val: string | number) {
  return Number(val).toLocaleString('vi-VN') + ' ₫'
}

async function load() {
  loading.value = true
  try {
    offers.value = await offerService.listForApplication(props.applicationId)
  } finally {
    loading.value = false
  }
}

function openCreate() {
  editingOffer.value = null
  showOfferForm.value = true
}

function openEdit(offer: OfferRead) {
  editingOffer.value = offer
  showOfferForm.value = true
}

function onOfferSaved(offer: OfferRead) {
  const idx = offers.value.findIndex((o) => o.id === offer.id)
  if (idx >= 0) offers.value[idx] = offer
  else offers.value.unshift(offer)
}

async function sendOffer(offer: OfferRead) {
  actionLoading.value = `send-${offer.id}`
  try {
    const updated = await offerService.send(offer.id)
    onOfferSaved(updated)
  } catch (err: any) {
    toast.add({ severity: 'error', summary: 'Lỗi', detail: err?.response?.data?.detail ?? 'Có lỗi xảy ra', life: 3000 })
  } finally {
    actionLoading.value = null
  }
}

async function acceptOffer(offer: OfferRead) {
  actionLoading.value = `accept-${offer.id}`
  try {
    const updated = await offerService.accept(offer.id)
    onOfferSaved(updated)
    toast.add({ severity: 'success', summary: 'Ứng viên đã chấp nhận offer', life: 2000 })
  } catch (err: any) {
    toast.add({ severity: 'error', summary: 'Lỗi', detail: err?.response?.data?.detail ?? 'Có lỗi xảy ra', life: 3000 })
  } finally {
    actionLoading.value = null
  }
}

function openReject(offer: OfferRead) {
  rejectingOffer.value = offer
  rejectReason.value = ''
  showRejectDialog.value = true
}

async function confirmReject() {
  if (!rejectingOffer.value || !rejectReason.value.trim()) {
    toast.add({ severity: 'warn', summary: 'Vui lòng nhập lý do từ chối', life: 2000 })
    return
  }
  rejectLoading.value = true
  try {
    const updated = await offerService.reject(rejectingOffer.value.id, { rejection_reason: rejectReason.value })
    onOfferSaved(updated)
    showRejectDialog.value = false
  } catch (err: any) {
    toast.add({ severity: 'error', summary: 'Lỗi', detail: err?.response?.data?.detail ?? 'Có lỗi xảy ra', life: 3000 })
  } finally {
    rejectLoading.value = false
  }
}

async function openDecision(offer: OfferRead) {
  decisionOffer.value = offer
  currentDecision.value = null
  try {
    currentDecision.value = await hiringDecisionService.getForOffer(offer.id)
  } catch {
    // 404 = no decision yet, that's fine
  }
  showDecisionDialog.value = true
}

function onDecisionSaved(decision: HiringDecisionRead) {
  currentDecision.value = decision
}

function onConverted(result: ConvertToEmployeeResult, decision: HiringDecisionRead) {
  currentDecision.value = decision
  emit('converted', result)
}

onMounted(load)
</script>
