<template>
  <div>
    <div class="page-header">
      <h2>Dashboard</h2>
      <span class="text-muted">Tổng quan nhân sự</span>
    </div>

    <!-- KPI Cards -->
    <div class="stats-grid">
      <div v-for="stat in stats" :key="stat.label" class="stat-card">
        <div class="stat-icon" :style="{ background: stat.color }">
          <i :class="['pi', stat.icon]" />
        </div>
        <div class="stat-body">
          <div class="stat-value">{{ stat.value }}</div>
          <div class="stat-label">{{ stat.label }}</div>
        </div>
      </div>
    </div>

    <!-- Placeholder charts -->
    <div class="charts-grid">
      <Card>
        <template #title>Biến động nhân sự (6 tháng)</template>
        <template #content>
          <div class="chart-placeholder">
            <i class="pi pi-chart-bar" />
            <span>Biểu đồ sẽ hiển thị sau khi có dữ liệu</span>
          </div>
        </template>
      </Card>
      <Card>
        <template #title>Cơ cấu nhân sự</template>
        <template #content>
          <div class="chart-placeholder">
            <i class="pi pi-chart-pie" />
            <span>Biểu đồ sẽ hiển thị sau khi có dữ liệu</span>
          </div>
        </template>
      </Card>
    </div>
  </div>
</template>

<script setup lang="ts">
import Card from 'primevue/card'

const stats = [
  { label: 'Tổng nhân viên', value: '—', icon: 'pi-users', color: '#0891b2' },
  { label: 'Tuyển mới tháng này', value: '—', icon: 'pi-user-plus', color: '#059669' },
  { label: 'Nghỉ việc tháng này', value: '—', icon: 'pi-user-minus', color: '#dc2626' },
  { label: 'Hợp đồng sắp hết hạn', value: '—', icon: 'pi-file-edit', color: '#d97706' },
]
</script>

<style scoped>
.page-header {
  display: block;
  margin-bottom: 1.5rem;
  h2 { margin: 0 0 0.25rem; font-size: 1.5rem; font-weight: 700; }
  .text-muted { color: var(--p-text-muted-color); font-size: 0.875rem; }
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1rem;
  margin-bottom: 1.5rem;
}

.stat-card {
  background: var(--p-surface-0);
  border-radius: 10px;
  padding: 1.25rem;
  display: flex;
  align-items: center;
  gap: 1rem;
  box-shadow: 0 1px 4px rgba(0,0,0,0.06);
  border: 1px solid var(--p-surface-200);
}

.stat-icon {
  width: 48px;
  height: 48px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  i { font-size: 1.4rem; color: white; }
}

.stat-value { font-size: 1.75rem; font-weight: 800; line-height: 1; }
.stat-label { font-size: 0.8rem; color: var(--p-text-muted-color); margin-top: 0.25rem; }

.charts-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 1rem;
}

.chart-placeholder {
  height: 200px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 0.75rem;
  color: var(--p-text-muted-color);
  i { font-size: 2.5rem; opacity: 0.3; }
  span { font-size: 0.875rem; }
}
</style>
