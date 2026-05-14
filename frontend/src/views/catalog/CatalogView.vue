<template>
  <div class="catalog-page">
    <div class="page-header">
      <div>
        <h2>Danh mục</h2>
        <span class="subtitle">Quản trị dữ liệu nền dùng chung cho các module nhân sự</span>
      </div>
    </div>

    <div class="catalog-grid">
      <RouterLink to="/catalog/administrative-units" class="catalog-card">
        <div class="catalog-icon"><i class="pi pi-map" /></div>
        <div class="catalog-body">
          <h3>Danh mục hành chính</h3>
          <p>Quản lý tỉnh/thành phố, xã/phường, cây phân cấp hệ mới và thao tác tạo khóa dữ liệu thủ công.</p>
        </div>
        <span class="catalog-link">Mở màn quản trị</span>
      </RouterLink>

      <RouterLink to="/catalog/administrative-imports" class="catalog-card">
        <div class="catalog-icon secondary"><i class="pi pi-download" /></div>
        <div class="catalog-body">
          <h3>Lịch sử import địa chỉ</h3>
          <p>Theo dõi các batch import, kết quả xử lý, lỗi dữ liệu và chạy lại import khi cần đồng bộ nguồn chính thức.</p>
        </div>
        <span class="catalog-link">Xem lịch sử</span>
      </RouterLink>
    </div>
  </div>
</template>

<script setup lang="ts"></script>

<style scoped>
.catalog-page { display: flex; flex-direction: column; gap: 1.5rem; }
.page-header h2 { margin: 0; font-size: 1.75rem; font-weight: 700; }
.subtitle { color: var(--p-text-muted-color); }
.catalog-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 1rem;
}
.catalog-card {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  min-height: 220px;
  padding: 1.25rem;
  border-radius: 18px;
  border: 1px solid color-mix(in srgb, var(--p-primary-color) 18%, var(--p-surface-300));
  background:
    radial-gradient(circle at top right, color-mix(in srgb, var(--p-primary-color) 10%, transparent), transparent 45%),
    linear-gradient(180deg, var(--p-surface-0), color-mix(in srgb, var(--p-surface-0) 82%, var(--p-primary-50)));
  text-decoration: none;
  color: inherit;
  transition: transform 0.18s ease, box-shadow 0.18s ease, border-color 0.18s ease;
}
.catalog-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 18px 36px rgba(15, 23, 42, 0.08);
  border-color: color-mix(in srgb, var(--p-primary-color) 32%, var(--p-surface-300));
}
.catalog-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 3rem;
  height: 3rem;
  border-radius: 14px;
  background: color-mix(in srgb, var(--p-primary-color) 18%, white);
  color: var(--p-primary-color);
  font-size: 1.25rem;
}
.catalog-icon.secondary {
  background: color-mix(in srgb, var(--p-orange-500) 18%, white);
  color: var(--p-orange-600);
}
.catalog-body { display: flex; flex-direction: column; gap: 0.5rem; }
.catalog-body h3 { margin: 0; font-size: 1.15rem; font-weight: 700; }
.catalog-body p { margin: 0; color: var(--p-text-muted-color); line-height: 1.55; }
.catalog-link { margin-top: auto; font-weight: 600; color: var(--p-primary-color); }
</style>
