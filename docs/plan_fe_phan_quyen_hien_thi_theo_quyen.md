# Kế hoạch chuẩn hóa FE hiển thị theo quyền

## Mục tiêu

Giảm tình trạng user nhìn thấy menu, route, button hoặc action mà cuối cùng chỉ nhận lỗi `Không có quyền thực hiện thao tác này`.

Nguyên tắc đích:

- FE chỉ hiển thị menu, tab, button, shortcut, action mà user thực sự có quyền dùng.
- Router FE vẫn giữ guard `forbidden` như lớp chặn cuối.
- Backend vẫn là nguồn quyết định cuối cùng; FE chỉ tối ưu UX, không thay thế authz ở BE.

## Findings đã kiểm chứng

### 1. Coverage permission ở router đang rất thấp

Đã kiểm tra [frontend/src/router/index.ts](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/frontend/src/router/index.ts).

- Có `58` route component.
- Chỉ `5` route có `meta.permission` hoặc `meta.anyPermissions`.
- Có `53` route không có permission meta.

Điều này có nghĩa phần lớn màn hình hiện chỉ được bảo vệ bởi:

- login guard
- backend `403`

chứ chưa được FE chặn theo quyền ở cấp route.

Ví dụ route chưa có permission meta:

- [frontend/src/router/index.ts:45](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/frontend/src/router/index.ts:45) `org/job-titles`
- [frontend/src/router/index.ts:76](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/frontend/src/router/index.ts:76) `employees`
- [frontend/src/router/index.ts:123](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/frontend/src/router/index.ts:123) `contracts`
- [frontend/src/router/index.ts:149](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/frontend/src/router/index.ts:149) `insurance`
- [frontend/src/router/index.ts:207](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/frontend/src/router/index.ts:207) `recruitment/jr`
- [frontend/src/router/index.ts:288](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/frontend/src/router/index.ts:288) `reports`
- [frontend/src/router/index.ts:388](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/frontend/src/router/index.ts:388) `catalog`
- [frontend/src/router/index.ts:441](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/frontend/src/router/index.ts:441) `settings`

### 2. Sidebar menu chưa hỗ trợ phân quyền ở child item

Đã kiểm tra [frontend/src/components/layout/AppMenu.vue](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/frontend/src/components/layout/AppMenu.vue).

Các điểm đã xác nhận:

- `MenuItem.items` hiện chỉ có `{ to, label, icon }`, không có `permission` hay `anyPermissions`: [AppMenu.vue:68](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/frontend/src/components/layout/AppMenu.vue:68)
- `canAccess()` chỉ check permission ở item cha: [AppMenu.vue:103](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/frontend/src/components/layout/AppMenu.vue:103)
- Khi render child, code lặp `item.items` trực tiếp, không lọc theo quyền từng child: [AppMenu.vue:28](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/frontend/src/components/layout/AppMenu.vue:28)

Hệ quả:

- Nếu nhóm cha được hiển thị, toàn bộ child bên trong đều hiện ra, dù child đó có thể đáng lẽ phải bị ẩn.

### 3. Một số menu quản trị hiện chưa gắn permission ở chính menu item

Đã xác nhận 3 menu quản trị ở sidebar không khai báo permission:

- [AppMenu.vue:340](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/frontend/src/components/layout/AppMenu.vue:340) `/admin/users`
- [AppMenu.vue:341](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/frontend/src/components/layout/AppMenu.vue:341) `/admin/roles`
- [AppMenu.vue:342](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/frontend/src/components/layout/AppMenu.vue:342) `/admin/audit-logs`

Trong khi route tương ứng lại có permission meta:

- [frontend/src/router/index.ts:457](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/frontend/src/router/index.ts:457) `users:view`
- [frontend/src/router/index.ts:463](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/frontend/src/router/index.ts:463) `roles:view`
- [frontend/src/router/index.ts:469](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/frontend/src/router/index.ts:469) `audit_logs:view`

Tức là hiện user có thể vẫn nhìn thấy link quản trị rồi mới bị đá sang `forbidden`.

### 4. FE action-level gating đang không nhất quán

Đã rà `useAuthStore` / `hasPermission` trong FE.

Các màn đã có gating rõ:

- [frontend/src/views/data/DataImportView.vue:111](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/frontend/src/views/data/DataImportView.vue:111)
- [frontend/src/views/employees/AttachmentsTab.vue:169](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/frontend/src/views/employees/AttachmentsTab.vue:169)
- [frontend/src/views/employees/ContractTab.vue:263](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/frontend/src/views/employees/ContractTab.vue:263)
- [frontend/src/views/org/DepartmentDetailView.vue:590](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/frontend/src/views/org/DepartmentDetailView.vue:590)

Nhưng phần lớn view CRUD không dùng `useAuthStore` hoặc `hasPermission`.

Ví dụ đã xác nhận:

- [frontend/src/views/rewards/components/RewardListTab.vue:48](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/frontend/src/views/rewards/components/RewardListTab.vue:48) có button `Thêm quyết định`
- [frontend/src/views/rewards/components/RewardListTab.vue:133](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/frontend/src/views/rewards/components/RewardListTab.vue:133) có button `Sửa`
- [frontend/src/views/rewards/components/RewardListTab.vue:142](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/frontend/src/views/rewards/components/RewardListTab.vue:142) có button `Xóa`

Nhưng file này không dùng `useAuthStore` / `hasPermission`.

Tương tự:

- [frontend/src/views/training/components/CourseListTab.vue:48](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/frontend/src/views/training/components/CourseListTab.vue:48) `Thêm khóa học`
- [frontend/src/views/training/components/CourseListTab.vue:139](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/frontend/src/views/training/components/CourseListTab.vue:139) `Sửa`
- [frontend/src/views/training/components/CourseListTab.vue:145](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/frontend/src/views/training/components/CourseListTab.vue:145) `Xóa`

File này cũng không có `useAuthStore` / `hasPermission`.

### 5. Router guard hiện hoạt động theo exact permission string

Đã kiểm tra:

- [frontend/src/stores/auth.ts:107](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/frontend/src/stores/auth.ts:107) `hasPermission()` dùng so khớp exact string
- [frontend/src/router/index.ts:508](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/frontend/src/router/index.ts:508) route guard dùng thẳng `meta.permission`

Điều này tốt ở mặt đơn giản, nhưng bắt buộc:

- route meta
- menu item
- button-level gating
- backend permission code

phải cùng dùng một vocabulary thống nhất.

## Kết luận audit

FE hiện chưa có một lớp “hiển thị theo quyền” đồng nhất.

Tình trạng thực tế đang là:

- một phần nhỏ route đã có guard theo quyền
- sidebar chỉ lọc top-level, chưa lọc child-level
- action button trong nhiều màn CRUD vẫn hiện đầy đủ
- nên user vẫn có thể thấy action rồi mới nhận `403` từ backend

## Hướng thiết kế sửa

### Nguyên tắc thống nhất

1. Route nào là màn nghiệp vụ thì phải khai báo quyền truy cập.
2. Menu không được khai báo tay khác logic với router.
3. Child menu phải hỗ trợ permission riêng.
4. Button/action CRUD phải được ẩn hoặc disable theo quyền tương ứng.
5. `403` từ backend vẫn giữ, nhưng là fallback, không phải UX chính.

### Permission model FE đề xuất

- Quyền vào màn:
  - dùng `meta.permission` hoặc `meta.anyPermissions`
- Quyền thao tác:
  - `create`, `edit`, `delete`, `export`
- Quyền xem:
  - `view`

Ví dụ:

- màn `RewardListTab`:
  - vào màn: `rewards:view`
  - hiện button thêm: `rewards:create`
  - hiện button sửa: `rewards:edit`
  - hiện button xóa: `rewards:delete`

## Kế hoạch triển khai theo slice

### Slice 1 — Chuẩn hóa nguồn sự thật cho route permission

Mục tiêu:

- mọi route component nghiệp vụ đều có `meta.permission` hoặc `meta.anyPermissions`

Việc làm:

- rà toàn bộ [frontend/src/router/index.ts](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/frontend/src/router/index.ts)
- bổ sung permission meta cho các route hiện còn trống
- thống nhất rule:
  - list/detail/report screen đọc dữ liệu: `*:view`
  - import screen: `*:edit` hoặc `*:create` tùy nghiệp vụ
  - admin screen: `users:view`, `roles:view`, `audit_logs:view`

Verify:

- unit/smoke: route guard đúng với `admin`, `hr_officer`, `line_manager`
- e2e:
  - route được phép vào được
  - route không được phép redirect `/forbidden`

### Slice 2 — Refactor sidebar menu để hỗ trợ permission ở từng child

Mục tiêu:

- menu chỉ hiện đúng mục user được phép thấy

Việc làm:

- mở rộng kiểu `MenuItem.items` để child có:
  - `permission?: string`
  - `anyPermissions?: string[]`
- lọc child trước khi render
- ẩn luôn group cha nếu sau khi lọc không còn child nào
- gắn permission cho các mục admin và các mục report/module có phân quyền riêng

Verify:

- snapshot/DOM test cho `AppMenu`
- e2e với các role:
  - `line_manager` không thấy admin / insurance / salary / recruitment report nếu không có quyền
  - `hr_officer` chỉ thấy mục hợp lệ

### Slice 3 — Chuẩn hóa action-level gating bằng composable/directive

Mục tiêu:

- không phải copy `auth.hasPermission(...)` rải rác thủ công

Việc làm:

- tạo composable hoặc directive thống nhất, ví dụ:
  - `usePermissionGate()`
  - `v-can`
- API gợi ý:
  - `canView(module)`
  - `canCreate(module)`
  - `canEdit(module)`
  - `canDelete(module)`
  - `canExport(module)`

Verify:

- component-level tests cho helper/composable
- rà type-safe để tránh hardcode sai string permission

### Slice 4 — Sửa các màn CRUD ưu tiên cao

Ưu tiên nhóm màn dễ lộ lỗi UX nhất:

1. `rewards`
2. `training`
3. `recruitment`
4. `insurance`
5. `catalog`
6. `employee detail` các tab con
7. `contracts`, `leaves`, `salary`

Việc làm:

- ẩn/disable:
  - nút thêm
  - nút sửa
  - nút xóa
  - nút export/import
  - action dropdown
- nếu màn có read-only mode hợp lệ, giữ nội dung xem nhưng bỏ action mutate

Verify:

- test theo role ở các màn đại diện:
  - `hr_officer`
  - `line_manager`
  - `finance`
- xác nhận không còn phải bấm action rồi mới nhận toast `403` cho các case phổ biến

### Slice 5 — Đồng bộ menu báo cáo, report hub và shortcut button

Mục tiêu:

- mọi đường vào report screen đều cùng logic quyền

Việc làm:

- rà:
  - sidebar menu
  - report hub
  - shortcut button trong module
  - breadcrumb/back-link điều hướng
- mỗi link phải dùng cùng permission với route đích

Verify:

- e2e cho:
  - `/reports/*`
  - shortcut “Xem báo cáo ...”
  - redirect route cũ

### Slice 6 — Chuẩn hóa UX khi vẫn gặp 403

Mục tiêu:

- khi backend vẫn trả `403`, UX phải rõ và ít gây khó chịu hơn

Việc làm:

- phân loại 403:
  - route access -> redirect `/forbidden`
  - action access -> toast ngắn gọn, không lặp spam
- tránh hiển thị raw message backend lặp đi lặp lại nếu đáng ra FE phải chặn trước

Verify:

- manual + e2e cho case deep-link và stale permission

## Danh sách module ưu tiên sửa

### P0

- Router permission meta
- Sidebar child permission
- Admin menu
- Report routes / report entry points

### P1

- Rewards
- Training
- Recruitment
- Insurance

### P2

- Catalog
- Settings
- Employee detail tabs
- Onboarding / probation / reminders

## Test plan

### Backend seam

- không đổi logic authz backend trong kế hoạch này
- chỉ dùng backend hiện tại làm nguồn permission thật

### Frontend seam

- `npm run build`
- component tests cho menu/composable nếu bổ sung
- e2e role-based cho:
  - `admin`
  - `hr_officer`
  - `line_manager`
  - `finance`

### Browser scenarios bắt buộc

1. User không có quyền không nhìn thấy menu tương ứng
2. User có quyền `view` vẫn vào được route đọc dữ liệu
3. User thiếu `edit/delete` không nhìn thấy action mutate
4. Deep-link trực tiếp vào route không được phép vẫn về `/forbidden`
5. Export/import button chỉ hiện khi có quyền phù hợp

## Khuyến nghị triển khai

- Không nên sửa rải rác từng button trước.
- Nên làm theo thứ tự:
  1. route meta
  2. menu child permission
  3. permission helper/composable
  4. action gating theo module

Lý do:

- nếu chưa có nguồn sự thật chung, sửa tay từng màn sẽ tiếp tục lệch giữa router, menu và button

## Kết quả mong muốn

Sau khi hoàn tất:

- user hầu như không còn nhìn thấy chức năng ngoài quyền của mình
- `forbidden` chỉ còn là fallback cho deep-link / stale state
- permission FE và permission BE dùng cùng vocabulary `view/create/edit/delete/export`
