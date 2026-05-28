<template>
  <div class="rc-detail" v-if="jr">
    <RecruitmentBreadcrumb :crumbs="[
      { label: 'Yêu cầu tuyển dụng', to: '/recruitment/jr' },
      { label: jr.code },
    ]" />
    <!-- Header -->
    <div class="rc-detail-header">
      <div class="rc-header-left">
        <Button
          icon="pi pi-arrow-left"
          text
          rounded
          severity="secondary"
          @click="$router.push('/recruitment/jr')"
        />
        <div>
          <div
            style="
              display: flex;
              align-items: center;
              gap: 0.6rem;
              flex-wrap: wrap;
            "
          >
            <span class="rc-jr-code">{{ jr.code }}</span>
            <Tag
              :value="jr.status_label"
              :severity="statusSeverity(jr.status)"
            />
          </div>
          <div class="rc-meta-row" style="margin-top: 0.2rem">
            <span>{{ jr.job_position_name }}</span>
            <span>·</span>
            <span>{{ jr.department_name }}</span>
            <span>·</span>
            <span>Tạo bởi {{ jr.created_by_name ?? "—" }}</span>
            <span>·</span>
            <span>{{ formatDate(jr.created_at) }}</span>
          </div>
        </div>
      </div>

      <div class="rc-header-right">
        <Button
          v-if="jr.status === 'draft'"
          label="Sửa"
          icon="pi pi-pencil"
          severity="secondary"
          outlined
          @click="openEdit"
        />
        <Button
          v-if="['approved', 'in_progress', 'completed'].includes(jr.status)"
          label="Tuyển chọn"
          icon="pi pi-sitemap"
          severity="warn"
          outlined
          @click="$router.push(`/recruitment/selection/${jr.id}`)"
        />
        <Button
          v-if="jr.status === 'draft'"
          label="Gửi duyệt"
          icon="pi pi-send"
          severity="info"
          @click="confirmSubmit"
        />
        <Button
          v-if="jr.status === 'pending_review'"
          label="Duyệt"
          icon="pi pi-check"
          severity="success"
          @click="confirmApprove"
        />
        <Button
          v-if="jr.status === 'pending_review'"
          label="Từ chối"
          icon="pi pi-times"
          severity="danger"
          outlined
          @click="openReject"
        />
        <Button
          v-if="
            ['draft', 'pending_review', 'approved', 'in_progress'].includes(
              jr.status,
            )
          "
          label="Hủy JR"
          icon="pi pi-ban"
          severity="secondary"
          text
          @click="confirmCancel"
        />
      </div>
    </div>

    <!-- Rejection note banner -->
    <div v-if="jr.rejection_note" class="rc-rejection-note">
      <i
        class="pi pi-times-circle"
        style="flex-shrink: 0; margin-top: 0.1rem"
      />
      <div>
        <strong>Lý do từ chối:</strong> {{ jr.rejection_note }}
        <span v-if="jr.approved_by_name"> — {{ jr.approved_by_name }}</span>
      </div>
    </div>

    <!-- Tabs -->
    <Tabs v-model:value="activeTab">
      <TabList>
        <Tab value="info">Thông tin chung</Tab>
        <Tab value="postings">Tin tuyển dụng
          <Badge v-if="postings.length" :value="postings.length" severity="info" style="margin-left: 0.4rem" />
        </Tab>
        <Tab value="pipeline">Ứng viên trong pipeline
          <Badge v-if="applications.length" :value="applications.length" severity="warn" style="margin-left: 0.4rem" />
        </Tab>
        <Tab value="budget">Ngân sách tuyển dụng</Tab>
        <Tab value="hired">Kết quả tuyển dụng
          <Badge v-if="hiredDecisions.length" :value="hiredDecisions.length" severity="success" style="margin-left: 0.4rem" />
        </Tab>
      </TabList>
      <TabPanels>
        <!-- Info tab -->
        <TabPanel value="info">
          <div class="section-stack" style="padding-top: 1rem">
            <!-- Basic info -->
            <div class="section-card">
              <div class="section-header">
                <span class="section-title">Thông tin yêu cầu</span>
              </div>
              <div class="info-grid">
                <div class="info-row">
                  <span class="info-label">Vị trí công việc</span>
                  <span class="info-value">{{ jr.job_position_name }}</span>
                </div>
                <div class="info-row">
                  <span class="info-label">Phòng ban</span>
                  <span class="info-value">{{ jr.department_name }}</span>
                </div>
                <div class="info-row">
                  <span class="info-label">Số lượng cần tuyển</span>
                  <span class="info-value"
                    >{{ jr.quantity }} (còn {{ jr.quantity_remaining }})</span
                  >
                </div>
                <div class="info-row">
                  <span class="info-label">Lý do tuyển</span>
                  <span class="info-value">{{ jr.reason_type_label }}</span>
                </div>
                <div class="info-row">
                  <span class="info-label">Hạn cần người</span>
                  <span class="info-value" :class="deadlineClass(jr.deadline)">
                    {{ jr.deadline ? formatDateShort(jr.deadline) : "—" }}
                  </span>
                </div>
                <div class="info-row">
                  <span class="info-label">Mức lương</span>
                  <span class="info-value">{{ salaryRange }}</span>
                </div>
                <div class="info-row" v-if="jr.submitted_at">
                  <span class="info-label">Gửi duyệt lúc</span>
                  <span class="info-value"
                    >{{ formatDate(jr.submitted_at)
                    }}<span v-if="jr.submitted_by_name">
                      — {{ jr.submitted_by_name }}</span
                    ></span
                  >
                </div>
                <div class="info-row" v-if="jr.approved_at">
                  <span class="info-label">Duyệt lúc</span>
                  <span class="info-value"
                    >{{ formatDate(jr.approved_at)
                    }}<span v-if="jr.approved_by_name">
                      — {{ jr.approved_by_name }}</span
                    ></span
                  >
                </div>
                <div class="info-row" v-if="jr.internal_note">
                  <span class="info-label">Ghi chú nội bộ</span>
                  <span class="info-value" style="white-space: pre-wrap">{{
                    jr.internal_note
                  }}</span>
                </div>
              </div>
            </div>

            <!-- JD -->
            <div class="section-card">
              <div class="section-header">
                <span class="section-title">Mô tả công việc</span>
              </div>
              <div v-if="jr.effective_description" class="rc-jd-block">
                {{ jr.effective_description }}
              </div>
              <div v-else class="rc-jd-empty">Chưa có mô tả công việc</div>

              <div class="section-header" style="margin-top: 1.25rem">
                <span class="section-title">Yêu cầu ứng viên</span>
              </div>
              <div v-if="jr.effective_requirements" class="rc-jd-block">
                {{ jr.effective_requirements }}
              </div>
              <div v-else class="rc-jd-empty">Chưa có yêu cầu ứng viên</div>
            </div>
          </div>
        </TabPanel>

        <!-- Hired tab -->
        <TabPanel value="hired">
          <div class="section-stack" style="padding-top: 1rem">
            <div class="section-card">
              <div v-if="hiredLoading" class="rc-jd-empty">Đang tải...</div>
              <div v-else-if="!hiredDecisions.length" class="rc-jd-empty">Chưa có ứng viên nào được tuyển.</div>
              <DataTable v-else :value="hiredDecisions" size="small">
                <Column header="Ứng viên" style="min-width: 160px">
                  <template #body="{ data }">
                    <RouterLink :to="`/recruitment/candidates/${data.candidate_id}`" class="rc-link">
                      {{ data.candidate_name }}
                    </RouterLink>
                  </template>
                </Column>
                <Column header="Phòng ban / Vị trí" style="min-width: 200px">
                  <template #body="{ data }">
                    <div>{{ data.department_name }}</div>
                    <div style="font-size: 0.8rem; color: var(--l-text-muted)">{{ data.job_position_name }}</div>
                  </template>
                </Column>
                <Column header="Ngày bắt đầu" style="width: 130px">
                  <template #body="{ data }">{{ data.start_date }}</template>
                </Column>
                <Column header="Mã NV" style="width: 110px">
                  <template #body="{ data }">
                    <span v-if="data.employee_code" class="rc-emp-code">{{ data.employee_code }}</span>
                    <span v-else class="rc-muted">—</span>
                  </template>
                </Column>
                <Column header="Trạng thái" style="width: 140px">
                  <template #body="{ data }">
                    <Tag :value="data.status_label" :severity="data.status === 'converted' ? 'success' : 'warn'" />
                  </template>
                </Column>
              </DataTable>
            </div>
          </div>
        </TabPanel>

        <!-- Postings tab -->
        <TabPanel value="postings">
          <div class="section-stack" style="padding-top: 1rem">
            <div class="section-card">
              <div v-if="postingsLoading" class="rc-jd-empty">Đang tải...</div>
              <div v-else-if="!postings.length" class="rc-jd-empty">Chưa có tin tuyển dụng nào được tạo cho yêu cầu này.</div>
              <DataTable v-else :value="postings" size="small">
                <Column header="Tiêu đề" style="min-width: 200px">
                  <template #body="{ data }: { data: JobPostingRead }">
                    <RouterLink :to="`/recruitment/postings/${data.id}`" class="rc-link">
                      {{ data.title }}
                    </RouterLink>
                  </template>
                </Column>
                <Column header="Loại" style="width: 110px">
                  <template #body="{ data }: { data: JobPostingRead }">
                    <Tag :value="data.posting_type_label" :severity="data.posting_type === 'internal' ? 'info' : 'secondary'" />
                  </template>
                </Column>
                <Column header="Trạng thái" style="width: 120px">
                  <template #body="{ data }: { data: JobPostingRead }">
                    <Tag :value="data.status_label" :severity="postingStatusSeverity(data.status)" />
                  </template>
                </Column>
                <Column header="Ứng viên" style="width: 90px; text-align: center">
                  <template #body="{ data }: { data: JobPostingRead }">
                    {{ data.candidate_count }}
                  </template>
                </Column>
                <Column header="Hạn nộp" style="width: 120px">
                  <template #body="{ data }: { data: JobPostingRead }">
                    <span :class="deadlineClass(data.deadline ?? null)">
                      {{ data.deadline ? formatDateShort(data.deadline) : '—' }}
                    </span>
                  </template>
                </Column>
                <Column header="Đăng lúc" style="width: 120px">
                  <template #body="{ data }: { data: JobPostingRead }">
                    <span class="rc-muted">{{ data.opened_at ? formatDateShort(data.opened_at) : '—' }}</span>
                  </template>
                </Column>
              </DataTable>
            </div>
          </div>
        </TabPanel>

        <!-- Pipeline tab -->
        <TabPanel value="pipeline">
          <div class="section-stack" style="padding-top: 1rem">
            <div class="section-card">
              <div v-if="applicationsLoading" class="rc-jd-empty">Đang tải...</div>
              <div v-else-if="!applications.length" class="rc-jd-empty">Chưa có ứng viên nào trong quy trình tuyển chọn.</div>
              <DataTable v-else :value="applications" size="small">
                <Column header="Ứng viên" style="min-width: 160px">
                  <template #body="{ data }: { data: ApplicationRead }">
                    <RouterLink :to="`/recruitment/candidates/${data.candidate_id}`" class="rc-link">
                      {{ data.candidate_name }}
                    </RouterLink>
                  </template>
                </Column>
                <Column header="Giai đoạn hiện tại" style="min-width: 140px">
                  <template #body="{ data }: { data: ApplicationRead }">
                    <Tag :value="stageLabel(data.current_stage)" :severity="stageSeverity(data.current_stage)" />
                  </template>
                </Column>
                <Column header="Nguồn" style="min-width: 120px">
                  <template #body="{ data }: { data: ApplicationRead }">
                    <span class="rc-muted">{{ data.source_channel_name ?? '—' }}</span>
                  </template>
                </Column>
                <Column header="Ngày nộp" style="width: 110px">
                  <template #body="{ data }: { data: ApplicationRead }">
                    <span class="rc-muted">{{ formatDateShort(data.applied_date) }}</span>
                  </template>
                </Column>
                <Column header="" style="width: 70px; text-align: right">
                  <template #body="{ data }: { data: ApplicationRead }">
                    <RouterLink :to="`/recruitment/applications/${data.id}`">
                      <Button icon="pi pi-eye" text rounded size="small" severity="secondary" v-tooltip.top="'Xem pipeline'" />
                    </RouterLink>
                  </template>
                </Column>
              </DataTable>
            </div>
          </div>
        </TabPanel>

        <!-- Budget tab -->
        <TabPanel value="budget">
          <div style="padding-top: 1rem">
            <!-- Summary -->
            <div v-if="budget" class="rc-budget-summary">
              <div class="rc-budget-stat">
                <span class="rc-budget-stat-label">Dự kiến</span>
                <span class="rc-budget-stat-value">{{
                  formatCurrency(budget.total_estimated)
                }}</span>
              </div>
              <div class="rc-budget-stat">
                <span class="rc-budget-stat-label">Thực tế</span>
                <span class="rc-budget-stat-value">{{
                  formatCurrency(budget.total_actual)
                }}</span>
              </div>
            </div>

            <div
              style="
                display: flex;
                justify-content: flex-end;
                margin-bottom: 0.75rem;
              "
            >
              <Button
                label="Thêm khoản"
                icon="pi pi-plus"
                size="small"
                @click="openAddBudget"
              />
            </div>

            <div class="card">
              <DataTable
                :value="budget?.items ?? []"
                :loading="budgetLoading"
                size="small"
                striped-rows
              >
                <template #empty>
                  <div class="rc-empty">Chưa có khoản chi phí nào</div>
                </template>
                <Column header="Khoản mục" style="min-width: 180px">
                  <template #body="{ data }: { data: BudgetItemRead }">
                    {{ data.item_name }}
                  </template>
                </Column>
                <Column
                  header="Dự kiến (VND)"
                  style="width: 150px; text-align: right"
                >
                  <template #body="{ data }: { data: BudgetItemRead }">
                    <span style="font-variant-numeric: tabular-nums">
                      {{
                        data.estimated_amount
                          ? Number(data.estimated_amount).toLocaleString(
                              "vi-VN",
                            )
                          : "—"
                      }}
                    </span>
                  </template>
                </Column>
                <Column
                  header="Thực tế (VND)"
                  style="width: 150px; text-align: right"
                >
                  <template #body="{ data }: { data: BudgetItemRead }">
                    <span style="font-variant-numeric: tabular-nums">
                      {{
                        data.actual_amount
                          ? Number(data.actual_amount).toLocaleString("vi-VN")
                          : "—"
                      }}
                    </span>
                  </template>
                </Column>
                <Column header="Ghi chú" style="min-width: 160px">
                  <template #body="{ data }: { data: BudgetItemRead }">
                    <span class="rc-muted">{{ data.note ?? "—" }}</span>
                  </template>
                </Column>
                <Column header="" style="width: 80px; text-align: right">
                  <template #body="{ data }: { data: BudgetItemRead }">
                    <Button
                      icon="pi pi-pencil"
                      text
                      rounded
                      size="small"
                      severity="secondary"
                      @click="openEditBudget(data)"
                    />
                    <Button
                      icon="pi pi-trash"
                      text
                      rounded
                      size="small"
                      severity="danger"
                      @click="confirmDeleteBudget(data)"
                    />
                  </template>
                </Column>
              </DataTable>
            </div>
          </div>
        </TabPanel>
      </TabPanels>
    </Tabs>

    <!-- Edit JR dialog -->
    <JRFormDialog
      v-model:visible="showEditDialog"
      :editing-jr="jr"
      @saved="onJrSaved"
    />

    <!-- Reject dialog -->
    <Dialog
      v-model:visible="showRejectDialog"
      header="Từ chối yêu cầu tuyển dụng"
      modal
      :style="{ width: '420px' }"
      :closable="!actionLoading"
    >
      <div class="rc-form">
        <div class="rc-field">
          <label class="rc-label"
            >Lý do từ chối <span class="rc-req">*</span></label
          >
          <Textarea
            v-model="rejectNote"
            rows="3"
            class="w-full"
            auto-resize
            placeholder="Nhập lý do từ chối..."
          />
          <span v-if="rejectError" class="rc-error">{{ rejectError }}</span>
        </div>
      </div>
      <template #footer>
        <Button
          label="Hủy"
          severity="secondary"
          text
          :disabled="actionLoading"
          @click="showRejectDialog = false"
        />
        <Button
          label="Xác nhận từ chối"
          severity="danger"
          :loading="actionLoading"
          @click="doReject"
        />
      </template>
    </Dialog>

    <!-- Budget dialog -->
    <Dialog
      v-model:visible="showBudgetDialog"
      :header="editingBudget ? 'Sửa khoản chi phí' : 'Thêm khoản chi phí'"
      modal
      :style="{ width: '420px' }"
      :closable="!budgetSaving"
    >
      <div class="rc-form">
        <div class="rc-field">
          <label class="rc-label"
            >Khoản mục <span class="rc-req">*</span></label
          >
          <InputText
            v-model="budgetForm.item_name"
            class="w-full"
            placeholder="VD: Phí đăng tuyển..."
          />
          <span v-if="budgetErrors.item_name" class="rc-error">{{
            budgetErrors.item_name
          }}</span>
        </div>
        <div class="rc-row">
          <div class="rc-field">
            <label class="rc-label">Dự kiến (VND)</label>
            <InputNumber
              v-model="budgetForm.estimated_amount"
              :min="0"
              :use-grouping="true"
              locale="vi-VN"
              class="w-full"
            />
          </div>
          <div class="rc-field">
            <label class="rc-label">Thực tế (VND)</label>
            <InputNumber
              v-model="budgetForm.actual_amount"
              :min="0"
              :use-grouping="true"
              locale="vi-VN"
              class="w-full"
            />
          </div>
        </div>
        <div class="rc-field">
          <label class="rc-label">Ghi chú</label>
          <Textarea
            v-model="budgetForm.note"
            rows="2"
            class="w-full"
            auto-resize
          />
        </div>
      </div>
      <template #footer>
        <Button
          label="Hủy"
          severity="secondary"
          text
          :disabled="budgetSaving"
          @click="showBudgetDialog = false"
        />
        <Button
          :label="editingBudget ? 'Lưu' : 'Thêm'"
          :loading="budgetSaving"
          @click="submitBudget"
        />
      </template>
    </Dialog>
  </div>

  <!-- Loading / error -->
  <div v-else-if="pageLoading" class="loading-state">
    <i class="pi pi-spin pi-spinner" />
    <span>Đang tải...</span>
  </div>
  <div v-else class="error-state">
    <i class="pi pi-exclamation-triangle" />
    <span>Không tìm thấy yêu cầu tuyển dụng</span>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from "vue";
import { useRoute, RouterLink } from "vue-router";
import Badge from "primevue/badge";
import Button from "primevue/button";
import Column from "primevue/column";
import DataTable from "primevue/datatable";
import Dialog from "primevue/dialog";
import InputNumber from "primevue/inputnumber";
import InputText from "primevue/inputtext";
import Tab from "primevue/tab";
import TabList from "primevue/tablist";
import TabPanel from "primevue/tabpanel";
import TabPanels from "primevue/tabpanels";
import Tabs from "primevue/tabs";
import Tag from "primevue/tag";
import Textarea from "primevue/textarea";
import { useConfirm } from "primevue/useconfirm";
import { useToast } from "primevue/usetoast";

import recruitmentService, {
  hiringDecisionService,
  type ApplicationRead,
  type HiringDecisionRead,
  type JobPostingRead,
  type JobRequisitionRead,
  type BudgetSummary,
  type BudgetItemRead,
} from "@/services/recruitmentService";
import JRFormDialog from "./components/JRFormDialog.vue";
import RecruitmentBreadcrumb from "./components/RecruitmentBreadcrumb.vue";

const route = useRoute();
const confirm = useConfirm();
const toast = useToast();

const jr = ref<JobRequisitionRead | null>(null);
const pageLoading = ref(true);
const activeTab = ref("info");

const budget = ref<BudgetSummary | null>(null);
const budgetLoading = ref(false);

const hiredDecisions = ref<HiringDecisionRead[]>([]);
const hiredLoading = ref(false);

const postings = ref<JobPostingRead[]>([]);
const postingsLoading = ref(false);

const applications = ref<ApplicationRead[]>([]);
const applicationsLoading = ref(false);

// Edit JR
const showEditDialog = ref(false);

// Reject dialog
const showRejectDialog = ref(false);
const rejectNote = ref("");
const rejectError = ref("");
const actionLoading = ref(false);

// Budget dialog
const showBudgetDialog = ref(false);
const budgetSaving = ref(false);
const budgetErrors = ref<Record<string, string>>({});
const editingBudget = ref<BudgetItemRead | null>(null);
const budgetForm = ref({
  item_name: "",
  estimated_amount: null as number | null,
  actual_amount: null as number | null,
  note: "",
});

const jrId = computed(() => Number(route.params.id));

function statusSeverity(st: string): string {
  const map: Record<string, string> = {
    draft: "secondary",
    pending_review: "warn",
    approved: "info",
    in_progress: "contrast",
    completed: "success",
    cancelled: "danger",
  };
  return map[st] ?? "secondary";
}

function formatDate(d: string) {
  return new Date(d).toLocaleString("vi-VN", {
    dateStyle: "short",
    timeStyle: "short",
  });
}

function formatDateShort(d: string) {
  return new Date(d).toLocaleDateString("vi-VN");
}

function deadlineClass(d: string | null) {
  if (!d) return "";
  const diff = (new Date(d).getTime() - Date.now()) / 86400000;
  if (diff < 0) return "rc-deadline-past";
  if (diff < 7) return "rc-deadline-near";
  return "";
}

function formatCurrency(v: string | number) {
  const n = Number(v);
  if (!n && n !== 0) return "—";
  return n.toLocaleString("vi-VN") + " ₫";
}

const salaryRange = computed(() => {
  if (!jr.value) return "—";
  const min = jr.value.salary_min
    ? Number(jr.value.salary_min).toLocaleString("vi-VN")
    : null;
  const max = jr.value.salary_max
    ? Number(jr.value.salary_max).toLocaleString("vi-VN")
    : null;
  if (min && max) return `${min} – ${max} VND`;
  if (min) return `Từ ${min} VND`;
  if (max) return `Đến ${max} VND`;
  return "Thương lượng";
});

async function loadJr() {
  pageLoading.value = true;
  try {
    const res = await recruitmentService.getJR(jrId.value);
    jr.value = res.data;
  } catch {
    jr.value = null;
  } finally {
    pageLoading.value = false;
  }
}

async function loadBudget() {
  budgetLoading.value = true;
  try {
    const res = await recruitmentService.getBudget(jrId.value);
    budget.value = res.data;
  } catch {
    /* ignore */
  } finally {
    budgetLoading.value = false;
  }
}

async function loadHired() {
  hiredLoading.value = true;
  try {
    hiredDecisions.value = await hiringDecisionService.listForJr(jrId.value);
  } catch {
    hiredDecisions.value = [];
  } finally {
    hiredLoading.value = false;
  }
}

async function loadPostings() {
  postingsLoading.value = true;
  try {
    const res = await recruitmentService.listPostings({ job_requisition_id: jrId.value, page_size: 100 });
    postings.value = res.data.items;
  } catch {
    postings.value = [];
  } finally {
    postingsLoading.value = false;
  }
}

async function loadApplications() {
  applicationsLoading.value = true;
  try {
    const res = await recruitmentService.listApplications(jrId.value, { page_size: 100 });
    applications.value = res.data.items;
  } catch {
    applications.value = [];
  } finally {
    applicationsLoading.value = false;
  }
}

function postingStatusSeverity(status: string) {
  const map: Record<string, string> = { draft: "secondary", active: "success", closed: "warn", expired: "danger" };
  return map[status] ?? "secondary";
}

function stageLabel(stage: string) {
  const map: Record<string, string> = {
    new:       "Mới nộp",
    screening: "Sơ loại hồ sơ",
    test:      "Kiểm tra",
    interview: "Phỏng vấn",
    final:     "Vòng cuối",
    hired:     "Đã tuyển",
    rejected:  "Đã loại",
    withdrawn: "Đã rút đơn",
  };
  return map[stage] ?? stage;
}

function stageSeverity(stage: string) {
  const map: Record<string, string> = {
    new:       "secondary",
    screening: "info",
    test:      "info",
    interview: "warn",
    final:     "warn",
    hired:     "success",
    rejected:  "danger",
    withdrawn: "secondary",
  };
  return map[stage] ?? "info";
}

watch(activeTab, (tab) => {
  if (tab === "hired" && !hiredDecisions.value.length) loadHired();
  if (tab === "postings" && !postings.value.length) loadPostings();
  if (tab === "pipeline" && !applications.value.length) loadApplications();
});

// JR actions
function openEdit() {
  showEditDialog.value = true;
}

async function onJrSaved() {
  showEditDialog.value = false;
  await loadJr();
  toast.add({ severity: "success", summary: "Đã cập nhật", life: 3000 });
}

function confirmSubmit() {
  confirm.require({
    message: `Gửi duyệt yêu cầu ${jr.value?.code}?`,
    header: "Xác nhận gửi duyệt",
    icon: "pi pi-send",
    acceptLabel: "Gửi duyệt",
    rejectLabel: "Hủy",
    accept: doSubmit,
  });
}

async function doSubmit() {
  try {
    await recruitmentService.submitJR(jrId.value);
    await loadJr();
    toast.add({ severity: "success", summary: "Đã gửi duyệt", life: 3000 });
  } catch {
    toast.add({
      severity: "error",
      summary: "Lỗi",
      detail: "Không thể gửi duyệt",
      life: 4000,
    });
  }
}

function confirmApprove() {
  confirm.require({
    message: `Duyệt yêu cầu ${jr.value?.code}?`,
    header: "Xác nhận duyệt",
    icon: "pi pi-check",
    acceptLabel: "Duyệt",
    rejectLabel: "Hủy",
    accept: doApprove,
  });
}

async function doApprove() {
  try {
    await recruitmentService.approveJR(jrId.value);
    await loadJr();
    toast.add({ severity: "success", summary: "Đã duyệt", life: 3000 });
  } catch {
    toast.add({
      severity: "error",
      summary: "Lỗi",
      detail: "Không thể duyệt",
      life: 4000,
    });
  }
}

function openReject() {
  rejectNote.value = "";
  rejectError.value = "";
  showRejectDialog.value = true;
}

async function doReject() {
  if (!rejectNote.value.trim()) {
    rejectError.value = "Vui lòng nhập lý do";
    return;
  }
  actionLoading.value = true;
  try {
    await recruitmentService.rejectJR(jrId.value, rejectNote.value.trim());
    showRejectDialog.value = false;
    await loadJr();
    toast.add({ severity: "warn", summary: "Đã từ chối", life: 3000 });
  } catch {
    toast.add({
      severity: "error",
      summary: "Lỗi",
      detail: "Không thể từ chối",
      life: 4000,
    });
  } finally {
    actionLoading.value = false;
  }
}

function confirmCancel() {
  confirm.require({
    message: `Hủy yêu cầu ${jr.value?.code}?`,
    header: "Xác nhận hủy",
    icon: "pi pi-ban",
    acceptLabel: "Hủy JR",
    rejectLabel: "Đóng",
    acceptClass: "p-button-danger",
    accept: doCancel,
  });
}

async function doCancel() {
  try {
    await recruitmentService.cancelJR(jrId.value);
    await loadJr();
    toast.add({ severity: "info", summary: "Đã hủy JR", life: 3000 });
  } catch {
    toast.add({
      severity: "error",
      summary: "Lỗi",
      detail: "Không thể hủy",
      life: 4000,
    });
  }
}

// Budget
function openAddBudget() {
  editingBudget.value = null;
  budgetErrors.value = {};
  budgetForm.value = {
    item_name: "",
    estimated_amount: null,
    actual_amount: null,
    note: "",
  };
  showBudgetDialog.value = true;
}

function openEditBudget(item: BudgetItemRead) {
  editingBudget.value = item;
  budgetErrors.value = {};
  budgetForm.value = {
    item_name: item.item_name,
    estimated_amount: item.estimated_amount
      ? Number(item.estimated_amount)
      : null,
    actual_amount: item.actual_amount ? Number(item.actual_amount) : null,
    note: item.note ?? "",
  };
  showBudgetDialog.value = true;
}

async function submitBudget() {
  budgetErrors.value = {};
  if (!budgetForm.value.item_name.trim()) {
    budgetErrors.value.item_name = "Vui lòng nhập tên khoản mục";
    return;
  }
  budgetSaving.value = true;
  try {
    const payload = {
      item_name: budgetForm.value.item_name.trim(),
      estimated_amount: budgetForm.value.estimated_amount,
      actual_amount: budgetForm.value.actual_amount,
      note: budgetForm.value.note.trim() || null,
    };
    if (editingBudget.value) {
      await recruitmentService.updateBudgetItem(
        jrId.value,
        editingBudget.value.id,
        payload,
      );
    } else {
      await recruitmentService.addBudgetItem(jrId.value, payload);
    }
    showBudgetDialog.value = false;
    await loadBudget();
    toast.add({
      severity: "success",
      summary: editingBudget.value ? "Đã cập nhật" : "Đã thêm",
      life: 3000,
    });
  } catch {
    toast.add({
      severity: "error",
      summary: "Lỗi",
      detail: "Không thể lưu khoản chi phí",
      life: 4000,
    });
  } finally {
    budgetSaving.value = false;
  }
}

function confirmDeleteBudget(item: BudgetItemRead) {
  confirm.require({
    message: `Xóa khoản "${item.item_name}"?`,
    header: "Xác nhận xóa",
    icon: "pi pi-trash",
    acceptLabel: "Xóa",
    rejectLabel: "Hủy",
    acceptClass: "p-button-danger",
    accept: () => doDeleteBudget(item.id),
  });
}

async function doDeleteBudget(itemId: number) {
  try {
    await recruitmentService.deleteBudgetItem(jrId.value, itemId);
    await loadBudget();
    toast.add({ severity: "success", summary: "Đã xóa", life: 3000 });
  } catch {
    toast.add({
      severity: "error",
      summary: "Lỗi",
      detail: "Không thể xóa",
      life: 4000,
    });
  }
}

onMounted(async () => {
  await loadJr();
  await loadBudget();
});
</script>
