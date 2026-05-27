# Kế hoạch Refactoring Layout & Routing — Module Tuyển Dụng

> **Nguyên tắc:** Mọi khẳng định trong file này đều được verify từ source code thực tế.
> Không có nội dung suy đoán.

> **Trạng thái:** ✅ **Tất cả 8 slices đã hoàn thành.** Xem mục "Sai khác so với kế hoạch"
> bên dưới để biết những điểm implementation thực tế khác với plan ban đầu.

---

## Bối cảnh & Vấn đề đã xác minh

### Trạng thái hiện tại (verified từ source)

**Router — `frontend/src/router/index.ts`** có đúng 5 routes liên quan tuyển dụng:
```
recruitment                  → RecruitmentView.vue
recruitment/jr/:id           → JRDetailView.vue
recruitment/postings/:id     → JobPostingDetailView.vue
recruitment/candidates/:id   → CandidateDetailView.vue
recruitment/applications/:id → ApplicationDetailView.vue
```

**Sidebar — `AppMenu.vue` dòng 120:**
```typescript
{ to: '/recruitment', label: 'Tuyển dụng', icon: 'pi-briefcase' }
```
Single item, không có `items[]`. Interface `MenuItem` đã hỗ trợ `items?: { to, label, icon? }[]`.

**RecruitmentView.vue** dùng 7 query params làm "tabs":
```typescript
const validTabs = new Set(["jr","postings","candidates","selection","headcount","legal","settings"])
const activeTab = ref(resolveTab(route.query.tab))
// 2-way watch: route.query.tab ↔ activeTab → router.replace({ query: { tab } })
```

**Toàn bộ hardcoded `?tab=` navigation strings (verified bằng grep):**

| File | Dòng | Navigation string |
|------|------|-------------------|
| `JRDetailView.vue` | 11 | `$router.push('/recruitment')` (back — thiếu tab) |
| `JRDetailView.vue` | 55 | `$router.push('/recruitment?tab=selection&jr_id=${jr.id}')` |
| `JobPostingDetailView.vue` | 6 | `$router.push('/recruitment?tab=postings')` |
| `CandidateDetailView.vue` | 11 | `router.push('/recruitment?tab=candidates')` |
| `ApplicationDetailView.vue` | 11–12 | `router.push('/recruitment?tab=selection&jr_id=${application.job_requisition_id}')` |

**KanbanPipelineView.vue** — JR selection:
```typescript
const selectedJrId = ref<number | null>(null)
watch(() => route.query.jr_id, (value) => { selectedJrId.value = Number(value) || null })
function onJrChange() {
  router.replace({ query: { ...route.query, jr_id: selectedJrId.value ?? undefined } })
  void loadBoard()
}
```

**Frontend tests:** Không tồn tại — 0 file `.test.ts` / `.spec.ts` trong `frontend/src`.

---

## Phân chia lát cắt (Slices)

Mỗi slice độc lập, có thể merge và test riêng.
Thứ tự thực hiện: **1 → 2 → 3 → 4 → 5 → 6 → 7 → 8**

---

## Slice 1 — Sidebar submenu (Additive, không breaking)

### Mục tiêu
Thêm submenu "Tuyển dụng" với 5 items chính. Không xóa route cũ, không thay đổi query param logic.
Tạm thời trỏ vào `/recruitment?tab=X` (sẽ được cập nhật lại ở Slice 2–6).

### Thay đổi code

**`AppMenu.vue` dòng 120** — thay single item thành group:
```typescript
// TRƯỚC:
{ to: '/recruitment', label: 'Tuyển dụng', icon: 'pi-briefcase' }

// SAU:
{
  label: 'Tuyển dụng',
  icon: 'pi-briefcase',
  items: [
    { to: '/recruitment?tab=jr',         label: 'Yêu cầu tuyển dụng' },
    { to: '/recruitment?tab=postings',   label: 'Tin tuyển dụng'     },
    { to: '/recruitment?tab=candidates', label: 'Ứng viên'           },
    { to: '/recruitment?tab=selection',  label: 'Tuyển chọn'         },
    { to: '/recruitment?tab=headcount',  label: 'Kế hoạch nhân sự'   },
  ]
}
// "Hồ sơ pháp lý" và "Cài đặt" được tách ở Slice 8
```

### Logic bị ảnh hưởng
- Rendering submenu trong `AppMenu.vue` — cần kiểm tra template render `items[]`
- `router-link-active` class: với query param, active state có thể không highlight đúng
  (đây là known limitation, sẽ giải quyết hoàn toàn ở Slice 2–6)

### Tests cần viết (Playwright E2E)
```
test("sidebar 'Tuyển dụng' renders submenu with 5 items")
test("click 'Yêu cầu tuyển dụng' navigates to /recruitment?tab=jr")
test("click 'Ứng viên' navigates to /recruitment?tab=candidates")
test("click 'Tuyển chọn' navigates to /recruitment?tab=selection")
test("submenu items are visible without clicking elsewhere")
```

---

## Slice 2 — Real route: Yêu cầu tuyển dụng (`/recruitment/jr`)

### Mục tiêu
Tách tab "jr" ra thành route riêng `/recruitment/jr`. JRListTab có thể load trực tiếp mà không cần hub.

### Thay đổi code

**`router/index.ts`** — thêm route mới:
```typescript
{
  path: 'recruitment/jr',
  name: 'jr-list',
  component: () => import('@/views/recruitment/components/JRListTab.vue'),
  meta: { title: 'Yêu cầu tuyển dụng' },
}
```

**`RecruitmentView.vue`** — xóa "jr" khỏi validTabs, xóa `<TabPanel value="jr">` và import `JRListTab`.

**`JRDetailView.vue` dòng 11** — sửa back button:
```typescript
// TRƯỚC:
$router.push('/recruitment')
// SAU:
$router.push('/recruitment/jr')
```

**`AppMenu.vue`** — cập nhật link item:
```typescript
{ to: '/recruitment/jr', label: 'Yêu cầu tuyển dụng' }
```

### Logic bị ảnh hưởng (phải test 100%)
1. `JRListTab.vue` render độc lập không cần wrapper `RecruitmentView`
   → Verify: không có prop nào inject từ parent hub
2. Back button `JRDetailView.vue` dòng 11 — chuyển từ `/recruitment` sang `/recruitment/jr`
3. Route `jr-detail` vẫn hoạt động (unchanged)
4. Sidebar active state highlight đúng khi ở `/recruitment/jr` và `/recruitment/jr/:id`

### Tests cần viết
```
test("GET /recruitment/jr renders JR list")
test("JR list displays table with data")
test("click JR row navigates to /recruitment/jr/:id")
test("back button in JRDetailView goes to /recruitment/jr")
test("sidebar 'Yêu cầu tuyển dụng' highlights when on /recruitment/jr")
test("sidebar 'Yêu cầu tuyển dụng' highlights when on /recruitment/jr/:id")
test("/recruitment without ?tab= still loads (redirect or default)")
```

---

## Slice 3 — Real route: Tin tuyển dụng (`/recruitment/postings`)

### Thay đổi code

**`router/index.ts`** — thêm route:
```typescript
{
  path: 'recruitment/postings',
  name: 'posting-list',
  component: () => import('@/views/recruitment/components/JobPostingTab.vue'),
  meta: { title: 'Tin tuyển dụng' },
}
```

**`RecruitmentView.vue`** — xóa "postings" tab.

**`JobPostingDetailView.vue` dòng 6** — sửa back button:
```typescript
// TRƯỚC:
$router.push('/recruitment?tab=postings')
// SAU:
$router.push('/recruitment/postings')
```

**`AppMenu.vue`** — cập nhật link.

### Logic bị ảnh hưởng (phải test 100%)
1. Back button `JobPostingDetailView.vue` dòng 6
2. `JobPostingTab.vue` render độc lập
3. Route `posting-detail` không bị ảnh hưởng

### Tests cần viết
```
test("GET /recruitment/postings renders posting list")
test("click posting row navigates to /recruitment/postings/:id")
test("back button in JobPostingDetailView goes to /recruitment/postings")
```

---

## Slice 4 — Real route: Ứng viên (`/recruitment/candidates`)

### Thay đổi code

**`router/index.ts`** — thêm route:
```typescript
{
  path: 'recruitment/candidates',
  name: 'candidate-list',
  component: () => import('@/views/recruitment/components/CandidateListTab.vue'),
  meta: { title: 'Ứng viên' },
}
```

**`RecruitmentView.vue`** — xóa "candidates" tab.

**`CandidateDetailView.vue` dòng 11** — sửa back button:
```typescript
// TRƯỚC:
router.push('/recruitment?tab=candidates')
// SAU:
router.push('/recruitment/candidates')
```

**`AppMenu.vue`** — cập nhật link.

### Logic bị ảnh hưởng (phải test 100%)
1. Back button `CandidateDetailView.vue` dòng 11
2. `CandidateListTab.vue` render độc lập (có filter, pagination)
3. Route `candidate-detail` không bị ảnh hưởng

### Tests cần viết
```
test("GET /recruitment/candidates renders candidate list")
test("back button in CandidateDetailView goes to /recruitment/candidates")
test("tab 'Ứng tuyển' trong CandidateDetailView links to /recruitment/applications/:id")
```

---

## Slice 5 — Real route + JR trong URL: Tuyển chọn (`/recruitment/selection/:jr_id`)

> Slice phức tạp nhất — thay đổi cả routing lẫn component state management.

### Mục tiêu
Đưa JR selection vào URL path. Giảm click path từ 4 bước xuống 2 bước:
- Trước: sidebar → tab → chọn JR dropdown → click card
- Sau: sidebar → chọn JR → click card (hoặc bookmark thẳng)

### Thay đổi code

**`router/index.ts`** — thêm 2 routes:
```typescript
{
  path: 'recruitment/selection',
  name: 'selection',
  component: () => import('@/views/recruitment/components/KanbanJrPickerView.vue'),
  meta: { title: 'Tuyển chọn' },
},
{
  path: 'recruitment/selection/:jr_id',
  name: 'selection-board',
  component: () => import('@/views/recruitment/components/KanbanPipelineView.vue'),
  meta: { title: 'Tuyển chọn' },
}
```

**Tạo mới `KanbanJrPickerView.vue`** — trang chọn JR khi chưa có `:jr_id`:
- Hiển thị danh sách JR đang hoạt động (status: `approved`, `in_progress`)
- Click JR → `router.push('/recruitment/selection/:jr_id')`
- Nếu chỉ có 1 JR active → auto-redirect

**`KanbanPipelineView.vue`** — thay đổi nguồn `selectedJrId`:
```typescript
// TRƯỚC:
const selectedJrId = ref<number | null>(null)
watch(() => route.query.jr_id, (value) => { selectedJrId.value = Number(value) || null })
function onJrChange() { router.replace({ query: { ...route.query, jr_id: ... } }); void loadBoard() }

// SAU:
const selectedJrId = computed(() => Number(route.params.jr_id) || null)
// onMounted: loadBoard() dựa vào selectedJrId từ params
// Xóa dropdown chọn JR (đã chọn từ picker hoặc URL)
// Giữ lại link "Chi tiết JR" → /recruitment/jr/:selectedJrId
```

**`ApplicationDetailView.vue` dòng 11–12** — sửa back button:
```typescript
// TRƯỚC:
router.push(`/recruitment?tab=selection&jr_id=${application.job_requisition_id}`)
// SAU:
router.push(`/recruitment/selection/${application.job_requisition_id}`)
```

**`JRDetailView.vue` dòng 55** — sửa "Tuyển chọn" button:
```typescript
// TRƯỚC:
$router.push(`/recruitment?tab=selection&jr_id=${jr.id}`)
// SAU:
$router.push(`/recruitment/selection/${jr.id}`)
```

**`RecruitmentView.vue`** — xóa "selection" tab.

**`AppMenu.vue`** — cập nhật link:
```typescript
{ to: '/recruitment/selection', label: 'Tuyển chọn' }
```

### Logic bị ảnh hưởng (phải test 100%)

| Logic | File | Loại thay đổi |
|-------|------|---------------|
| `selectedJrId` source | `KanbanPipelineView.vue` | `query.jr_id` → `params.jr_id` |
| `onJrChange()` | `KanbanPipelineView.vue` | Xóa hoặc refactor thành `router.push` |
| Back button | `ApplicationDetailView.vue` dòng 11–12 | URL mới |
| "Tuyển chọn" button | `JRDetailView.vue` dòng 55 | URL mới |
| Board loading | `KanbanPipelineView.vue` `loadBoard()` | Phải vẫn hoạt động đúng |
| `KanbanJrPickerView` | Mới | 100% cần test |

### Tests cần viết
```
test("GET /recruitment/selection renders JR picker list")
test("click JR in picker navigates to /recruitment/selection/:jr_id")
test("GET /recruitment/selection/:jr_id renders Kanban board for that JR")
test("Kanban board loads correct data for jr_id in URL")
test("back button in ApplicationDetailView goes to /recruitment/selection/:jr_id")
test("'Tuyển chọn' button in JRDetailView goes to /recruitment/selection/:jr_id")
test("auto-redirect when only 1 active JR exists")
test("link 'Chi tiết JR' in KanbanPipelineView goes to /recruitment/jr/:id")
```

---

## Slice 6 — Real route: Kế hoạch nhân sự (`/recruitment/headcount`)

### Thay đổi code

**`router/index.ts`** — thêm route:
```typescript
{
  path: 'recruitment/headcount',
  name: 'headcount-plan',
  component: () => import('@/views/recruitment/components/HeadcountPlanTab.vue'),
  meta: { title: 'Kế hoạch nhân sự' },
}
```

**`RecruitmentView.vue`** — xóa "headcount" tab.  
**`AppMenu.vue`** — cập nhật link.

### Logic bị ảnh hưởng (phải test 100%)
1. `HeadcountPlanTab.vue` render độc lập (có filter theo năm, phòng ban)
2. Không có back button cần sửa (HeadcountPlanTab không navigate đi đâu)

### Tests cần viết
```
test("GET /recruitment/headcount renders headcount plan")
test("year/department filter works on /recruitment/headcount")
```

> Sau khi hoàn thành Slice 2–6: `RecruitmentView.vue` chỉ còn 2 tabs còn lại ("legal", "settings") và
> có thể xem xét xóa hoàn toàn ở Slice 8.

---

## Slice 7 — Breadcrumb component

### Mục tiêu
Thêm breadcrumb vào tất cả detail pages. Xác minh: hiện tại không có breadcrumb — chỉ có
`rc-meta-row` hiển thị metadata dạng text (verified từ `ApplicationDetailView.vue`).

### Component mới: `RecruitmentBreadcrumb.vue`
```typescript
interface Crumb { label: string; to?: string }
defineProps<{ crumbs: Crumb[] }>()
// Render: Tuyển dụng > Tuyển chọn > JR-2026-0001 > Nguyễn Văn A
// Mỗi crumb (trừ cuối) là RouterLink, crumb cuối là plain text
```

### Thêm vào từng detail page

| Page | Breadcrumb path |
|------|-----------------|
| `JRDetailView.vue` | Tuyển dụng > Yêu cầu tuyển dụng > `{jr.code}` |
| `JobPostingDetailView.vue` | Tuyển dụng > Tin tuyển dụng > `{posting.title}` |
| `CandidateDetailView.vue` | Tuyển dụng > Ứng viên > `{candidate.full_name}` |
| `ApplicationDetailView.vue` | Tuyển dụng > Tuyển chọn > `{jr_id}` > `{candidate.full_name}` |

> Breadcrumb ở `ApplicationDetailView` cần `jr_id` — chỉ khả thi sau khi Slice 5 hoàn thành
> (jr_id có trong `route.params.jr_id` thay vì phải fetch riêng).

### Logic bị ảnh hưởng (phải test 100%)
1. `RecruitmentBreadcrumb.vue` — render đúng số crumbs, RouterLink đúng path
2. Crumb cuối không có link (plain text)
3. Các props crumbs truyền vào từng page

### Tests cần viết
```
test("RecruitmentBreadcrumb renders correct number of items")
test("all crumbs except last are RouterLink")
test("last crumb is plain text (no link)")
test("JRDetailView breadcrumb shows: Tuyển dụng > Yêu cầu tuyển dụng > {jr.code}")
test("ApplicationDetailView breadcrumb shows full path with jr_id and candidate name")
test("click breadcrumb 'Tuyển chọn' navigates to /recruitment/selection")
```

---

## Slice 8 — Tách "Hồ sơ pháp lý" và "Cài đặt" ra khỏi hub

### Mục tiêu
Sau các slice trên, `RecruitmentView.vue` chỉ còn "legal" và "settings".
Tách chúng thành routes riêng, xóa hoàn toàn `RecruitmentView.vue` nếu không còn cần thiết.

### Thay đổi code

**`router/index.ts`** — thêm 2 routes:
```typescript
{
  path: 'recruitment/legal',
  name: 'legal-documents',
  component: () => import('@/views/recruitment/components/DocumentChecklistSummaryTab.vue'),
  meta: { title: 'Hồ sơ pháp lý' },
},
{
  path: 'recruitment/settings',
  name: 'recruitment-settings',
  component: () => import('@/views/recruitment/components/EmailTemplateListTab.vue'),
  meta: { title: 'Cài đặt tuyển dụng' },
}
```

**`AppMenu.vue`** — thêm dưới cùng submenu Tuyển dụng hoặc vào group Cài đặt:
```typescript
// Tùy thuộc vào quyết định UX — xem mục "Quyết định cần người dùng xác nhận" bên dưới
```

**`RecruitmentView.vue`** — xóa file sau khi không còn tab nào.
Thêm redirect tại `/recruitment` → `/recruitment/jr` (hoặc trang dashboard tuyển dụng nếu cần).

### Logic bị ảnh hưởng (phải test 100%)
1. `DocumentChecklistSummaryTab.vue` render độc lập (có filter mã NV, phòng ban)
2. `EmailTemplateListTab.vue` render độc lập (CRUD email templates)
3. Route redirect `/recruitment` → `/recruitment/jr`
4. Xóa `RecruitmentView.vue` không break bất kỳ import nào

### Tests cần viết
```
test("GET /recruitment/legal renders document checklist")
test("GET /recruitment/settings renders email template list")
test("GET /recruitment redirects to /recruitment/jr")
test("no import of RecruitmentView exists after deletion")  // grep test
```

---

## Tổng quan các files bị thay đổi

| File | Slices | Loại thay đổi |
|------|--------|---------------|
| `router/index.ts` | 2,3,4,5,6,8 | Thêm 7 routes mới |
| `AppMenu.vue` | 1,2,3,4,5,6,8 | Đổi single item → submenu group |
| `RecruitmentView.vue` | 2,3,4,5,6,8 | Xóa dần tabs → xóa hoàn toàn |
| `JRDetailView.vue` | 2,5 | Sửa 2 navigation strings (dòng 11, 55) |
| `JobPostingDetailView.vue` | 3 | Sửa 1 navigation string (dòng 6) |
| `CandidateDetailView.vue` | 4 | Sửa 1 navigation string (dòng 11) |
| `ApplicationDetailView.vue` | 5 | Sửa 1 navigation string (dòng 11–12) |
| `KanbanPipelineView.vue` | 5 | Refactor `selectedJrId` + `onJrChange()` |
| `KanbanJrPickerView.vue` | 5 | Tạo mới |
| `RecruitmentBreadcrumb.vue` | 7 | Tạo mới |

---

## Thứ tự thực hiện và dependencies

```
Slice 1 (Sidebar submenu)
    └─► Slice 2 (JR route)
        └─► Slice 3 (Postings route)
            └─► Slice 4 (Candidates route)
                └─► Slice 5 (Selection + JR in URL)   ← phức tạp nhất
                    └─► Slice 6 (Headcount route)
                        └─► Slice 7 (Breadcrumb)      ← cần Slice 5 cho ApplicationDetailView
                            └─► Slice 8 (Tách legal/settings + xóa hub)
```

Slice 1 hoàn toàn additive — có thể merge độc lập mà không gây regression.
Từ Slice 2 trở đi, mỗi slice cần pass toàn bộ tests của slice trước đó.

---

## Quyết định cần người dùng xác nhận trước khi thực hiện

1. **Slice 5 — `/recruitment/selection` khi chưa chọn JR:** Hiển thị JR picker, hay redirect
   thẳng đến JR gần nhất (hoặc JR đang `in_progress`)?

2. **Slice 8 — Vị trí "Hồ sơ pháp lý" sau khi tách:** Giữ trong submenu Tuyển dụng, hay
   chuyển sang module Nhân sự (`/employees/legal`)?

3. **Slice 8 — Vị trí "Cài đặt":** Giữ trong submenu Tuyển dụng (`/recruitment/settings`),
   hay merge vào `/settings` chung của hệ thống?

4. **Sau Slice 8 — `/recruitment` redirect:** Redirect về `/recruitment/jr` (mặc định), hay
   tạo trang dashboard tổng quan tuyển dụng mới?

---

---

## Sai khác so với kế hoạch (Implementation Notes)

### Slice 5 — Tuyển chọn

**Kế hoạch:** Tạo 2 routes riêng + file `KanbanJrPickerView.vue` mới cho picker state.

**Thực tế:** Dùng 1 route duy nhất với optional param:
```typescript
{ path: 'recruitment/selection/:jr_id?', name: 'selection', component: KanbanPipelineView.vue }
```
`KanbanPipelineView.vue` tự xử lý cả 2 state (chưa chọn JR → hiển thị Select dropdown;
đã chọn → hiển thị Kanban). `KanbanJrPickerView.vue` **không được tạo**.

**Lý do:** Đơn giản hơn, không cần tách view khi component đã handle được cả 2 trạng thái.

---

### `RecruitmentView.vue` — Trạng thái sau refactoring

File vẫn **tồn tại** trên disk nhưng **không còn trong router** (orphaned).  
Tất cả routes trong `router/index.ts` giờ trỏ trực tiếp đến component con.  
→ Có thể xóa file này khi không còn bất kỳ import nào tham chiếu đến nó.

---

### Sidebar submenu — Số items thực tế

Kế hoạch Slice 1 đề xuất 5 items, Slice 8 thêm 2. Thực tế sidebar có **7 items**:
```typescript
items: [
  { to: '/recruitment/jr',        label: 'Yêu cầu tuyển dụng' },
  { to: '/recruitment/postings',  label: 'Tin tuyển dụng'     },
  { to: '/recruitment/candidates',label: 'Ứng viên'           },
  { to: '/recruitment/selection', label: 'Tuyển chọn'         },
  { to: '/recruitment/headcount', label: 'Kế hoạch nhân sự'   },
  { to: '/recruitment/legal',     label: 'Hồ sơ pháp lý'      },
  { to: '/recruitment/settings',  label: 'Cài đặt tuyển dụng' },
]
```
Mục **`Báo cáo tuyển dụng`** (`/recruitment/reports`) sẽ được thêm khi implement Plan 13.8.

---

### Các chi tiết bổ sung ngoài plan

- **Tab "Tin tuyển dụng" và "Ứng viên trong pipeline"** được thêm vào `JRDetailView.vue`
  (không có trong refactoring plan ban đầu — phát sinh khi review UX).
- **"Kết quả tuyển dụng"** được chuyển từ `JobPostingDetailView.vue` → `JRDetailView.vue`.
- **Auto-close job postings** khi JR hoàn thành: implemented trong `hiring_decision_service.py`.
- **Cột "Số đợt tuyển dụng"** thêm vào `CandidateListTab.vue`.

---

## Chiến lược test

**Công cụ:** Playwright (E2E, phù hợp nhất cho navigation/routing testing).

**Lý do không dùng Vue Test Utils đơn thuần:** Routing logic liên quan đến `router.push`,
`route.params`, `route.query` — cần browser environment thực sự để verify đúng behavior.

**File tests đề xuất:**
```
frontend/e2e/
  recruitment-sidebar.spec.ts       (Slice 1)
  recruitment-jr.spec.ts            (Slice 2)
  recruitment-postings.spec.ts      (Slice 3)
  recruitment-candidates.spec.ts    (Slice 4)
  recruitment-selection.spec.ts     (Slice 5)
  recruitment-headcount.spec.ts     (Slice 6)
  recruitment-breadcrumb.spec.ts    (Slice 7)
  recruitment-legal-settings.spec.ts (Slice 8)
```

Mỗi file test phải chạy pass trước khi slice tiếp theo được bắt đầu.
