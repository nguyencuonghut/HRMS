# Lỗi đã biết, chưa sửa

Chỉ ghi lỗi **đã có bằng chứng** (quan sát thật hoặc đọc mã), kèm điều **chưa kiểm**. Khi sửa, theo `docs/verification_policy.md`: lỗi giao diện phải kiểm bằng trình duyệt thật, và thêm kiểm tra ở đúng tầng nơi lỗi xuất hiện.

| Mã | Lỗi | Trạng thái | Phát hiện |
|---|---|---|---|
| LD-001 | Hộp thoại "Xác nhận xóa" vẫn còn sau khi xóa (tab tệp đính kèm, và có thể các màn hình khác) | Chưa sửa | 2026-10-31, production (kế hoạch 15.7) |
| LD-002 | Nút "Tải xuống" ở tab "Tệp đính kèm hồ sơ" không tải được (401) | Chưa sửa | 2026-10-30, dev (kế hoạch 15.7, Slice 2) |

Cả hai có từ trước và **không liên quan** việc chuyển kho tệp sang Garage.

---

## LD-001. Hộp thoại "Xác nhận xóa" vẫn còn sau khi xóa

**Triệu chứng.** Hồ sơ nhân viên, tab "Tệp đính kèm hồ sơ": bấm biểu tượng thùng rác, hộp thoại "Xác nhận xóa" hiện ra, bấm "Xóa". Tệp biến mất khỏi danh sách nhưng hộp thoại vẫn hiện. Chủ hệ thống báo trên production ngày 2026-10-31 (có ảnh chụp).

**Bằng chứng.**
- Khi chạy Playwright (2026-10-30), selector `.p-confirmdialog .p-button-danger:visible` khớp **2** phần tử: hai hộp thoại cùng hiện cho một yêu cầu xóa. Bấm vào nút của hộp thoại đầu tiên làm test hết thời gian chờ, bấm vào hộp cuối thì qua.
- Mã nguồn (đọc, chưa gỡ lỗi lúc chạy): `frontend/src/components/layout/AppLayout.vue:22` mount một `<ConfirmDialog />` chung; `frontend/src/views/employees/AttachmentsTab.vue:142` mount thêm một `<ConfirmDialog />`. Hàm `confirmDelete` trong tab đó gọi `confirm.require({...})` **không chỉ định `group`**, nên cả hai hộp thoại cùng lắng nghe.

**Nguyên nhân (suy ra từ hai bằng chứng trên).** Hai `ConfirmDialog` không `group` cùng hiện cho một lần `confirm.require`. Bấm "Xóa" ở một hộp thì gọi `accept` (tệp bị xóa) và chỉ đóng hộp đó; hộp kia vẫn mở.

**Có thể còn ở các màn hình khác.** Các nơi sau cũng mount thêm một `ConfirmDialog` không `group` (chưa quan sát triệu chứng ở đây, chỉ thấy cùng cấu trúc trong mã):
`frontend/src/components/FileAttachmentList.vue:73`, `views/catalog/BhytClinicView.vue:111`, `views/leaves/LeaveListView.vue:308`, `views/leaves/LeaveEntitlementView.vue:329`, `views/rewards/components/DisciplineListTab.vue:347`, `views/rewards/components/RewardListTab.vue:338`.
`views/employees/ContractTab.vue:233` tránh được vì dùng `group="employee-contracts"`.

**Chưa kiểm.**
1. Tất cả các view trên có nằm trong `AppLayout` không (quyết định hướng sửa).
2. Bấm "Xóa" ở hộp thoại còn lại có chạy `accept` lần thứ hai không (xóa lần hai, toast lỗi "Không xóa được tài liệu"?).
3. Sáu màn hình còn lại có thật sự lỗi không (chỉ mới quan sát ở tab tệp đính kèm).

**Hướng sửa đề xuất.** Bỏ `<ConfirmDialog />` thừa ở những view nằm trong `AppLayout` (giữ một cái chung), hoặc gán `group` riêng cho từng view như `ContractTab`. Chọn sau khi có kết quả câu 1.

**Cách kiểm chứng khi sửa.** Trình duyệt thật, ở **từng** màn hình bị ảnh hưởng: bấm xóa, xác nhận, rồi khẳng định chỉ có một hộp thoại và nó đóng lại; đồng thời trả lời các câu 1-3 ở mục "Chưa kiểm". Thêm hoặc chỉnh test e2e (`frontend/tests/e2e`) để khẳng định số hộp thoại hiển thị sau khi xóa bằng 0.

---

## LD-002. Nút "Tải xuống" ở tab "Tệp đính kèm hồ sơ" không tải được (401)

**Triệu chứng.** Bấm biểu tượng tải xuống ở một tệp đính kèm: trình duyệt hủy tải và không nhận được tệp (Playwright: `download.failure()` trả `canceled`). Nút "Xem file" cùng tab vẫn chạy.

**Bằng chứng.** Kiểm bằng `curl` ngày 2026-10-30 trên môi trường dev, cùng một tệp:
- Có header `Authorization: Bearer <token>`: HTTP 200, đúng tên tệp trong `Content-Disposition`, đúng số byte và `sha256`.
- Không có token: HTTP 401.

**Nguyên nhân (đọc mã).** Hàm `download(att)` trong `frontend/src/views/employees/AttachmentsTab.vue` (khoảng dòng 288) tạo một thẻ `<a href="/api/v1/employees/{id}/attachments/{attId}/download" download>` thuần rồi `click()`. Trình duyệt điều hướng tới URL đó **không gửi** header `Authorization` (token nằm trong bộ nhớ của ứng dụng, không phải cookie), nên backend trả 401 trước khi đọc tệp. Nút xem hoạt động vì dùng `preview-url` (đường dẫn có chữ ký).

**Không liên quan kho tệp.** Lỗi xảy ra ở lớp xác thực, trước khi chạm kho tệp. Chưa kiểm xem nó có xảy ra trên MinIO cũ hay không.

**Chỗ có thể tương tự (chưa rõ).** `frontend/src/services/recruitmentService.ts:434` có `getAttachmentDownloadUrl` trả URL thuần cùng kiểu. Tìm trong `frontend/src` không thấy nơi gọi nó, nên chưa biết có lỗi ở đó hay không.

**Hướng sửa đề xuất.** Tải qua `api.get(url, { responseType: 'blob' })` (axios gắn token), rồi tạo URL tạm từ blob và `click()`, lấy tên tệp từ `Content-Disposition`. Mẫu đã dùng đúng ở nhiều nơi: `employeeService.ts` (tải tệp checklist hồ sơ, khoảng dòng 877), `rewardService.ts`, `disciplineService.ts`, `contractService.ts`, `trainingService.ts`.

**Cách kiểm chứng khi sửa.** Trình duyệt thật: bấm tải xuống rồi nhận được tệp, tên đúng (thử tên có tiếng Việt, khoảng trắng, `#`, `%`, `+`), `sha256` khớp tệp gốc, thử cả tệp lớn hơn 5 MiB. Thêm test e2e dùng sự kiện `download` của trình duyệt và đối chiếu `sha256` (đoạn thử đã viết ở Slice 2 dùng đúng cách này).
