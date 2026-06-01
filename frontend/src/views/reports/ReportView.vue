<template>
  <div class="report-hub">
    <div class="report-hub-header">
      <div>
        <h2>Tổng quan báo cáo</h2>
        <p>Trung tâm truy cập các báo cáo và dashboard chính thức của hệ thống HRMS.</p>
      </div>
    </div>

    <div class="report-hub-grid">
      <RouterLink
        v-for="item in reportCards"
        :key="item.to"
        :to="item.to"
        class="report-hub-card"
      >
        <div class="report-hub-icon">
          <i :class="['pi', item.icon]" />
        </div>
        <div class="report-hub-content">
          <h3>{{ item.title }}</h3>
          <p>{{ item.description }}</p>
        </div>
        <i class="pi pi-arrow-right report-hub-arrow" />
      </RouterLink>
    </div>
  </div>
</template>

<script setup lang="ts">
type ReportCard = {
  to: string
  title: string
  description: string
  icon: string
}

const reportCards: ReportCard[] = [
  {
    to: '/reports/dashboard',
    title: 'Dashboard tổng quan',
    description: 'KPI điều hành, headcount, biến động và cơ cấu nhân sự toàn hệ thống.',
    icon: 'pi-chart-pie',
  },
  {
    to: '/reports/hr',
    title: 'Báo cáo nhân sự',
    description: 'Danh sách nhân sự, biến động, thâm niên và cơ cấu tổ chức.',
    icon: 'pi-users',
  },
  {
    to: '/reports/probation',
    title: 'Thử việc & onboarding',
    description: 'Theo dõi thử việc, tỷ lệ vượt thử việc và tiến độ hội nhập.',
    icon: 'pi-user-plus',
  },
  {
    to: '/reports/leave',
    title: 'Báo cáo nghỉ phép',
    description: 'Tổng hợp nghỉ phép theo nhân viên, phòng ban và tồn phép cuối năm.',
    icon: 'pi-calendar',
  },
  {
    to: '/reports/insurance',
    title: 'Bảo hiểm',
    description: 'Phân tích tình hình bảo hiểm và chỉ số biến động liên quan.',
    icon: 'pi-shield',
  },
  {
    to: '/reports/contracts',
    title: 'Báo cáo hợp đồng',
    description: 'Theo dõi hợp đồng sắp hết hạn, cơ cấu loại hợp đồng và lịch sử ký kết.',
    icon: 'pi-file',
  },
  {
    to: '/reports/recruitment',
    title: 'Báo cáo tuyển dụng',
    description: 'Phễu tuyển dụng, hiệu quả nguồn ứng viên và chỉ số thời gian tuyển.',
    icon: 'pi-briefcase',
  },
  {
    to: '/reports/training',
    title: 'Báo cáo đào tạo',
    description: 'Tổng hợp hoàn thành đào tạo, chi phí và tình trạng bắt buộc.',
    icon: 'pi-graduation-cap',
  },
  {
    to: '/reports/rewards',
    title: 'Báo cáo khen thưởng & kỷ luật',
    description: 'Thống kê quyết định khen thưởng, kỷ luật và phân bố theo phòng ban.',
    icon: 'pi-star',
  },
  {
    to: '/reports/performance',
    title: 'Báo cáo hiệu suất / KPI',
    description: 'Phân phối xếp loại, xu hướng KPI và tổng hợp theo phòng ban.',
    icon: 'pi-chart-bar',
  },
  {
    to: '/reports/export',
    title: 'Xuất báo cáo',
    description: 'Tạo file xuất, theo dõi lịch sử export và quản lý mẫu xuất.',
    icon: 'pi-file-export',
  },
]
</script>

<style>
.report-hub {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}

.report-hub-header h2 {
  margin: 0;
  font-size: 1.5rem;
  font-weight: 700;
}

.report-hub-header p {
  margin: 0.4rem 0 0;
  color: var(--p-text-muted-color);
  max-width: 52rem;
  line-height: 1.6;
}

.report-hub-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: 1rem;
}

.report-hub-card {
  display: grid;
  grid-template-columns: auto 1fr auto;
  gap: 0.9rem;
  align-items: start;
  padding: 1.1rem 1rem;
  border-radius: 14px;
  border: 1px solid var(--p-surface-300);
  background: var(--p-surface-0);
  color: inherit;
  text-decoration: none;
  transition: transform 0.15s ease, border-color 0.15s ease, box-shadow 0.15s ease;
}

.report-hub-card:hover {
  transform: translateY(-2px);
  border-color: var(--p-primary-300);
  box-shadow: 0 10px 24px rgba(15, 23, 42, 0.08);
}

.report-hub-icon {
  width: 2.75rem;
  height: 2.75rem;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 12px;
  background: color-mix(in srgb, var(--p-primary-color) 14%, transparent);
  color: var(--p-primary-color);
  font-size: 1.1rem;
}

.report-hub-content h3 {
  margin: 0;
  font-size: 1rem;
  font-weight: 700;
}

.report-hub-content p {
  margin: 0.35rem 0 0;
  font-size: 0.875rem;
  line-height: 1.55;
  color: var(--p-text-muted-color);
}

.report-hub-arrow {
  margin-top: 0.15rem;
  color: var(--p-text-muted-color);
}

html.dark-mode .report-hub-card {
  background: var(--p-content-background);
}
</style>
