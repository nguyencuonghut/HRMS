# DANH SÁCH TÍNH NĂNG PHẦN MỀM QUẢN LÝ NHÂN SỰ (HRMS)

**Phiên bản:** 1.0  
**Ngày:** 2026-05-12  
**Phạm vi:** Phần mềm HRM chuyên nghiệp phù hợp quy trình, quy định tại Việt Nam

---

## Phạm vi & Giới hạn

| Tính năng | Trong phạm vi |
|---|---|
| Cơ cấu tổ chức & Phân quyền | ✅ |
| Danh mục hành chính & Học vấn | ✅ |
| Hồ sơ nhân sự | ✅ |
| Hợp đồng lao động | ✅ |
| Nghỉ phép (không có quy trình phê duyệt) | ✅ |
| Bảo hiểm BHXH/BHYT/BHTN | ✅ |
| Lương bảo hiểm xã hội (BHXH) | ✅ |
| Khen thưởng & Kỷ luật | ✅ |
| Đào tạo & Phát triển | ✅ |
| Đánh giá hiệu suất / KPI | ✅ |
| Báo cáo & Dashboard | ✅ |
| Nhập/Xuất dữ liệu | ✅ |
| Tuyển dụng & Ứng viên (ATS) | 🔜 Sẽ làm sau |
| Tiếp nhận & Thử việc | 🔜 Sẽ làm sau |
| Chấm công & Ca kíp | ❌ Ngoài phạm vi |
| Quy trình phê duyệt nghỉ phép | ❌ Ngoài phạm vi |
| Lương sản xuất kinh doanh | ❌ Ngoài phạm vi |
| Cổng thông tin nhân viên (Employee Portal) | ❌ Ngoài phạm vi |

---

## 1. Cơ cấu Tổ chức & Phân quyền (Org & RBAC)

### 1.1. Cơ cấu tổ chức
- Quản lý **Công ty / Chi nhánh** (đa chi nhánh)
- Quản lý **Phòng/Ban/Bộ phận** theo cây phân cấp
- Quản lý **Chức danh** (Director, Manager, Staff,...)
- Quản lý **Vị trí công việc** (Job Position):
  - Mô tả công việc, yêu cầu tuyển dụng
  - Mức lương BHXH mặc định theo vị trí
  - Phụ cấp vị trí
  - File đính kèm tiêu chuẩn tuyển dụng
- Lịch sử thay đổi cơ cấu tổ chức

### 1.2. Phân quyền (RBAC)
- Quản lý **Vai trò** (Roles): Admin, HR Manager, HR Officer, Line Manager, Finance
- Phân quyền theo **chức năng** (xem, thêm, sửa, xóa, xuất)
- Phân quyền theo **phạm vi tổ chức** (toàn công ty, chi nhánh, phòng ban)
- **Audit log** toàn bộ thao tác thay đổi dữ liệu
- Quản lý tài khoản người dùng hệ thống

---

## 2. Danh mục Hành chính & Học vấn

### 2.1. Danh mục hành chính
- Quản lý địa chỉ theo **hệ thống hành chính cũ** (3 cấp): Tỉnh/Thành phố → Quận/Huyện → Xã/Phường
- Quản lý địa chỉ theo **hệ thống hành chính mới** (2 cấp): Tỉnh/Thành phố → Xã/Phường (bỏ cấp Quận/Huyện theo cải cách hành chính)
- Hỗ trợ nhập địa chỉ theo cả hai hệ thống (cũ/mới) trong hồ sơ nhân sự
- Import/cập nhật từ dữ liệu hành chính chính thức

### 2.2. Danh mục học vấn
- Danh mục **Trình độ học vấn**: Tiểu học, THCS, THPT, Trung cấp, Cao đẳng, Đại học, Thạc sĩ, Tiến sĩ
- Danh mục **Trường học** (liên kết hồ sơ nhân sự)
- Danh mục **Chuyên ngành**

### 2.3. Danh mục nghiệp vụ khác
- Danh mục **Loại hợp đồng lao động**
- Danh mục **Quốc tịch**
- Danh mục **Dân tộc**, **Tôn giáo**
- Danh mục **Ngân hàng**
- Danh mục **Kỹ năng**, **Chứng chỉ**
- Danh mục **Loại nghỉ phép**

---

## 3. Hồ sơ Nhân sự (Employee Profile)

### 3.1. Thông tin cá nhân
- Họ tên, ngày sinh, giới tính, quốc tịch, dân tộc, tôn giáo
- CCCD/CMND/Hộ chiếu: số, ngày cấp, nơi cấp, ngày hết hạn (đối với người nước ngoài)
- Giấy phép lao động (đối với người nước ngoài): số, ngày cấp, ngày hết hạn, cảnh báo sắp hết hạn
- Hộ khẩu thường trú, địa chỉ liên lạc (hỗ trợ cả hệ thống địa chỉ cũ và mới)
- Số điện thoại, email cá nhân
- Mã số thuế cá nhân (MST)
- Số tài khoản ngân hàng

### 3.2. Thông tin công việc
- Phòng ban, chức danh, vị trí công việc
- Ngày vào làm, ngày thử việc, ngày chính thức
- Trạng thái: Thử việc / Chính thức / Nghỉ phép dài hạn / Đã nghỉ việc
- Mã nhân viên (tự động sinh)

### 3.3. Thông tin người thân
- Danh sách người thân: tên, quan hệ, ngày sinh, nghề nghiệp
- Người liên hệ khẩn cấp

### 3.4. Học vấn & Kinh nghiệm
- Quá trình học vấn: trường, chuyên ngành, trình độ, năm tốt nghiệp
- Kinh nghiệm làm việc trước đây: công ty, vị trí, thời gian
- Kỹ năng, chứng chỉ, ngoại ngữ

### 3.5. Hồ sơ đính kèm
- Upload ảnh thẻ, CCCD, bằng cấp, chứng chỉ,...
- Quản lý phiên bản tài liệu

### 3.6. Sự kiện & Nhắc nhở
- Cảnh báo **sinh nhật** nhân viên
- Cảnh báo **thâm niên** (1, 3, 5, 10 năm)
- Cảnh báo **sắp hết hạn hợp đồng**
- Cảnh báo **sắp hết thời gian thử việc**

### 3.7. Import/Export
- **Import nhân viên** hàng loạt từ file Excel theo mẫu
- **Export** danh sách nhân viên ra Excel/PDF
- Export hồ sơ cá nhân đầy đủ

---

## 4. Hợp đồng Lao động

### 4.1. Quản lý hợp đồng
- Các **loại hợp đồng**: thử việc, xác định thời hạn (1 năm, 2 năm, 3 năm), không xác định thời hạn
- Thông tin hợp đồng: số HĐ, ngày ký, ngày hiệu lực, ngày hết hạn, mức lương BHXH
- Upload file hợp đồng scan/PDF
- Lịch sử tất cả hợp đồng của nhân viên

### 4.2. Mẫu hợp đồng
- Quản lý **mẫu hợp đồng** (template) theo loại
- Sinh hợp đồng tự động từ mẫu với dữ liệu nhân viên
- Hỗ trợ định dạng Word/PDF

### 4.3. Nhắc tái ký
- Tự động cảnh báo khi hợp đồng **sắp hết hạn** (30, 15, 7 ngày trước)
- Danh sách nhân viên cần tái ký hợp đồng
- Theo dõi trạng thái tái ký

---

## 5. Nghỉ phép & Vắng mặt (Leave Management)

### 5.1. Danh mục loại nghỉ phép
- Cấu hình các loại nghỉ: Phép năm, Nghỉ bệnh, Nghỉ thai sản, Nghỉ tang, Nghỉ cưới, Không lương,...
- Cấu hình quy tắc cho từng loại: có/không trừ lương, tính vào ngày lễ không,...

### 5.2. Quản lý số ngày phép
- **Nạp phép** theo năm: tự động hoặc nhập thủ công
- Quy tắc nạp phép theo thâm niên (theo Bộ luật Lao động VN: 12 ngày + thêm theo thâm niên)
- **Chuyển phép** từ năm trước (cấu hình giới hạn)
- Theo dõi **số ngày phép còn lại** theo từng loại

### 5.3. Ghi nhận nghỉ phép
- HR ghi nhận nghỉ phép cho nhân viên (không cần quy trình phê duyệt)
- Ghi nhận: nhân viên, loại phép, ngày bắt đầu, ngày kết thúc, lý do
- Hỗ trợ nghỉ nửa ngày
- Tự động trừ số ngày phép còn lại

### 5.4. Báo cáo nghỉ phép
- Báo cáo **số ngày phép đã dùng / còn lại** theo nhân viên
- Báo cáo tổng hợp nghỉ phép theo phòng ban, thời gian
- Báo cáo **tồn phép** cuối năm
- Xuất Excel/PDF

---

## 6. Bảo hiểm Xã hội (BHXH/BHYT/BHTN)

### 6.1. Thông tin bảo hiểm nhân viên
- Mã số BHXH của nhân viên
- Nơi đăng ký khám chữa bệnh ban đầu (BHYT)
- Mức lương đóng BHXH (liên kết vị trí công việc)
- Ngày tham gia BHXH tại công ty
- Trạng thái: Đang đóng / Tạm dừng / Đã nghỉ

### 6.2. Tỷ lệ đóng BHXH
- Cấu hình tỷ lệ đóng theo quy định hiện hành:
  - **BHXH:** Người lao động 8%, Người sử dụng lao động 17.5%
  - **BHYT:** Người lao động 1.5%, Người sử dụng lao động 3%
  - **BHTN:** Người lao động 1%, Người sử dụng lao động 1%
- Tự động cập nhật khi có thay đổi quy định

### 6.3. Biến động tăng/giảm BHXH
- Tự động ghi nhận **TĂNG** khi nhân viên mới tham gia bảo hiểm
- Tự động ghi nhận **GIẢM** khi nhân viên nghỉ việc hoặc tạm dừng
- Thông tin biến động: tên, mã BHXH, mức lương đóng, ngày hiệu lực, loại biến động
- Xem lịch sử biến động theo tháng

### 6.4. Báo cáo BHXH
- **Báo cáo tăng/giảm BHXH hàng tháng** (chuẩn mẫu cơ quan BHXH)
- Danh sách nhân viên đang tham gia BHXH
- Tổng quỹ lương đóng BHXH toàn công ty
- Xuất biểu mẫu kê khai BHXH (D02-TS, C12-TS,...) ra Excel

---

## 7. Quản lý Lương BHXH

> **Lưu ý:** Module này chỉ quản lý **lương làm căn cứ đóng BHXH**, không quản lý lương thực nhận hay lương sản xuất kinh doanh.

### 7.1. Mức lương BHXH
- Ghi nhận **mức lương BHXH** của từng nhân viên (theo hợp đồng lao động)
- Lịch sử thay đổi mức lương BHXH theo thời gian
- Liên kết với vị trí công việc (mức lương BHXH mặc định theo vị trí)

### 7.2. Điều chỉnh lương BHXH
- Tạo **quyết định điều chỉnh lương BHXH**: nhân viên, mức cũ, mức mới, ngày hiệu lực, lý do
- Tự động cập nhật mức đóng BHXH khi có điều chỉnh
- Ghi nhận biến động tăng/giảm mức đóng BHXH sang module Bảo hiểm

### 7.3. Bảng tổng hợp lương BHXH
- Bảng tổng hợp mức lương BHXH toàn công ty theo tháng
- Tính toán số tiền đóng BHXH của nhân viên và công ty
- Xuất Excel để đối chiếu với cơ quan BHXH

---

## 8. Khen thưởng & Kỷ luật

### 8.1. Khen thưởng
- Tạo **quyết định khen thưởng**: loại khen thưởng, nhân viên, nội dung, giá trị, ngày
- Danh mục loại khen thưởng: Bằng khen, Giấy khen, Thưởng tiền, Thưởng hiện vật,...
- Lưu file quyết định khen thưởng
- Lịch sử khen thưởng trong hồ sơ nhân viên

### 8.2. Kỷ luật
- Tạo **quyết định kỷ luật**: hình thức, nhân viên, nội dung, mức độ, ngày hiệu lực
- Hình thức kỷ luật theo Bộ luật Lao động VN: Khiển trách, Kéo dài thời hạn nâng lương, Cách chức, Sa thải
- Lưu biên bản, quyết định kỷ luật
- Lịch sử kỷ luật trong hồ sơ nhân viên

### 8.3. Báo cáo
- Báo cáo tổng hợp khen thưởng/kỷ luật theo kỳ
- Thống kê theo phòng ban, loại khen thưởng/kỷ luật

---

## 9. Đào tạo & Phát triển (L&D)

### 9.1. Quản lý khóa học
- Danh mục **khóa học/chương trình đào tạo**: tên, loại, thời lượng, đơn vị tổ chức
- Loại đào tạo: Nội bộ, Bên ngoài, Online
- Kế hoạch đào tạo theo năm/quý

### 9.2. Theo dõi đào tạo nhân viên
- Gán nhân viên vào khóa học
- Ghi nhận kết quả: Đạt / Không đạt / Điểm số
- Theo dõi trạng thái hoàn thành
- **Hộ chiếu đào tạo** (Training Passport): toàn bộ lịch sử đào tạo của nhân viên

### 9.3. Chứng chỉ
- Quản lý chứng chỉ sau đào tạo: tên, ngày cấp, ngày hết hạn
- Cảnh báo chứng chỉ sắp hết hạn
- Lưu file chứng chỉ

### 9.4. Báo cáo đào tạo
- Báo cáo tỷ lệ hoàn thành theo khóa học, phòng ban
- Chi phí đào tạo theo kỳ
- Danh sách nhân viên chưa hoàn thành đào tạo bắt buộc

---

## 10. Đánh giá Hiệu suất / KPI (Performance Management)

### 10.1. KPI tháng
- Nhân sự nhập tay hoặc **import file Excel** điểm KPI hàng tháng cho từng nhân viên
- Thông tin bao gồm: mã nhân viên, họ tên, năm, tháng, điểm KPI, ghi chú, người nhập

### 10.2. Đánh giá cuối năm
- **Điểm KPI trung bình** tự động tính từ các tháng đã nhập trong năm
- Xếp loại tự động theo điểm: **Xuất sắc / Tốt / Đạt / Cần cải thiện**
- Nhận xét – đánh giá cuối năm do nhân sự bổ sung

### 10.3. Liên kết kết quả đánh giá
- Kết nối kết quả đánh giá với quyết định khen thưởng
- Kết nối với kế hoạch đào tạo (cải thiện điểm yếu)
- Lịch sử kết quả đánh giá trong hồ sơ nhân viên

### 10.4. Báo cáo hiệu suất
- Phân phối xếp loại toàn công ty theo năm
- Báo cáo điểm KPI trung bình theo phòng ban

---

## 11. Báo cáo & Dashboard (People Analytics)

### 11.1. Dashboard tổng quan
- **Headcount** hiện tại theo phòng ban, chi nhánh
- Biến động nhân sự trong tháng (tuyển mới, nghỉ việc)
- Tỷ lệ nghỉ việc (Turnover Rate)
- Cơ cấu nhân sự: giới tính, độ tuổi, trình độ học vấn, thâm niên

### 11.2. Báo cáo Nhân sự
- Danh sách nhân viên theo nhiều tiêu chí lọc
- Báo cáo **biến động nhân sự**: tuyển dụng, thôi việc theo tháng/quý/năm
- Báo cáo **thâm niên** nhân viên
- Báo cáo **cơ cấu tổ chức**

### 11.3. Báo cáo Nghỉ phép
- Tổng hợp nghỉ phép theo nhân viên, phòng ban
- Tồn phép cuối kỳ
- Thống kê theo loại phép

### 11.4. Báo cáo Bảo hiểm
- Tăng/giảm BHXH hàng tháng
- Tổng quỹ lương đóng BHXH
- Danh sách nhân viên tham gia/không tham gia

### 11.5. Báo cáo Hợp đồng
- Hợp đồng sắp hết hạn
- Thống kê theo loại hợp đồng

### 11.6. Xuất báo cáo
- Xuất tất cả báo cáo ra **Excel / PDF**
- Lọc theo: phòng ban, chi nhánh, khoảng thời gian
- Lưu mẫu báo cáo tùy chỉnh

---

## 12. Nhập/Xuất & Tự động hóa

### 12.1. Import dữ liệu
- Import hàng loạt từ **file Excel theo mẫu**: nhân viên, hợp đồng, nghỉ phép, BHXH
- Kiểm tra lỗi dữ liệu trước khi import (validation)
- Báo cáo kết quả import (thành công / lỗi)

### 12.2. Export dữ liệu
- Export danh sách, hồ sơ, báo cáo ra Excel/PDF
- Template export chuẩn doanh nghiệp
- Export biểu mẫu BHXH theo chuẩn cơ quan Nhà nước

### 12.3. Thông báo & Nhắc việc tự động
- Email nhắc: hợp đồng sắp hết hạn, thử việc sắp kết thúc, sinh nhật nhân viên
- Email nhắc: chứng chỉ sắp hết hạn, đánh giá KPI sắp đến hạn
- Cấu hình **mẫu email** (template) cho từng loại thông báo
- Log lịch sử gửi email

### 12.4. API tích hợp
- **REST API** mở cho tích hợp hệ thống bên ngoài (kế toán, ERP)
- Xác thực API qua token (Bearer Token)
- Tài liệu API (API Documentation)

---

## 13. Tuyển dụng & Ứng viên (ATS)

> **Lưu ý:** Module này sẽ được phát triển sau. Chưa nằm trong phạm vi triển khai hiện tại.

### 13.1. Kế hoạch tuyển dụng
- Tạo **Yêu cầu tuyển dụng** (Job Requisition): vị trí, số lượng, lý do, thời hạn
- Phê duyệt kế hoạch tuyển dụng (HR Manager)
- Theo dõi ngân sách tuyển dụng
- Liên kết với vị trí công việc trong cơ cấu tổ chức

### 13.2. Quản lý ứng viên
- Hồ sơ ứng viên: thông tin cá nhân, CV, kinh nghiệm, học vấn
- Trạng thái ứng viên trong pipeline: Mới → Đang xét → Phỏng vấn → Offer → Đã tuyển / Từ chối
- Upload và lưu trữ CV, hồ sơ đính kèm
- Tìm kiếm & lọc ứng viên đa tiêu chí

### 13.3. Quy trình phỏng vấn
- Cấu hình **vòng phỏng vấn** (Vòng 1: HR, Vòng 2: Chuyên môn,...)
- Lập lịch phỏng vấn, phân công người phỏng vấn
- Ghi nhận **đánh giá & điểm số** từng vòng
- Ghi chú, nhận xét của từng người phỏng vấn
- Kết quả cuối: Đậu / Trượt / Hold

### 13.4. Giao tiếp ứng viên
- Gửi **email mời phỏng vấn** theo mẫu
- Gửi **email thông báo kết quả** (đậu/trượt)
- Gửi **thư mời nhận việc** (Offer Letter)
- Log lịch sử gửi email

### 13.5. Báo cáo tuyển dụng
- Báo cáo **funnel tuyển dụng** (số ứng viên từng bước)
- Báo cáo tỷ lệ chuyển đổi, thời gian tuyển dụng
- Báo cáo theo vị trí, phòng ban, thời gian

---

## 14. Tiếp nhận & Thử việc (Onboarding/Probation)

> **Lưu ý:** Module này sẽ được phát triển sau. Chưa nằm trong phạm vi triển khai hiện tại.

### 14.1. Tiếp nhận nhân viên mới
- Hồ sơ tiếp nhận: chuyển thông tin từ ứng viên sang nhân viên
- **Checklist onboarding** theo phòng ban (tài khoản, thiết bị, đào tạo nội quy,...)
- Theo dõi tiến độ hoàn thành checklist
- Gán người phụ trách hướng dẫn (Buddy)

### 14.2. Quản lý thử việc
- **Hợp đồng thử việc**: thời hạn, mức lương thử việc
- Theo dõi thời gian thử việc, cảnh báo sắp kết thúc
- **Đánh giá kết quả thử việc**: tiêu chí, điểm số, nhận xét
- Kết quả: Đạt (chuyển chính thức) / Không đạt (thôi việc) / Gia hạn

---

## 15. Yêu cầu Phi chức năng

### 15.1. Bảo mật
- Xác thực: username/password, hỗ trợ SSO (OIDC/SAML)
- Mã hóa dữ liệu nhạy cảm (CCCD, tài khoản ngân hàng, MST)
- **Audit log** toàn bộ thao tác: ai, làm gì, lúc nào, dữ liệu trước/sau
- Session timeout, chính sách mật khẩu mạnh

### 15.2. Hiệu năng
- Thời gian phản hồi API < 800ms với dữ liệu 100.000 bản ghi
- Export file lớn (5.000 dòng) hoàn thành < 60 giây (xử lý background queue)
- Hỗ trợ đồng thời tối thiểu 200 người dùng

### 15.3. Giao diện
- **Web Responsive** (Desktop, Tablet)
- Ngôn ngữ: **Tiếng Việt** toàn bộ
- Tìm kiếm đa tiêu chí, lọc nhanh
- Thông báo realtime (Toast notification)
- Hiển thị trực quan với biểu đồ, dashboard

### 15.4. Lưu trữ file

- Toàn bộ file đính kèm (hồ sơ nhân sự, hợp đồng, tài liệu vị trí...) lưu trên **MinIO** (S3-compatible object storage, tự host)
- Download file proxy qua FastAPI — không expose trực tiếp URL MinIO ra ngoài
- Bucket tách biệt theo môi trường (`hrms-attachments-dev`, `hrms-attachments-prod`)
- Sao lưu bucket MinIO định kỳ (tương tự DB backup)

### 15.5. Vận hành
- Môi trường: DEV / STAGING / PRODUCTION
- Sao lưu dữ liệu hàng ngày (PostgreSQL + MinIO), lưu trữ tối thiểu 90 ngày
- CI/CD pipeline
- Giám sát lỗi (Error monitoring)
- SLA: khả dụng 99.5%

---

## Lộ trình Triển khai (Đề xuất)

| Phase | Nội dung | Ưu tiên |
|---|---|---|
| **Phase 1 (MVP)** | Cơ cấu tổ chức, Danh mục, Hồ sơ nhân sự, Hợp đồng, BHXH, Lương BHXH | Cao |
| **Phase 2** | Nghỉ phép, Khen thưởng/Kỷ luật, Đào tạo, Báo cáo cơ bản | Cao |
| **Phase 3** | Đánh giá KPI, Dashboard nâng cao, Tự động hóa email, API tích hợp | Trung bình |
| **Phase 4** | Tuyển dụng (ATS), Tiếp nhận & Thử việc, Import/Export nâng cao | Sẽ làm sau |

---

*Tài liệu này mô tả phạm vi tính năng của hệ thống HRMS. Mọi thay đổi phạm vi cần được xác nhận bằng văn bản.*
