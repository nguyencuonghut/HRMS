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

## Việc chưa làm

1. Chưa tách `contract_templates` khỏi `sample`
   - Hiện chưa có bằng chứng đủ mạnh để kết luận chúng là `required` hay `bootstrap`
2. Chưa tách `skills`, `certificates`, `education institutions`, `education majors`
   - Hiện đã xác nhận chúng là catalog dùng runtime, nhưng chưa xác nhận tenant production của dự án này bắt buộc phải có sẵn ngay sau deploy
3. Chưa đổi toàn bộ test harness sang topology seed mới
   - nhiều test hiện vẫn giả định sự tồn tại của `admin@hrms.local`
