<template>
  <Dialog
    :visible="visible"
    header="Cấu hình quy trình tuyển chọn"
    modal
    :style="{ width: '680px', maxWidth: '96vw' }"
    :closable="!saving"
    @update:visible="emit('update:visible', $event)"
  >
    <div class="rc-form rc-form--wide">
      <div class="rc-field">
        <label class="rc-label">Nguồn cấu hình</label>
        <SelectButton
          v-model="mode"
          :options="modeOptions"
          option-label="label"
          option-value="value"
        />
      </div>

      <div v-if="mode === 'template'" class="rc-field">
        <label class="rc-label">Chọn mẫu quy trình <span class="rc-req">*</span></label>
        <div v-if="loadingTemplates" class="rc-muted">Đang tải mẫu quy trình...</div>
        <div v-else-if="templates.length" class="rc-template-list">
          <div
            v-for="tpl in templates"
            :key="tpl.id"
            class="rc-template-item"
            :class="{ 'rc-template-item--selected': selectedTemplateId === tpl.id }"
            @click="selectedTemplateId = tpl.id"
          >
            <div class="rc-template-name">
              {{ tpl.name }}
              <Tag v-if="tpl.is_default" value="Mặc định" severity="info" />
            </div>
            <div class="rc-template-stages">
              <Tag
                v-for="item in tpl.items"
                :key="item.id"
                :value="`${item.stage_order}. ${item.stage_name}`"
                severity="secondary"
              />
            </div>
          </div>
        </div>
        <div v-else class="rc-muted">Chưa có mẫu nào. Hãy tạo thủ công.</div>
      </div>

      <div v-if="mode === 'manual'">
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
              Các bước tuyển chọn <span class="rc-req">*</span>
            </label>
            <Button
              icon="pi pi-plus"
              label="Thêm bước"
              size="small"
              severity="secondary"
              outlined
              @click="addStage"
            />
          </div>

          <div v-if="manualStages.length" class="rc-stage-setup-list">
            <div
              v-for="(stage, index) in manualStages"
              :key="index"
              class="rc-stage-setup-row"
            >
              <span class="rc-stage-order">{{ index + 1 }}</span>
              <InputText
                v-model="stage.stage_name"
                placeholder="Tên bước"
                style="flex: 1"
              />
              <Select
                v-model="stage.stage_type"
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
                :disabled="manualStages.length <= 1"
                @click="removeStage(index)"
              />
            </div>
          </div>
        </div>
      </div>

      <p v-if="errorMessage" class="rc-api-error">
        <i class="pi pi-exclamation-circle" />
        {{ errorMessage }}
      </p>
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
        label="Cấu hình quy trình"
        icon="pi pi-check"
        :loading="saving"
        @click="submit"
      />
    </template>
  </Dialog>
</template>

<script setup lang="ts">
import { ref, watch } from "vue";
import Button from "primevue/button";
import Dialog from "primevue/dialog";
import InputText from "primevue/inputtext";
import Select from "primevue/select";
import SelectButton from "primevue/selectbutton";
import Tag from "primevue/tag";
import { useToast } from "primevue/usetoast";

import recruitmentService, {
  type PipelineStageCreate,
  type PipelineStageTemplateRead,
} from "@/services/recruitmentService";

const props = defineProps<{
  visible: boolean;
  jrId: number | null;
}>();

const emit = defineEmits<{
  (e: "update:visible", value: boolean): void;
  (e: "saved"): void;
}>();

const toast = useToast();

const saving = ref(false);
const loadingTemplates = ref(false);
const errorMessage = ref("");

const mode = ref<"template" | "manual">("template");
const templates = ref<PipelineStageTemplateRead[]>([]);
const selectedTemplateId = ref<number | null>(null);
const manualStages = ref<PipelineStageCreate[]>([
  { stage_order: 1, stage_name: "Sàng lọc hồ sơ", stage_type: "screening" },
  { stage_order: 2, stage_name: "Phỏng vấn", stage_type: "interview" },
]);

const modeOptions = [
  { label: "Từ mẫu có sẵn", value: "template" },
  { label: "Tạo thủ công", value: "manual" },
] as const;

const stageTypeOptions = [
  { label: "Sàng lọc", value: "screening" },
  { label: "Kiểm tra", value: "test" },
  { label: "Phỏng vấn", value: "interview" },
  { label: "Vòng cuối", value: "final" },
] as const;

function addStage() {
  manualStages.value.push({
    stage_order: manualStages.value.length + 1,
    stage_name: "",
    stage_type: "interview",
  });
}

function removeStage(index: number) {
  manualStages.value.splice(index, 1);
  manualStages.value.forEach((stage, i) => {
    stage.stage_order = i + 1;
  });
}

async function loadTemplates() {
  loadingTemplates.value = true;
  try {
    const response = await recruitmentService.listPipelineTemplates();
    templates.value = response.data;
    if (templates.value.length) {
      const defaultTpl = templates.value.find((t) => t.is_default);
      selectedTemplateId.value = (defaultTpl ?? templates.value[0]).id;
    }
  } catch {
    toast.add({
      severity: "warn",
      summary: "Cảnh báo",
      detail: "Không thể tải danh sách mẫu quy trình",
      life: 3000,
    });
  } finally {
    loadingTemplates.value = false;
  }
}

watch(
  () => props.visible,
  (visible) => {
    if (!visible) {
      return;
    }
    mode.value = "template";
    errorMessage.value = "";
    selectedTemplateId.value = null;
    manualStages.value = [
      { stage_order: 1, stage_name: "Sàng lọc hồ sơ", stage_type: "screening" },
      { stage_order: 2, stage_name: "Phỏng vấn", stage_type: "interview" },
    ];
    void loadTemplates();
  },
);

async function submit() {
  errorMessage.value = "";
  if (!props.jrId) {
    errorMessage.value = "Không xác định được JR.";
    return;
  }

  if (mode.value === "template") {
    if (!selectedTemplateId.value) {
      errorMessage.value = "Vui lòng chọn một mẫu quy trình.";
      return;
    }
  } else {
    const invalid = manualStages.value.some((s) => !s.stage_name.trim());
    if (invalid) {
      errorMessage.value = "Vui lòng nhập tên cho tất cả các bước.";
      return;
    }
    if (!manualStages.value.length) {
      errorMessage.value = "Cần ít nhất một bước tuyển chọn.";
      return;
    }
  }

  saving.value = true;
  try {
    const payload =
      mode.value === "template"
        ? { template_id: selectedTemplateId.value }
        : { stages: manualStages.value };

    await recruitmentService.setupPipelineForJR(props.jrId, payload);
    toast.add({
      severity: "success",
      summary: "Đã cấu hình",
      detail: "Quy trình tuyển chọn đã được thiết lập",
      life: 3000,
    });
    emit("saved");
    emit("update:visible", false);
  } catch (error: unknown) {
    errorMessage.value =
      (error as { response?: { data?: { detail?: string } } })?.response?.data
        ?.detail ?? "Không thể cấu hình quy trình";
  } finally {
    saving.value = false;
  }
}
</script>
