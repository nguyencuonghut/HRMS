<template>
  <Dialog
    :visible="visible"
    :header="readonly ? 'Scorecard phỏng vấn' : 'Chấm điểm phỏng vấn'"
    modal
    :style="{ width: '720px', maxWidth: '96vw' }"
    :closable="!saving"
    @update:visible="emit('update:visible', $event)"
  >
    <div class="rc-form rc-form--wide">
      <div v-if="panelist?.submitted_at" class="rc-scorecard-banner">
        Đã gửi lúc {{ formatDatetime(panelist.submitted_at) }}.
      </div>

      <div class="rc-field">
        <label class="rc-label">Kết quả tổng</label>
        <SelectButton
          v-model="result"
          :options="resultOptions"
          option-label="label"
          option-value="value"
          :disabled="readonly"
        />
      </div>

      <div class="rc-scorecard-grid">
        <div v-for="item in scoreRows" :key="item.key" class="rc-scorecard-row">
          <div class="rc-scorecard-name">
            <strong>{{ item.criterion }}</strong>
            <span class="rc-muted">Tối đa {{ item.max_score }} điểm</span>
          </div>
          <InputNumber
            v-model="item.score"
            :min="0"
            :max="item.max_score"
            :min-fraction-digits="0"
            :max-fraction-digits="2"
            :use-grouping="false"
            input-class="rc-scorecard-input"
            :disabled="readonly"
          />
        </div>
      </div>

      <div class="rc-scorecard-summary">
        <span class="rc-muted">Điểm trung bình</span>
        <strong>{{ averageScoreLabel }}</strong>
      </div>

      <div class="rc-field">
        <label class="rc-label">Ghi chú riêng</label>
        <Textarea
          v-model="privateNotes"
          rows="4"
          class="w-full"
          auto-resize
          :disabled="readonly"
        />
      </div>

      <p v-if="errorMessage" class="rc-api-error">
        <i class="pi pi-exclamation-circle" />
        {{ errorMessage }}
      </p>

      <InterviewKitPanel
        :loading="loading"
        :questions="[]"
        :criteria="criteria"
      />
    </div>

    <template #footer>
      <Button
        label="Đóng"
        severity="secondary"
        text
        :disabled="saving"
        @click="emit('update:visible', false)"
      />
      <Button
        v-if="!readonly"
        label="Gửi scorecard"
        :loading="saving"
        @click="submit"
      />
    </template>
  </Dialog>
</template>

<script setup lang="ts">
import { computed, ref, watch } from "vue";
import Button from "primevue/button";
import Dialog from "primevue/dialog";
import InputNumber from "primevue/inputnumber";
import SelectButton from "primevue/selectbutton";
import Textarea from "primevue/textarea";
import { useToast } from "primevue/usetoast";
import { formatDatetime } from "@/utils/format";

import recruitmentService, {
  type InterviewPanelistRead,
  type ScorecardCriterionRead,
} from "@/services/recruitmentService";
import InterviewKitPanel from "./InterviewKitPanel.vue";

type ScoreRow = {
  key: string;
  criterion: string;
  max_score: number;
  score: number | null;
};

const props = defineProps<{
  visible: boolean;
  interviewId: number | null;
  panelist: InterviewPanelistRead | null;
  jobPositionId: number | null;
}>();

const emit = defineEmits<{
  (e: "update:visible", value: boolean): void;
  (e: "saved"): void;
}>();

const toast = useToast();

const loading = ref(false);
const saving = ref(false);
const errorMessage = ref("");

const criteria = ref<ScorecardCriterionRead[]>([]);
const scoreRows = ref<ScoreRow[]>([]);
const privateNotes = ref("");
const result = ref<"pass" | "fail" | "hold" | "pending">("hold");

const resultOptions = [
  { label: "Đạt", value: "pass" },
  { label: "Giữ", value: "hold" },
  { label: "Không đạt", value: "fail" },
];

const readonly = computed(() => !!props.panelist?.submitted_at);

const averageScore = computed(() => {
  const values = scoreRows.value
    .map((item) => item.score)
    .filter((value): value is number => typeof value === "number");
  if (!values.length) {
    return null;
  }
  const total = values.reduce((sum, value) => sum + value, 0);
  return Number((total / values.length).toFixed(2));
});

const averageScoreLabel = computed(() => averageScore.value?.toString() ?? "—");


function resetForm() {
  errorMessage.value = "";
  privateNotes.value = props.panelist?.private_notes ?? "";
  result.value =
    props.panelist?.result && props.panelist.result !== "pending"
      ? props.panelist.result
      : "hold";
}

async function loadCriteria() {
  if (!props.jobPositionId) {
    criteria.value = [];
    scoreRows.value = (props.panelist?.criteria_scores ?? []).map(
      (item, index) => ({
        key: `existing-${index}`,
        criterion: item.criterion,
        max_score: Number(item.max_score ?? 5),
        score: Number(item.score),
      }),
    );
    return;
  }

  loading.value = true;
  try {
    const response = await recruitmentService.listScorecardCriteria({
      job_position_id: props.jobPositionId,
      stage_type: "interview",
    });
    criteria.value = response.data;

    const existingMap = new Map(
      (props.panelist?.criteria_scores ?? []).map((item) => [
        item.criterion,
        item,
      ]),
    );

    const rows: ScoreRow[] = response.data.map((item) => {
      const existing = existingMap.get(item.name);
      return {
        key: `criterion-${item.id}`,
        criterion: item.name,
        max_score: item.max_score,
        score: existing ? Number(existing.score) : null,
      };
    });

    for (const [criterion, existing] of existingMap.entries()) {
      if (rows.some((row) => row.criterion === criterion)) {
        continue;
      }
      rows.push({
        key: `existing-${criterion}`,
        criterion,
        max_score: Number(existing.max_score ?? 5),
        score: Number(existing.score),
      });
    }

    scoreRows.value = rows;
  } catch {
    criteria.value = [];
    scoreRows.value = [];
    toast.add({
      severity: "warn",
      summary: "Cảnh báo",
      detail: "Không thể tải scorecard criteria",
      life: 3000,
    });
  } finally {
    loading.value = false;
  }
}

watch(
  () => props.visible,
  (visible) => {
    if (!visible) {
      return;
    }
    resetForm();
    void loadCriteria();
  },
);

watch(
  () => props.panelist,
  () => {
    if (props.visible) {
      resetForm();
      void loadCriteria();
    }
  },
);

async function submit() {
  errorMessage.value = "";
  if (!props.interviewId || !props.panelist) {
    errorMessage.value = "Không tìm thấy panelist để chấm điểm.";
    return;
  }

  saving.value = true;
  try {
    await recruitmentService.submitPanelistScore(
      props.interviewId,
      props.panelist.user_id,
      {
        criteria_scores: scoreRows.value
          .filter((item) => item.score !== null)
          .map((item) => ({
            criterion: item.criterion,
            score: item.score as number,
            max_score: item.max_score,
          })),
        overall_score: averageScore.value,
        result: result.value,
        private_notes: privateNotes.value || null,
      },
    );
    toast.add({
      severity: "success",
      summary: "Đã gửi",
      detail: "Scorecard đã được lưu",
      life: 3000,
    });
    emit("saved");
    emit("update:visible", false);
  } catch (error: unknown) {
    errorMessage.value =
      (error as { response?: { data?: { detail?: string } } })?.response?.data
        ?.detail ?? "Không thể lưu scorecard";
  } finally {
    saving.value = false;
  }
}
</script>
