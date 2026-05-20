<template>
  <div class="employee-insurance-view">
    <div class="page-header">
      <div>
        <h2>Bảo hiểm BHXH</h2>
        <span class="subtitle">Không gian nghiệp vụ cho hồ sơ bảo hiểm nhân viên, biến động tăng giảm và báo cáo BHXH</span>
      </div>
      <div class="employee-insurance-actions">
        <Button
          label="Mở cấu hình BHXH dùng chung"
          icon="pi pi-sliders-h"
          severity="secondary"
          @click="router.push('/catalog/insurance')"
        />
      </div>
    </div>

    <section class="employee-insurance-hero">
      <div class="card employee-insurance-summary">
        <span class="employee-insurance-kicker">Đúng lớp màn hình</span>
        <h3>Module này dành cho thông tin BHXH của nhân viên</h3>
        <p>
          Theo đặc tả hiện tại, menu <strong>Bảo hiểm BHXH</strong> sẽ là nơi quản lý mã số BHXH,
          nơi KCB ban đầu, ngày tham gia tại công ty, trạng thái tham gia và các nghiệp vụ tăng giảm.
        </p>
      </div>

      <div class="card employee-insurance-summary muted">
        <span class="employee-insurance-kicker">Foundation đã tách riêng</span>
        <h3>Cấu hình policy, tỷ lệ đóng và vùng công ty</h3>
        <p>
          Các cấu hình dùng chung của BHXH đã được chuyển về <strong>Danh mục</strong> để đúng
          vai trò dữ liệu nền cho <code>6.1</code>, <code>6.2</code>, <code>6.3</code> và
          <code>7.x</code>.
        </p>
      </div>
    </section>

    <section class="employee-insurance-grid">
      <article class="card employee-insurance-card">
        <div class="section-heading">
          <h3>Phạm vi 6.1</h3>
          <span class="section-hint">Hồ sơ BHXH nhân viên</span>
        </div>
        <ul class="employee-insurance-list">
          <li>Mã số BHXH của nhân viên</li>
          <li>Nơi đăng ký khám chữa bệnh ban đầu</li>
          <li>Mức lương đóng BHXH hiện hành</li>
          <li>Ngày tham gia BHXH tại công ty</li>
          <li>Trạng thái: Đang đóng / Tạm dừng / Đã nghỉ</li>
        </ul>
      </article>

      <article class="card employee-insurance-card">
        <div class="section-heading">
          <h3>Lát cắt tiếp theo</h3>
          <span class="section-hint">Sau Slice 0</span>
        </div>
        <ul class="employee-insurance-list">
          <li>Tạo hồ sơ bảo hiểm hiện hành cho từng nhân viên</li>
          <li>List/filter tra cứu theo phòng ban, trạng thái, mã BHXH</li>
          <li>Liên kết mức lương BHXH từ hợp đồng hiện hành</li>
          <li>Chuẩn bị dữ liệu cho biến động tăng/giảm và báo cáo BHXH</li>
        </ul>
      </article>

      <article class="card employee-insurance-card employee-insurance-card--accent">
        <div class="section-heading">
          <h3>Điểm vào hiện tại</h3>
          <span class="section-hint">Trong lúc chờ implementation 6.1</span>
        </div>
        <div class="employee-insurance-links">
          <Button label="Xem danh sách nhân viên" icon="pi pi-users" @click="router.push('/employees')" />
          <Button label="Xem hợp đồng lao động" icon="pi pi-file-edit" severity="secondary" @click="router.push('/contracts')" />
          <Button label="Mở cấu hình BHXH dùng chung" icon="pi pi-sliders-h" severity="secondary" outlined @click="router.push('/catalog/insurance')" />
        </div>
      </article>
    </section>
  </div>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'
import Button from 'primevue/button'

const router = useRouter()
</script>
