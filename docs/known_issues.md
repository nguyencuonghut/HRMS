# Lỗi đã biết, chưa sửa

Chỉ ghi lỗi **đã có bằng chứng** (quan sát thật hoặc đọc mã), kèm điều **chưa kiểm**. Khi sửa, theo `docs/verification_policy.md`: lỗi giao diện phải kiểm bằng trình duyệt thật, và thêm kiểm tra ở đúng tầng nơi lỗi xuất hiện.

| Mã | Lỗi | Trạng thái | Phát hiện |
|---|---|---|---|
| LD-001 | Hộp thoại "Xác nhận xóa" vẫn còn sau khi xóa (7 màn hình mount thêm `ConfirmDialog`; riêng `/rewards` hiện 3 hộp thoại) | **Đã sửa 2026-10-31** (đã dựng lại image frontend; chủ hệ thống xác nhận trên production cùng ngày) | 2026-10-31, production (kế hoạch 15.7) |
| LD-002 | Nút "Tải xuống" ở tab "Tệp đính kèm hồ sơ" không tải được (401) | **Đã sửa 2026-10-31** (đã dựng lại image frontend; chủ hệ thống xác nhận trên production cùng ngày) | 2026-10-30, dev (kế hoạch 15.7, Slice 2) |
| LD-003 | Tải tệp đính kèm mà tệp không còn trong kho trả về HTTP 200 với thân rỗng thay vì 404 (và 3 lần liền làm kho trả 503 cho mọi người) | **Đã sửa 2026-10-31** (chưa commit; có tác dụng sau khi dựng lại image backend) | 2026-10-31, dev (kế hoạch 15.7, Slice 9) |
| LD-004 | Backup Console cho đặt "Giờ chạy hằng ngày" riêng cho kho tệp nhưng lịch tự động chỉ đọc giờ của dòng cơ sở dữ liệu | **Đã sửa 2026-10-31** (có tác dụng sau khi dựng lại image frontend) (chỉ giao diện: hành vi của bộ điều phối không đổi) | 2026-10-31, production (kế hoạch 15.7, Slice 9) |
| LD-005 | Trang hồ sơ nhân viên thỉnh thoảng sập ("Cannot read properties of null (reading 'scrollTop')") khi bấm tab lúc trang còn đang tải | Chưa sửa | 2026-10-31, dev (kế hoạch 15.7, Slice 9) |
| LD-006 | Hai test e2e của Backup Center đỏ sẵn (locator "Sao lưu đầy đủ" khớp 2 nút) | Chưa sửa | 2026-10-31, dev (kế hoạch 15.7, Slice 9) |
| LD-007 | Chạy toàn bộ `pytest` như job CI (DB sạch, `--sample`) cho 86 test đỏ và 1 lỗi, như nhau với cả MinIO lẫn Garage | Chưa điều tra | 2026-10-31, dev (kế hoạch 15.7, Slice 9) |

LD-001, LD-002 và LD-006 có từ trước và **không liên quan** việc chuyển kho tệp sang Garage. LD-003 là cơ chế của mã tải tệp, không phụ thuộc loại kho (chưa kiểm trên MinIO). LD-004 lộ ra khi đổi lịch sao lưu ở production. LD-005 phát hiện khi chạy test e2e, chưa rõ có phụ thuộc thay đổi nào ở Slice 9 hay không (xem mục).

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

**Cách đã sửa (2026-10-31).** Xóa `<ConfirmDialog />` và `import` thừa khỏi 7 nơi (`AttachmentsTab.vue`, `FileAttachmentList.vue`, `BhytClinicView.vue`, `LeaveListView.vue`, `LeaveEntitlementView.vue`, `DisciplineListTab.vue`, `RewardListTab.vue`); giữ `ConfirmDialog` chung ở `AppLayout.vue` và `ConfirmDialog group="employee-contracts"` của `ContractTab.vue` (duy nhất dùng `group`).

**Trả lời các điều trước đây "chưa kiểm".**
1. Tất cả các view đó nằm trong `AppLayout` (mọi component liên quan đều được dùng bởi các route con của `/`; chỉ `/login` và `/forbidden` nằm ngoài và không dùng chúng), nên `ConfirmDialog` chung luôn có mặt.
2. Hộp thoại còn lại chạy `accept` lần thứ hai hay không: **không kiểm** (không còn ý nghĩa sau khi bỏ bản trùng).
3. Cả **sáu** màn hình còn lại đều bị: gọi `confirm.require` qua dịch vụ toàn cục của PrimeVue rồi đếm hộp thoại hiện ra, trên mã gốc là 2 ở `/leaves`, `/leave-entitlements`, `/catalog/bhyt-clinics` và tab chi tiết vị trí (`FileAttachmentList`), và **3** ở `/rewards` (cả hai tab Khen thưởng và Kỷ luật đều mount một cái, kể cả khi không hiển thị); sau khi sửa là **1** ở cả sáu.

**Đã kiểm.**
- Tái hiện trên mã gốc bằng trình duyệt thật (Playwright): bấm thùng rác hiện 2 hộp thoại; bấm "Xóa" ở hộp trên cùng thì tệp bị xóa (`DELETE ... -> 204`) nhưng còn 1 hộp thoại hiển thị.
- Test e2e hồi quy mới `frontend/tests/e2e/employee-attachments.spec.ts` ("deleting an attachment closes the confirmation dialog"): **đỏ trên mã gốc** (`Expected: 1, Received: 2`) và **xanh sau khi sửa** (chạy 3 lần liên tiếp đều xanh), cộng thăm dò chung ở trên cho sáu màn hình.
- `vue-tsc --noEmit` và `npm run build` đạt.
- **Production (2026-10-31, chủ hệ thống báo sau khi dựng lại image `frontend`):** hộp thoại xóa ở tab tệp đính kèm đóng đúng sau khi xóa; container frontend đang chạy chứa bản mới (`grep` chuỗi mới trong `/usr/share/nginx/html` ra 1 tệp).

**Chưa kiểm.** Chưa bấm thật luồng xóa ở sáu màn hình còn lại (chỉ đếm số hộp thoại cho một `confirm.require`); có thể còn `<Toast />` trùng tương tự ở các view đó (`LeaveListView`, `LeaveEntitlementView`, `DisciplineListTab`, `RewardListTab` có `<Toast />` riêng bên cạnh `<Toast />` của `AppLayout`), chưa quan sát triệu chứng.

---

## LD-002. Nút "Tải xuống" ở tab "Tệp đính kèm hồ sơ" không tải được (401)

**Triệu chứng.** Bấm biểu tượng tải xuống ở một tệp đính kèm: trình duyệt hủy tải và không nhận được tệp (Playwright: `download.failure()` trả `canceled`). Nút "Xem file" cùng tab vẫn chạy.

**Bằng chứng.** Kiểm bằng `curl` ngày 2026-10-30 trên môi trường dev, cùng một tệp:
- Có header `Authorization: Bearer <token>`: HTTP 200, đúng tên tệp trong `Content-Disposition`, đúng số byte và `sha256`.
- Không có token: HTTP 401.

**Nguyên nhân (đọc mã).** Hàm `download(att)` trong `frontend/src/views/employees/AttachmentsTab.vue` (khoảng dòng 288) tạo một thẻ `<a href="/api/v1/employees/{id}/attachments/{attId}/download" download>` thuần rồi `click()`. Trình duyệt điều hướng tới URL đó **không gửi** header `Authorization` (token nằm trong bộ nhớ của ứng dụng, không phải cookie), nên backend trả 401 trước khi đọc tệp. Nút xem hoạt động vì dùng `preview-url` (đường dẫn có chữ ký).

**Không liên quan kho tệp.** Lỗi xảy ra ở lớp xác thực, trước khi chạm kho tệp. Chưa kiểm xem nó có xảy ra trên MinIO cũ hay không.

**Chỗ có thể tương tự (chưa rõ).** `frontend/src/services/recruitmentService.ts:434` có `getAttachmentDownloadUrl` trả URL thuần cùng kiểu. Tìm trong `frontend/src` không thấy nơi gọi nó, nên chưa biết có lỗi ở đó hay không.

**Cách đã sửa (2026-10-31).** `employeeService.downloadAttachment(id, attId, fileName)` dùng hàm `downloadBlob` có sẵn (`api.get(..., { responseType: 'blob' })`, giống `downloadChecklistFile`), và `AttachmentsTab.vue` gọi nó thay cho thẻ `<a href>`; lỗi hiện toast "Không tải được file". `getAttachmentDownloadUrl` của `employeeService` bị xóa (không còn nơi dùng, tránh dùng lại đường sai). `recruitmentService.getAttachmentDownloadUrl` không có nơi gọi nên không đụng.

**Đã kiểm.**
- Tái hiện trên mã gốc bằng trình duyệt thật: tên tệp gợi ý đúng nhưng `download.failure()` trả `canceled`.
- Test e2e hồi quy mới (cùng tệp spec ở LD-001, hai test): tên có khoảng trắng và `#`, `%`, `+` (`Bằng cấp #1 100% + A.pdf`) và tệp 6 MiB, đều khẳng định **tải thành công, đúng tên tệp và `sha256` khớp tệp gốc**. **Đỏ trên mã gốc** (`Received: "canceled"`), **xanh sau khi sửa** (3 lần liên tiếp).
- `vue-tsc --noEmit` và `npm run build` đạt.
- **Production (2026-10-31, chủ hệ thống báo):** tải xuống tệp đính kèm hoạt động bình thường.

**Chưa kiểm.** Thông báo khi tệp không còn trong kho: theo mã thì lỗi blob không đọc được `detail` nên toast hiện thông báo chung "Không tải được file" (chưa chạy); các view tải tệp khác (hợp đồng, khen thưởng, kỷ luật, đào tạo) vốn đã dùng `blob` nên không đụng, không kiểm lại.

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

---

## LD-004. Giờ sao lưu của kho tệp trong Backup Console không có tác dụng

**Triệu chứng.** Màn "Cấu hình sao lưu" có hai dòng (cơ sở dữ liệu và kho tệp ứng dụng), mỗi dòng cho sửa "Giờ chạy hằng ngày". Chủ hệ thống đặt DB 10:30 và kho tệp 10:35 trên production và chờ hai lần chạy riêng.

**Bằng chứng (2026-10-31, production, số liệu do chủ hệ thống dán).**
- Chỉ có **một** bộ mới: `backup_sets` #59, `scheduled_full`, `created_at` 03:30:00 UTC (10:30 giờ Việt Nam), gồm job 125 (`db`) và 126 (`object_storage`). Sau 10:35 không có bộ hay job nào thêm (`backup_sets` mới nhất vẫn là #59, `backup_jobs` mới nhất vẫn là 126).
- Log `celery_worker`: tác vụ `dispatch_scheduled_backup_set_task` chạy mỗi phút; chỉ lúc 03:30:00 có `scheduled_backup_set_created backup_set_id=59`; lúc 03:35:00 chạy xong sau khoảng 0,05 giây mà không tạo gì.
- Mã (`backend/app/services/backup_service.py`, `create_scheduled_backup_set_if_due`): chỉ gọi `_cron_matches(db_config.cron_expression, ...)`, rồi tạo một bộ gồm cả job `db` và `object_storage`; `object_config.cron_expression` chỉ được đọc để kiểm tra `enabled`, không dùng để chọn thời điểm.

**Giao diện (đọc mã `frontend/src/views/admin/BackupCenterView.vue`, chưa mở bằng trình duyệt).** Trường "Giờ chạy hằng ngày" dùng chung cho cả hai dòng và chỉ hiện mô tả giờ chạy (`dailyScheduleDescription`); không tìm thấy chú thích nào nói giờ của kho tệp không quyết định lịch.

**Chưa kiểm.** Giao diện thật hiển thị ra sao; `MINIO_BACKUP_CRON` trong `.env` chỉ là giá trị khởi tạo của dòng cấu hình (đọc mã, chưa thử).

**Cách đã sửa (2026-10-31, chỉ giao diện, chọn phương án "ghi rõ" thay vì đổi bộ điều phối).**
- Bảng "Lịch chạy": dòng kho tệp hiện "Cùng bộ sao lưu với cơ sở dữ liệu" thay cho giờ và mô tả giờ.
- Hộp thoại sửa cấu hình: dòng kho tệp không còn ô nhập giờ, thay bằng "Kho tệp chạy cùng bộ sao lưu với cơ sở dữ liệu, theo giờ của dòng cơ sở dữ liệu."; dòng cơ sở dữ liệu thêm "Áp dụng cho cả bộ sao lưu đầy đủ (cơ sở dữ liệu và kho tệp)."
- Lưu cấu hình kho tệp giữ nguyên `cron_expression` đang lưu (không tính lại từ ô đã ẩn).
- Không đổi `create_scheduled_backup_set_if_due`, API hay DB. Nếu chủ hệ thống muốn lịch riêng cho từng loại thì cần đổi bộ điều phối (chưa làm).

**Đã kiểm.** Ba test e2e mới trong `backup-center.spec.ts` (backend thật): dòng kho tệp không có giờ, hộp thoại kho tệp không có ô giờ và `PUT` giữ đúng `cron_expression` cũ, hộp thoại DB có ghi chú; test dòng kho tệp **đỏ trên giao diện cũ** (`Received: "...03:00Hằng ngày lúc 03:00..."`) và xanh sau khi sửa; đã xem ảnh chụp bảng và hộp thoại; `vue-tsc` và `npm run build` đạt. Một lỗi trong test của chính tôi được sửa trước khi tin kết quả (biểu thức `\b` không khớp vì văn bản các ô liền nhau).

**Chưa kiểm.** `MINIO_BACKUP_CRON` trong `.env` chỉ là giá trị khởi tạo của dòng cấu hình (đọc mã, chưa thử); chưa xem trên production sau khi dựng lại image.

---

## LD-005. Trang hồ sơ nhân viên thỉnh thoảng sập khi bấm tab lúc trang còn đang tải

**Triệu chứng.** Khung lỗi toàn trang "Đã xảy ra lỗi không mong muốn ... Cannot read properties of null (reading 'scrollTop')" thay cho trang `/employees/:id`.

**Bằng chứng (2026-10-31, dev, Playwright 1280x720 "Desktop Chrome", bản sao DB).**
- Gặp 2 lần khi chạy test e2e: nhật ký Playwright ghi tab "Tệp đính kèm hồ sơ" được tìm thấy, `done scrolling`, rồi `element is not visible` và `element was detached from the DOM`; ảnh chụp lúc lỗi là khung lỗi trên.
- Thăm dò có kiểm soát (xóa bộ đếm giới hạn tốc độ trước, phiên hợp lệ): bấm tab **ngay sau** `page.goto` gây khung lỗi **1 trên 40** lần tải với mã đã sửa (ba đợt 8, 16, 16 lần: 1, 0, 0 lần sập) và **0 trên 40** với mã gốc (cùng ba đợt xen kẽ), chưa đủ mẫu để nói có hay không liên quan thay đổi; chờ trang yên 1,2 giây trước khi bấm thì 0 lỗi (6/6 cho cả mã sửa và mã gốc). Tải trang thường không gây lỗi.
- Mã thư viện (đọc `node_modules/primevue/tablist/TabList.vue`): `updateButtonState()` lấy `content` từ `this.$refs` rồi đọc `content.scrollTop`; sẽ ném đúng lỗi này nếu `content` là `null` lúc được gọi (ví dụ từ `ResizeObserver`/`updated` khi danh sách tab vừa đổi). Chưa chứng minh được điểm kích hoạt chính xác.

**Chưa kiểm.** Người dùng thật có gặp không (cần bấm tab trong vài chục mili giây đầu); có xảy ra ở mã gốc với cùng tần suất không; chưa thử sửa. Test e2e hồi quy ở LD-001/002 chờ `networkidle` trước khi bấm tab để tránh điều kiện này.

**Hướng sửa đề xuất.** Chưa chọn; ứng viên là đặt `:key`/`v-if` ổn định cho các `Tab` điều kiện (`showEmployeeSubTabs`) hoặc bọc lỗi của `TabList` sau khi xác định được điểm kích hoạt.

---

## LD-006. Hai test e2e của Backup Center đỏ sẵn

**Triệu chứng.** `frontend/tests/e2e/backup-center.spec.ts`: "full backup button updates latest task status immediately" và "admin can queue a full backup set and restore from that set" thất bại với `strict mode violation: getByRole('button', { name: 'Sao lưu đầy đủ' }) resolved to 2 elements`; do chế độ `serial`, mọi test sau chúng bị bỏ qua.

**Bằng chứng (2026-10-31).** Cùng lỗi trên **mã giao diện gốc** và mã đã sửa, nên không do thay đổi ở Slice 9. Theo mã `BackupCenterView.vue`, tên "Sao lưu đầy đủ" (khớp chuỗi con, không phân biệt hoa thường) khớp cả nút "Sao lưu đầy đủ" lẫn nút làm mới có nhãn "Làm mới bộ sao lưu đầy đủ" (đọc mã, chưa liệt kê hai phần tử từ lần chạy).

**Hướng sửa đề xuất.** Dùng `exact: true` trong locator ở hai test. Chưa sửa. Khi chạy spec này, loại hai test bằng `--grep-invert` để các test sau chạy được.

---

## LD-007. Bộ test backend đỏ nhiều khi chạy như job CI

**Triệu chứng.** Dựng lại các bước của job `test-backend` trong `.github/workflows/ci.yml` trên máy dev (Postgres 16 và Redis tạm, DB `hrms_test` mới, `alembic upgrade head`, `python -m app.seeds --sample`, `pytest tests/`) cho **86 test thất bại và 1 lỗi**.

**Bằng chứng (2026-10-31).**
- Chạy hai lần, mỗi lần mất khoảng 10 phút, cùng DB sạch: một lần với Garage (cấu hình CI mới ở nhánh `ci/garage-service`), một lần với MinIO (cấu hình CI hiện tại). **Tập test đỏ giống hệt** ở cả hai (87 mã test, không test nào chỉ đỏ ở một bên), nên đây không phải hệ quả của việc đổi kho lưu trữ.
- Phân bố theo tệp (lần chạy Garage): `test_leave_records` 17, `test_leave_entitlements` 15, `test_leave_analytics` 13, `test_recruitment_posting` 11, `test_leave_reports` 10, `test_recruitment_candidates` 6, `test_recruitment_pipeline` 3, `test_employee_document_preview_api` 3, `test_other_business_seed` 2, `test_backups` 2, và mỗi tệp 1 ở `test_yearly_reviews`, `test_recruitment_reports`, `test_employee_io`, `test_employee_attachments`, `test_department_scope_rbac`.
- Chạy riêng năm test đại diện: lý do khác nhau (`assert 0 >= 1` trên danh sách rỗng; `KeyError: 'id'` khi tạo tin tuyển dụng; `assert 404 == 201`; `assert 0 == 1` ở seed; một test về che bí mật). Chưa tìm nguyên nhân gốc; các test này có vẻ phụ thuộc dữ liệu seed hoặc thứ tự chạy, nhưng đó là suy đoán chưa kiểm.
- Lệnh pytest của CI (`pytest tests/ -q ...`) cộng với `-q` trong `pytest.ini` nên không in dòng tổng kết, chỉ mã thoát.

**Chưa kiểm.** Job CI thật trên GitHub hiện đỏ hay xanh (không xem được từ máy dev; ngày, múi giờ và dữ liệu có thể khác); nguyên nhân từng nhóm test; khác biệt giữa bản mô phỏng này và runner `ubuntu-latest` (tôi chạy trong image backend, không phải `pip install` trên Python 3.12 của runner).

**Hệ quả cho nhánh `ci/garage-service`.** Khi mở pull request, job `Backend Tests` có thể đỏ vì lý do này chứ không phải do Garage; so sánh danh sách test đỏ với một lần chạy trên `master` thay vì chỉ nhìn màu.
