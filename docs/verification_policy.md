# Verification Policy

## Mục tiêu

Tránh false positive khi:

- backend test pass nhưng UI vẫn sai
- build pass nhưng tương tác thực tế vẫn sai
- agent kết luận từ suy luận thay vì từ kiểm chứng

## Root Cause đã xảy ra

Bug ở màn `Danh mục hành chính` lọt qua vì chỉ kiểm tra:

- test backend
- `npm run build`

nhưng không kiểm tra seam người dùng thực sự dùng:

- đổi filter trên UI
- quan sát DOM render
- đối chiếu request/network theo state mới

## Policy áp dụng cho các task sau

### 1. Không đoán

- Mọi kết luận phải dựa trên:
  - code inspection
  - command output
  - automated tests
  - browser/runtime verification

### 2. Verify đúng seam

- Backend/data bug:
  - test API/service
  - kiểm tra dữ liệu runtime nếu có query/seed/import
- Frontend/UI bug:
  - build
  - browser-level verification
- Full-stack bug:
  - phải verify cả backend seam và browser seam

### 3. Browser-level verification là bắt buộc nếu thay đổi

- filter/select/search
- pagination/sorting
- async loading/state sync
- empty state / conditional rendering
- dialog / CRUD flow / route flow

### 4. Final report phải nêu rõ

- đã verify gì
- chưa verify gì
- phần nào là fact, phần nào chưa xác nhận
