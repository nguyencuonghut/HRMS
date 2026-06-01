# Kế hoạch Refactor Hệ thống Báo cáo — HRMS

**Ngày:** 2026-06-01  
**Mục tiêu:** Chuẩn hóa kiến trúc thông tin (IA) của toàn bộ báo cáo trong HRMS, loại bỏ tình trạng báo cáo bị phân tán giữa menu `Báo cáo`, menu nghiệp vụ, và tab nội bộ trong từng module.

---

## 1. Bối cảnh hiện tại

Qua rà soát menu và router hiện tại:

- Có một cụm `Báo cáo` tập trung tại:
  - `/reports`
  - `/reports/dashboard`
  - `/reports/hr`
  - `/reports/leave-analytics`
  - `/reports/insurance`
  - `/reports/contracts`
  - `/reports/export`
- Đồng thời vẫn tồn tại các báo cáo nằm trong menu nghiệp vụ:
  - `/employees/probation-reports`
  - `/leave-reports`
  - `/insurance/reports`
  - `/recruitment/reports`
- Và thêm một lớp thứ ba là `tab Báo cáo` nằm bên trong màn hình module:
  - `RewardsView.vue`
  - `TrainingView.vue`
  - `PerformanceView.vue`

Hệ quả:

- Người dùng không có một mental model rõ ràng về “báo cáo nằm ở đâu”.
- Cùng một nhu cầu “xem báo cáo” nhưng phải học nhiều pattern UI khác nhau:
  - route riêng
  - tab nội bộ
  - menu `Báo cáo`
- Về dài hạn khó chuẩn hóa:
  - phân quyền
  - export
  - bookmark / deep-link
  - tài liệu hướng dẫn
  - E2E test

---

## 2. Quan điểm thiết kế chuẩn cho HRMS production

### 2.1 Nguyên tắc cốt lõi

1. **Mỗi báo cáo chính thức chỉ có 1 route canonical**
   - Không có 2 màn hình khác nhau cho cùng 1 loại báo cáo.

2. **Menu `Báo cáo` là reporting hub duy nhất**
   - Mọi báo cáo phân tích, tổng hợp, dashboard cấp hệ thống phải đi qua đây.

3. **Module nghiệp vụ được phép có shortcut ngữ cảnh**
   - Nhưng shortcut chỉ là link tới route canonical trong `/reports/...`
   - Không tạo thêm report page / report tab riêng logic.

4. **Phân biệt rõ giữa “báo cáo phân tích” và “workflow tác nghiệp có tên là báo cáo”**
   - Không phải thứ gì có chữ “báo cáo” cũng nên nằm trong reporting hub.

5. **Tên gọi shortcut phải thể hiện đúng vai trò**
   - Ưu tiên `Xem báo cáo ...` thay vì chỉ `Báo cáo ...`
   - Giúp người dùng hiểu đây là lối tắt, không phải nơi gốc.

---

## 3. Phân loại báo cáo trong HRMS này

### 3.1 Nhóm A — Báo cáo phân tích / tổng hợp cấp hệ thống

Các báo cáo này nên tập trung dưới menu `Báo cáo`:

- Dashboard tổng quan
- Báo cáo nhân sự
- Báo cáo thử việc / onboarding
- Báo cáo nghỉ phép
- Báo cáo bảo hiểm phân tích
- Báo cáo hợp đồng
- Báo cáo tuyển dụng
- Báo cáo đào tạo
- Báo cáo khen thưởng & kỷ luật
- Báo cáo hiệu suất / KPI
- Trung tâm xuất báo cáo

### 3.2 Nhóm B — Workflow tác nghiệp, hồ sơ định kỳ, hồ sơ nộp cơ quan

Các màn này **không nên ép gộp hết vào menu `Báo cáo`**, vì bản chất chúng là quy trình tác nghiệp:

- `insurance/reports`
- `insurance/reports/:id`

Lý do:

- Đây không chỉ là xem thống kê.
- Đây là vòng đời hồ sơ báo cáo BHXH: draft, pending_review, approved, rejected, export biểu mẫu.
- Nên coi nó là **nghiệp vụ bảo hiểm định kỳ**, không phải chỉ là analytics.

Khuyến nghị:

- Giữ trong module `Bảo hiểm BHXH`
- Đổi label cho rõ bản chất, ví dụ:
  - `Kỳ báo cáo BHXH`
  - hoặc `Hồ sơ báo cáo BHXH`
- Không dùng cùng nhãn với report analytics để tránh nhầm.

---

## 4. Cấu trúc menu báo cáo chuẩn đề xuất

### 4.1 Sidebar cấp 1

Giữ nguyên `Báo cáo` là một nhóm/menu riêng ở sidebar.

### 4.2 Cấu trúc bên trong menu `Báo cáo`

Đề xuất chuẩn:

- `Tổng quan báo cáo`
  - `/reports`
- `Dashboard tổng quan`
  - `/reports/dashboard`
- `Nhân sự`
  - `/reports/hr`
- `Thử việc & Onboarding`
  - `/reports/probation`
- `Nghỉ phép`
  - `/reports/leave`
- `Bảo hiểm`
  - `/reports/insurance`
- `Hợp đồng`
  - `/reports/contracts`
- `Tuyển dụng`
  - `/reports/recruitment`
- `Đào tạo`
  - `/reports/training`
- `Khen thưởng & Kỷ luật`
  - `/reports/rewards`
- `Hiệu suất / KPI`
  - `/reports/performance`
- `Xuất báo cáo`
  - `/reports/export`

### 4.3 Quy tắc ở các module nghiệp vụ

Trong các module nghiệp vụ:

- Có thể giữ shortcut
- Nhưng đổi text thành dạng:
  - `Xem báo cáo thử việc`
  - `Xem báo cáo nghỉ phép`
  - `Xem báo cáo tuyển dụng`
- Shortcut phải trỏ vào route canonical trong `/reports/...`

---

## 5. Route canonical mục tiêu

### 5.1 Route canonical nên tồn tại sau refactor

Giữ hoặc tạo mới các route sau:

- `/reports`
- `/reports/dashboard`
- `/reports/hr`
- `/reports/probation`
- `/reports/leave`
- `/reports/insurance`
- `/reports/contracts`
- `/reports/recruitment`
- `/reports/training`
- `/reports/rewards`
- `/reports/performance`
- `/reports/export`

### 5.2 Route nghiệp vụ vẫn nên giữ ngoài `reports`

Giữ riêng vì đây là workflow tác nghiệp:

- `/insurance`
- `/insurance/reports`
- `/insurance/reports/:id`

Nhưng đổi nhãn menu/module để tránh trùng nghĩa với analytics report.

---

## 6. Ma trận route/menu: giữ, merge, redirect

## 6.1 Nhóm nên giữ nguyên

| Route / Menu hiện tại | Hành động | Ghi chú |
|---|---|---|
| `/reports` | Giữ | Là hub tổng quan báo cáo |
| `/reports/dashboard` | Giữ | Canonical dashboard |
| `/reports/hr` | Giữ | Canonical báo cáo nhân sự |
| `/reports/contracts` | Giữ | Canonical báo cáo hợp đồng |
| `/reports/export` | Giữ | Canonical export center |
| `/insurance/reports` | Giữ | Nhưng đổi nghĩa thành workflow hồ sơ báo cáo BHXH |
| `/insurance/reports/:id` | Giữ | Detail của hồ sơ báo cáo BHXH |

## 6.2 Nhóm nên đổi tên nhưng giữ route

| Route hiện tại | Menu label hiện tại | Đề xuất mới |
|---|---|---|
| `/reports/insurance` | `Báo cáo bảo hiểm` | Giữ route, label có thể là `Phân tích bảo hiểm` |
| `/insurance/reports` | `Báo cáo biến động` | Đổi thành `Kỳ báo cáo BHXH` hoặc `Hồ sơ báo cáo BHXH` |

## 6.3 Nhóm nên merge hoặc redirect về `Báo cáo`

| Route hiện tại | Trạng thái sau refactor | Route đích canonical | Ghi chú |
|---|---|---|---|
| `/employees/probation-reports` | Redirect | `/reports/probation` | Giữ shortcut trong menu `Nhân sự` |
| `/leave-reports` | Redirect | `/reports/leave` | Đổi tên route canonical cho đồng nhất |
| `/recruitment/reports` | Redirect | `/reports/recruitment` | Module `Tuyển dụng` chỉ giữ shortcut |

## 6.4 Nhóm hiện đang là tab nội bộ, nên tách thành report page canonical

| Vị trí hiện tại | Hành động | Route canonical đề xuất | Ghi chú |
|---|---|---|---|
| `RewardsView.vue` tab `report` | Tách ra | `/reports/rewards` | Module `Khen thưởng & Kỷ luật` chỉ giữ shortcut |
| `TrainingView.vue` tab `report` | Tách ra | `/reports/training` | Module `Đào tạo` chỉ giữ shortcut |
| `PerformanceView.vue` tab `report` | Tách ra | `/reports/performance` | Module `Đánh giá KPI` chỉ giữ shortcut |

## 6.5 Nhóm đã canonical nhưng menu module nên bổ sung shortcut

| Module | Shortcut nên có | Route canonical |
|---|---|---|
| `Hợp đồng` | `Xem báo cáo hợp đồng` | `/reports/contracts` |
| `Bảo hiểm BHXH` | `Xem phân tích bảo hiểm` | `/reports/insurance` |

---

## 7. Đề xuất menu sidebar sau refactor

### 7.1 Menu `Nhân sự`

- `Danh sách nhân viên`
- `Tiếp nhận nhân viên mới`
- `Xem báo cáo thử việc`

### 7.2 Menu `Nghỉ phép`

- `Số ngày phép`
- `Ghi nhận nghỉ phép`
- `Xem báo cáo nghỉ phép`

### 7.3 Menu `Bảo hiểm BHXH`

- `Hồ sơ & Chính sách`
- `Kỳ báo cáo BHXH`
- `Xem phân tích bảo hiểm`

### 7.4 Menu `Tuyển dụng`

- Giữ các menu vận hành như hiện tại
- thêm `Xem báo cáo tuyển dụng`

### 7.5 Menu `Khen thưởng & Kỷ luật`

Hai phương án:

- Phương án A — ngắn hạn:
  - giữ `RewardsView`
  - bỏ tab `Báo cáo`
  - thêm menu con `Xem báo cáo khen thưởng & kỷ luật`
- Phương án B — dài hạn:
  - tách module thành route list riêng cho reward / discipline
  - giữ report canonical riêng trong `/reports/rewards`

### 7.6 Menu `Đào tạo`

- giữ các tab nghiệp vụ
- bỏ tab `Báo cáo`
- thêm shortcut `Xem báo cáo đào tạo`

### 7.7 Menu `Đánh giá KPI`

- giữ `KPI tháng`, `Đánh giá cuối năm`, `Liên kết kết quả`
- bỏ tab `Báo cáo`
- thêm shortcut `Xem báo cáo hiệu suất`

### 7.8 Menu `Báo cáo`

- `Tổng quan báo cáo`
- `Dashboard tổng quan`
- `Nhân sự`
- `Thử việc & Onboarding`
- `Nghỉ phép`
- `Bảo hiểm`
- `Hợp đồng`
- `Tuyển dụng`
- `Đào tạo`
- `Khen thưởng & Kỷ luật`
- `Hiệu suất / KPI`
- `Xuất báo cáo`

---

## 8. Kế hoạch triển khai refactor

### Slice 1 — Chuẩn hóa IA và route map `✅ Hoàn thành`

- Chốt canonical routes
- Chốt tên hiển thị menu
- Chốt route nào là workflow, route nào là analytics

#### Kết quả chốt của Slice 1

##### A. Route canonical chính thức

Các route sau được chốt là nguồn chính thức cho báo cáo cấp hệ thống:

| Nhóm | Route canonical | Nhãn chuẩn |
|---|---|---|
| Hub | `/reports` | `Tổng quan báo cáo` |
| Dashboard | `/reports/dashboard` | `Dashboard tổng quan` |
| HR | `/reports/hr` | `Báo cáo nhân sự` |
| Probation / onboarding | `/reports/probation` | `Báo cáo thử việc & onboarding` |
| Leave | `/reports/leave` | `Báo cáo nghỉ phép` |
| Insurance analytics | `/reports/insurance` | `Phân tích bảo hiểm` |
| Contracts | `/reports/contracts` | `Báo cáo hợp đồng` |
| Recruitment | `/reports/recruitment` | `Báo cáo tuyển dụng` |
| Training | `/reports/training` | `Báo cáo đào tạo` |
| Rewards / discipline | `/reports/rewards` | `Báo cáo khen thưởng & kỷ luật` |
| Performance | `/reports/performance` | `Báo cáo hiệu suất / KPI` |
| Export | `/reports/export` | `Xuất báo cáo` |

##### B. Route workflow không nhập vào reporting hub

Các route sau **không được coi là analytics report canonical**:

| Route | Phân loại | Quyết định IA |
|---|---|---|
| `/insurance/reports` | Workflow hồ sơ kỳ báo cáo BHXH | Giữ trong module bảo hiểm |
| `/insurance/reports/:id` | Workflow detail | Giữ trong module bảo hiểm |

##### C. Quy tắc shortcut ngữ cảnh

Shortcut trong module được chấp nhận nếu đáp ứng đủ 3 điều kiện:

1. Chỉ dùng để điều hướng
2. Trỏ đúng route canonical dưới `/reports/...`
3. Nhãn nên thể hiện vai trò shortcut, ưu tiên dạng `Xem báo cáo ...`

##### D. Quyết định với các màn hiện có

| Route / màn hiện tại | Quyết định Slice 1 |
|---|---|
| `/employees/probation-reports` | Không còn là canonical |
| `/leave-reports` | Không còn là canonical |
| `/recruitment/reports` | Không còn là canonical |
| `RewardsView.vue` tab `report` | Không còn là canonical |
| `TrainingView.vue` tab `report` | Không còn là canonical |
| `PerformanceView.vue` tab `report` | Không còn là canonical |

##### E. Kết quả áp dụng cho sidebar

Sau Slice 1, cấu trúc IA được chốt như sau:

- Sidebar `Báo cáo` là hub duy nhất cho báo cáo chính thức
- Menu nghiệp vụ vẫn giữ shortcut ngữ cảnh
- Báo cáo không còn được phép “sống song song” ở cả:
  - module page riêng
  - module tab nội bộ
  - route canonical dưới `/reports/...`

##### F. Tiêu chí hoàn thành Slice 1

- [x] Chốt danh sách route canonical
- [x] Chốt ranh giới analytics vs workflow
- [x] Chốt naming chuẩn cho menu báo cáo
- [x] Chốt policy shortcut ngữ cảnh
- [x] Chốt danh sách route/màn không còn là canonical

##### G. Điều chưa làm trong Slice 1

Slice 1 **chỉ chốt quyết định kiến trúc thông tin**. Chưa bao gồm:

- tạo route mới
- redirect route cũ
- sửa AppMenu / router
- bỏ tab report nội bộ
- browser regression test

### Slice 2 — Tạo route canonical còn thiếu

- Thêm:
  - `/reports/probation`
  - `/reports/leave`
  - `/reports/recruitment`
  - `/reports/training`
  - `/reports/rewards`
  - `/reports/performance`

### Slice 3 — Redirect route cũ

- `/employees/probation-reports` → `/reports/probation`
- `/leave-reports` → `/reports/leave`
- `/recruitment/reports` → `/reports/recruitment`

### Slice 4 — Gỡ report tab nội bộ

- `RewardsView.vue`
- `TrainingView.vue`
- `PerformanceView.vue`

Thay bằng:

- nút/link shortcut sang route canonical

### Slice 5 — Chỉnh menu và breadcrumb

- AppMenu
- router meta title
- page header
- breadcrumb text

### Slice 6 — Regression test

- browser-level verification cho:
  - menu navigation
  - redirect cũ → route mới
  - shortcut trong module
  - permission guards

---

## 9. Quy tắc kỹ thuật sau refactor

1. Không thêm report mới trực tiếp vào module nếu đó là báo cáo chính thức.
2. Report mới phải được cấp route trong `/reports/...` trước.
3. Module chỉ được thêm shortcut nếu:
   - shortcut dẫn về route canonical
   - label thể hiện đây là shortcut
4. Các report page phải có:
   - filter state rõ ràng
   - URL deep-link được
   - export nhất quán
   - permission rõ ràng

---

## 10. Kết luận

Hướng refactor đúng cho hệ thống này là:

- **Tập trung toàn bộ báo cáo chính thức về `Báo cáo`**
- **Giữ shortcut ngữ cảnh trong module**
- **Không để module sở hữu một report implementation riêng nếu đã có report canonical**
- **Tách rõ analytics report với workflow hồ sơ định kỳ**

Điểm quan trọng nhất:

- `insurance/reports` nên được xử lý như **nghiệp vụ hồ sơ báo cáo BHXH**
- còn `reports/insurance` là **màn phân tích / tổng hợp bảo hiểm**

Nếu không tách 2 khái niệm này, người dùng sẽ tiếp tục bị nhầm giữa “lập hồ sơ báo cáo” và “xem báo cáo phân tích”.
