<template>
  <div class="other-business-catalog">
    <section class="hero-panel">
      <div class="hero-copy">
        <span class="eyebrow">Recruitment Catalog Workspace</span>
        <h1>Danh mục tuyển dụng</h1>
        <p class="hero-text">
          Cấu hình nền cho quy trình tuyển dụng: mẫu quy trình tái sử dụng,
          ngân hàng câu hỏi phỏng vấn và tiêu chí chấm điểm.
        </p>
        <div class="hero-actions">
          <Button v-can:create="'recruitment'" :label="primaryCreateLabel" icon="pi pi-plus" @click="openCreate" />
          <Button
            label="Về tổng quan danh mục"
            icon="pi pi-th-large"
            severity="secondary"
            outlined
            @click="router.push('/catalog')"
          />
        </div>
      </div>

      <div class="hero-side">
        <article class="signal-card">
          <div class="signal-head">
            <span class="signal-label">Nhóm đang quản trị</span>
            <Tag :value="activeTabLabel" severity="info" rounded />
          </div>
          <p class="signal-value">{{ activeHeadline }}</p>
          <p class="signal-note">{{ activeSubline }}</p>
        </article>
      </div>
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
            <h2>{{ activeHeadline }}</h2>
          </div>
          <div class="tabs-scroll">
            <TabList>
              <Tab value="templates">Mẫu quy trình</Tab>
              <Tab value="questions">Câu hỏi phỏng vấn</Tab>
              <Tab value="criteria">Tiêu chí chấm điểm</Tab>
            </TabList>
          </div>
        </div>

        <TabPanels>
          <!-- ── Pipeline Templates ── -->
          <TabPanel value="templates">
            <div class="toolbar">
              <Button
                icon="pi pi-refresh"
                severity="secondary"
                text
                rounded
                :loading="templateState.loading"
                @click="loadTemplates"
              />
            </div>
            <DataTable
              :value="templateState.items"
              :loading="templateState.loading"
              stripedRows
              responsive-layout="scroll"
            >
              <template #empty>
                <div class="empty-state">
                  <i class="pi pi-inbox" />
                  <span>Chưa có mẫu quy trình nào</span>
                </div>
              </template>
              <Column header="Tên mẫu" style="min-width: 220px">
                <template #body="{ data }: { data: PipelineStageTemplateRead }">
                  <div style="display: flex; align-items: center; gap: 0.5rem">
                    <strong>{{ data.name }}</strong>
                    <Tag v-if="data.is_default" value="Mặc định" severity="info" />
                  </div>
                </template>
              </Column>
              <Column header="Các bước" style="min-width: 300px">
                <template #body="{ data }: { data: PipelineStageTemplateRead }">
                  <div style="display: flex; flex-wrap: wrap; gap: 0.3rem">
                    <Tag
                      v-for="item in data.items"
                      :key="item.id"
                      :value="`${item.stage_order}. ${item.stage_name}`"
                      severity="secondary"
                    />
                  </div>
                </template>
              </Column>
              <Column header="Ngày tạo" style="width: 150px">
                <template #body="{ data }: { data: PipelineStageTemplateRead }">
                  {{ formatDate(data.created_at) }}
                </template>
              </Column>
              <Column header="" style="width: 110px">
                <template #body="{ data }: { data: PipelineStageTemplateRead }">
                  <div class="action-cell">
                    <Button
                      v-can:edit="'recruitment'"
                      icon="pi pi-pencil"
                      severity="secondary"
                      text
                      rounded
                      size="small"
                      @click="openEditTemplate(data)"
                    />
                    <Button
                      v-can:delete="'recruitment'"
                      icon="pi pi-trash"
                      severity="danger"
                      text
                      rounded
                      size="small"
                      @click="confirmDeleteTemplate(data)"
                    />
                  </div>
                </template>
              </Column>
            </DataTable>
          </TabPanel>

          <!-- ── Interview Questions ── -->
          <TabPanel value="questions">
            <div class="toolbar">
              <Select
                v-model="questionFilter.stage_type"
                :options="stageTypeFilterOptions"
                option-label="label"
                option-value="value"
                show-clear
                placeholder="Tất cả bước"
                class="toolbar-filter"
                @change="loadQuestions"
              />
              <Select
                v-model="questionFilter.difficulty"
                :options="difficultyOptions"
                option-label="label"
                option-value="value"
                show-clear
                placeholder="Tất cả mức độ"
                class="toolbar-filter"
                @change="loadQuestions"
              />
              <Button
                icon="pi pi-refresh"
                severity="secondary"
                text
                rounded
                :loading="questionState.loading"
                @click="loadQuestions"
              />
            </div>
            <DataTable
              :value="questionState.items"
              :loading="questionState.loading"
              stripedRows
              responsive-layout="scroll"
            >
              <template #empty>
                <div class="empty-state">
                  <i class="pi pi-inbox" />
                  <span>Chưa có câu hỏi phỏng vấn nào</span>
                </div>
              </template>
              <Column header="Câu hỏi" style="min-width: 300px">
                <template #body="{ data }: { data: InterviewQuestionRead }">
                  {{ data.question_text }}
                </template>
              </Column>
              <Column header="Danh mục" style="width: 150px">
                <template #body="{ data }: { data: InterviewQuestionRead }">
                  {{ data.category ?? "—" }}
                </template>
              </Column>
              <Column header="Bước" style="width: 130px">
                <template #body="{ data }: { data: InterviewQuestionRead }">
                  {{ stageTypeLabel(data.stage_type) }}
                </template>
              </Column>
              <Column header="Độ khó" style="width: 120px">
                <template #body="{ data }: { data: InterviewQuestionRead }">
                  <Tag
                    v-if="data.difficulty"
                    :value="difficultyLabel(data.difficulty)"
                    :severity="difficultySeverity(data.difficulty)"
                  />
                  <span v-else class="rc-muted">—</span>
                </template>
              </Column>
              <Column header="Trạng thái" style="width: 120px">
                <template #body="{ data }: { data: InterviewQuestionRead }">
                  <Tag
                    :value="data.is_active ? 'Hoạt động' : 'Đã khóa'"
                    :severity="data.is_active ? 'success' : 'danger'"
                  />
                </template>
              </Column>
              <Column header="" style="width: 110px">
                <template #body="{ data }: { data: InterviewQuestionRead }">
                  <div class="action-cell">
                    <Button
                      v-can:edit="'recruitment'"
                      icon="pi pi-pencil"
                      severity="secondary"
                      text
                      rounded
                      size="small"
                      @click="openEditQuestion(data)"
                    />
                    <Button
                      v-can:delete="'recruitment'"
                      icon="pi pi-trash"
                      severity="danger"
                      text
                      rounded
                      size="small"
                      @click="confirmDeleteQuestion(data)"
                    />
                  </div>
                </template>
              </Column>
            </DataTable>
          </TabPanel>

          <!-- ── Scorecard Criteria ── -->
          <TabPanel value="criteria">
            <div class="toolbar">
              <Select
                v-model="criterionFilter.stage_type"
                :options="stageTypeFilterOptions"
                option-label="label"
                option-value="value"
                show-clear
                placeholder="Tất cả bước"
                class="toolbar-filter"
                @change="loadCriteria"
              />
              <Button
                icon="pi pi-refresh"
                severity="secondary"
                text
                rounded
                :loading="criterionState.loading"
                @click="loadCriteria"
              />
            </div>
            <DataTable
              :value="criterionState.items"
              :loading="criterionState.loading"
              stripedRows
              responsive-layout="scroll"
            >
              <template #empty>
                <div class="empty-state">
                  <i class="pi pi-inbox" />
                  <span>Chưa có tiêu chí scorecard nào</span>
                </div>
              </template>
              <Column field="sort_order" header="Thứ tự" style="width: 80px" />
              <Column field="name" header="Tiêu chí" style="min-width: 220px" />
              <Column header="Bước" style="width: 130px">
                <template #body="{ data }: { data: ScorecardCriterionRead }">
                  {{ stageTypeLabel(data.stage_type) }}
                </template>
              </Column>
              <Column field="max_score" header="Điểm tối đa" style="width: 120px" />
              <Column header="Trạng thái" style="width: 120px">
                <template #body="{ data }: { data: ScorecardCriterionRead }">
                  <Tag
                    :value="data.is_active ? 'Hoạt động' : 'Đã khóa'"
                    :severity="data.is_active ? 'success' : 'danger'"
                  />
                </template>
              </Column>
              <Column header="" style="width: 110px">
                <template #body="{ data }: { data: ScorecardCriterionRead }">
                  <div class="action-cell">
                    <Button
                      v-can:edit="'recruitment'"
                      icon="pi pi-pencil"
                      severity="secondary"
                      text
                      rounded
                      size="small"
                      @click="openEditCriterion(data)"
                    />
                    <Button
                      v-can:delete="'recruitment'"
                      icon="pi pi-trash"
                      severity="danger"
                      text
                      rounded
                      size="small"
                      @click="confirmDeleteCriterion(data)"
                    />
                  </div>
                </template>
              </Column>
            </DataTable>
          </TabPanel>
        </TabPanels>
      </Tabs>
    </div>

    <!-- ── Template Form Dialog ── -->
    <Dialog
      v-model:visible="templateDialog.visible"
      :header="templateDialog.editing ? 'Sửa mẫu quy trình' : 'Tạo mẫu quy trình'"
      modal
      :style="{ width: '640px', maxWidth: '96vw' }"
      :closable="!templateDialog.saving"
    >
      <div class="rc-form rc-form--wide">
        <div class="rc-field">
          <label class="rc-label">Tên mẫu <span class="rc-req">*</span></label>
          <InputText v-model="templateDialog.name" class="w-full" />
        </div>
        <div class="rc-field" style="display: flex; align-items: center; gap: 0.75rem">
          <Checkbox v-model="templateDialog.is_default" binary input-id="tpl-default" />
          <label for="tpl-default">Đặt làm mẫu mặc định</label>
        </div>

        <div class="rc-field">
          <div
            style="
              display: flex;
              align-items: center;
              justify-content: space-between;
              margin-bottom: 0.5rem;
            "
          >
            <label class="rc-label" style="margin: 0">
              Các bước <span class="rc-req">*</span>
            </label>
            <Button
              icon="pi pi-plus"
              label="Thêm bước"
              size="small"
              severity="secondary"
              outlined
              @click="addTemplateStage"
            />
          </div>
          <div class="rc-stage-setup-list">
            <div
              v-for="(item, index) in templateDialog.items"
              :key="index"
              class="rc-stage-setup-row"
            >
              <span class="rc-stage-order">{{ index + 1 }}</span>
              <InputText
                v-model="item.stage_name"
                placeholder="Tên bước"
                style="flex: 1"
              />
              <Select
                v-model="item.stage_type"
                :options="stageTypeOptions"
                option-label="label"
                option-value="value"
                style="width: 150px"
              />
              <Button
                icon="pi pi-trash"
                text
                rounded
                severity="danger"
                size="small"
                :disabled="templateDialog.items.length <= 1"
                @click="templateDialog.items.splice(index, 1)"
              />
            </div>
          </div>
        </div>

        <p v-if="templateDialog.error" class="rc-api-error">
          <i class="pi pi-exclamation-circle" />
          {{ templateDialog.error }}
        </p>
      </div>
      <template #footer>
        <Button
          label="Hủy"
          severity="secondary"
          text
          :disabled="templateDialog.saving"
          @click="templateDialog.visible = false"
        />
        <Button
          v-can="templateDialog.editing ? 'recruitment:edit' : 'recruitment:create'"
          :label="templateDialog.editing ? 'Cập nhật' : 'Tạo mẫu quy trình'"
          :loading="templateDialog.saving"
          @click="submitTemplate"
        />
      </template>
    </Dialog>

    <!-- ── Question Form Dialog ── -->
    <Dialog
      v-model:visible="questionDialog.visible"
      :header="questionDialog.editing ? 'Sửa câu hỏi' : 'Thêm câu hỏi phỏng vấn'"
      modal
      :style="{ width: '580px', maxWidth: '96vw' }"
      :closable="!questionDialog.saving"
    >
      <div class="rc-form rc-form--wide">
        <div class="rc-field">
          <label class="rc-label">Câu hỏi <span class="rc-req">*</span></label>
          <Textarea v-model="questionDialog.question_text" rows="3" class="w-full" auto-resize />
        </div>
        <div class="rc-field">
          <label class="rc-label">Vị trí tuyển dụng</label>
          <MultiSelect
            v-model="questionDialog.job_position_ids"
            :options="jobPositionOptions"
            option-label="label"
            option-value="value"
            filter
            display="chip"
            class="w-full"
            placeholder="Dùng chung (tất cả vị trí)"
          />
        </div>
        <div class="rc-row">
          <div class="rc-field">
            <label class="rc-label">Bước</label>
            <Select
              v-model="questionDialog.stage_type"
              :options="stageTypeOptions"
              option-label="label"
              option-value="value"
              show-clear
              class="w-full"
              placeholder="Tất cả bước"
            />
          </div>
          <div class="rc-field">
            <label class="rc-label">Độ khó</label>
            <Select
              v-model="questionDialog.difficulty"
              :options="difficultyOptions"
              option-label="label"
              option-value="value"
              show-clear
              class="w-full"
              placeholder="Không phân loại"
            />
          </div>
        </div>
        <div class="rc-field">
          <label class="rc-label">Danh mục (tuỳ chọn)</label>
          <InputText
            v-model="questionDialog.category"
            class="w-full"
            placeholder="VD: Kỹ thuật, Hành vi, Tình huống..."
          />
        </div>
        <div class="rc-field" style="display: flex; align-items: center; gap: 0.75rem">
          <Checkbox v-model="questionDialog.is_active" binary input-id="q-active" />
          <label for="q-active">Đang hoạt động</label>
        </div>
        <p v-if="questionDialog.error" class="rc-api-error">
          <i class="pi pi-exclamation-circle" />
          {{ questionDialog.error }}
        </p>
      </div>
      <template #footer>
        <Button
          label="Hủy"
          severity="secondary"
          text
          :disabled="questionDialog.saving"
          @click="questionDialog.visible = false"
        />
        <Button
          v-can="questionDialog.editing ? 'recruitment:edit' : 'recruitment:create'"
          :label="questionDialog.editing ? 'Cập nhật' : 'Thêm câu hỏi'"
          :loading="questionDialog.saving"
          @click="submitQuestion"
        />
      </template>
    </Dialog>

    <!-- ── Criterion Form Dialog ── -->
    <Dialog
      v-model:visible="criterionDialog.visible"
      :header="criterionDialog.editing ? 'Sửa tiêu chí' : 'Thêm tiêu chí scorecard'"
      modal
      :style="{ width: '480px', maxWidth: '96vw' }"
      :closable="!criterionDialog.saving"
    >
      <div class="rc-form">
        <div class="rc-field">
          <label class="rc-label">Tên tiêu chí <span class="rc-req">*</span></label>
          <InputText v-model="criterionDialog.name" class="w-full" />
        </div>
        <div class="rc-field">
          <label class="rc-label">Vị trí tuyển dụng</label>
          <MultiSelect
            v-model="criterionDialog.job_position_ids"
            :options="jobPositionOptions"
            option-label="label"
            option-value="value"
            filter
            display="chip"
            class="w-full"
            placeholder="Dùng chung (tất cả vị trí)"
          />
        </div>
        <div class="rc-row">
          <div class="rc-field">
            <label class="rc-label">Bước</label>
            <Select
              v-model="criterionDialog.stage_type"
              :options="stageTypeOptions"
              option-label="label"
              option-value="value"
              show-clear
              class="w-full"
              placeholder="Tất cả bước"
            />
          </div>
          <div class="rc-field">
            <label class="rc-label">Điểm tối đa</label>
            <InputNumber
              v-model="criterionDialog.max_score"
              class="w-full"
              :min="1"
              :max="10"
            />
          </div>
        </div>
        <div class="rc-field">
          <label class="rc-label">Thứ tự sắp xếp</label>
          <InputNumber v-model="criterionDialog.sort_order" class="w-full" :min="0" />
        </div>
        <div class="rc-field" style="display: flex; align-items: center; gap: 0.75rem">
          <Checkbox v-model="criterionDialog.is_active" binary input-id="crit-active" />
          <label for="crit-active">Đang hoạt động</label>
        </div>
        <p v-if="criterionDialog.error" class="rc-api-error">
          <i class="pi pi-exclamation-circle" />
          {{ criterionDialog.error }}
        </p>
      </div>
      <template #footer>
        <Button
          label="Hủy"
          severity="secondary"
          text
          :disabled="criterionDialog.saving"
          @click="criterionDialog.visible = false"
        />
        <Button
          v-can="criterionDialog.editing ? 'recruitment:edit' : 'recruitment:create'"
          :label="criterionDialog.editing ? 'Cập nhật' : 'Thêm tiêu chí'"
          :loading="criterionDialog.saving"
          @click="submitCriterion"
        />
      </template>
    </Dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { useRouter } from "vue-router";
import Button from "primevue/button";
import Checkbox from "primevue/checkbox";
import Column from "primevue/column";
import DataTable from "primevue/datatable";
import Dialog from "primevue/dialog";
import InputNumber from "primevue/inputnumber";
import InputText from "primevue/inputtext";
import MultiSelect from "primevue/multiselect";
import Select from "primevue/select";
import Tab from "primevue/tab";
import TabList from "primevue/tablist";
import TabPanel from "primevue/tabpanel";
import TabPanels from "primevue/tabpanels";
import Tabs from "primevue/tabs";
import Tag from "primevue/tag";
import Textarea from "primevue/textarea";
import { useConfirm } from "primevue/useconfirm";
import { useToast } from "primevue/usetoast";

import jobPositionService from "@/services/jobPositionService";
import recruitmentService, {
  type InterviewQuestionRead,
  type PipelineStageTemplateItemInput,
  type PipelineStageTemplateRead,
  type ScorecardCriterionRead,
} from "@/services/recruitmentService";

const router = useRouter();
const toast = useToast();
const confirm = useConfirm();

const activeTab = ref("templates");
const errorBanner = ref("");

const jobPositionOptions = ref<Array<{ label: string; value: number }>>([]);

async function loadJobPositions() {
  try {
    const res = await jobPositionService.getList({ is_active: true });
    jobPositionOptions.value = res.data.map((jp) => ({
      label: jp.name,
      value: jp.id,
    }));
  } catch {
    // silent — job positions are optional filter
  }
}

// ── Label helpers ──────────────────────────────────────────────────────────────

const stageTypeOptions = [
  { label: "Sàng lọc", value: "screening" },
  { label: "Kiểm tra", value: "test" },
  { label: "Phỏng vấn", value: "interview" },
  { label: "Vòng cuối", value: "final" },
];

const stageTypeFilterOptions = [{ label: "Tất cả bước", value: null }, ...stageTypeOptions];

const difficultyOptions = [
  { label: "Dễ", value: "easy" },
  { label: "Trung bình", value: "medium" },
  { label: "Khó", value: "hard" },
];

function stageTypeLabel(value: string | null | undefined) {
  const map: Record<string, string> = {
    screening: "Sàng lọc",
    test: "Kiểm tra",
    interview: "Phỏng vấn",
    final: "Vòng cuối",
  };
  return value ? (map[value] ?? value) : "—";
}

function difficultyLabel(value: string | null | undefined) {
  const map: Record<string, string> = { easy: "Dễ", medium: "Trung bình", hard: "Khó" };
  return value ? (map[value] ?? value) : "—";
}

function difficultySeverity(value: string | null | undefined) {
  const map: Record<string, string> = { easy: "success", medium: "warn", hard: "danger" };
  return value ? (map[value] ?? "secondary") : "secondary";
}

function formatDate(value: string) {
  return new Date(value).toLocaleDateString("vi-VN");
}

// ── Tab meta ──────────────────────────────────────────────────────────────────

const activeTabLabel = computed(() => {
  const map: Record<string, string> = {
    templates: "Mẫu quy trình",
    questions: "Câu hỏi PV",
    criteria: "Tiêu chí chấm điểm",
  };
  return map[activeTab.value] ?? activeTab.value;
});

const activeHeadline = computed(() => {
  const map: Record<string, string> = {
    templates: "Mẫu quy trình tuyển chọn",
    questions: "Ngân hàng câu hỏi phỏng vấn",
    criteria: "Tiêu chí chấm điểm",
  };
  return map[activeTab.value] ?? "";
});

const activeSubline = computed(() => {
  const map: Record<string, string> = {
    templates: `${templateState.value.items.length} mẫu đã tạo`,
    questions: `${questionState.value.items.length} câu hỏi`,
    criteria: `${criterionState.value.items.length} tiêu chí`,
  };
  return map[activeTab.value] ?? "";
});

const primaryCreateLabel = computed(() => {
  const map: Record<string, string> = {
    templates: "Tạo mẫu quy trình",
    questions: "Thêm câu hỏi",
    criteria: "Thêm tiêu chí",
  };
  return map[activeTab.value] ?? "Thêm mới";
});

function openCreate() {
  if (activeTab.value === "templates") openCreateTemplate();
  else if (activeTab.value === "questions") openCreateQuestion();
  else openCreateCriterion();
}

// ── Pipeline Templates ────────────────────────────────────────────────────────

const templateState = ref<{ items: PipelineStageTemplateRead[]; loading: boolean }>({
  items: [],
  loading: false,
});

const templateDialog = ref({
  visible: false,
  saving: false,
  error: "",
  editing: null as PipelineStageTemplateRead | null,
  name: "",
  is_default: false,
  items: [
    { stage_order: 1, stage_name: "Sàng lọc hồ sơ", stage_type: "screening" as const, is_required: true },
    { stage_order: 2, stage_name: "Phỏng vấn", stage_type: "interview" as const, is_required: true },
  ] as PipelineStageTemplateItemInput[],
});

async function loadTemplates() {
  templateState.value.loading = true;
  try {
    const res = await recruitmentService.listPipelineTemplates();
    templateState.value.items = res.data;
  } catch {
    errorBanner.value = "Không thể tải danh sách mẫu quy trình";
  } finally {
    templateState.value.loading = false;
  }
}

function openCreateTemplate() {
  templateDialog.value = {
    visible: true,
    saving: false,
    error: "",
    editing: null,
    name: "",
    is_default: false,
    items: [
      { stage_order: 1, stage_name: "Sàng lọc hồ sơ", stage_type: "screening", is_required: true },
      { stage_order: 2, stage_name: "Phỏng vấn", stage_type: "interview", is_required: true },
    ],
  };
}

function openEditTemplate(tpl: PipelineStageTemplateRead) {
  templateDialog.value = {
    visible: true,
    saving: false,
    error: "",
    editing: tpl,
    name: tpl.name,
    is_default: tpl.is_default,
    items: tpl.items.map((item) => ({
      stage_order: item.stage_order,
      stage_name: item.stage_name,
      stage_type: item.stage_type as "screening" | "test" | "interview" | "final",
      is_required: item.is_required,
    })),
  };
}

function addTemplateStage() {
  templateDialog.value.items.push({
    stage_order: templateDialog.value.items.length + 1,
    stage_name: "",
    stage_type: "interview",
    is_required: false,
  });
}

async function submitTemplate() {
  templateDialog.value.error = "";
  if (!templateDialog.value.name.trim()) {
    templateDialog.value.error = "Vui lòng nhập tên mẫu quy trình.";
    return;
  }
  if (templateDialog.value.items.some((i) => !i.stage_name.trim())) {
    templateDialog.value.error = "Vui lòng nhập tên cho tất cả các bước.";
    return;
  }
  const payload = {
    name: templateDialog.value.name.trim(),
    is_default: templateDialog.value.is_default,
    items: templateDialog.value.items.map((item, idx) => ({
      ...item,
      stage_order: idx + 1,
    })),
  };
  templateDialog.value.saving = true;
  try {
    if (templateDialog.value.editing) {
      await recruitmentService.updatePipelineTemplate(templateDialog.value.editing.id, payload);
      toast.add({ severity: "success", summary: "Đã cập nhật", detail: "Mẫu quy trình đã được cập nhật", life: 3000 });
    } else {
      await recruitmentService.createPipelineTemplate(payload);
      toast.add({ severity: "success", summary: "Đã tạo", detail: "Mẫu quy trình mới đã được tạo", life: 3000 });
    }
    templateDialog.value.visible = false;
    await loadTemplates();
  } catch (error: unknown) {
    templateDialog.value.error =
      (error as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
      "Không thể lưu mẫu quy trình";
  } finally {
    templateDialog.value.saving = false;
  }
}

function confirmDeleteTemplate(tpl: PipelineStageTemplateRead) {
  confirm.require({
    message: `Xóa mẫu quy trình "${tpl.name}"?`,
    header: "Xác nhận xóa",
    icon: "pi pi-trash",
    acceptLabel: "Xóa",
    rejectLabel: "Hủy",
    acceptClass: "p-button-danger",
    accept: async () => {
      try {
        await recruitmentService.deletePipelineTemplate(tpl.id);
        toast.add({ severity: "warn", summary: "Đã xóa", detail: `Mẫu quy trình "${tpl.name}" đã bị xóa`, life: 3000 });
        await loadTemplates();
      } catch {
        toast.add({ severity: "error", summary: "Lỗi", detail: "Không thể xóa mẫu quy trình", life: 3000 });
      }
    },
  });
}

// ── Interview Questions ───────────────────────────────────────────────────────

const questionState = ref<{ items: InterviewQuestionRead[]; loading: boolean }>({
  items: [],
  loading: false,
});

const questionFilter = ref<{ stage_type: string | null; difficulty: string | null }>({
  stage_type: null,
  difficulty: null,
});

const questionDialog = ref({
  visible: false,
  saving: false,
  error: "",
  editing: null as InterviewQuestionRead | null,
  question_text: "",
  category: "",
  job_position_ids: [] as number[],
  stage_type: null as string | null,
  difficulty: null as string | null,
  is_active: true,
});

async function loadQuestions() {
  questionState.value.loading = true;
  try {
    const params: Record<string, unknown> = {};
    if (questionFilter.value.stage_type) params.stage_type = questionFilter.value.stage_type;
    if (questionFilter.value.difficulty) params.difficulty = questionFilter.value.difficulty;
    const res = await recruitmentService.listQuestions(params);
    questionState.value.items = res.data;
  } catch {
    errorBanner.value = "Không thể tải danh sách câu hỏi";
  } finally {
    questionState.value.loading = false;
  }
}

function openCreateQuestion() {
  questionDialog.value = {
    visible: true,
    saving: false,
    error: "",
    editing: null,
    question_text: "",
    category: "",
    job_position_ids: [],
    stage_type: null,
    difficulty: null,
    is_active: true,
  };
}

function openEditQuestion(q: InterviewQuestionRead) {
  questionDialog.value = {
    visible: true,
    saving: false,
    error: "",
    editing: q,
    question_text: q.question_text,
    category: q.category ?? "",
    job_position_ids: q.job_position_ids ?? [],
    stage_type: q.stage_type ?? null,
    difficulty: q.difficulty ?? null,
    is_active: q.is_active,
  };
}

async function submitQuestion() {
  questionDialog.value.error = "";
  if (!questionDialog.value.question_text.trim()) {
    questionDialog.value.error = "Vui lòng nhập nội dung câu hỏi.";
    return;
  }
  const payload = {
    question_text: questionDialog.value.question_text.trim(),
    category: questionDialog.value.category.trim() || null,
    job_position_ids: questionDialog.value.job_position_ids,
    stage_type: questionDialog.value.stage_type || null,
    difficulty: (questionDialog.value.difficulty as "easy" | "medium" | "hard" | null) || null,
    is_active: questionDialog.value.is_active,
  };
  questionDialog.value.saving = true;
  try {
    if (questionDialog.value.editing) {
      await recruitmentService.updateQuestion(questionDialog.value.editing.id, payload);
      toast.add({ severity: "success", summary: "Đã cập nhật", detail: "Câu hỏi đã được cập nhật", life: 3000 });
    } else {
      await recruitmentService.createQuestion(payload);
      toast.add({ severity: "success", summary: "Đã thêm", detail: "Câu hỏi mới đã được thêm", life: 3000 });
    }
    questionDialog.value.visible = false;
    await loadQuestions();
  } catch (error: unknown) {
    questionDialog.value.error =
      (error as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
      "Không thể lưu câu hỏi";
  } finally {
    questionDialog.value.saving = false;
  }
}

function confirmDeleteQuestion(q: InterviewQuestionRead) {
  confirm.require({
    message: "Xóa câu hỏi này?",
    header: "Xác nhận xóa",
    icon: "pi pi-trash",
    acceptLabel: "Xóa",
    rejectLabel: "Hủy",
    acceptClass: "p-button-danger",
    accept: async () => {
      try {
        await recruitmentService.deleteQuestion(q.id);
        toast.add({ severity: "warn", summary: "Đã xóa", detail: "Câu hỏi đã bị xóa", life: 3000 });
        await loadQuestions();
      } catch {
        toast.add({ severity: "error", summary: "Lỗi", detail: "Không thể xóa câu hỏi", life: 3000 });
      }
    },
  });
}

// ── Scorecard Criteria ────────────────────────────────────────────────────────

const criterionState = ref<{ items: ScorecardCriterionRead[]; loading: boolean }>({
  items: [],
  loading: false,
});

const criterionFilter = ref<{ stage_type: string | null }>({ stage_type: null });

const criterionDialog = ref({
  visible: false,
  saving: false,
  error: "",
  editing: null as ScorecardCriterionRead | null,
  name: "",
  job_position_ids: [] as number[],
  stage_type: null as string | null,
  max_score: 5,
  sort_order: 0,
  is_active: true,
});

async function loadCriteria() {
  criterionState.value.loading = true;
  try {
    const params: Record<string, unknown> = {};
    if (criterionFilter.value.stage_type) params.stage_type = criterionFilter.value.stage_type;
    const res = await recruitmentService.listScorecardCriteria(params);
    criterionState.value.items = res.data;
  } catch {
    errorBanner.value = "Không thể tải danh sách tiêu chí scorecard";
  } finally {
    criterionState.value.loading = false;
  }
}

function openCreateCriterion() {
  criterionDialog.value = {
    visible: true,
    saving: false,
    error: "",
    editing: null,
    name: "",
    job_position_ids: [],
    stage_type: null,
    max_score: 5,
    sort_order: 0,
    is_active: true,
  };
}

function openEditCriterion(c: ScorecardCriterionRead) {
  criterionDialog.value = {
    visible: true,
    saving: false,
    error: "",
    editing: c,
    name: c.name,
    job_position_ids: c.job_position_ids ?? [],
    stage_type: c.stage_type ?? null,
    max_score: c.max_score,
    sort_order: c.sort_order,
    is_active: c.is_active,
  };
}

async function submitCriterion() {
  criterionDialog.value.error = "";
  if (!criterionDialog.value.name.trim()) {
    criterionDialog.value.error = "Vui lòng nhập tên tiêu chí.";
    return;
  }
  const payload = {
    name: criterionDialog.value.name.trim(),
    job_position_ids: criterionDialog.value.job_position_ids,
    stage_type: criterionDialog.value.stage_type || null,
    max_score: criterionDialog.value.max_score,
    sort_order: criterionDialog.value.sort_order,
    is_active: criterionDialog.value.is_active,
  };
  criterionDialog.value.saving = true;
  try {
    if (criterionDialog.value.editing) {
      await recruitmentService.updateScorecardCriterion(criterionDialog.value.editing.id, payload);
      toast.add({ severity: "success", summary: "Đã cập nhật", detail: "Tiêu chí đã được cập nhật", life: 3000 });
    } else {
      await recruitmentService.createScorecardCriterion(payload);
      toast.add({ severity: "success", summary: "Đã thêm", detail: "Tiêu chí mới đã được thêm", life: 3000 });
    }
    criterionDialog.value.visible = false;
    await loadCriteria();
  } catch (error: unknown) {
    criterionDialog.value.error =
      (error as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
      "Không thể lưu tiêu chí";
  } finally {
    criterionDialog.value.saving = false;
  }
}

function confirmDeleteCriterion(c: ScorecardCriterionRead) {
  confirm.require({
    message: `Xóa tiêu chí "${c.name}"?`,
    header: "Xác nhận xóa",
    icon: "pi pi-trash",
    acceptLabel: "Xóa",
    rejectLabel: "Hủy",
    acceptClass: "p-button-danger",
    accept: async () => {
      try {
        await recruitmentService.deleteScorecardCriterion(c.id);
        toast.add({ severity: "warn", summary: "Đã xóa", detail: `Tiêu chí "${c.name}" đã bị xóa`, life: 3000 });
        await loadCriteria();
      } catch {
        toast.add({ severity: "error", summary: "Lỗi", detail: "Không thể xóa tiêu chí", life: 3000 });
      }
    },
  });
}

// ── Init ─────────────────────────────────────────────────────────────────────

watch(activeTab, (tab) => {
  if (tab === "templates") loadTemplates();
  else if (tab === "questions") loadQuestions();
  else if (tab === "criteria") loadCriteria();
});

onMounted(() => {
  void loadJobPositions();
  loadTemplates();
});
</script>
