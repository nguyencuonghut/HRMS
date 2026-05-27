<template>
  <div>
    <div class="rc-toolbar">
      <Select
        v-model="selectedJrId"
        :options="jrOptions"
        option-label="label"
        option-value="value"
        filter
        show-clear
        placeholder="Chọn JR để xem quy trình tuyển chọn"
        style="width: 340px"
        @change="onJrChange"
      />
      <Button
        icon="pi pi-refresh"
        severity="secondary"
        text
        rounded
        :loading="loading"
        @click="void loadBoard()"
      />
      <RouterLink
        v-if="selectedJrId"
        :to="`/recruitment/jr/${selectedJrId}`"
        class="ml-auto"
      >
        <Button
          label="Chi tiết JR"
          icon="pi pi-briefcase"
          severity="secondary"
          outlined
        />
      </RouterLink>
    </div>

    <div v-if="!selectedJrId" class="card">
      <div class="rc-empty">Chọn một JR để xem Kanban tuyển chọn</div>
    </div>

    <div v-else-if="board && board.stages.length" class="rc-kanban-board">
      <div
        v-for="column in board.stages"
        :key="column.stage.id"
        class="rc-kanban-column"
      >
        <div class="rc-kanban-column-head">
          <div>
            <div class="rc-kanban-column-title">
              {{ column.stage.stage_name }}
            </div>
            <div class="rc-muted">
              {{ stageTypeLabel(column.stage.stage_type) }}
            </div>
          </div>
          <Tag :value="String(column.applications.length)" severity="info" />
        </div>

        <div v-if="column.applications.length" class="rc-kanban-cards">
          <RouterLink
            v-for="card in column.applications"
            :key="card.application_id"
            :to="applicationLink(card.application_id)"
            class="rc-kanban-card-link"
          >
            <article class="rc-kanban-card">
              <div class="rc-kanban-card-title">{{ card.candidate_name }}</div>
              <div class="rc-muted">
                Nộp ngày {{ formatDate(card.applied_date) }}
              </div>
              <div class="rc-muted">
                {{ card.source_channel ?? "Không rõ nguồn" }}
              </div>
              <div v-if="card.last_result" class="rc-kanban-card-result">
                <Tag
                  :value="resultLabel(card.last_result)"
                  :severity="resultSeverity(card.last_result)"
                />
              </div>
            </article>
          </RouterLink>
        </div>
        <div v-else class="rc-kanban-empty">Chưa có ứng viên ở cột này</div>
      </div>
    </div>

    <div v-else-if="selectedJrId && !loading" class="card">
      <div
        class="rc-empty"
        style="display: flex; flex-direction: column; gap: 1rem; align-items: center"
      >
        <span>JR này chưa có quy trình tuyển chọn.</span>
        <Button
          label="Cấu hình quy trình"
          icon="pi pi-sliders-h"
          severity="info"
          @click="showSetupDialog = true"
        />
      </div>
    </div>

    <PipelineSetupDialog
      v-model:visible="showSetupDialog"
      :jr-id="selectedJrId"
      @saved="void loadBoard()"
    />
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref, watch } from "vue";
import { RouterLink, useRoute, useRouter } from "vue-router";
import Button from "primevue/button";
import Select from "primevue/select";
import Tag from "primevue/tag";
import { useToast } from "primevue/usetoast";

import recruitmentService, {
  type JobRequisitionListItem,
  type KanbanBoard,
} from "@/services/recruitmentService";
import PipelineSetupDialog from "./components/PipelineSetupDialog.vue";

const route = useRoute();
const router = useRouter();
const toast = useToast();

const loading = ref(false);
const jrOptions = ref<Array<{ label: string; value: number }>>([]);
const selectedJrId = ref<number | null>(null);
const board = ref<KanbanBoard | null>(null);
const showSetupDialog = ref(false);

function formatDate(value: string) {
  return new Date(value).toLocaleDateString("vi-VN");
}

function stageTypeLabel(value: string) {
  const map: Record<string, string> = {
    screening: "Screening",
    test: "Test",
    interview: "Interview",
    final: "Final",
  };
  return map[value] ?? value;
}

function resultLabel(value: string) {
  const map: Record<string, string> = {
    pass: "Đạt",
    fail: "Không đạt",
    hold: "Tạm giữ",
    pending: "Đang chờ",
  };
  return map[value] ?? value;
}

function resultSeverity(value: string) {
  const map: Record<string, string> = {
    pass: "success",
    fail: "danger",
    hold: "warn",
    pending: "secondary",
  };
  return map[value] ?? "secondary";
}

function applicationLink(applicationId: number) {
  return `/recruitment/applications/${applicationId}`;
}

async function loadJR() {
  try {
    const response = await recruitmentService.listJR({ page_size: 200 });
    const items = response.data.items.filter((item: JobRequisitionListItem) =>
      ["approved", "in_progress", "completed"].includes(item.status),
    );
    jrOptions.value = items.map((item: JobRequisitionListItem) => ({
      label: `${item.code} — ${item.job_position_name}`,
      value: item.id,
    }));
  } catch {
    toast.add({
      severity: "error",
      summary: "Lỗi",
      detail: "Không thể tải danh sách JR",
      life: 3000,
    });
  }
}

async function loadBoard() {
  if (!selectedJrId.value) {
    board.value = null;
    return;
  }
  loading.value = true;
  try {
    const response = await recruitmentService.getKanban(selectedJrId.value);
    board.value = response.data;
  } catch {
    board.value = null;
    toast.add({
      severity: "error",
      summary: "Lỗi",
      detail: "Không thể tải bảng Kanban",
      life: 3000,
    });
  } finally {
    loading.value = false;
  }
}

function onJrChange() {
  if (selectedJrId.value) {
    router.push(`/recruitment/selection/${selectedJrId.value}`);
  } else {
    router.push("/recruitment/selection");
    board.value = null;
  }
  void loadBoard();
}

watch(
  () => route.params.jr_id,
  (value) => {
    const next = value ? Number(value) : null;
    const resolved = next && Number.isFinite(next) ? next : null;
    if (selectedJrId.value !== resolved) {
      selectedJrId.value = resolved;
      void loadBoard();
    }
  },
);

onMounted(async () => {
  const paramJrId = route.params.jr_id;
  const initial = paramJrId ? Number(paramJrId) : null;
  selectedJrId.value = initial && Number.isFinite(initial) ? initial : null;
  await loadJR();
  await loadBoard();
});
</script>
