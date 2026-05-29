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
> **Căn cứ pháp lý:** Bộ luật Lao động 2019 (Luật 45/2019/QH14), Luật Việc làm 2013, Nghị định 145/2020/NĐ-CP, Thông tư 23/2014/TT-BLĐTBXH.  
> **Lưu ý kiến trúc:** Module ATS sử dụng bảng `candidates` **riêng biệt** với `employees`. Ứng viên chỉ được chuyển sang `employees` sau khi có Quyết định tuyển dụng (xem 13.5). Hồ sơ ứng viên (`học vấn`, `kinh nghiệm`, `kỹ năng`) lưu trong bảng riêng song song với cấu trúc tương ứng bên nhân viên; khi chuyển đổi mới migrate sang `employee_education_histories`, `employee_work_experiences`, `employee_skills`.

### 13.1. Kế hoạch & Yêu cầu tuyển dụng

#### Kế hoạch nhân sự (Headcount Planning)
- Lập **kế hoạch nhân sự theo năm** theo từng phòng ban: số lượng hiện tại, nhu cầu bổ sung, lý do
- Theo dõi **tỷ lệ thực hiện** kế hoạch tuyển dụng theo kỳ
- Liên kết cơ cấu tổ chức: tham chiếu trực tiếp `departments`, `job_titles`, `job_positions` đã có

#### Yêu cầu tuyển dụng (Job Requisition — JR)
- Tạo JR **độc lập**, không bắt buộc phải có kế hoạch nhân sự trước — đáp ứng cả tuyển theo kế hoạch lẫn phát sinh đột xuất (thay thế nghỉ việc, mở rộng giữa năm, dự án mới,...)
- Thông tin JR: liên kết `job_position_id` (vị trí công việc đã có trong hệ thống), phòng ban, số lượng cần tuyển, lý do tuyển (mới/thay thế/bổ sung), thời hạn cần người, mức lương dự kiến
- **Nội dung JD**: mặc định kế thừa `description` và `requirements` từ `JobPosition` được chọn; cho phép ghi đè (override) nếu JR này có yêu cầu khác tiêu chuẩn vị trí
- **Liên kết kế hoạch nhân sự** (tuỳ chọn — không bắt buộc): nếu công ty có lập kế hoạch thì gắn vào để theo dõi thực hiện; nếu không có kế hoạch vẫn tạo JR bình thường
- Trạng thái JR: **Nháp → Chờ duyệt → Đã duyệt → Đang tuyển → Hoàn thành / Hủy**
- **Phê duyệt JR** theo phân quyền: Trưởng bộ phận → HR Manager → (Ban giám đốc nếu cần)
- Lịch sử thay đổi, ghi chú nội bộ trên từng JR

#### Ngân sách tuyển dụng
- Dự toán chi phí tuyển dụng cho từng JR: phí đăng tin, phí headhunter, chi phí phỏng vấn,...
- Theo dõi chi phí thực tế vs. dự toán
- Báo cáo **chi phí tuyển dụng mỗi vị trí** (Cost per Hire)

---

### 13.2. Đăng tin tuyển dụng (Job Posting)

#### Quản lý tin đăng
- Tạo **tin tuyển dụng** từ JR đã duyệt: tên vị trí, mô tả, yêu cầu, quyền lợi, địa điểm làm việc, thời hạn nộp hồ sơ
- Phân loại: **Tuyển nội bộ** (ưu tiên xét dịch chuyển nội bộ trước) / **Tuyển bên ngoài**
- Trạng thái tin: Nháp / Đang đăng / Đã đóng / Hết hạn
- Tự động đóng tin khi đủ số lượng hoặc hết thời hạn

#### Đa kênh tuyển dụng
- Quản lý danh sách **kênh tuyển dụng**: website công ty, LinkedIn, TopCV, VietnamWorks, VietnamJobs, headhunter, giới thiệu nội bộ (referral),...
- Ghi nhận **nguồn ứng viên** (source) để phân tích hiệu quả kênh
- *(Tính năng nâng cao — tùy chọn)* Tích hợp form nộp hồ sơ online (Career Page) nhúng vào website công ty

#### Tuân thủ pháp lý khi đăng tin
- *(Điều 10, 11 Luật Việc làm 2013; Điều 8 BLLĐ 2019)* Tin tuyển dụng **không được** chứa nội dung phân biệt đối xử về giới tính, độ tuổi, tình trạng hôn nhân, dân tộc, tôn giáo, khuyết tật
- Cảnh báo khi tin đăng chứa ngôn ngữ có dấu hiệu vi phạm nguyên tắc bình đẳng
- Lưu log toàn bộ lần đăng/sửa/đóng tin theo yêu cầu lưu trữ hồ sơ

---

### 13.3. Quản lý hồ sơ ứng viên (Candidate Management)

#### Hồ sơ ứng viên
- **Bảng `candidates` độc lập** — không phải `employees`; chỉ migrate sang nhân viên khi có quyết định tuyển dụng
- Thông tin cá nhân: họ tên, ngày sinh, giới tính, quốc tịch, CCCD/hộ chiếu, địa chỉ, SĐT, email
- Học vấn: trường, chuyên ngành, trình độ, năm tốt nghiệp
- Kinh nghiệm làm việc: công ty, vị trí, thời gian, mô tả
- Kỹ năng, chứng chỉ, ngoại ngữ
- Upload và lưu trữ file đính kèm: **CV (PDF/Word), bằng cấp, CCCD scan, ảnh thẻ** — lưu trên MinIO theo cùng cơ chế file đính kèm hiện có
- Ghi chú nội bộ (không hiển thị với ứng viên)
- **Tái sử dụng hồ sơ**: ứng viên cũ có thể được gắn vào JR mới (talent pool)

#### Tiếp nhận hồ sơ
- Nhập thủ công bởi HR (luồng chính)
- Import hàng loạt từ **file Excel theo mẫu**
- *(Tính năng nâng cao — tùy chọn)* Form online (Career Page): ứng viên tự điền, đính kèm CV
- **Lưu ý**: Tự động parse nội dung CV từ PDF/Word đòi hỏi NLP/AI — nằm ngoài phạm vi triển khai cơ bản; file CV chỉ được lưu đính kèm, HR tự đọc và điền thông tin

#### Ngân hàng ứng viên (Talent Pool)
- Lưu trữ hồ sơ ứng viên **chưa tuyển nhưng tiềm năng** cho các đợt tuyển dụng sau
- Phân loại ứng viên theo kỹ năng, kinh nghiệm, vị trí phù hợp
- Tìm kiếm và lọc đa tiêu chí trên toàn bộ talent pool
- Cảnh báo khi hồ sơ ứng viên **chưa được xử lý** quá số ngày quy định

---

### 13.4. Quy trình tuyển chọn (Recruitment Pipeline)

#### Cấu hình pipeline
- HR cấu hình các **bước tuyển chọn** linh hoạt cho từng vị trí/JR:
  - Sàng lọc hồ sơ → Test năng lực → Phỏng vấn HR → Phỏng vấn chuyên môn → Phỏng vấn BGĐ → Offer
- Mỗi bước có thể bật/tắt tùy vị trí
- Bảng **Kanban pipeline**: xem và cập nhật trạng thái ứng viên theo từng bước

#### Sàng lọc hồ sơ
- Đánh dấu hồ sơ: **Phù hợp / Không phù hợp / Cần xem lại**
- Ghi lý do loại hồ sơ (lưu lại để báo cáo và tránh phân biệt đối xử)
- Gửi email thông báo **không phù hợp** tự động theo mẫu

#### Bài kiểm tra / Đánh giá năng lực
- Ghi nhận kết quả **bài test chuyên môn, tính cách** (nhập tay hoặc upload file kết quả)
- Liên kết kết quả test với hồ sơ ứng viên
- Cấu hình điểm đạt/không đạt cho từng bài test

#### Quản lý phỏng vấn
- **Lập lịch phỏng vấn**: ngày giờ, hình thức (trực tiếp/online), địa điểm/link
- Phân công **người phỏng vấn** (interviewer panel) — người phỏng vấn tham chiếu `users` hiện có trong hệ thống
- Gửi **email xác nhận lịch phỏng vấn** cho ứng viên và người phỏng vấn tự động
- Ghi nhận **kết quả & điểm số** từng vòng theo bộ tiêu chí: thái độ, kỹ năng chuyên môn, kỹ năng mềm, ngoại ngữ, lương kỳ vọng,...
- Nhận xét chi tiết của từng người phỏng vấn (private notes)
- Kết quả vòng: **Đậu / Trượt / Đưa vào Hold**
- Lịch sử tất cả vòng phỏng vấn theo từng ứng viên

#### Bộ câu hỏi phỏng vấn (Interview Kit)
- Thư viện câu hỏi phỏng vấn theo vị trí/nhóm kỹ năng
- Gắn bộ câu hỏi gợi ý vào từng vòng phỏng vấn
- Scorecard tiêu chuẩn hóa để so sánh khách quan giữa các ứng viên

---

### 13.5. Offer & Quyết định tuyển dụng

#### Thư mời nhận việc (Offer Letter)
- Soạn **Offer Letter** từ mẫu: vị trí, phòng ban, ngày bắt đầu dự kiến, mức lương, phúc lợi
- **Tái dụng cơ chế template hiện có** (`contract_templates` + `contract_generate_service`): Offer Letter là một loại document mới trong hệ thống template Word/PDF hiện hành — không cần xây dựng từ đầu
- Gửi email offer kèm file PDF đính kèm
- Theo dõi trạng thái offer: **Đã gửi / Chờ phản hồi / Chấp nhận / Từ chối / Đàm phán lại**
- Ghi nhận lý do ứng viên từ chối offer (để phân tích cải thiện)
- Lưu lịch sử offer (kể cả offer bị từ chối) để kiểm toán

#### Quyết định tuyển dụng & Chuyển đổi sang nhân viên
- Sau khi ứng viên chấp nhận offer → tạo **Quyết định tuyển dụng** chính thức:
  - Số quyết định, ngày ký, vị trí, phòng ban, ngày bắt đầu làm việc, mức lương thử việc, thời gian thử việc
- *(Điều 24 BLLĐ 2019)* Cảnh báo nếu thời gian thử việc **vượt giới hạn pháp lý**:
  - ≤ 180 ngày cho chức danh quản lý doanh nghiệp
  - ≤ 60 ngày cho công việc yêu cầu trình độ CĐ trở lên
  - ≤ 30 ngày cho công việc yêu cầu TC/CNKT/nhân viên chuyên môn
  - ≤ 6 ngày cho các trường hợp còn lại
- *(Điều 26 BLLĐ 2019)* Cảnh báo nếu lương thử việc nhập vào **thấp hơn 85%** mức lương chính thức
- Upload file quyết định tuyển dụng scan/PDF
- **Chuyển đổi ứng viên → nhân viên**: tự động tạo bản ghi `Employee` + `EmployeeJobRecord` (trạng thái `probation`, điền `probation_start_date`, `probation_end_date`) + migrate học vấn/kinh nghiệm/kỹ năng từ `candidates` sang các bảng tương ứng của nhân viên — Module 14 tiếp nhận từ đây

---

### 13.6. Hồ sơ pháp lý & Tuân thủ

#### Checklist hồ sơ nhân viên mới *(theo quy định VN)*
- Danh sách giấy tờ cần thu thập khi tiếp nhận:
  - CCCD/CMND (bản sao công chứng)
  - Sổ hộ khẩu / KT3 (bản sao)
  - Giấy khai sinh (bản sao)
  - Bằng cấp, chứng chỉ (bản sao công chứng)
  - Lý lịch tư pháp số 1 *(đối với vị trí nhạy cảm)*
  - Giấy chứng nhận sức khỏe *(Điều 35, Nghị định 145/2020/NĐ-CP)*
  - Mã số thuế cá nhân
  - Thông tin tài khoản ngân hàng
  - Ảnh thẻ 3×4
  - Sổ BHXH (nếu đã tham gia trước)
  - Giấy phép lao động *(đối với người nước ngoài)*
- Theo dõi trạng thái từng giấy tờ: **Chưa nộp / Đã nộp / Hết hạn**
- File scan giấy tờ lưu trên MinIO theo cùng cơ chế `employee_attachments` hiện có
- Cảnh báo giấy tờ còn thiếu hoặc sắp hết hạn

#### Đăng ký lao động với cơ quan Nhà nước
- *(Thông tư 23/2014/TT-BLĐTBXH)* Nhắc nhở HR **báo cáo biến động lao động** định kỳ (quý/năm) lên Sở LĐTBXH
- Xuất danh sách lao động mới theo mẫu biểu báo cáo Nhà nước
- *(Luật Việc làm 2013, Điều 16)* Cảnh báo khi cần đăng ký nhu cầu tuyển dụng với **Trung tâm Dịch vụ Việc làm** (đối với doanh nghiệp có nghĩa vụ thông báo)

---

### 13.7. Giao tiếp ứng viên

- Thư viện **mẫu email** theo từng bước: xác nhận nhận hồ sơ, mời phỏng vấn, thông báo trượt, gửi offer, xác nhận ngày bắt đầu
- Biến merge field: tên ứng viên, vị trí, ngày giờ phỏng vấn, địa điểm, tên người liên hệ HR
- Gửi email **tự động** khi ứng viên chuyển trạng thái (cấu hình bật/tắt từng loại) — tái dụng `reminder_service` và log email hiện có
- Gửi email **thủ công** bất kỳ lúc nào với nội dung tùy chỉnh
- **Log lịch sử giao tiếp** đầy đủ: ngày giờ, loại email, nội dung, trạng thái gửi (thành công/lỗi)

---

### 13.8. Báo cáo & Phân tích tuyển dụng

- **Funnel tuyển dụng**: số ứng viên từng bước → tỷ lệ chuyển đổi giữa các bước
- **Thời gian tuyển dụng** (Time to Hire / Time to Fill): từ mở JR đến khi ứng viên nhận việc
- **Chi phí mỗi lần tuyển** (Cost per Hire) theo vị trí, phòng ban
- **Tỷ lệ chấp nhận offer** (Offer Acceptance Rate)
- **Hiệu quả kênh tuyển dụng**: số ứng viên, số tuyển thành công theo từng nguồn
- **Tỷ lệ vượt qua thử việc** (Probation Pass Rate) liên kết ngược từ Module 14
- Báo cáo lọc theo: vị trí, phòng ban, khoảng thời gian, kênh tuyển dụng
- Xuất tất cả báo cáo ra Excel/PDF

---

## 14. Tiếp nhận & Thử việc (Onboarding/Probation)

> **Lưu ý:** Module này sẽ được phát triển sau. Chưa nằm trong phạm vi triển khai hiện tại.  
> **Căn cứ pháp lý:** Điều 24–27 BLLĐ 2019; Nghị định 145/2020/NĐ-CP Điều 35 (khám sức khỏe); Thông tư 23/2014/TT-BLĐTBXH (báo cáo lao động).  
> **Lưu ý kiến trúc:** Module 14 tiếp nhận nhân viên **đã được tạo** từ Module 13 (bản ghi `Employee` + `EmployeeJobRecord` trạng thái `probation` đã tồn tại). Phần lớn dữ liệu thử việc (ngày thử việc, hợp đồng, nhắc nhở) tái dụng hạ tầng hiện có; phần cần xây mới chủ yếu là **checklist onboarding** và **form đánh giá thử việc**.

### 14.1. Tiếp nhận nhân viên mới (Onboarding)

#### Tiếp nhận từ Module 13
- Nhân viên mới được tạo tự động từ Quyết định tuyển dụng (Module 13.5): `Employee` status=`probation`, `EmployeeJobRecord.probation_start_date` và `probation_end_date` đã điền
- HR kiểm tra và bổ sung thông tin còn thiếu trong hồ sơ nhân viên (địa chỉ, tài khoản ngân hàng, MST,...)

#### Checklist onboarding *(tính năng xây mới)*
- Cấu hình **danh sách công việc cần làm** khi tiếp nhận, phân theo nhóm:
  - *Hành chính:* Thu thập hồ sơ giấy tờ, cấp thẻ nhân viên, đăng ký BHXH, mở tài khoản ngân hàng
  - *IT:* Cấp tài khoản email, phần mềm, thiết bị làm việc
  - *Đào tạo hội nhập:* Giới thiệu nội quy, an toàn lao động, văn hóa công ty *(Điều 18 BLLĐ 2019 — nghĩa vụ đào tạo ATLĐ)*
  - *Chuyên môn:* Đào tạo nghiệp vụ, bàn giao công việc
- Phân công người phụ trách (HR, IT, Trưởng bộ phận) cho từng hạng mục — tham chiếu `users` hiện có
- Giao **Buddy** (người hướng dẫn trong bộ phận)
- Theo dõi tiến độ hoàn thành checklist theo %
- Cảnh báo checklist trễ hạn — tích hợp `reminder_service` hiện có

---

### 14.2. Quản lý thử việc (Probation)

#### Hợp đồng thử việc
- Tạo **hợp đồng thử việc** *(Điều 24 BLLĐ 2019)* — lưu vào bảng `employee_contracts` hiện có với loại hợp đồng thử việc; sinh từ `contract_templates` hiện có
- Hệ thống kiểm tra và **cảnh báo vi phạm pháp lý**:
  - Thời hạn thử việc vượt giới hạn theo từng nhóm chức danh (180/60/30/6 ngày)
  - Lương thử việc < 85% lương chính thức *(Điều 26 BLLĐ 2019)*
  - Thử việc quá 1 lần với cùng một công việc *(Điều 24 BLLĐ 2019)*

#### Theo dõi & Đánh giá thử việc
- Countdown ngày còn lại đọc từ `EmployeeJobRecord.probation_end_date` hiện có; cảnh báo **trước 15 ngày và 7 ngày** qua `reminder_service` hiện có
- **Form đánh giá thử việc** *(tính năng xây mới)*: bộ tiêu chí theo vị trí (thái độ, năng lực chuyên môn, hội nhập văn hóa, KPI thử việc), thang điểm tùy chỉnh, nhận xét của Trưởng bộ phận và HR
- Lưu toàn bộ lịch sử đánh giá trong thử việc vào hồ sơ nhân viên

#### Kết thúc thử việc
- *(Điều 27 BLLĐ 2019)* Phải thông báo kết quả trước khi hết thời hạn; `reminder_service` nhắc HR đúng thời điểm
- Kết quả thử việc:
  - **Đạt — Chuyển chính thức**: cập nhật `Employee.status` → `official`, ghi `EmployeeJobRecord.official_date`; tạo hợp đồng lao động chính thức trong `employee_contracts`
  - **Không đạt — Thôi việc**: cập nhật `Employee.status` → `resigned`; ghi nhận lý do; sinh Thông báo chấm dứt thử việc từ template *(Điều 27 BLLĐ — không cần bồi thường nếu thông báo trước ít nhất 3 ngày)*
  - **Gia hạn thử việc**: cập nhật `EmployeeJobRecord.probation_end_date`; kiểm tra tổng thời gian không vượt giới hạn pháp lý
- Sinh văn bản kết quả thử việc từ template, lưu file

---

### 14.3. Báo cáo Onboarding & Thử việc

- Danh sách nhân viên đang trong thời gian thử việc, số ngày còn lại
- Tỷ lệ hoàn thành checklist onboarding theo phòng ban
- **Tỷ lệ vượt qua thử việc** (Probation Pass Rate) theo phòng ban, vị trí, kỳ
- Thống kê lý do không qua thử việc
- Thời gian trung bình hoàn thành checklist onboarding
- Xuất Excel/PDF

---

## 15. Yêu cầu Phi chức năng

### 15.1. Bảo mật
- Xác thực: username/password
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
