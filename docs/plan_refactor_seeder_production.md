## Mục tiêu

Tách rõ 4 lớp dữ liệu seed để chuẩn bị deploy production:

1. `required`
   - baseline hệ thống, áp dụng cho mọi môi trường
2. `bootstrap`
   - dữ liệu khởi tạo vận hành của doanh nghiệp
3. `local-users`
   - tài khoản mặc định chỉ dùng cho dev/test
4. `sample`
   - dữ liệu demo/test

## Các vấn đề đã được xác nhận trước refactor

1. `sample.py` chứa `departments`, `job_titles`, `salary_scales`
2. `notification_templates` không nằm trong CLI seeder, mà được seed ngầm ở app startup
3. `rbac.py` đang seed cả roles/permissions lẫn 5 user local mặc định
4. `app.main` auto-seed RBAC và notification templates khi app boot

## Trạng thái sau refactor

### 1. Required

- `backend/app/seeds/required.py`
- Bao gồm:
  - insurance baseline
  - administrative catalogs
  - required education / business catalogs
  - BHYT clinics
  - notification templates

### 2. Bootstrap

- `backend/app/seeds/bootstrap.py`
- Bao gồm:
  - `job_titles`
  - `salary_scales`
  - `salary_scale_entries`
  - `departments`

### 3. Local users

- `backend/app/seeds/rbac.py`
- `run_core()` chỉ seed:
  - permissions
  - roles
  - role_permissions
- `seed_users()` seed 5 tài khoản local mặc định

### 4. Sample

- `backend/app/seeds/sample.py`
- Chỉ còn:
  - sample education catalogs
  - sample skills / certificates / template metadata
  - sample employees
  - sample job history / relatives / education

## Phân loại còn lại đã được xác nhận

### Giữ ở `sample`

1. `skills`, `certificates`
   - Đã xác nhận có provisioning path thật:
     - backend CRUD/lookup ở `other_business_catalog`
     - frontend quản trị tại `frontend/src/views/catalog/OtherBusinessCatalogView.vue`
   - Đã xác nhận UI runtime chịu được danh sách rỗng:
     - `EducationTab.vue` map kết quả lookup sang option arrays
     - `CandidateDetailView.vue` cũng load bằng `Promise.allSettled(...)` và fallback `[]`
   - Kết luận đã xác nhận:
     - đây là catalog vận hành tùy doanh nghiệp, không phải baseline bắt buộc để app boot/module load

2. `educational_institutions`, `education_majors`
   - Đã xác nhận có CRUD/lookup thật qua `education_catalog`
   - Đã xác nhận frontend chỉ dùng theo kiểu autocomplete/lookup, không có chỗ nào yêu cầu phải tồn tại sẵn một row cụ thể để mở màn hình
   - Kết luận đã xác nhận:
     - giữ ở `sample`; nếu doanh nghiệp muốn corpus sẵn, đó là dữ liệu onboarding chứ không phải `required`

3. `contract_templates`, `contract_template_placeholders`
   - Đã xác nhận có provisioning path thật:
     - backend CRUD/inspection/placeholders ở `other_business_catalog`
     - frontend quản trị tại tab `Mẫu hợp đồng` trong `OtherBusinessCatalogView.vue`
   - Đã xác nhận runtime chấp nhận trạng thái chưa có template:
     - `backend/tests/test_probation.py` chấp nhận `POST /probation/contract/generate` trả `404` khi chưa có template
   - Kết luận đã xác nhận:
     - template là dữ liệu onboarding/nghiệp vụ, không phải baseline hệ thống bắt buộc

## Lệnh CLI mới

```bash
# Baseline hệ thống
docker compose exec backend python -m app.seeds

# Baseline + bootstrap vận hành
docker compose exec backend python -m app.seeds --bootstrap

# Baseline + user local mặc định
docker compose exec backend python -m app.seeds --local-users

# Dev/test đầy đủ
docker compose exec backend python -m app.seeds --sample
```

Ghi chú:
- `--sample` hiện kéo theo cả `bootstrap` và `local-users`
- startup auto-seed chỉ còn chạy ngoài production

## Trạng thái test harness / runbook

1. `backend/tests/conftest.py`
   - đã seed `rbac.run(..., include_users=True)` trước khi mở `TestClient`
   - test suite không còn phụ thuộc vào việc người chạy phải gọi `python -m app.seeds --local-users` trước

2. Runbook production
   - đã cập nhật lệnh production seed vào:
     - `README.md`
     - `scripts/restore_procedure.md`
     - `docs/sla.md`

## Việc chưa làm

1. Chưa bỏ hoàn toàn việc các test module dùng email local `*@hrms.local`
   - hiện dependency đã được chuyển vào test harness session-level thay vì CLI/prod seed flow
2. Chưa rerun full backend suite trong chính tài liệu này
   - cần kết quả runtime thật của `pytest -q` sau refactor cuối cùng
