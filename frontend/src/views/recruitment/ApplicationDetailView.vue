<template>
  <div v-if="application && candidate" class="rc-detail">
    <RecruitmentBreadcrumb :crumbs="[
      { label: 'Tuyển chọn', to: '/recruitment/selection' },
      { label: application.job_requisition_code, to: `/recruitment/selection/${application.job_requisition_id}` },
      { label: candidate.full_name },
    ]" />
    <div class="rc-detail-header">
      <div class="rc-header-left">
        <Button
          icon="pi pi-arrow-left"
          text
          rounded
          severity="secondary"
          @click="router.push(`/recruitment/selection/${application.job_requisition_id}`)"
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
            <span class="rc-jr-code">{{ candidate.full_name }}</span>
            <Tag
              :value="stageLabel(application.current_stage)"
              :severity="stageSeverity(application.current_stage)"
            />
          </div>
          <div class="rc-meta-row" style="margin-top: 0.2rem">
            <span>{{ application.job_requisition_code }}</span>
            <span>·</span>
            <span>{{ application.job_position_name }}</span>
            <span>·</span>
            <span>{{ application.department_name }}</span>
            <span>·</span>
            <span>Nộp ngày {{ formatDate(application.applied_date) }}</span>
          </div>
        </div>
      </div>

      <div class="rc-header-right">
        <RouterLink :to="`/recruitment/candidates/${candidate.id}`">
          <Button
            label="Hồ sơ ứng viên"
            icon="pi pi-user"
            severity="secondary"
            outlined
          />
        </RouterLink>
        <Button
          v-if="currentStage && !isTerminalStage"
          label="Đánh giá bước"
          icon="pi pi-check-circle"
          severity="info"
          @click="openDecisionDialog('pass')"
        />
        <Button
          v-if="interviewStage && !isTerminalStage"
          label="Lên lịch PV"
          icon="pi pi-calendar-plus"
          severity="warn"
          outlined
          @click="openCreateInterview"
        />
      </div>
    </div>

    <Tabs v-model:value="activeTab">
      <TabList>
        <Tab value="profile">Hồ sơ</Tab>
        <Tab value="pipeline">Pipeline</Tab>
        <Tab value="interviews">Phỏng vấn</Tab>
        <Tab value="offers">Offer & Tuyển dụng</Tab>
        <Tab value="notes">Ghi chú</Tab>
      </TabList>

      <TabPanels>
        <TabPanel value="profile">
          <div class="section-stack" style="padding-top: 0.75rem">
            <div class="section-card">
              <div class="section-header">
                <span class="section-title">Thông tin liên hệ</span>
              </div>
              <div class="info-grid">
                <div class="info-row">
                  <span class="info-label">Email cá nhân</span>
                  <span class="info-value">{{
                    candidate.personal_email ?? "—"
                  }}</span>
                </div>
                <div class="info-row">
                  <span class="info-label">Điện thoại</span>
                  <span class="info-value">{{
                    candidate.phone_number ?? "—"
                  }}</span>
                </div>
                <div class="info-row">
                  <span class="info-label">Quốc tịch</span>
                  <span class="info-value">{{
                    candidate.nationality_name ??
                    candidate.raw_nationality_text ??
                    "—"
                  }}</span>
                </div>
                <div class="info-row">
                  <span class="info-label">Công ty / Vị trí hiện tại</span>
                  <span class="info-value">
                    {{ candidate.current_company ?? "—" }}
                    <span v-if="candidate.current_position">
                      · {{ candidate.current_position }}</span
                    >
                  </span>
                </div>
                <div class="info-row">
                  <span class="info-label">Kênh nguồn</span>
                  <span class="info-value">{{
                    application.source_channel_name ??
                    candidate.source_channel_name ??
                    "—"
                  }}</span>
                </div>
                <div class="info-row">
                  <span class="info-label">CCCD / Hộ chiếu</span>
                  <span class="info-value">{{
                    candidate.id_number ?? candidate.passport_number ?? "—"
                  }}</span>
                </div>
              </div>
            </div>

            <div class="section-card">
              <div class="section-header">
                <span class="section-title">Mức độ sẵn sàng</span>
              </div>
              <div
                style="
                  display: flex;
                  align-items: center;
                  gap: 0.75rem;
                  flex-wrap: wrap;
                "
              >
                <Tag
                  :value="candidate.identity_strength_label"
                  :severity="
                    identityStrengthSeverity(candidate.identity_strength)
                  "
                />
                <Tag
                  :value="
                    candidate.conversion_ready
                      ? 'Sẵn sàng convert'
                      : 'Chưa đủ dữ liệu convert'
                  "
                  :severity="candidate.conversion_ready ? 'success' : 'warn'"
                />
              </div>
            </div>
          </div>
        </TabPanel>

        <TabPanel value="pipeline">
          <div class="section-stack" style="padding-top: 0.75rem">
            <div class="section-card" v-if="currentStage && !isTerminalStage">
              <div class="section-header">
                <span class="section-title">Hành động hiện tại</span>
              </div>
              <div class="rc-action-row">
                <Button
                  label="Đánh giá đạt"
                  icon="pi pi-check"
                  severity="success"
                  @click="openDecisionDialog('pass')"
                />
                <Button
                  label="Tạm giữ"
                  icon="pi pi-pause"
                  severity="warn"
                  outlined
                  @click="openDecisionDialog('hold')"
                />
                <Button
                  label="Loại"
                  icon="pi pi-times"
                  severity="danger"
                  outlined
                  @click="openDecisionDialog('fail')"
                />
              </div>
            </div>

            <div class="section-card">
              <div class="section-header">
                <span class="section-title">Các bước tuyển chọn</span>
              </div>
              <div class="rc-stage-list">
                <div
                  v-for="stage in pipelineStages"
                  :key="stage.id"
                  class="rc-stage-item"
                  :class="{
                    'rc-stage-item--current':
                      application.current_stage === stage.stage_type,
                  }"
                >
                  <div class="rc-stage-item-top">
                    <div>
                      <div class="rc-stage-item-name">
                        {{ stage.stage_order }}. {{ stage.stage_name }}
                      </div>
                      <div class="rc-muted">
                        {{ stageTypeLabel(stage.stage_type) }}
                      </div>
                    </div>
                    <Tag
                      :value="stageProgressLabel(stage)"
                      :severity="stageProgressSeverity(stage)"
                    />
                  </div>

                  <div v-if="stageResultFor(stage.id)" class="rc-stage-result">
                    <div>
                      <strong>Kết quả:</strong>
                      {{ resultLabel(stageResultFor(stage.id)?.result) }}
                    </div>
                    <div
                      v-if="
                        stageResultFor(stage.id)?.score !== null &&
                        stageResultFor(stage.id)?.score !== undefined
                      "
                    >
                      <strong>Điểm:</strong>
                      {{ stageResultFor(stage.id)?.score }}
                    </div>
                    <div v-if="stageResultFor(stage.id)?.notes">
                      <strong>Ghi chú:</strong>
                      {{ stageResultFor(stage.id)?.notes }}
                    </div>
                    <div
                      v-if="stageResultFor(stage.id)?.evaluated_at"
                      class="rc-muted"
                    >
                      {{
                        stageResultFor(stage.id)?.evaluated_by_name ??
                        "Người đánh giá"
                      }}
                      ·
                      {{
                        formatDatetime(
                          stageResultFor(stage.id)?.evaluated_at ?? "",
                        )
                      }}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </TabPanel>

        <TabPanel value="interviews">
          <div style="padding-top: 0.75rem">
            <div class="rc-toolbar">
              <Button
                v-if="interviewStage && !isTerminalStage"
                label="Lên lịch phỏng vấn"
                icon="pi pi-calendar-plus"
                severity="warn"
                @click="openCreateInterview"
              />
              <Button
                icon="pi pi-refresh"
                severity="secondary"
                text
                rounded
                :loading="loading"
                @click="void loadAll()"
              />
            </div>

            <div class="card">
              <DataTable :value="interviews" size="small" :loading="loading">
                <template #empty>
                  <div class="rc-empty">Chưa có lịch phỏng vấn nào</div>
                </template>

                <Column header="Lịch" style="min-width: 180px">
                  <template #body="{ data }: { data: InterviewSessionRead }">
                    <div>{{ formatDatetime(data.scheduled_at) }}</div>
                    <div class="rc-muted">{{ data.duration_minutes }} phút</div>
                  </template>
                </Column>

                <Column header="Hình thức / Địa điểm" style="min-width: 180px">
                  <template #body="{ data }: { data: InterviewSessionRead }">
                    <div>{{ interviewFormatLabel(data.format) }}</div>
                    <div class="rc-muted">{{ data.location ?? "—" }}</div>
                  </template>
                </Column>

                <Column header="Hội đồng" style="min-width: 200px">
                  <template #body="{ data }: { data: InterviewSessionRead }">
                    <div v-if="data.panelists.length" class="rc-chip-list">
                      <Tag
                        v-for="panelist in data.panelists"
                        :key="panelist.id"
                        :value="
                          panelist.user_name ?? `User #${panelist.user_id}`
                        "
                        :severity="
                          panelist.submitted_at ? 'success' : 'secondary'
                        "
                      />
                    </div>
                    <span v-else class="rc-muted">—</span>
                  </template>
                </Column>

                <Column header="Trạng thái" style="width: 130px">
                  <template #body="{ data }: { data: InterviewSessionRead }">
                    <Tag
                      :value="interviewStatusLabel(data.status)"
                      :severity="interviewStatusSeverity(data.status)"
                    />
                  </template>
                </Column>

                <Column header="" style="width: 180px; text-align: right">
                  <template #body="{ data }: { data: InterviewSessionRead }">
                    <Button
                      v-if="scorecardPanelist(data)"
                      icon="pi pi-star"
                      text
                      rounded
                      size="small"
                      severity="warning"
                      v-tooltip.top="
                        scorecardPanelist(data)?.submitted_at
                          ? 'Xem scorecard'
                          : 'Chấm điểm'
                      "
                      @click="openScorecard(data)"
                    />
                    <Button
                      v-if="data.status === 'scheduled'"
                      icon="pi pi-pencil"
                      text
                      rounded
                      size="small"
                      severity="secondary"
                      v-tooltip.top="'Sửa lịch'"
                      @click="openEditInterview(data)"
                    />
                    <Button
                      v-if="data.status === 'scheduled'"
                      icon="pi pi-check"
                      text
                      rounded
                      size="small"
                      severity="success"
                      v-tooltip.top="'Hoàn thành'"
                      @click="completeInterview(data)"
                    />
                    <Button
                      v-if="data.status === 'scheduled'"
                      icon="pi pi-ban"
                      text
                      rounded
                      size="small"
                      severity="danger"
                      v-tooltip.top="'Hủy lịch'"
                      @click="cancelInterview(data)"
                    />
                  </template>
                </Column>
              </DataTable>
            </div>
          </div>
        </TabPanel>

        <TabPanel value="offers">
          <OfferListTab
            :application-id="application.id"
            :can-create="!['rejected', 'withdrawn'].includes(application.current_stage)"
            :jr-job-position-id="jr?.job_position_id ?? null"
            :jr-dept-id="jr?.department_id ?? null"
            :jr-job-position-name="jr?.job_position_name ?? null"
            :jr-dept-name="jr?.department_name ?? null"
            @converted="onEmployeeConverted"
          />
        </TabPanel>

        <TabPanel value="notes">
          <div class="section-card" style="margin-top: 0.75rem">
            <div class="section-header">
              <span class="section-title">Ghi chú nội bộ application</span>
            </div>
            <div v-if="application.internal_note" class="rc-jd-block">
              {{ application.internal_note }}
            </div>
            <div v-else class="rc-jd-empty">Chưa có ghi chú nội bộ.</div>
            <div
              v-if="application.rejection_reason"
              class="rc-rejection-note"
              style="margin-top: 1rem"
            >
              <i class="pi pi-times-circle" />
              <div>
                <strong>Lý do loại:</strong> {{ application.rejection_reason }}
              </div>
            </div>
          </div>
        </TabPanel>
      </TabPanels>
    </Tabs>

    <Dialog
      v-model:visible="showDecisionDialog"
      header="Đánh giá bước tuyển chọn"
      modal
      :style="{ width: '520px', maxWidth: '96vw' }"
      :closable="!actionLoading"
    >
      <div class="rc-form">
        <div class="rc-field">
          <label class="rc-label">Kết quả</label>
          <SelectButton
            v-model="decisionResult"
            :options="decisionOptions"
            option-label="label"
            option-value="value"
          />
        </div>

        <div class="rc-row">
          <div class="rc-field">
            <label class="rc-label">Bước hiện tại</label>
            <InputText
              :model-value="currentStage?.stage_name ?? '—'"
              disabled
            />
          </div>
          <div class="rc-field">
            <label class="rc-label">Điểm (nếu có)</label>
            <InputNumber
              v-model="decisionScore"
              class="w-full"
              :min="0"
              :max="100"
              :max-fraction-digits="2"
            />
          </div>
        </div>

        <div class="rc-field">
          <label class="rc-label">Ghi chú</label>
          <Textarea
            v-model="decisionNotes"
            rows="3"
            class="w-full"
            auto-resize
          />
        </div>

        <div v-if="decisionResult === 'fail'" class="rc-field">
          <label class="rc-label"
            >Lý do loại <span class="rc-req">*</span></label
          >
          <Textarea
            v-model="decisionRejectReason"
            rows="3"
            class="w-full"
            auto-resize
          />
        </div>

        <p v-if="actionError" class="rc-api-error">
          <i class="pi pi-exclamation-circle" />
          {{ actionError }}
        </p>
      </div>

      <template #footer>
        <Button
          label="Hủy"
          severity="secondary"
          text
          :disabled="actionLoading"
          @click="showDecisionDialog = false"
        />
        <Button
          label="Lưu kết quả"
          :loading="actionLoading"
          @click="submitDecision"
        />
      </template>
    </Dialog>

    <InterviewScheduleDialog
      v-model:visible="showScheduleDialog"
      :application="application"
      :interview-stage-id="interviewStage?.id ?? null"
      :job-position-id="jobPositionId"
      :editing="editingInterview"
      @saved="onInterviewSaved"
    />

    <Dialog
      v-model:visible="showCancelInterviewDialog"
      header="Hủy lịch phỏng vấn"
      modal
      :style="{ width: '420px' }"
    >
      <div style="display: flex; flex-direction: column; gap: 0.75rem; margin-top: 0.25rem">
        <p style="margin: 0; color: var(--l-text-muted); font-size: 0.9rem">Lý do hủy (không bắt buộc):</p>
        <InputText v-model="cancelInterviewReason" placeholder="Nhập lý do hủy lịch..." class="w-full" />
      </div>
      <template #footer>
        <Button label="Đóng" severity="secondary" outlined @click="showCancelInterviewDialog = false" />
        <Button label="Hủy lịch" severity="danger" icon="pi pi-ban" @click="confirmCancelInterview" />
      </template>
    </Dialog>

    <ScorecardDialog
      v-model:visible="showScorecardDialog"
      :interview-id="activeInterview?.id ?? null"
      :panelist="activePanelist"
      :job-position-id="jobPositionId"
      @saved="onInterviewSaved"
    />
  </div>

  <div v-else-if="loading" class="loading-state">
    <i class="pi pi-spin pi-spinner" />
    <span>Đang tải application...</span>
  </div>
  <div v-else class="error-state">
    <i class="pi pi-exclamation-triangle" />
    <span>Không tìm thấy application</span>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { RouterLink, useRoute, useRouter } from "vue-router";
import Button from "primevue/button";
import Column from "primevue/column";
import DataTable from "primevue/datatable";
import Dialog from "primevue/dialog";
import InputNumber from "primevue/inputnumber";
import InputText from "primevue/inputtext";
import SelectButton from "primevue/selectbutton";
import Tab from "primevue/tab";
import TabList from "primevue/tablist";
import TabPanel from "primevue/tabpanel";
import TabPanels from "primevue/tabpanels";
import Tabs from "primevue/tabs";
import Tag from "primevue/tag";
import Textarea from "primevue/textarea";
import { useConfirm } from "primevue/useconfirm";
import { useToast } from "primevue/usetoast";
import { formatDate, formatDatetime } from "@/utils/format";

import recruitmentService, {
  type ApplicationRead,
  type CandidateRead,
  type CandidateStageResultRead,
  type InterviewPanelistRead,
  type InterviewSessionRead,
  type JobRequisitionRead,
  type PipelineStageRead,
} from "@/services/recruitmentService";
import { useAuthStore } from "@/stores/auth";
import InterviewScheduleDialog from "./components/InterviewScheduleDialog.vue";
import OfferListTab from "./components/OfferListTab.vue";
import ScorecardDialog from "./components/ScorecardDialog.vue";
import RecruitmentBreadcrumb from "./components/RecruitmentBreadcrumb.vue";

const route = useRoute();
const router = useRouter();
const toast = useToast();
const confirm = useConfirm();
const auth = useAuthStore();

const applicationId = computed(() => Number(route.params.id));

const loading = ref(true);
const actionLoading = ref(false);
const activeTab = ref("pipeline");

const application = ref<ApplicationRead | null>(null);
const candidate = ref<CandidateRead | null>(null);
const pipelineStages = ref<PipelineStageRead[]>([]);
const stageResults = ref<CandidateStageResultRead[]>([]);
const interviews = ref<InterviewSessionRead[]>([]);
const derivedJobPositionId = ref<number | null>(null);
const jr = ref<JobRequisitionRead | null>(null);

const showDecisionDialog = ref(false);
const decisionResult = ref<"pass" | "fail" | "hold">("pass");
const decisionNotes = ref("");
const decisionScore = ref<number | null>(null);
const decisionRejectReason = ref("");
const actionError = ref("");

const showScheduleDialog = ref(false);
const editingInterview = ref<InterviewSessionRead | null>(null);
const showScorecardDialog = ref(false);
const activeInterview = ref<InterviewSessionRead | null>(null);

const showCancelInterviewDialog = ref(false);
const cancelInterviewTarget = ref<InterviewSessionRead | null>(null);
const cancelInterviewReason = ref('');

const decisionOptions = [
  { label: "Đạt", value: "pass" },
  { label: "Tạm giữ", value: "hold" },
  { label: "Loại", value: "fail" },
] as const;

const resultMap = computed(
  () => new Map(stageResults.value.map((item) => [item.stage_id, item])),
);
const currentStage = computed(
  () =>
    pipelineStages.value.find(
      (item) => item.stage_type === application.value?.current_stage,
    ) ?? null,
);
const interviewStage = computed(
  () =>
    pipelineStages.value.find((item) => item.stage_type === "interview") ??
    null,
);
const isTerminalStage = computed(() =>
  ["offer", "hired", "rejected", "withdrawn"].includes(
    application.value?.current_stage ?? "",
  ),
);
const jobPositionId = computed(() => derivedJobPositionId.value);
const currentUserId = computed(() => auth.user?.id ?? null);
const activePanelist = computed<InterviewPanelistRead | null>(() => {
  if (!activeInterview.value || !currentUserId.value) {
    return null;
  }
  return (
    activeInterview.value.panelists.find(
      (item) => item.user_id === currentUserId.value,
    ) ?? null
  );
});


function stageLabel(value: string) {
  const map: Record<string, string> = {
    new: "Mới",
    screening: "Sàng lọc",
    test: "Kiểm tra",
    interview: "Phỏng vấn",
    final: "Vòng cuối",
    offer: "Offer",
    hired: "Tuyển",
    rejected: "Loại",
    withdrawn: "Rút",
  };
  return map[value] ?? value;
}

function stageSeverity(value: string) {
  const map: Record<string, string> = {
    new: "info",
    screening: "secondary",
    test: "warn",
    interview: "warn",
    final: "contrast",
    offer: "info",
    hired: "success",
    rejected: "danger",
    withdrawn: "secondary",
  };
  return map[value] ?? "secondary";
}

function stageTypeLabel(value: PipelineStageRead["stage_type"]) {
  const map = {
    screening: "Screening",
    test: "Test",
    interview: "Interview",
    final: "Final",
  } as const;
  return map[value] ?? value;
}

function resultLabel(
  value: CandidateStageResultRead["result"] | InterviewPanelistRead["result"],
) {
  const map = {
    pass: "Đạt",
    fail: "Không đạt",
    hold: "Tạm giữ",
    pending: "Đang chờ",
  } as const;
  return value ? (map[value] ?? value) : "—";
}

function interviewFormatLabel(value: InterviewSessionRead["format"]) {
  const map = {
    in_person: "Trực tiếp",
    online: "Online",
    phone: "Điện thoại",
  } as const;
  return map[value] ?? value;
}

function interviewStatusLabel(value: InterviewSessionRead["status"]) {
  const map = {
    scheduled: "Đã lên lịch",
    completed: "Hoàn thành",
    cancelled: "Đã hủy",
    rescheduled: "Dời lịch",
  } as const;
  return map[value] ?? value;
}

function interviewStatusSeverity(value: InterviewSessionRead["status"]) {
  const map = {
    scheduled: "info",
    completed: "success",
    cancelled: "danger",
    rescheduled: "warn",
  } as const;
  return map[value] ?? "secondary";
}

function identityStrengthSeverity(value: CandidateRead["identity_strength"]) {
  const map = {
    strong: "success",
    medium: "warn",
    weak: "danger",
  } as const;
  return map[value] ?? "secondary";
}

function stageProgressLabel(stage: PipelineStageRead) {
  const result = resultMap.value.get(stage.id);
  if (result?.result) {
    return resultLabel(result.result);
  }
  if (application.value?.current_stage === stage.stage_type) {
    return "Đang xử lý";
  }
  return "Chưa tới";
}

function stageProgressSeverity(stage: PipelineStageRead) {
  const result = resultMap.value.get(stage.id);
  if (result?.result === "pass") return "success";
  if (result?.result === "fail") return "danger";
  if (result?.result === "hold") return "warn";
  if (application.value?.current_stage === stage.stage_type) return "info";
  return "secondary";
}

function scorecardPanelist(interview: InterviewSessionRead) {
  if (!currentUserId.value) {
    return null;
  }
  return (
    interview.panelists.find((item) => item.user_id === currentUserId.value) ??
    null
  );
}

function stageResultFor(stageId: number) {
  return resultMap.value.get(stageId) ?? null;
}

async function loadAll() {
  loading.value = true;
  try {
    const appResponse = await recruitmentService.getApplication(
      applicationId.value,
    );
    application.value = appResponse.data;

    const [
      candidateResponse,
      pipelineResponse,
      stageResultResponse,
      interviewResponse,
      jrResponse,
    ] = await Promise.all([
      recruitmentService.getCandidate(appResponse.data.candidate_id),
      recruitmentService.listPipelineForJR(appResponse.data.job_requisition_id),
      recruitmentService.listStageResults(appResponse.data.id),
      recruitmentService.listApplicationInterviews(appResponse.data.id),
      recruitmentService.getJR(appResponse.data.job_requisition_id),
    ]);

    candidate.value = candidateResponse.data;
    pipelineStages.value = pipelineResponse.data;
    stageResults.value = stageResultResponse.data;
    interviews.value = interviewResponse.data;
    derivedJobPositionId.value = jrResponse.data.job_position_id;
    jr.value = jrResponse.data;
  } catch {
    application.value = null;
    candidate.value = null;
    derivedJobPositionId.value = null;
  } finally {
    loading.value = false;
  }
}

function openDecisionDialog(result: "pass" | "fail" | "hold") {
  decisionResult.value = result;
  decisionNotes.value = "";
  decisionScore.value = null;
  decisionRejectReason.value = "";
  actionError.value = "";
  showDecisionDialog.value = true;
}

async function submitDecision() {
  if (!application.value || !currentStage.value) {
    actionError.value = "Không xác định được bước hiện tại.";
    return;
  }
  if (decisionResult.value === "fail" && !decisionRejectReason.value.trim()) {
    actionError.value = "Vui lòng nhập lý do loại.";
    return;
  }

  actionLoading.value = true;
  actionError.value = "";
  try {
    if (decisionResult.value === "hold") {
      await recruitmentService.holdApplication(application.value.id, {
        stage_id: currentStage.value.id,
        notes: decisionNotes.value || null,
      });
    } else {
      await recruitmentService.advanceApplication(application.value.id, {
        stage_id: currentStage.value.id,
        result: decisionResult.value,
        notes: decisionNotes.value || null,
        score: decisionScore.value,
        rejection_reason:
          decisionResult.value === "fail" ? decisionRejectReason.value : null,
      });
    }
    showDecisionDialog.value = false;
    toast.add({
      severity: "success",
      summary: "Đã cập nhật",
      detail: "Kết quả pipeline đã được lưu",
      life: 3000,
    });
    await loadAll();
  } catch (error: unknown) {
    actionError.value =
      (error as { response?: { data?: { detail?: string } } })?.response?.data
        ?.detail ?? "Không thể cập nhật kết quả";
  } finally {
    actionLoading.value = false;
  }
}

function openCreateInterview() {
  editingInterview.value = null;
  showScheduleDialog.value = true;
}

function openEditInterview(interview: InterviewSessionRead) {
  editingInterview.value = interview;
  showScheduleDialog.value = true;
}

function openScorecard(interview: InterviewSessionRead) {
  activeInterview.value = interview;
  showScorecardDialog.value = true;
}

function onInterviewSaved() {
  void loadAll();
}

function onEmployeeConverted() {
  toast.add({ severity: 'success', summary: 'Đã tạo nhân viên', detail: 'Hồ sơ ứng viên đã được chuyển thành nhân viên.', life: 4000 })
  void loadAll()
}

function completeInterview(interview: InterviewSessionRead) {
  confirm.require({
    message: "Đánh dấu lịch phỏng vấn này là hoàn thành?",
    header: "Hoàn thành phỏng vấn",
    icon: "pi pi-check-circle",
    acceptLabel: "Hoàn thành",
    rejectLabel: "Hủy",
    accept: async () => {
      try {
        await recruitmentService.completeInterview(interview.id);
        toast.add({
          severity: "success",
          summary: "Đã hoàn thành",
          detail: "Phiên phỏng vấn đã được chốt",
          life: 3000,
        });
        await loadAll();
      } catch {
        toast.add({
          severity: "error",
          summary: "Lỗi",
          detail: "Không thể hoàn thành phiên phỏng vấn",
          life: 3000,
        });
      }
    },
  });
}

function cancelInterview(interview: InterviewSessionRead) {
  cancelInterviewTarget.value = interview;
  cancelInterviewReason.value = '';
  showCancelInterviewDialog.value = true;
}

async function confirmCancelInterview() {
  if (!cancelInterviewTarget.value) return;
  try {
    await recruitmentService.cancelInterview(
      cancelInterviewTarget.value.id,
      cancelInterviewReason.value.trim() || null,
    );
    showCancelInterviewDialog.value = false;
    toast.add({ severity: "warn", summary: "Đã hủy", detail: "Lịch phỏng vấn đã được hủy", life: 3000 });
    await loadAll();
  } catch {
    toast.add({ severity: "error", summary: "Lỗi", detail: "Không thể hủy lịch phỏng vấn", life: 3000 });
  }
}

onMounted(async () => {
  if (!auth.user && auth.accessToken) {
    try {
      await auth.fetchMe();
    } catch {
      // ignore
    }
  }
  await loadAll();
});
</script>
