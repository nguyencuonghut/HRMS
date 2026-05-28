<template>
  <Dialog
    :visible="visible"
    :header="dialogTitle"
    modal
    :style="{ width: '760px', maxWidth: '96vw' }"
    :closable="!saving"
    @update:visible="emit('update:visible', $event)"
  >
    <div class="rc-form rc-form--wide">
      <div class="rc-row">
        <div class="rc-field">
          <label class="rc-label"
            >Lịch phỏng vấn <span class="rc-req">*</span></label
          >
          <DatePicker
            v-model="scheduledAt"
            class="w-full"
            date-format="dd/mm/yy"
            show-time
            hour-format="24"
            show-button-bar
          />
        </div>
        <div class="rc-field">
          <label class="rc-label">Thời lượng (phút)</label>
          <InputNumber
            v-model="durationMinutes"
            class="w-full"
            :min="15"
            :max="480"
            :step="15"
          />
        </div>
      </div>

      <div class="rc-row">
        <div class="rc-field">
          <label class="rc-label">Hình thức</label>
          <Select
            v-model="format"
            :options="formatOptions"
            option-label="label"
            option-value="value"
            class="w-full"
          />
        </div>
        <div class="rc-field">
          <label class="rc-label">{{ locationLabel }}</label>
          <InputText
            v-model="location"
            class="w-full"
            :placeholder="locationPlaceholder"
          />
        </div>
      </div>

      <div class="rc-field">
        <label class="rc-label"
          >Người phỏng vấn <span class="rc-req">*</span></label
        >
        <MultiSelect
          v-model="panelistUserIds"
          :options="userOptions"
          option-label="label"
          option-value="value"
          filter
          :loading="userSearchLoading"
          display="chip"
          class="w-full"
          placeholder="Chọn người phỏng vấn"
          @filter="onUserFilter"
        />
      </div>

      <div class="rc-field">
        <label class="rc-label">Ghi chú</label>
        <Textarea v-model="note" rows="3" class="w-full" auto-resize />
      </div>

      <p v-if="errorMessage" class="rc-api-error">
        <i class="pi pi-exclamation-circle" />
        {{ errorMessage }}
      </p>

      <InterviewKitPanel
        :loading="kitLoading"
        :questions="questions"
        :criteria="criteria"
      />
    </div>

    <template #footer>
      <Button
        label="Hủy"
        severity="secondary"
        text
        :disabled="saving"
        @click="emit('update:visible', false)"
      />
      <Button
        :label="editing ? 'Cập nhật lịch' : 'Lên lịch'"
        :loading="saving"
        @click="submit"
      />
    </template>
  </Dialog>
</template>

<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { parseDatetimeUTC } from "@/utils/format";
import type { MultiSelectFilterEvent } from "primevue/multiselect";
import Button from "primevue/button";
import DatePicker from "primevue/datepicker";
import Dialog from "primevue/dialog";
import InputNumber from "primevue/inputnumber";
import InputText from "primevue/inputtext";
import MultiSelect from "primevue/multiselect";
import Select from "primevue/select";
import Textarea from "primevue/textarea";
import { useToast } from "primevue/usetoast";

import recruitmentService, {
  type ApplicationRead,
  type InterviewQuestionRead,
  type InterviewSessionRead,
  type ScorecardCriterionRead,
} from "@/services/recruitmentService";
import userService from "@/services/userService";
import InterviewKitPanel from "./InterviewKitPanel.vue";

const props = defineProps<{
  visible: boolean;
  application: ApplicationRead | null;
  interviewStageId: number | null;
  jobPositionId: number | null;
  editing?: InterviewSessionRead | null;
}>();

const emit = defineEmits<{
  (e: "update:visible", value: boolean): void;
  (e: "saved"): void;
}>();

const toast = useToast();

const saving = ref(false);
const kitLoading = ref(false);
const errorMessage = ref("");

const scheduledAt = ref<Date | null>(null);
const durationMinutes = ref<number | null>(60);
const format = ref<"in_person" | "online" | "phone">("in_person");
const location = ref("");
const note = ref("");
const panelistUserIds = ref<number[]>([]);
const userOptions = ref<Array<{ label: string; value: number }>>([]);
const userSearchLoading = ref(false);
const questions = ref<InterviewQuestionRead[]>([]);
const criteria = ref<ScorecardCriterionRead[]>([]);

let _searchTimer: ReturnType<typeof setTimeout> | null = null;

async function searchUsers(query: string) {
  userSearchLoading.value = true;
  try {
    const res = await userService.list({ search: query || undefined, is_active: true, limit: 50 });
    const fetched = res.data.items.map((item) => ({
      label: item.full_name || item.email,
      value: item.id,
    }));
    // Giữ lại các user đã được chọn nhưng không có trong kết quả search
    const selectedNotInResult = userOptions.value.filter(
      (opt) => panelistUserIds.value.includes(opt.value) && !fetched.some((f) => f.value === opt.value),
    );
    userOptions.value = [...selectedNotInResult, ...fetched];
  } catch {
    // silent — không ảnh hưởng UX
  } finally {
    userSearchLoading.value = false;
  }
}

function onUserFilter(event: MultiSelectFilterEvent) {
  if (_searchTimer) clearTimeout(_searchTimer);
  _searchTimer = setTimeout(() => void searchUsers(event.value), 300);
}

const formatOptions = [
  { label: "Trực tiếp", value: "in_person" },
  { label: "Online", value: "online" },
  { label: "Điện thoại", value: "phone" },
];

const dialogTitle = computed(() =>
  props.editing ? "Cập nhật lịch phỏng vấn" : "Lên lịch phỏng vấn",
);

const locationLabel = computed(() =>
  format.value === "online" ? "Link meeting" : "Địa điểm",
);

const locationPlaceholder = computed(() =>
  format.value === "online"
    ? "VD: https://meet.google.com/..."
    : format.value === "phone"
      ? "Số điện thoại / ghi chú cuộc gọi"
      : "Phòng họp / địa chỉ",
);

function resetForm() {
  scheduledAt.value = parseDatetimeUTC(props.editing?.scheduled_at);
  durationMinutes.value = props.editing?.duration_minutes ?? 60;
  format.value = props.editing?.format ?? "in_person";
  location.value = props.editing?.location ?? "";
  note.value = props.editing?.note ?? "";
  panelistUserIds.value =
    props.editing?.panelists.map((item) => item.user_id) ?? [];
  errorMessage.value = "";
}

async function loadKit() {
  kitLoading.value = true;
  try {
    const questionRequest = props.jobPositionId
      ? recruitmentService.listQuestions({
          job_position_id: props.jobPositionId,
          stage_type: "interview",
        })
      : Promise.resolve({ data: [] as InterviewQuestionRead[] });
    const criteriaRequest = props.jobPositionId
      ? recruitmentService.listScorecardCriteria({
          job_position_id: props.jobPositionId,
          stage_type: "interview",
        })
      : Promise.resolve({ data: [] as ScorecardCriterionRead[] });

    const [questionRes, criteriaRes] = await Promise.all([questionRequest, criteriaRequest]);
    questions.value = questionRes.data;
    criteria.value = criteriaRes.data;
  } catch {
    toast.add({
      severity: "warn",
      summary: "Cảnh báo",
      detail: "Không thể tải Interview Kit",
      life: 3000,
    });
  } finally {
    kitLoading.value = false;
  }
}

async function preloadSelectedUsers() {
  if (!props.editing?.panelists.length) {
    userOptions.value = [];
    return;
  }
  // Pre-populate options với panelists hiện tại để label hiển thị đúng
  userOptions.value = props.editing.panelists.map((p) => ({
    label: p.user_name ?? `User #${p.user_id}`,
    value: p.user_id,
  }));
}

watch(
  () => props.visible,
  (visible) => {
    if (!visible) {
      return;
    }
    resetForm();
    void preloadSelectedUsers();
    void loadKit();
    void searchUsers("");
  },
);

watch(
  () => props.editing,
  () => {
    if (props.visible) {
      resetForm();
    }
  },
);

async function submit() {
  errorMessage.value = "";

  if (!props.application) {
    errorMessage.value = "Không tìm thấy application.";
    return;
  }
  if (!props.editing && !props.interviewStageId) {
    errorMessage.value = "JR này chưa có bước phỏng vấn.";
    return;
  }
  if (!scheduledAt.value) {
    errorMessage.value = "Vui lòng chọn lịch phỏng vấn.";
    return;
  }
  if (!panelistUserIds.value.length) {
    errorMessage.value = "Vui lòng chọn ít nhất một người phỏng vấn.";
    return;
  }

  saving.value = true;
  try {
    const payload = {
      stage_id: props.editing?.stage_id ?? props.interviewStageId!,
      scheduled_at: scheduledAt.value.toISOString(),
      duration_minutes: durationMinutes.value ?? 60,
      format: format.value,
      location: location.value || null,
      note: note.value || null,
      panelist_user_ids: panelistUserIds.value,
    };

    if (props.editing) {
      await recruitmentService.updateInterview(props.editing.id, payload);
      toast.add({
        severity: "success",
        summary: "Đã cập nhật",
        detail: "Lịch phỏng vấn đã được cập nhật",
        life: 3000,
      });
    } else {
      await recruitmentService.createInterview(props.application.id, payload);
      toast.add({
        severity: "success",
        summary: "Đã tạo",
        detail: "Đã lên lịch phỏng vấn",
        life: 3000,
      });
    }

    emit("saved");
    emit("update:visible", false);
  } catch (error: unknown) {
    errorMessage.value =
      (error as { response?: { data?: { detail?: string } } })?.response?.data
        ?.detail ?? "Không thể lưu lịch phỏng vấn";
  } finally {
    saving.value = false;
  }
}
</script>
