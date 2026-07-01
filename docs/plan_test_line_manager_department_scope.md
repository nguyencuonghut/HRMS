# Kế hoạch test phân quyền phạm vi phòng ban cho role `line_manager`

## Mục tiêu

Đảm bảo tài khoản `linemanager@hrms.local` với role `line_manager` và scope seed sẵn cho phòng `KS` (`Phòng kiểm soát`) chỉ được:

- xem dữ liệu thuộc `Phòng kiểm soát` và toàn bộ đơn vị con trong cây của `KS`
- thực hiện các thao tác được phân quyền (`view/create/edit/delete/export/approve/run report`) chỉ trong phạm vi đó
- không nhìn thấy hoặc không thao tác được với dữ liệu ngoài scope `KS`

Tài liệu này là kế hoạch test tổng thể, không phải kết luận rằng tất cả module đã đạt.

## Facts đã kiểm chứng

### 1. Seed user và scope đã tồn tại

Đã kiểm tra [backend/tests/test_rbac_seed.py](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/backend/tests/test_rbac_seed.py).

- `linemanager@hrms.local` được seed với role `line_manager`
- `user_roles.scope_type = 'department'`
- `department_ids` có đúng 1 phần tử
- phòng ban scope seed ra mã `KS`

Đoạn kiểm chứng hiện có:

- [backend/tests/test_rbac_seed.py:282](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/backend/tests/test_rbac_seed.py:282)

### 2. Danh mục module RBAC hiện tại

Nguồn sự thật hiện tại nằm ở [backend/app/core/rbac_catalog.py](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/backend/app/core/rbac_catalog.py).

Các module cần rà theo scope:

1. `org` — Cơ cấu tổ chức
2. `catalog` — Danh mục
3. `settings` — Cài đặt
4. `employees` — Nhân sự
5. `contracts` — Hợp đồng
6. `leaves` — Nghỉ phép
7. `insurance` — Bảo hiểm BHXH
8. `salary` — Lương BHXH
9. `rewards` — Khen thưởng
10. `disciplines` — Kỷ luật
11. `training` — Đào tạo
12. `recruitment` — Tuyển dụng
13. `performance` — Đánh giá KPI
14. `reports` — Báo cáo
15. `users` — Tài khoản người dùng
16. `roles` — Vai trò & Quyền
17. `audit_logs` — Nhật ký hệ thống

### 3. Hiện đã có một phần coverage rải rác

Đã xác nhận hiện có test rải rác cho `line_manager` hoặc department scope tại:

- [backend/tests/test_department_scope_rbac.py](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/backend/tests/test_department_scope_rbac.py)
- [backend/tests/test_permission_boundaries_org_reports.py](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/backend/tests/test_permission_boundaries_org_reports.py)
- [backend/tests/test_contract_reports.py](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/backend/tests/test_contract_reports.py)
- [frontend/tests/e2e/permission-visibility.spec.ts](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/frontend/tests/e2e/permission-visibility.spec.ts)
- [frontend/tests/e2e/permission-action-visibility.spec.ts](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/frontend/tests/e2e/permission-action-visibility.spec.ts)
- [frontend/tests/e2e/line-manager-department-scope.spec.ts](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/frontend/tests/e2e/line-manager-department-scope.spec.ts)
- [frontend/tests/e2e/line-manager-leaves-access.spec.ts](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/frontend/tests/e2e/line-manager-leaves-access.spec.ts)
- [frontend/tests/e2e/line-manager-rewards-access.spec.ts](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/frontend/tests/e2e/line-manager-rewards-access.spec.ts)

Vấn đề hiện tại là coverage chưa được tổ chức thành một ma trận hoàn chỉnh cho tất cả module và tất cả kiểu thao tác.

### 4. Seed RBAC hiện tại chỉ cấp quyền nghiệp vụ cho 4 module

Đã kiểm tra [backend/tests/test_rbac_seed.py](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/backend/tests/test_rbac_seed.py).

Role `line_manager` hiện chỉ có permission ở các module:

- `org`
- `employees`
- `leaves`
- `performance`

Đoạn kiểm chứng:

- [backend/tests/test_rbac_seed.py:177](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/backend/tests/test_rbac_seed.py:177)

Hệ quả:

- với seed hiện tại, các module khác không nên đặt mục tiêu test `department scope` như thể user có quyền thao tác
- thay vào đó, kỳ vọng đúng hiện tại là:
  - menu/route/action bị ẩn ở FE
  - truy cập trực tiếp bị chặn
  - API trả `403`

Nếu business sau này cấp thêm quyền cho `line_manager`, khi đó mới mở rộng matrix scope cho module tương ứng.

## Business rules đã được chốt

Các mục dưới đây là rule nghiệp vụ đã được user xác nhận, dùng làm expected result đích cho test plan. Chúng có thể chưa khớp hoàn toàn với seed/code hiện tại, nên cần phân biệt rõ với phần `Facts đã kiểm chứng`.

### 1. Scope phòng ban luôn bao gồm con và cháu

Với user có role `line_manager`, khi được gán scope cho một phòng/ban nào đó thì scope hợp lệ bao gồm:

- chính phòng/ban được gán
- toàn bộ phòng/ban con
- toàn bộ phòng/ban cháu và sâu hơn trong subtree

Nói ngắn gọn: scope là toàn bộ subtree của node được gán, không chỉ 1 cấp con.

### 2. `job_titles` không phải dữ liệu global cho `line_manager`

Rule đã chốt:

- `job_titles` không phải global read-only cho `line_manager`

Điều này có nghĩa:

- không được mặc định cho rằng line manager luôn xem toàn bộ chức danh
- expected behavior hiện cần đi theo hướng bị chặn hoặc bị giới hạn theo rule riêng của org module

### 3. `catalog`

Rule đã chốt:

- role `line_manager` không được phép xem `catalog`

Expected:

- menu hidden
- direct route forbidden
- API `403`

### 4. `recruitment`

Rule đã chốt:

- `line_manager` chỉ được xem hồ sơ gắn với requisition trong scope

Điều này có nghĩa:

- không được xem toàn bộ candidate pool toàn cục
- phải lọc theo requisition/headcount thuộc subtree phòng ban được gán

### 5. `insurance` và `salary`

Rule đã chốt:

- `line_manager` không được xem `insurance`
- `line_manager` không được xem `salary`

Expected:

- menu hidden
- direct route forbidden
- report route forbidden trừ khi route đó được business gom về module `reports` với rule riêng
- API `403`

### 6. `reports`

Rule đã chốt:

- `line_manager` xem được tất cả các báo cáo
- `line_manager` export được tất cả các báo cáo
- nhưng dữ liệu báo cáo phải scope theo phạm vi phòng/ban được gán và toàn bộ con/cháu của nó

Đây là rule nghiệp vụ rất quan trọng vì nó khác với seed/code hiện tại ở một số chỗ. Khi triển khai test, phải tách rõ:

- `current-state verification`: code hiện tại có đang đúng rule này chưa
- `target-state expectation`: đây là expected business behavior cần đạt

### 7. `rewards` / `disciplines`

Rule đã chốt:

- `line_manager` được dùng trực tiếp module nghiệp vụ KT/KL để xem và thao tác
- dữ liệu KT/KL phải scope theo phòng/ban được gán và toàn bộ con/cháu

Expected:

- menu `/rewards` được hiển thị
- route `/rewards` vào được
- nếu UI dùng chung tab `Khen thưởng` / `Kỷ luật` thì cả hai tab đều phải hoạt động theo scope
- API nguồn `rewards` và `disciplines` phải enforce subtree scope

## Phân loại phạm vi test theo trạng thái seed hiện tại

Lưu ý:

- phần phân loại dưới đây phản ánh `current state` của seed/code hiện tại
- nếu khác với phần `Business rules đã được chốt` thì đó là gap cần test và sau đó cần sửa code/seed

### Nhóm A — Phải test `department scope` thực sự

Đây là các module role `line_manager` hiện có quyền và cần kiểm tra dữ liệu bị giới hạn theo subtree `KS`:

1. `org`
2. `employees`
3. `leaves`
4. `performance`
5. `reports`
   - current state: mới thấy rõ ở dashboard/HR/leave/performance
   - target state theo business: tất cả report đều phải xem/export được nhưng dữ liệu vẫn scope theo subtree phòng ban

### Nhóm B — Với seed hiện tại chỉ cần test `hidden / forbidden`

Các module dưới đây hiện không có permission cho `line_manager`, nên tiêu chí test hiện tại là không lộ quyền trái phép:

1. `catalog`
2. `settings`
3. `contracts`
4. `insurance`
5. `salary`
6. `training`
7. `recruitment`
8. `users`
9. `roles`
10. `audit_logs`

Lưu ý:

- `reports/contracts`, `reports/insurance`, `reports/recruitment`, `reports/training` hiện cũng thuộc nhóm này nếu line manager không có permission nguồn tương ứng
- test cho nhóm này vẫn rất quan trọng, nhưng là test `permission boundary`, không phải test `data scope`

## Inventory coverage hiện có

Phần này phản ánh tình trạng coverage hiện tại đã kiểm chứng từ code, chưa phải coverage mong muốn cuối cùng.

| Module | Backend hiện có | Frontend/E2E hiện có | Nhận định hiện tại |
| --- | --- | --- | --- |
| `org` | Có scope test ở [test_department_scope_rbac.py](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/backend/tests/test_department_scope_rbac.py) cho list/tree/detail department và job positions trong scope; có boundary test ở [test_permission_boundaries_org_reports.py](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/backend/tests/test_permission_boundaries_org_reports.py) cho job titles/org history | Có browser scope test ở [line-manager-department-scope.spec.ts](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/frontend/tests/e2e/line-manager-department-scope.spec.ts); có action visibility test ở [permission-action-visibility.spec.ts](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/frontend/tests/e2e/permission-action-visibility.spec.ts) | Coverage khá tốt cho read-only + scope; còn thiếu scope assertion cho create/edit org endpoint và browser loop cho position detail/filter sâu hơn |
| `catalog` | Chưa thấy test line_manager riêng theo catalog module; chỉ có seed RBAC khẳng định không có permission | Chưa thấy e2e riêng cho catalog với line_manager | Gap rõ: cần test menu/route catalog hidden hoặc forbidden |
| `settings` | Chỉ thấy boundary-only ở [test_permission_boundaries_org_reports.py](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/backend/tests/test_permission_boundaries_org_reports.py) cho `employee-code-sequences`; chưa thấy line_manager test cho các settings API khác | Có e2e ở [settings-permissions.spec.ts](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/frontend/tests/e2e/settings-permissions.spec.ts) xác nhận line_manager không thấy menu và vào route bị forbidden | FE có coverage; BE API boundary còn rất mỏng và không có scope assertion |
| `employees` | Có scope test ở [test_department_scope_rbac.py](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/backend/tests/test_department_scope_rbac.py) cho list/detail/attachments blocked; ngoài ra có nhiều test line_manager ở các file `test_employee_attachments.py`, `test_employee_job_records.py`, `test_employee_relatives.py`, `test_employee_education.py`, `test_employee_io.py` nhưng chủ yếu là permission boundary | Chưa thấy e2e employee list/detail xác nhận chỉ hiện nhân sự trong `KS` | Gap lớn ở browser-level list/detail/data filtering; BE subresource coverage còn thiếu cặp in-scope/out-of-scope |
| `contracts` | Có test [test_contract_reports.py](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/backend/tests/test_contract_reports.py) xác nhận line_manager bị `403` ở contract reports; trong [test_department_scope_rbac.py](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/backend/tests/test_department_scope_rbac.py) có scenario cho scoped contract user nhưng không dùng role line_manager | Có e2e ở [permission-visibility.spec.ts](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/frontend/tests/e2e/permission-visibility.spec.ts) xác nhận route `/contracts` bị forbidden | Đủ cho boundary hiện tại; chưa cần scope test cho line_manager vì seed không có permission |
| `leaves` | Có scope test create/cancel/list ở [test_department_scope_rbac.py](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/backend/tests/test_department_scope_rbac.py); có lookup test ở [test_leave_type_catalog.py](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/backend/tests/test_leave_type_catalog.py) | Có e2e route/access ở [line-manager-leaves-access.spec.ts](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/frontend/tests/e2e/line-manager-leaves-access.spec.ts) | Coverage tốt cho route/open screen; còn thiếu scope assertion cho leave entitlements, leave reports/analytics/export ở BE và browser assertion rằng dữ liệu hiển thị chỉ trong scope |
| `insurance` | Chưa thấy backend scope test line_manager; theo seed hiện tại line_manager không có permission | Có route guard test ở [report-route-map.spec.ts](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/frontend/tests/e2e/report-route-map.spec.ts) cho `/reports/insurance`; [permission-visibility.spec.ts](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/frontend/tests/e2e/permission-visibility.spec.ts) xác nhận menu hidden và report hub hidden | Boundary FE có; chưa có direct route FE cho `/insurance`; boundary BE chưa có test riêng |
| `salary` | Chưa thấy backend test line_manager cho salary | Có visibility test ở [permission-visibility.spec.ts](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/frontend/tests/e2e/permission-visibility.spec.ts) xác nhận menu hidden | Gap: thiếu direct route FE và direct BE boundary test; cần lưu ý router hiện đang guard salary bằng quyền `insurance:view`, phải xác minh đây là chủ ý hay bug |
| `rewards` | Chưa thấy backend line_manager scope test riêng cho rewards API | Có e2e ở [line-manager-rewards-access.spec.ts](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/frontend/tests/e2e/line-manager-rewards-access.spec.ts), nhưng assertion hiện tại đang phản ánh permission cũ và chưa đủ cho target state mới | Theo business rule mới, đây phải là module scope-testable thật; cần cập nhật lại seed/code/test để line_manager vào được `/rewards` và chỉ thấy dữ liệu trong subtree |
| `disciplines` | Chưa thấy backend line_manager scope test riêng cho disciplines API | Có gián tiếp qua [line-manager-rewards-access.spec.ts](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/frontend/tests/e2e/line-manager-rewards-access.spec.ts), nhưng hiện mới assert tab bị ẩn và không gọi API disciplines | Theo business rule mới, tab/flow disciplines phải hoạt động cho line_manager và enforce scope; coverage hiện tại chưa còn phù hợp |
| `training` | Chưa thấy backend line_manager scope/boundary riêng cho training; onboarding list trong [test_permission_boundaries_org_reports.py](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/backend/tests/test_permission_boundaries_org_reports.py) là gần kề nhưng không phải training module | [permission-visibility.spec.ts](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/frontend/tests/e2e/permission-visibility.spec.ts) chỉ xác nhận report hub ẩn `Báo cáo đào tạo`; chưa thấy line_manager test menu `/training` hay route direct `/training` | Gap rõ |
| `recruitment` | Chưa thấy backend line_manager test recruitment module | Có visibility test ở [permission-visibility.spec.ts](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/frontend/tests/e2e/permission-visibility.spec.ts) cho menu/report hidden | Gap rõ |
| `performance` | Có scope test list/detail/report/create ở [test_department_scope_rbac.py](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/backend/tests/test_department_scope_rbac.py) cho KPI/yearly-review/rating-distribution | Có visibility test ở [permission-visibility.spec.ts](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/frontend/tests/e2e/permission-visibility.spec.ts) cho menu/report hub; chưa thấy browser data-scope test trên màn performance | Backend tốt cho các seam chính đã nêu; FE còn thiếu loop dữ liệu theo scope |
| `reports` | Có scope test dashboard + HR reports trong [test_department_scope_rbac.py](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/backend/tests/test_department_scope_rbac.py); có forbidden test contract reports trong [test_contract_reports.py](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/backend/tests/test_contract_reports.py) | Có visibility/canonical route tests ở [permission-visibility.spec.ts](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/frontend/tests/e2e/permission-visibility.spec.ts) và [report-route-map.spec.ts](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/frontend/tests/e2e/report-route-map.spec.ts) | Coverage khá tốt cho permission boundary; còn thiếu line_manager coverage cho các report endpoint khác và browser assertion số liệu report đúng theo scope |
| `users` | Có backend test assign role scope ở [test_users.py](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/backend/tests/test_users.py), nhưng đây là admin flow, không phải line_manager self-access | Có visibility test ở [permission-visibility.spec.ts](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/frontend/tests/e2e/permission-visibility.spec.ts) ẩn menu admin users | Đủ cho boundary FE cơ bản; thiếu API direct `403` test cho line_manager |
| `roles` | Chưa thấy backend line_manager direct access test | Có visibility test ở [permission-visibility.spec.ts](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/frontend/tests/e2e/permission-visibility.spec.ts) ẩn menu roles | Gap BE |
| `audit_logs` | Chưa thấy backend line_manager direct access test | Có visibility test ở [permission-visibility.spec.ts](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/frontend/tests/e2e/permission-visibility.spec.ts) ẩn menu audit logs | Gap BE |

### Tín hiệu mạnh từ inventory BE

Kết quả rà BE cho thấy:

- department-scope thật cho `line_manager` hiện chỉ cover rõ ở `org`, `employees`, `leaves`, `performance`, `reports` thông qua [test_department_scope_rbac.py](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/backend/tests/test_department_scope_rbac.py)
- nhiều file `backend/tests/test_employee_*` có `line_manager`, nhưng phần lớn đang test permission boundary của subresource, chưa test record `in-scope` / `out-of-scope`
- `contracts` chỉ có line_manager boundary `403`; scope-positive path đang được test bằng một scoped `hr_officer`, không phải line_manager
- `insurance`, `salary`, `training`, `recruitment`, `audit_logs` hiện chưa có line_manager backend coverage đáng kể
- `rewards` và `disciplines` theo business rule mới phải trở thành nhóm scope-testable, nhưng backend coverage hiện tại gần như chưa có

### Coverage đang mâu thuẫn, chưa được tính là đã xác nhận

Có một số test hiện mâu thuẫn với code hoặc mâu thuẫn lẫn nhau, nên chưa được tính là coverage đã verify:

1. `job-titles` / `org-history`
   - một số test cũ kỳ vọng `200`
   - nhưng endpoint hiện tại đã chặn department-scoped org user
2. FE `/org/job-titles`
   - một spec kỳ vọng `forbidden`
   - một spec khác lại kỳ vọng load được page

Vì vậy, các mục này phải được rerun và reconcile trước khi dùng làm căn cứ pass/fail.

## Điều kiện tiên quyết để chạy test plan này

### 1. Local user không phải lúc nào cũng tồn tại

`linemanager@hrms.local` chỉ được seed khi chạy:

- `python -m app.seeds --local-users`
- hoặc `python -m app.seeds --sample`

Không được giả định cứ có DB là sẽ có user này.

### 2. Sample hiện tại không tạo được đối chứng `out-of-scope`

Sample cross-module hiện tập trung cho `KS / KSNB / IT`, trong khi `IT` và `KSNB` đều là con của `KS`.

Hệ quả:

- sample hiện tại không tạo ra control branch ngoài scope của `linemanager@hrms.local`
- muốn test `out-of-scope` phải chuẩn bị fixture explicit ở nhánh khác ngoài `KS`

### 3. Có surface reachable không map 1-1 với module RBAC

Ngoài matrix module, cần nhớ một số surface line manager có thể chạm tới qua permission khác tên module, ví dụ:

- onboarding
- employee code sequences

Các surface này cần có checklist riêng trong execution phase.

## Kết luận coverage hiện tại

### Đã có nền tốt

- `org`
- `employees`
- `leaves`
- `performance`
- `reports` liên quan đến dashboard/HR/leave/performance

Đây là các module đã có ít nhất một phần backend scope enforcement được test.

### Mới dừng ở mức permission boundary

- `settings`
- `contracts`
- `insurance`
- `salary`
- `training`
- `recruitment`
- `users`
- `roles`
- `audit_logs`

Với các module này, test hiện tại chủ yếu trả lời câu hỏi:

- có thấy menu không
- có vào route được không
- có bị `403` không

nhưng chưa phải bài test “dữ liệu thuộc subtree `KS`”.

### Cần rà lại ngay vì business rule mới lệch với seed/e2e cũ

- `rewards`
- `disciplines`

Lý do:

- [test_rbac_seed.py](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/backend/tests/test_rbac_seed.py) hiện xác nhận `line_manager` chỉ có module `org`, `employees`, `leaves`, `performance`
- nhưng business rule mới đã chốt rằng `line_manager` được dùng trực tiếp module nghiệp vụ KT/KL
- suite [line-manager-rewards-access.spec.ts](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/frontend/tests/e2e/line-manager-rewards-access.spec.ts) cũng đang phản ánh trạng thái chuyển tiếp, chưa phải target state hoàn chỉnh

Đây là nhóm gap cần sửa seed/code/test, không chỉ là chuyện xác minh runtime DB.

### Tín hiệu mạnh từ inventory FE

Kết quả rà FE/e2e cho thấy:

- coverage browser thực sự theo `department scope` mới mạnh nhất ở `org`
- `leaves` hiện mới chứng minh “mở màn hình được”, chưa chứng minh “data trong màn hình đã lọc theo scope”
- `employees`, `performance`, và phần lớn `reports` vẫn thiếu browser assertion ở mức dữ liệu
- nhiều module đang chỉ có `menu hidden / route forbidden`, chưa có direct API/DB seam tương ứng
- `rewards` / `disciplines` hiện có e2e nhưng đang phản ánh expected behavior cũ, cần rewrite theo target state mới

## Nguyên tắc test

### 1. Không chỉ test permission code, phải test dữ liệu theo scope

Mỗi module cần kiểm tra đồng thời 3 lớp:

- FE visibility:
  - menu, tab, button, shortcut, filter, dialog action
- FE route access:
  - có vào route được không
  - có bị redirect `forbidden` không
- BE data/authz:
  - API trả đúng dữ liệu trong scope
  - API chặn dữ liệu ngoài scope
  - API chặn mutation ngoài scope

### 2. Scope đúng là `phòng được gán + toàn bộ đơn vị con`

Với seed hiện tại:

- root scope là `KS`
- dữ liệu ở `KS` và các đơn vị con dưới `KS` phải nhìn thấy nếu module đó cho phép
- dữ liệu ở nhánh khác phải bị ẩn hoặc bị chặn

### 3. Mỗi thao tác phải có cặp test `in-scope` và `out-of-scope`

Ví dụ:

- xem employee trong `KS` => `200`
- xem employee ngoài `KS` => `403` hoặc không xuất hiện trong list

Không chấp nhận chỉ test một chiều.

## Ma trận test theo module

## A. `org` — Cơ cấu tổ chức

Mục tiêu:

- chỉ xem được đơn vị thuộc scope `KS`
- không tạo/sửa/xóa cấu trúc tổ chức ngoài quyền đã cấp
- không chọn/tra cứu nhân sự ngoài scope trong các UI gán head/scope

Case cần có:

- list department chỉ trả về `KS` subtree
- department detail ngoài subtree bị chặn
- job positions chỉ xem được position liên quan scope
- job titles là danh mục dùng chung:
  - cần quyết định rõ có cho line manager xem toàn cục hay không
  - nếu cho xem toàn cục thì chỉ read-only

Seam cần test:

- backend service/query filter
- route `/org/*`
- UI table/filter/detail

## B. `catalog` — Danh mục

Mục tiêu:

- line manager không được sửa danh mục toàn cục trừ khi business thật sự cho phép

Case cần có:

- menu và route catalog có hiện hay không đúng theo permission
- nếu có xem thì mọi action mutate phải bị ẩn/chặn
- import/export catalog phải bị chặn nếu không có quyền

Lưu ý:

- catalog thường là global data, không phải departmental data
- module này cần test theo `permission boundary`, không phải theo record scope

## C. `settings` — Cài đặt

Mục tiêu:

- line manager không được vào các màn cài đặt hệ thống nếu không có quyền riêng

Case cần có:

- menu `Cài đặt` có/không
- route `/settings/*` bị chặn đúng
- API notification/settings không truy cập trái phép

## D. `employees` — Nhân sự

Mục tiêu:

- chỉ thấy nhân sự thuộc `KS` subtree
- chỉ mở detail, edit, attachment, probation, document checklist trong scope
- ngoài scope phải bị ẩn hoặc `403`

Case cần có:

- employee list chỉ chứa nhân sự trong `KS`
- search/filter không lộ nhân sự ngoài scope
- employee detail ngoài scope bị chặn
- create employee:
  - nếu line manager được tạo thì chỉ gán được department trong scope
  - nếu không được tạo thì UI và API đều chặn
- edit employee trong scope được phép theo role
- edit employee ngoài scope bị chặn
- import/export employee:
  - nếu route hiện thì dữ liệu xuất ra chỉ trong scope
  - import không được tạo dữ liệu sang department ngoài scope

## E. `contracts` — Hợp đồng

Trạng thái seed hiện tại:

- `line_manager` không có permission module này

Mục tiêu:

- hidden / forbidden đúng

Case cần có:

- menu hidden
- direct route `/contracts` => `forbidden`
- direct route `/reports/contracts` => `forbidden`
- API list/detail/report/export => `403`

## F. `leaves` — Nghỉ phép

Mục tiêu:

- line manager chỉ thao tác đơn nghỉ phép của nhân sự trong scope

Case cần có:

- leave request list trong scope
- tạo đơn nghỉ cho nhân sự trong scope
- không tạo/sửa/duyệt đơn cho nhân sự ngoài scope
- manual leave entitlement chỉ trong scope nếu được phép
- leave report/dashboard chỉ tổng hợp subtree `KS`

## G. `insurance` — Bảo hiểm BHXH

Mục tiêu:

- với seed hiện tại: hidden / forbidden
- nếu sau này được cấp quyền thì mới mở rộng sang scope subtree

Case cần có:

- permission visibility
- direct route guard
- API list/detail/report/export => `403`

## H. `salary` — Lương BHXH

Mục tiêu:

- với seed hiện tại: hidden / forbidden
- đồng thời phải xác minh route guard hiện tại dùng `insurance:view` là chủ ý hay bug

Case cần có:

- FE menu/route/action visibility
- FE direct route guard
- BE list/detail/report/export => `403`

## I. `rewards` — Khen thưởng

Mục tiêu:

- `line_manager` được xem và thao tác trực tiếp trên nghiệp vụ khen thưởng
- dữ liệu khen thưởng phải scope theo phòng/ban được gán và toàn bộ con/cháu

Case cần có:

- menu `/rewards` hiển thị
- route `/rewards` vào được
- list reward chỉ chứa employee trong subtree scope
- create reward cho employee trong scope
- create reward cho employee ngoài scope bị chặn
- edit/delete ngoài scope bị chặn
- report/export reward trong module này nếu có chỉ ra dữ liệu trong scope

## J. `disciplines` — Kỷ luật

Mục tiêu:

- `line_manager` được xem và thao tác trực tiếp trên nghiệp vụ kỷ luật
- dữ liệu kỷ luật phải scope theo phòng/ban được gán và toàn bộ con/cháu

Case cần có:

- tab `Kỷ luật` hiển thị và dùng được
- list discipline chỉ chứa employee trong subtree scope
- create discipline cho employee trong scope
- create/edit/delete ngoài scope bị chặn
- report/export discipline nếu có chỉ ra dữ liệu trong scope

## K. `training` — Đào tạo

Mục tiêu:

- với seed hiện tại: hidden / forbidden
- nếu sau này được cấp quyền thì tách tiếp training catalog và training record theo employee scope

Case cần có:

- menu hidden
- direct route forbidden
- API `403`

## L. `recruitment` — Tuyển dụng

Mục tiêu:

- với seed hiện tại: hidden / forbidden
- nếu sau này được cấp quyền thì mới tách tiếp các nhóm dữ liệu dùng chung và gắn department

Case cần có:

- menu hidden
- direct route forbidden
- API `403`

Đây là module có rủi ro business rule cao, cần ưu tiên review kỹ domain trước khi viết assertion cuối.

## M. `performance` — Đánh giá KPI

Mục tiêu:

- line manager chỉ xem và thao tác KPI/review của nhân sự trong scope

Case cần có:

- KPI list/report scoped
- tạo review/KPI cho employee trong scope
- không thao tác record ngoài scope
- analytics/report không lẫn nhân sự ngoài subtree

## N. `reports` — Báo cáo

Mục tiêu:

- theo business rule đã chốt, `line_manager` xem được và export được tất cả các báo cáo
- mọi report có dữ liệu nhân sự phải lọc theo subtree của phòng/ban được gán, bao gồm toàn bộ con/cháu

Case cần có:

- `/reports` hiện đầy đủ tất cả report card/menu theo business rule mới
- dashboard/HR/probation/leave/contracts/insurance/salary/recruitment/training/rewards/performance:
  - số liệu chỉ tính trên scope
- export ở tất cả report không kéo dữ liệu ngoài scope

Ghi chú:

- đây là `target-state expectation`
- current state trong code có thể chưa đạt, và chính đó là nội dung cần test để xác định gap

## O. `users`, `roles`, `audit_logs`

Mục tiêu:

- line manager không được truy cập các module quản trị hệ thống trừ khi có permission đặc biệt

Case cần có:

- menu hidden
- route direct access => `forbidden`
- backend API => `403`

## Chiến lược triển khai test

### Slice 1 — Baseline seed và dữ liệu đối chứng

Mục tiêu:

- chuẩn hóa fixture để luôn có:
  - user `linemanager@hrms.local` chắc chắn tồn tại
  - employee/leave/performance trong `KS`
  - employee tương đương ở nhánh ngoài `KS`
  - fixture explicit ngoài `KS` cho các bài test out-of-scope

Việc làm:

- bổ sung fixture explicit để có cặp dữ liệu `in-scope` và `out-of-scope`
- đặt tên dữ liệu rõ ràng để assertion không mơ hồ
- không dùng sample `KS/KSNB/IT` làm dữ liệu out-of-scope

Exit criteria:

- có thể xác định chắc chắn từng record thuộc `KS` hay ngoài `KS`

### Slice 2 — Backend authz matrix

Mục tiêu:

- chặn đúng ở API trước

Việc làm:

- gom test theo module vào các file `backend/tests/test_*`
- mỗi API quan trọng có ít nhất:
  - list scoped
  - detail out-of-scope blocked
  - mutation out-of-scope blocked
  - export/report scoped nếu có

Ưu tiên module:

1. employees
2. leaves
3. performance
4. rewards
5. disciplines
6. reports
7. org
8. boundary pack cho contracts/insurance/salary/settings/catalog/users/roles/audit_logs/recruitment/training

### Slice 3 — Frontend visibility và route guard

Mục tiêu:

- line manager không nhìn thấy UI không dùng được

Việc làm:

- e2e cho sidebar, report hub, tab, action button, dialog trigger
- direct route access test cho từng nhóm route

Exit criteria:

- không còn tình trạng click menu hợp lệ rồi mới bị đá `forbidden`

### Slice 4 — Browser CRUD/report loops

Mục tiêu:

- xác nhận end-to-end với dữ liệu thật theo scope

Việc làm:

- với từng module ưu tiên, chạy loop:
  - vào list
  - xác nhận chỉ thấy dữ liệu `KS`
  - thử mở record trong scope
  - thử truy cập record ngoài scope bằng URL trực tiếp nếu có id
  - thử action mutate/report/export nếu role được phép

### Slice 5 — Regression pack cho go-live

Mục tiêu:

- có pack test riêng cho `line_manager`

Việc làm:

- tạo nhóm command smoke:
  - backend authz suite cho scope
  - frontend Playwright suite cho line manager
- đưa vào checklist trước release

## Các quyết định đã chốt trước khi viết full assertion

1. scope phòng ban của `line_manager` luôn bao gồm toàn bộ con/cháu trong subtree
2. `job_titles` không phải global cho `line_manager`
3. `catalog`: `line_manager` không được xem
4. `recruitment`: chỉ xem hồ sơ gắn requisition trong scope
5. `insurance` và `salary`: `line_manager` không được xem
6. `rewards` / `disciplines`: `line_manager` được dùng trực tiếp module nghiệp vụ KT/KL để xem và thao tác, dữ liệu phải scope theo subtree phòng ban được gán
7. `reports`: `line_manager` xem được và export được tất cả report, nhưng dữ liệu phải scope theo subtree phòng ban được gán

## Điểm còn cần xác nhận thêm

Hiện chưa còn điểm mở nào ở nhóm rule chính; phần còn lại là gap giữa target state và current state cần được test và sửa.

## Checklist kết quả mong muốn

- FE chỉ hiện menu, tab, button đúng với permission và scope
- route direct access ngoài quyền bị chặn
- API list/detail/mutation/export đều enforce scope `KS` subtree
- không có báo cáo nào lộ dữ liệu ngoài `Phòng kiểm soát`
- regression suite có thể chạy lặp lại khi đổi seed RBAC hoặc đổi query filter

## Gợi ý file test cần gom về sau

- backend:
  - `test_department_scope_rbac.py`
  - `test_permission_boundaries_org_reports.py`
  - nhóm `test_*` theo từng module có line manager scenario
- frontend:
  - `permission-visibility.spec.ts`
  - `permission-action-visibility.spec.ts`
  - `line-manager-*.spec.ts`

## Tên command smoke đề xuất

- backend:
  - `pytest tests/test_department_scope_rbac.py -q`
- frontend:
  - `npx playwright test frontend/tests/e2e/line-manager-*.spec.ts`

Sau khi tài liệu này được duyệt, bước tiếp theo nên là lập ma trận coverage thực tế:

- đã có test
- test còn thiếu
- test có rồi nhưng assertion chưa đủ chặt
