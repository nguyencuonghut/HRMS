<template>
  <div class="data-export-container">
    <div class="page-header mb-4">
      <div>
        <h2>Xuất dữ liệu nhân sự tổng hợp</h2>
        <div class="subtitle">Tải xuống file Excel chứa toàn bộ thông tin chi tiết của nhân viên trong hệ thống</div>
      </div>
    </div>

    <div class="grid mt-3">
      <div class="col-12 md:col-10 lg:col-8 mx-auto">
        <Card class="export-card">
          <template #title>
            <div class="flex align-items-center gap-2 export-title">
              <i class="pi pi-file-excel text-green-500 text-3xl"></i>
              <span>Xuất Báo Cáo Nhân Sự Toàn Diện</span>
            </div>
          </template>

          <template #content>
            <p class="intro-text text-color-secondary">
              Hệ thống sẽ tổng hợp toàn bộ hồ sơ nhân sự hiện có, bao gồm thông tin cá nhân, lịch sử công tác,
              quá trình ký hợp đồng, thông tin đóng BHXH, tài sản cấp phát và checklist giấy tờ pháp lý.
            </p>

            <div class="columns-grid p-4 border-round bg-light">
              <h4 class="mt-0 mb-3 flex align-items-center gap-2">
                <i class="pi pi-list text-primary"></i> Dữ liệu bao gồm các nhóm thông tin:
              </h4>
              <ul class="info-list">
                <li><i class="pi pi-check text-green-500"></i> Thông tin cơ bản (Mã NV, Họ tên, Giới tính, Dân tộc...)</li>
                <li><i class="pi pi-check text-green-500"></i> CCCD & Địa chỉ thường trú (Địa chỉ chi tiết, Xã/Phường, Tỉnh/Thành phố)</li>
                <li><i class="pi pi-check text-green-500"></i> Hợp đồng lao động hiện tại & Lịch sử ký hợp đồng (Lần 1, 2... N)</li>
                <li><i class="pi pi-check text-green-500"></i> BHXH (Mã số, Bậc đóng, Lương đóng mới nhất, Thẻ CSSK/24/24...)</li>
                <li><i class="pi pi-check text-green-500"></i> Học vấn (Trường tốt nghiệp, Trình độ, Chuyên ngành) & Thuế/Ngân hàng</li>
                <li><i class="pi pi-check text-green-500"></i> Người thân & Số điện thoại liên hệ khẩn cấp</li>
                <li><i class="pi pi-check text-green-500"></i> Nhật ký bổ nhiệm/thuyên chuyển công tác</li>
                <li><i class="pi pi-check text-green-500"></i> Khen thưởng, Kỷ luật & Tài sản đang bàn giao</li>
                <li><i class="pi pi-check text-green-500"></i> Trạng thái cam kết bảo mật & Checklist giấy tờ còn thiếu</li>
              </ul>
            </div>

            <div class="warning-box p-4 border-round flex gap-3 align-items-start">
              <i class="pi pi-exclamation-triangle text-amber-500 text-2xl mt-1"></i>
              <div>
                <strong class="text-amber-700">Lưu ý khi xuất dữ liệu:</strong>
                <p class="m-0 text-amber-600 mt-2 leading-relaxed">
                  Quá trình kết xuất dữ liệu và đóng gói file Excel có thể mất vài giây tùy thuộc vào khối lượng hồ sơ
                  của công ty. Vui lòng không đóng trình duyệt hoặc tải lại trang khi quá trình đang chạy.
                </p>
              </div>
            </div>

            <div class="button-container">
              <Button
                label="Quay lại"
                icon="pi pi-arrow-left"
                class="p-button-outlined p-button-secondary px-4 py-2"
                @click="goBack"
                :disabled="loading"
              />
              <Button
                label="Xuất dữ liệu Excel"
                icon="pi pi-download"
                class="p-button-success px-4 py-2"
                :loading="loading"
                @click="handleExport"
              />
            </div>
          </template>
        </Card>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import Card from 'primevue/card'
import Button from 'primevue/button'
import { useToast } from 'primevue/usetoast'
import employeeService from '@/services/employeeService'

const router = useRouter()
const toast = useToast()
const loading = ref(false)

const goBack = () => {
  router.push('/employees')
}

const handleExport = async () => {
  loading.value = true
  try {
    await employeeService.exportComprehensiveEmployeeList()
    toast.add({
      severity: 'success',
      summary: 'Thành công',
      detail: 'Đã xuất dữ liệu nhân sự thành công!',
      life: 3000,
    })
  } catch (error: any) {
    toast.add({
      severity: 'error',
      summary: 'Lỗi xuất dữ liệu',
      detail: error.message || 'Có lỗi xảy ra trong quá trình xuất dữ liệu.',
      life: 5000,
    })
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.data-export-container {
  padding: 1.5rem 0;
}

.export-card {
  border: 1px solid rgba(226, 232, 240, 0.8);
  box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.05), 0 8px 10px -6px rgba(0, 0, 0, 0.05);
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(10px);
  border-radius: 12px;
}

.export-title {
  padding: 0.5rem 0;
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

:deep(.p-card-body) {
  padding: 2.5rem !important;
}

.intro-text {
  margin-bottom: 2rem;
  font-size: 1.05rem;
  line-height: 1.6;
}

.columns-grid {
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 1.5rem !important;
  margin-bottom: 2rem;
  background-color: #f8fafc;
}

.dark-mode .columns-grid {
  border-color: #334155;
  background-color: #1e293b;
}

.dark-mode .export-card {
  background: rgba(30, 41, 59, 0.95);
  border-color: rgba(71, 85, 105, 0.5);
}

.info-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-top: 1rem;
}

.info-list li {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 0.95rem;
}

.warning-box {
  background-color: #fffbeb;
  border: 1px solid #fef3c7;
  border-radius: 8px;
  padding: 1.5rem !important;
  margin-bottom: 2.5rem;
}

.dark-mode .warning-box {
  background-color: rgba(251, 191, 36, 0.05);
  border-color: rgba(251, 191, 36, 0.15);
}

.text-amber-700 {
  color: #b45309;
}

.text-amber-600 {
  color: #d97706;
}

.dark-mode .text-amber-700 {
  color: #fbbf24;
}

.dark-mode .text-amber-600 {
  color: #f59e0b;
}

.button-container {
  display: flex;
  justify-content: flex-end;
  gap: 1rem;
  margin-top: 2rem;
}
</style>
