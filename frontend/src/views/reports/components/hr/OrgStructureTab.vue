<template>
  <div class="hr-report-tab">
    <Toast />

    <div class="hr-toolbar">
      <div class="hr-toolbar-actions">
        <Button
          label="Xem báo cáo"
          icon="pi pi-refresh"
          :loading="loading"
          @click="loadReport"
        />
        <Button
          label="Xuất Excel"
          icon="pi pi-file-excel"
          severity="success"
          outlined
          :loading="exporting"
          @click="exportExcel"
        />
      </div>
    </div>

    <div class="card hr-filter-card">
      <div class="hr-filter-grid" style="grid-template-columns: repeat(2, minmax(0, 1fr))">
        <div class="hr-field">
          <label>Phòng ban gốc</label>
          <Select
            v-model="departmentId"
            :options="departments"
            option-label="name"
            option-value="id"
            placeholder="Toàn công ty"
            show-clear
            filter
          />
        </div>
      </div>
    </div>

    <div v-if="report" class="hr-summary-strip">
      <div class="hr-summary-item">
        <span class="hr-summary-label">Tổng nhân viên</span>
        <strong>{{ report.total_headcount }}</strong>
      </div>
      <div class="hr-summary-item">
        <span class="hr-summary-label">Số phòng ban</span>
        <strong>{{ report.department_count }}</strong>
      </div>
    </div>

    <div class="card hr-table-card">
      <TreeTable
        :value="treeNodes"
        :loading="loading"
        responsive-layout="scroll"
      >
        <template #empty>
          <div class="hr-empty">Chưa có dữ liệu cơ cấu tổ chức.</div>
        </template>

        <Column field="name" header="Phòng ban / Chức danh" expander style="min-width: 220px" />
        <Column field="direct_headcount" header="Trực tiếp" style="width: 110px" />
        <Column field="total_headcount" header="Tổng (gồm phòng con)" style="width: 180px" />
      </TreeTable>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import Button from 'primevue/button'
import Column from 'primevue/column'
import Toast from 'primevue/toast'
import TreeTable from 'primevue/treetable'
import Select from 'primevue/select'
import { useToast } from 'primevue/usetoast'

import departmentService, { type DepartmentRead } from '@/services/departmentService'
import hrReportService from '@/services/hrReportService'
import type { HrDepartmentNode, HrOrgStructureResponse } from '@/types/hr_report.types'

interface TreeNodeData {
  name: string
  direct_headcount: number | string
  total_headcount: number | string
}

interface TreeNode {
  key: string
  data: TreeNodeData
  children?: TreeNode[]
}

const toast = useToast()

const departments = ref<DepartmentRead[]>([])
const report = ref<HrOrgStructureResponse | null>(null)
const loading = ref(false)
const exporting = ref(false)
const departmentId = ref<number | null>(null)

function convertToTreeNodes(nodes: HrDepartmentNode[]): TreeNode[] {
  return nodes.map((node) => {
    const jobTitleChildren: TreeNode[] = node.by_job_title
      .filter((jt) => jt.headcount > 0)
      .map((jt) => ({
        key: `jt-${node.department_id}-${jt.job_title_id ?? 'none'}`,
        data: {
          name: jt.job_title_name ?? '(Chưa có chức danh)',
          direct_headcount: jt.headcount,
          total_headcount: jt.headcount,
        },
      }))

    return {
      key: String(node.department_id),
      data: {
        name: node.department_name,
        direct_headcount: node.direct_headcount,
        total_headcount: node.total_headcount,
      },
      children: [...convertToTreeNodes(node.children), ...jobTitleChildren],
    }
  })
}

const treeNodes = computed<TreeNode[]>(() =>
  report.value ? convertToTreeNodes(report.value.tree) : [],
)

async function loadDepartments() {
  try {
    const res = await departmentService.getList(true)
    departments.value = res.data
  } catch {
    departments.value = []
  }
}

async function loadReport() {
  loading.value = true
  try {
    const res = await hrReportService.getOrgStructure(departmentId.value)
    report.value = res.data
  } catch {
    toast.add({
      severity: 'error',
      summary: 'Không tải được báo cáo',
      detail: 'Vui lòng thử lại.',
      life: 3000,
    })
  } finally {
    loading.value = false
  }
}

async function exportExcel() {
  exporting.value = true
  try {
    await hrReportService.exportReport('org-structure', { department_id: departmentId.value })
  } catch {
    toast.add({
      severity: 'error',
      summary: 'Xuất Excel thất bại',
      detail: 'Không thể xuất báo cáo cơ cấu.',
      life: 3000,
    })
  } finally {
    exporting.value = false
  }
}

onMounted(async () => {
  await loadDepartments()
  await loadReport()
})
</script>
