<template>
  <div class="rc-kit-panel">
    <div class="rc-kit-section">
      <div class="rc-kit-title">Câu hỏi gợi ý</div>
      <div v-if="loading" class="rc-muted">Đang tải Interview Kit...</div>
      <div v-else-if="questions.length" class="rc-kit-list">
        <div
          v-for="question in questions"
          :key="question.id"
          class="rc-kit-item"
        >
          <div class="rc-kit-item-top">
            <Tag
              v-if="question.category"
              :value="question.category"
              severity="secondary"
            />
            <Tag
              v-if="question.difficulty"
              :value="difficultyLabel(question.difficulty)"
              severity="contrast"
            />
          </div>
          <div class="rc-kit-question">{{ question.question_text }}</div>
        </div>
      </div>
      <div v-else class="rc-muted">Chưa có câu hỏi gợi ý cho vị trí này.</div>
    </div>

    <div class="rc-kit-section">
      <div class="rc-kit-title">Tiêu chí scorecard</div>
      <div v-if="loading" class="rc-muted">Đang tải tiêu chí...</div>
      <div v-else-if="criteria.length" class="rc-kit-criteria">
        <div
          v-for="criterion in criteria"
          :key="criterion.id"
          class="rc-kit-criterion"
        >
          <span>{{ criterion.name }}</span>
          <Tag :value="`${criterion.max_score} điểm`" severity="info" />
        </div>
      </div>
      <div v-else class="rc-muted">Chưa cấu hình scorecard criteria.</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import Tag from "primevue/tag";

import type {
  InterviewQuestionRead,
  ScorecardCriterionRead,
} from "@/services/recruitmentService";

defineProps<{
  loading?: boolean;
  questions: InterviewQuestionRead[];
  criteria: ScorecardCriterionRead[];
}>();

function difficultyLabel(value: InterviewQuestionRead["difficulty"]) {
  const map = {
    easy: "Dễ",
    medium: "Trung bình",
    hard: "Khó",
  } as const;
  return value ? (map[value] ?? value) : "";
}
</script>
