# Lỗi đã biết, chưa sửa

Chỉ ghi lỗi **đã có bằng chứng** (quan sát thật hoặc đọc mã), kèm điều **chưa kiểm**. Khi sửa, theo `docs/verification_policy.md`: lỗi giao diện phải kiểm bằng trình duyệt thật, và thêm kiểm tra ở đúng tầng nơi lỗi xuất hiện.

| Mã | Lỗi | Trạng thái | Phát hiện |
|---|---|---|---|
| LD-001 | Hộp thoại "Xác nhận xóa" vẫn còn sau khi xóa (tab tệp đính kèm, và có thể các màn hình khác) | Chưa sửa | 2026-10-31, production (kế hoạch 15.7) |
| LD-002 | Nút "Tải xuống" ở tab "Tệp đính kèm hồ sơ" không tải được (401) | Chưa sửa | 2026-10-30, dev (kế hoạch 15.7, Slice 2) |
| LD-003 | Tải tệp đính kèm mà tệp không còn trong kho trả về HTTP 200 với thân rỗng thay vì 404 (và 3 lần liền làm kho trả 503 cho mọi người) | **Đã sửa 2026-10-31** (chưa commit; có tác dụng sau khi dựng lại image backend) | 2026-10-31, dev (kế hoạch 15.7, Slice 9) |

LD-001 và LD-002 (chưa sửa) có từ trước và **không liên quan** việc chuyển kho tệp sang Garage. LD-003 là cơ chế của mã tải tệp, không phụ thuộc loại kho (chưa kiểm trên MinIO).

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

---

## LD-003. Tải tệp không còn trong kho trả về 200 và thân rỗng

**Triệu chứng.** Tệp đính kèm có bản ghi trong DB nhưng object không còn trong bucket (ví dụ khôi phục DB mà chưa khôi phục kho tệp, hoặc trỏ `MINIO_BUCKET` sang kho khác). Gọi `GET /api/v1/employees/{id}/attachments/{att}/download` trả **HTTP 200**, header `Content-Disposition` và `Content-Type` đúng, nhưng thân **0 byte**, không có mã lỗi nào cho người dùng.

**Bằng chứng (2026-10-31, dev, kế hoạch 15.7 Slice 9).**
- Đặt `MINIO_BUCKET` sang một bucket rỗng rồi gọi API có token: `curl -D -` cho `HTTP/1.1 200 OK`, `content-disposition: attachment; filename="s9_test.pdf"`, và tệp lưu về `body bytes=0` (`sha256` là của chuỗi rỗng `e3b0c442...`).
- Log backend cùng thời điểm: dòng `http_request` ghi `"status": 200`, rồi `ERROR: Exception in ASGI application` với `minio.error.S3Error: ... code: NoSuchKey ... resource: /s9-empty/employees/1/a45872aa_s9_test.pdf`.
- Đặt lại `MINIO_BUCKET` đúng bucket có tệp: cùng lệnh trả 200 và `sha256` khớp tệp gốc.

**Nguyên nhân (đọc mã, khớp với log).** `backend/app/core/storage.py` hàm `get_object_stream` là **generator**: `_minio_get(object_name)` chỉ chạy khi `StreamingResponse` bắt đầu đọc thân, tức sau khi đã gửi dòng trạng thái 200 và header. `S3Error NoSuchKey` nổ ở thời điểm đó nên không còn đổi được thành 404.

**Phạm vi (đọc mã, chưa gọi từng nơi).** Cùng hàm được dùng ở: `employees.py` (2 nơi: tải và preview), `employee_contracts.py` (2), `rewards.py`, `disciplines.py`, `job_positions.py`, `training.py`, `other_business_catalog.py` (mẫu biểu), `candidate_import_service.py`.

**Chưa kiểm.**
1. Trình duyệt thật hiển thị gì (tệp 0 byte, lỗi mạng, hay tệp hỏng) khi bấm tải.
2. Các nơi khác ngoài tải tệp đính kèm hồ sơ có cùng triệu chứng không.
3. Có xảy ra y hệt trên MinIO cũ không (cơ chế nằm ở mã chứ không ở kho, nhưng chưa chạy thử).

**Hệ quả thứ hai, phát hiện khi sửa (thăm dò trực tiếp trên mã gốc).** `minio_circuit` (`backend/app/core/circuit_breaker.py`) tính **mọi** exception là sự cố, ngưỡng 3 lần liên tiếp, mở 30 giây. `NoSuchKey` cũng bị tính: gọi `get_object_stream` với object thiếu 4 lần cho `S3Error`, `S3Error`, `S3Error` (mạch chuyển sang `open`), rồi `HTTPException 503`. Nghĩa là chỉ cần một bản ghi "mồ côi" (ví dụ sau khôi phục DB mà chưa khôi phục kho tệp) bị bấm tải 3 lần là **mọi** tải và tải lên tệp của **mọi người dùng** trả 503 trong 30 giây. `get_object_bytes` (dùng cho mẫu DOCX) có cùng đường đi.

**Cách đã sửa (2026-10-31, `backend/app/core/storage.py`).**
- `_minio_get` trả `None` khi `NoSuchKey` (kho vẫn trả lời bình thường nên không tính vào mạch ngắt); các lỗi kho khác (ví dụ `AccessDenied`) vẫn tính.
- Hàm mới `_open_object`: `None` thành HTTP 404 ("Không tìm thấy tệp trong kho lưu trữ"), mạch ngắt mở thành 503.
- `get_object_stream` không còn là generator: nó **mở object ngay khi được gọi** rồi mới trả generator stream, nên lỗi nổ trước khi `StreamingResponse` gửi dòng 200. Toàn bộ 11 nơi gọi (`StreamingResponse(get_object_stream(...))`) tự được sửa, không đổi nơi gọi nào. `get_object_bytes` dùng `_open_object`; cả hai nơi gọi nó bắt `Exception` rồi quay về đường dẫn cục bộ nên hành vi giữ nguyên.
- Đánh đổi: việc mở object (chỉ nhận header, không đọc thân) nay chạy trong coroutine của endpoint thay vì threadpool; cùng kiểu với `_minio_put` hiện có ở các hàm `save_*` (cũng gọi đồng bộ trong `async def`).

**Đã kiểm.**
- Test mới, **chạy đỏ trên mã gốc rồi xanh sau khi sửa**: `backend/tests/test_storage_missing_object.py` (5 test, máy chủ S3 giả, không cần DB hay Garage: lỗi nổ lúc gọi chứ không lúc stream; tệp có thật vẫn stream đúng; `get_object_bytes` thiếu object là 404; 4 lần thiếu không mở mạch ngắt; lỗi kho thật `AccessDenied` vẫn mở mạch ngắt thành 503) và `test_employee_attachments.py::test_download_attachment_object_missing_returns_404` (tầng API, Garage thật).
- Chạy lại kịch bản gốc trên backend thật (uvicorn, bản sao DB, Garage thật): bucket rỗng nay trả `HTTP/1.1 404` kèm `{"detail":"Không tìm thấy tệp trong kho lưu trữ"}` (trước: 200, 0 byte); lặp 5 lần vẫn 404 và một tệp còn trong kho tải được ngay sau đó (`sha256` khớp; trên mã gốc lần thứ 4 là 503); log backend 0 dòng `Exception in ASGI application`.
- Không có hồi quy trong các module có đường tải tệp: 15 tệp test chạy trên mã gốc và mã sửa cho **đúng cùng tập test thất bại** (20 test đỏ sẵn trên bản sao dữ liệu thật này, ví dụ các test tính lương hợp đồng và `test_viewer_can_list_and_download`; không liên quan thay đổi này, chưa điều tra nguyên nhân).

**Chưa kiểm.** Giao diện thật hiển thị gì khi bấm tải một tệp thiếu (mới kiểm API: nay là 404 JSON; các view tải bằng `blob` có thể hiện thông báo lỗi chung); các nơi gọi khác ngoài tải hồ sơ nhân viên chỉ kiểm qua tập test hiện có, không gọi từng endpoint bằng tay; production vẫn chạy image cũ cho tới khi dựng lại image backend và tạo lại `backend`, `celery_worker`, `celery_beat`.
