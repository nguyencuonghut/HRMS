# Kế hoạch triển khai — 15.3. Giao diện

**Phạm vi:** Responsive · Tiếng Việt · Tìm kiếm đa tiêu chí · Toast notification · Dashboard  
**Phụ thuộc:** Vue 3 ✅ · PrimeVue v4 ✅ · Vite ✅  
**Căn cứ nghiệp vụ:** FEATURES.md §15.3  
**Đặc điểm:** Phần lớn đã đáp ứng; plan tập trung vào các gap còn lại và đảm bảo chất lượng

---

## Trạng thái hiện tại

### Đã có (✅)

| Thành phần | Chi tiết |
|---|---|
| Vue 3 + TypeScript + Vite | Composition API, `<script setup>`, strict TS |
| PrimeVue v4 | DataTable, Dialog, Form, Tag, Toast, Chart... |
| Responsive layout | @media breakpoints 768px/960px/1200px, sidebar overlay mobile |
| Dark mode | Toggle + localStorage persist, CSS variables |
| Toast notification | `useToast()` — 30+ call sites, severity: success/error/warn/info |
| Tiếng Việt | Labels hardcoded toàn bộ tiếng Việt |
| Tìm kiếm / filter | Multi-column search, Select dropdown, DatePicker filter |
| Dashboard charts | Custom SVG charts, PrimeVue Chart (không dùng Chart.js) |
| PrimeIcons v4 | Icon pack đầy đủ |
| Form validation | VeeValidate + Zod — error messages tiếng Việt |

### Chưa có / Cần cải thiện (❌/⚠️)

| Thành phần | Vấn đề | Ưu tiên |
|---|---|---|
| **i18n library** | Labels hardcoded — khó dịch/thay đổi sau này | 🟡 Medium |
| **Accessibility (A11y)** | Chưa test ARIA labels, keyboard nav, contrast WCAG | 🟠 High |
| **Responsive kiểm thử** | Chưa test trên thiết bị thật (iPad, iPhone 12) | 🟠 High |
| **Lazy-loading routes** | Một số routes chưa dynamic import | 🟡 Medium |
| **Mobile bottom navigation** | Trên mobile chỉ có sidebar overlay, chưa bottom nav | 🟡 Medium |

---

## Phạm vi Plan 15.3

### Trong phạm vi

1. **Accessibility audit** — ARIA labels, keyboard navigation, WCAG AA contrast
2. **Responsive test & fix** — tablet (768px) và mobile (390px) thực tế
3. **Lazy-loading routes** — tất cả views dùng dynamic `import()`
4. **i18n chuẩn bị** — cấu trúc sẵn, không bắt buộc dịch ngay
5. **Mobile UX improvements** — touch targets ≥ 48px, bottom sheet patterns

### Ngoài phạm vi

- Đa ngôn ngữ (English UI) — chưa có yêu cầu từ khách hàng
- PWA (Progressive Web App) / offline support
- Native mobile app (iOS/Android)
- Custom theming per tenant

---

## Chi tiết kỹ thuật

### 1. Accessibility (A11y) Audit — Slice 1

**Checklist WCAG 2.1 AA:**

| Tiêu chí | Hiện trạng | Cần làm |
|---|---|---|
| Text contrast ratio ≥ 4.5:1 | ⚠️ Chưa verify | Dùng `axe` hoặc Chrome DevTools Lighthouse |
| Touch targets ≥ 48×48px | ⚠️ Cần đo | Kiểm tra các nút icon-only (filter, action buttons) |
| Keyboard navigation | ⚠️ PrimeVue hỗ trợ nhưng chưa test | Tab order, focus indicators, Escape close dialog |
| ARIA labels | ⚠️ Chưa đồng đều | Thêm `aria-label` cho icon buttons, form fields không có label hiển thị |
| Screen reader | ❌ Chưa test | Test với NVDA/VoiceOver |
| Skip to main content | ❌ Chưa có | Thêm skip link cho keyboard users |
| Focus visible | ⚠️ Phụ thuộc PrimeVue theme | Verify focus ring không bị ẩn |

**Tool kiểm tra:**
```bash
# Cài axe-core CLI
npm install -g @axe-core/cli

# Chạy kiểm tra
axe http://localhost:5173 --tags wcag2a,wcag2aa --reporter csv > a11y-report.csv
```

**Fix mẫu:**
```html
<!-- ❌ Thiếu aria-label -->
<Button icon="pi pi-filter" @click="openFilter" />

<!-- ✅ Có aria-label -->
<Button icon="pi pi-filter" aria-label="Mở bộ lọc" @click="openFilter" />

<!-- ❌ Input không có label hiển thị -->
<InputText v-model="keyword" placeholder="Tìm kiếm..." />

<!-- ✅ Dùng aria-label -->
<InputText v-model="keyword" placeholder="Tìm kiếm..." aria-label="Tìm kiếm nhân viên" />
```

---

### 2. Responsive Test & Fix — Slice 1

**Breakpoints hiện có:**
```css
/* Đã có trong các component */
@media (max-width: 768px)  { /* mobile */ }
@media (max-width: 960px)  { /* tablet portrait */ }
@media (max-width: 1200px) { /* tablet landscape */ }
```

**Test matrix:**
| Thiết bị | Viewport | Trạng thái |
|---|---|---|
| iPhone 12 | 390×844px | Cần test |
| iPhone SE | 375×667px | Cần test |
| iPad (portrait) | 768×1024px | Cần test |
| iPad (landscape) | 1024×768px | Cần test |
| Desktop FHD | 1920×1080px | ✅ Đang làm |

**Các màn hình cần kiểm tra đặc biệt:**
- Employee list → DataTable horizontal scroll trên mobile
- Employee detail → tab view có hiển thị đúng không
- Forms với nhiều field → layout 1/2/4 column có đúng không
- Dashboard charts → resize đúng không
- Import dialog → FileUpload zone đủ lớn không
- Notification settings → Editor có overflow không

**Fix mẫu cho DataTable mobile:**
```html
<DataTable
  :value="data"
  responsive-layout="scroll"   <!-- ✅ đã có -->
  scrollable
  scroll-height="400px"        <!-- thêm max height -->
>
```

---

### 3. Lazy-Loading Routes — Slice 1

**Kiểm tra router/index.ts — tất cả routes phải dùng dynamic import:**
```typescript
// ❌ Eager import (không tốt cho bundle size)
import EmployeeListView from '@/views/employees/EmployeeListView.vue'
{ component: EmployeeListView }

// ✅ Lazy import (đúng cách)
{ component: () => import('@/views/employees/EmployeeListView.vue') }
```

**Verify hiện trạng:**
```bash
grep -n "component:" frontend/src/router/index.ts | grep -v "import(" | head -20
```

Tất cả routes trong `router/index.ts` phải dùng `() => import(...)`.

---

### 4. i18n Chuẩn bị — Slice 2

**Không bắt buộc dịch ngay**, chỉ cần cấu trúc sẵn để dễ bổ sung sau:

**Cài đặt:**
```bash
npm install vue-i18n@9
```

**Cấu trúc file:**
```
frontend/src/
└── locales/
    └── vi.json    ← Tiếng Việt (primary)
    └── en.json    ← (tương lai — bỏ trống hoặc copy từ vi.json)
```

**Nhóm keys theo module:**
```json
// locales/vi.json
{
  "common": {
    "save": "Lưu",
    "cancel": "Hủy",
    "delete": "Xóa",
    "search": "Tìm kiếm",
    "loading": "Đang tải...",
    "noData": "Không có dữ liệu"
  },
  "employee": {
    "title": "Danh sách nhân viên",
    "add": "Thêm nhân viên",
    "status": {
      "probation": "Thử việc",
      "official": "Chính thức",
      "long_leave": "Nghỉ dài hạn",
      "resigned": "Đã nghỉ việc"
    }
  },
  "nav": {
    "dashboard": "Dashboard",
    "employees": "Nhân sự",
    "contracts": "Hợp đồng"
  }
}
```

**Setup trong main.ts:**
```typescript
import { createI18n } from 'vue-i18n'
import vi from './locales/vi.json'

const i18n = createI18n({
  locale: 'vi',
  fallbackLocale: 'vi',
  messages: { vi },
})
app.use(i18n)
```

**Không migrate ngay** — chỉ setup, dùng `$t('common.save')` cho các string mới thêm; string cũ giữ nguyên hardcoded.

---

### 5. Mobile UX Improvements — Slice 2

**Touch targets (WCAG 2.5.8):**
```css
/* Đảm bảo mọi interactive element ≥ 48×48px trên mobile */
@media (max-width: 768px) {
  .p-button {
    min-height: 48px;
    min-width: 48px;
  }
  .p-inputtext {
    min-height: 48px;
  }
}
```

**Bottom sheet cho mobile (thay thế Dialog):**

Trên màn hình nhỏ (< 640px), Dialog nên mở từ dưới lên thay vì center:
```css
@media (max-width: 640px) {
  .p-dialog {
    position: fixed !important;
    bottom: 0 !important;
    left: 0 !important;
    width: 100% !important;
    max-width: 100% !important;
    margin: 0 !important;
    border-radius: 1rem 1rem 0 0 !important;
  }
}
```

---

## Cấu trúc file thay đổi

```
frontend/src/
├── locales/
│   └── vi.json          ← NEW — i18n strings (optional)
├── router/
│   └── index.ts         ← UPDATE — verify all lazy imports
└── assets/styles/
    └── main.scss        ← UPDATE — touch targets, mobile fixes
```

---

## Kế hoạch theo Slice

### Slice 1 — Responsive Test + A11y + Lazy Routes (High)

**Việc cần làm:**
1. Chạy `axe` audit → fix các lỗi WCAG AA tìm thấy
2. Test responsive trên DevTools: iPhone 12 (390px), iPad (768px)
3. Fix layout broken nếu có (DataTable overflow, form 4 cột trên mobile)
4. Verify tất cả routes dùng `() => import(...)`, fix nếu có eager import
5. Thêm `aria-label` cho icon-only buttons

**Verify:** `axe http://localhost:5173` → 0 violations critical, ≤ 5 serious.

---

### Slice 2 — i18n Setup + Mobile UX (Medium)

**Việc cần làm:**
1. Cài `vue-i18n@9` + tạo `locales/vi.json` với ~100 common keys
2. Setup i18n trong main.ts — chỉ register, chưa migrate cũ
3. Thêm CSS mobile touch targets + bottom sheet Dialog pattern
4. Test trên thiết bị thật (iOS Safari, Android Chrome) nếu có

---

## Rủi ro & Cách xử lý

| Rủi ro | Cách xử lý |
|---|---|
| i18n làm vỡ layout (string dài hơn tiếng Việt) | Hardcode fallback, chỉ migrate dần; không migrate 100% một lúc |
| PrimeVue v4 A11y issues | Report lên PrimeVue GitHub; workaround bằng wrapper component |
| Responsive fix làm vỡ desktop layout | Test cả 2 breakpoints sau mỗi fix; không dùng !important khi có thể |

---

## Checklist

### High priority
- [ ] `axe` audit chạy — fix critical violations
- [ ] Responsive test: 390px, 768px, 1200px, 1920px không có layout broken
- [ ] Tất cả router routes dùng lazy import
- [ ] Icon-only buttons có `aria-label`

### Medium priority
- [ ] `vue-i18n` cài và config (không cần migrate toàn bộ)
- [ ] `locales/vi.json` có ít nhất common.* keys
- [ ] Mobile: touch targets ≥ 48px
- [ ] Dark mode: contrast ratio verify bằng Chrome DevTools
