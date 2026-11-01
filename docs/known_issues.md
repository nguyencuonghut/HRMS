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
| LD-007 | Chạy toàn bộ `pytest` như job CI (DB sạch, `--sample`) cho 86 test đỏ và 1 lỗi, như nhau với cả MinIO lẫn Garage | **Đã sửa 2026-10-31** (chưa commit; chạy lại toàn bộ trên DB sạch: 0 đỏ; chưa chạy trên GitHub) | 2026-10-31, dev (kế hoạch 15.7, Slice 9) |
| LD-008 | Bấm tên tệp đính kèm của vị trí công việc (hộp thoại "Chi tiết vị trí công việc") mở tab mới báo 401 `Not authenticated`, không tải được tệp | **Đã sửa 2026-10-31** (chưa commit; có tác dụng trên production sau khi dựng lại image frontend) | 2026-10-31, dev (phát hiện khi dọn chú thích MinIO; tái hiện bằng trình duyệt thật) |
| LD-009 | Spec e2e `org-position-auth-refresh.spec.ts` đỏ (tìm "Chuyên viên HR" không thấy): dữ liệu giả lập của spec không theo kịp hai thay đổi của màn "Vị trí công việc" sau 02/06/2026 | **Đã sửa 2026-10-31** (chỉ sửa test, không đụng mã sản phẩm; chưa commit) | 2026-10-31, dev (phát hiện khi sửa LD-008) |

LD-001, LD-002, LD-006, LD-008 và LD-009 có từ trước và **không liên quan** việc chuyển kho tệp sang Garage (LD-008 cùng cơ chế với LD-002; LD-009 là test lỗi thời, không phải lỗi của sản phẩm). LD-003 là cơ chế của mã tải tệp, không phụ thuộc loại kho (chưa kiểm trên MinIO). LD-004 lộ ra khi đổi lịch sao lưu ở production. LD-005 phát hiện khi chạy test e2e, chưa rõ có phụ thuộc thay đổi nào ở Slice 9 hay không (xem mục).

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

**Hệ quả thứ hai, phát hiện khi sửa (thăm dò trực tiếp trên mã gốc).** `minio_circuit` (nay đổi tên thành `storage_circuit`, `backend/app/core/circuit_breaker.py`) tính **mọi** exception là sự cố, ngưỡng 3 lần liên tiếp, mở 30 giây. `NoSuchKey` cũng bị tính: gọi `get_object_stream` với object thiếu 4 lần cho `S3Error`, `S3Error`, `S3Error` (mạch chuyển sang `open`), rồi `HTTPException 503`. Nghĩa là chỉ cần một bản ghi "mồ côi" (ví dụ sau khôi phục DB mà chưa khôi phục kho tệp) bị bấm tải 3 lần là **mọi** tải và tải lên tệp của **mọi người dùng** trả 503 trong 30 giây. `get_object_bytes` (dùng cho mẫu DOCX) có cùng đường đi.

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

**Triệu chứng.** Dựng lại các bước của job `test-backend` trong `.github/workflows/ci.yml` trên máy dev (Postgres 16 và Redis tạm, DB `hrms_test` mới, `alembic upgrade head`, `python -m app.seeds --sample`, `pytest tests/`) cho **86 test thất bại và 1 lỗi**, như nhau với Garage và MinIO (nên không do kho lưu trữ).

**Nguyên nhân (mỗi nguyên nhân đã tái hiện riêng bằng một lần chạy đỏ, rồi xanh sau khi sửa).** Đây là 8 nguyên nhân độc lập, không phải một lỗi:

| # | Test đỏ | Nguyên nhân | Sửa |
|---|---|---|---|
| 1 | 55 test nghỉ phép (`test_leave_records`, `_entitlements`, `_analytics`, `_reports`) và 3 test `test_employee_document_preview_api` | Seed `--sample` đặt lại sequence bằng `setval(seq, COALESCE(MAX(id), 1), true)`; trên bảng rỗng việc này làm id kế tiếp là **2**, nên nhân viên đầu tiên có `id=2` trong khi các test dùng `employee_id=1` (đúng trên DB dev, là bản sao production). Đã đo bằng SQL trên bảng tạm: cách cũ cho 2, cách mới cho 1; bảng đã có dữ liệu cho kết quả như nhau (`max+1`) nên DB dev và production không đổi hành vi. Chạy riêng với seed cũ trong cùng môi trường: `test_leave_records` 17 đỏ, `test_leave_entitlements` 15 đỏ, `test_employee_document_preview_api` 3 đỏ; `test_leave_analytics` và `test_leave_reports` (23 test) chỉ được kiểm theo nhóm (đỏ trước, xanh sau khi sửa seed), chưa chạy riêng với seed cũ | `backend/app/seeds/sample.py`: hàm `reset_id_sequence` dùng `setval(seq, COALESCE(MAX(id), 0) + 1, false)`; thêm `tests/test_sample_seed_sequences.py` (đỏ `assert 2 == 1` trước khi sửa) |
| 2 | 21 test tuyển dụng (`test_recruitment_posting` 11, `_candidates` 6, `_pipeline` 3, `_reports` 1) | Chỉ đỏ khi chạy cả bộ (chạy riêng thì xanh). Các tệp `test_job_positions`, `test_job_position_attachments`, `test_job_position_department_mapping`, `test_org_history` tạo phòng ban thử ở phạm vi phiên (vd "Test Dept JP"), nên "phòng ban đầu tiên" bị ghép sai với "vị trí đầu tiên" và tạo JR trả 422 ("Vị trí công việc không thuộc phòng ban đã chọn…"). Cơ chế đã thăm dò trực tiếp ở `test_job_positions` (phòng ban đầu tiên là "Test Dept JP", id 47); ba tệp còn lại cũng làm test tuyển dụng đỏ khi chạy trước nó (thử từng tệp riêng) nhưng chưa thăm dò cơ chế từng tệp | Bốn tệp tuyển dụng lấy phòng ban từ chính dòng vị trí đầu tiên (`department_id` của vị trí), như `test_recruitment_offer.py` |
| 3 | `test_backups` 2 test "…without_exposing_secrets" | Test lấy bí mật từ `settings.BACKUP_STORAGE_SECRET_KEY`; job CI không đặt biến này nên là chuỗi rỗng và `"" not in "…"` luôn sai. Xanh khi biến có giá trị, đỏ khi rỗng (đã chạy cả hai) | Test tự đặt giá trị bằng `monkeypatch` |
| 4 | `test_employee_io::test_export_profile_reads_bhxh_code_from_insurance_profile` | `NameError: name 'rows' is not defined`: test thiếu dòng đọc sheet (dòng `assert` này có từ commit `8bb6ac6`) | Thêm dòng đọc sheet "Thông tin cá nhân" thành `rows` |
| 5 | `test_other_business_seed` 2 test | Kỳ vọng lỗi thời: tổng placeholder cố định 51 (seed hiện cho 60) và khóa `employee.full_name` (seed hiện dùng khóa `employee_full_name` cho mẫu `ld_indefinite`) | Kiểm tra seed chạy lần hai không thêm dòng và mọi placeholder seed khai báo đều có mặt |
| 6 | `test_department_scope_rbac::test_scoped_contract_user_only_sees_contracts_within_assigned_departments` | Hợp đồng đặt `effective_to="2026-07-15"`, còn báo cáo "sắp hết hạn" lấy `effective_to` trong `[hôm nay, hôm nay + 90 ngày]` nên test chỉ đúng khi chạy trong khoảng 16/04–15/07/2026 | Ngày tính theo `date.today()` |
| 7 | `test_employee_attachments::test_viewer_can_list_and_download` | `line_manager` chỉ có phạm vi phòng ban `[2, 16, 17]`; nhân viên test không thuộc phòng ban nào nên API trả 404 (đúng theo phân quyền theo phòng ban) | Tạo nhân viên trong phòng ban đầu tiên của phạm vi lấy từ `/auth/me` |
| 8 | ERROR cuối phiên (gán cho test cuối `test_yearly_reviews`) | `test_job_position_department_mapping` lấy "phòng ban đầu tiên" làm phòng ban chủ, trong phiên đầy đủ là `TEST_DEPT_ATT` của fixture phạm vi phiên ở `test_job_position_attachments`; vị trí `TSPOS…` tạo ra không được dọn nên teardown xóa phòng ban bị lỗi khóa ngoại | Test tự tạo phòng ban chủ riêng |

**Kết quả (2026-10-31).** Chạy lại đúng các bước của job CI trên DB `hrms_test` mới, bỏ đặt các biến môi trường mà job CI không đặt (`BACKUP_STORAGE_*`, `SMTP_*`, `APP_TIMEZONE`…): **1630 test xanh, 3 test bỏ qua, 0 đỏ, 0 lỗi** (trước đó 86 đỏ và 1 lỗi). Chạy trong image backend dev với Garage dev; mã thoát của pytest không được lưu (đã lọc qua `grep`), kết luận dựa trên việc không có dòng `FAILED`/`ERROR` nào và không có ký tự `F`/`E` trong dòng tiến độ.

**Chưa kiểm.**
- Job CI thật trên GitHub (Python 3.12 cài bằng `pip`, service MinIO, `ubuntu-latest`) chưa chạy; tôi chạy trong image backend.
- Chưa chạy trên DB dev (bản sao production): các sửa ở mục 1 không đổi hành vi với bảng đã có dữ liệu (đã đo trên bảng tạm), nhưng chưa chạy lại toàn bộ suite trên DB đó.
- Các test khác vẫn có thể có cùng kiểu mong manh (lấy "phòng ban đầu tiên", ngày cố định, phụ thuộc id=1). Tôi chỉ sửa những test đã đỏ; chưa rà soát toàn bộ.
- Nhánh `ci/garage-service` chưa push, nên chưa biết job `Backend Tests` trên GitHub xanh hay đỏ.


## LD-008. Bấm tên tệp đính kèm của vị trí công việc không tải được (401)

**Triệu chứng.** Ở màn "Vị trí công việc" (`/org/positions`), mở hộp thoại "Chi tiết vị trí công việc", tab "Tài liệu đính kèm", bấm tên một tệp: trình duyệt mở một tab mới chỉ hiện `{"detail":"Not authenticated"}` và không tải được tệp.

**Bằng chứng (2026-10-31, trình duyệt thật).** Chrome điều khiển bằng Playwright 1.60.0, backend thật trong một stack cô lập (DB mới có seed `--sample`, backend, Vite dev server, Garage dev), tài khoản `admin@hrms.local`, vị trí `CT_HDQT`, tệp PDF 4 KiB tải lên bằng API:
- **Đối chứng:** gọi thẳng `GET /api/v1/job-positions/{id}/attachments/{attId}/download`: không có token trả 401 `{"detail":"Not authenticated"}`; có `Authorization: Bearer <token>` trả 200 và `sha256` đúng bằng tệp đã tải lên. Endpoint không hỏng.
- **Qua giao diện:** liên kết là `<a href="/api/v1/job-positions/1/attachments/N/download" target="_blank">`. Bấm vào: yêu cầu trong tab mới nhận **401**, **không có** header `Authorization`, và tab hiện đúng `{"detail":"Not authenticated"}`. Tái hiện **6/6 lần** (một lần đầu và năm lần lặp).

**Nguyên nhân (đọc mã, khớp với kết quả trên).** `frontend/src/components/FileAttachmentList.vue:35` dùng thẻ `<a :href="data.download_url" target="_blank">`. `download_url` do `backend/app/api/v1/endpoints/job_positions.py:162` trả là đường dẫn API tải xuống (không phải URL có chữ ký), và endpoint đó yêu cầu quyền `org:view`. Token truy cập nằm trong bộ nhớ của ứng dụng, không phải cookie, nên thẻ `<a>` điều hướng tới URL mà không gửi header `Authorization` và backend trả 401. Cùng cơ chế với LD-002.

**Chú thích sai cùng chỗ (đã sửa 2026-10-31, commit `504e834`).** `FileAttachmentList.vue` và `backend/app/schemas/job_position.py` ghi `download_url` là "presigned URL, hết hạn sau 1 giờ"; không có URL presigned nào trong mã. Đã viết lại thành "đường dẫn API tải xuống (cần token xác thực)".

**Không liên quan kho tệp.** Lỗi xảy ra ở lớp xác thực, trước khi chạm kho tệp. Không kiểm trên MinIO.

**Phạm vi (chưa rà hết).** Trong `frontend/src`, đây là nơi duy nhất dùng thẻ `<a :href>` trỏ tới `download_url` hay đường dẫn `/download` (tìm bằng `grep`). Các chỗ gán `a.href` bằng script ở các service tải xuống (`employeeService`, `contractService`, `trainingService`, ...) chưa rà từng nơi; nhiều khả năng dùng URL blob có token như cách sửa LD-002.

**Cách đã sửa (2026-10-31).** `FileAttachmentList.vue`: tên tệp là `<a href="#" @click.prevent="download(data)">`; hàm `download(att)` gọi `api.get('/job-positions/{id}/attachments/{attId}/download', { responseType: 'blob' })` (có token, giống cách sửa LD-002), tạo liên kết blob với `download = att.file_name` rồi bấm; lỗi hiện toast "Không tải được file". Chú thích của `download_url` ghi rõ không dùng làm `href`. Hành vi mong muốn không đổi so với ý đồ ban đầu: endpoint trả `Content-Disposition: attachment` nên đó vốn là một lượt tải xuống; chỉ bỏ việc mở tab mới.

**Đã kiểm (2026-10-31, stack cô lập, Chrome qua Playwright 1.60.0).**
- Test mới `frontend/tests/e2e/position-attachments.spec.ts` (hai trường hợp: tên thường, và tên có khoảng trắng, `#`, `%`, `+`): **đỏ trước khi sửa** (bấm tên tệp không phát sinh lượt tải xuống: chờ sự kiện `download` quá hạn 15 giây) và **xanh sau khi sửa** (tải không lỗi, `suggestedFilename` đúng tên, `sha256` khớp tệp đã tải lên).
- Đường lỗi (thăm dò bằng trình duyệt thật, không có test trong repo): xóa tệp ở backend sau khi danh sách đã hiện rồi bấm tên: hiện toast "Không tải được file", không tải gì, không mở tab mới, giữ nguyên trang.
- `vue-tsc --noEmit` không lỗi; `vite build` thành công (đầu ra ghi vào thư mục tạm trong container, không đụng `frontend/dist`).
- Spec có sẵn của màn này, `org-position-auth-refresh.spec.ts`, **đỏ ở dòng `getByText('Chuyên viên HR')` trên stack cô lập, giống hệt trên mã chưa sửa** (đối chứng bằng cách hoàn tác bản sửa), nên không do bản sửa này; chưa điều tra nguyên nhân (spec dùng nhiều phản hồi giả lập).

**Chưa kiểm.** Trên production (cần dựng lại image frontend); trình duyệt khác ngoài Chrome; tệp rất lớn qua đường này (kiểm bằng tệp tới 90 KB); tải lên và xóa trong cùng danh sách (không đổi, không có test mới); các chỗ gán `a.href` bằng script ở các service khác (xem Phạm vi).


## LD-009. Spec e2e `org-position-auth-refresh.spec.ts` đỏ vì dữ liệu giả lập đã lỗi thời

**Triệu chứng.** Chạy `frontend/tests/e2e/org-position-auth-refresh.spec.ts` trên stack cô lập (DB mới có seed `--sample`, backend, Vite dev server) thì đỏ ở `expect(page.getByText("Chuyên viên HR")).toBeVisible()`: `element(s) not found`. Đỏ **giống hệt** trước và sau bản sửa LD-008 (đối chứng bằng cách hoàn tác bản sửa), nên không do LD-008.

**Nguyên nhân: hai nguyên nhân độc lập, cả hai do spec chưa theo kịp sản phẩm.** Spec được thêm ngày 2026-06-02 (commit `1c08542`) và chưa được sửa lần nào kể từ đó. Spec giả lập (mock) `auth/refresh`, `departments`, `job-titles`, `employee-code-rules/sequences` và `job-positions**`, và dựng trang dựa trên các phản hồi giả đó.
1. **Có thêm một yêu cầu mà spec không biết.** `PositionListView.loadData()` hiện gọi song song ba yêu cầu: danh sách vị trí, phòng ban, và `getProbationLegalGroups()` tới `GET /job-positions/probation-legal-groups/options` (thêm ở commit `2c53e22`, 2026-06-15). Glob `**/api/v1/job-positions**` của spec khớp cả URL này. Lần đầu nó bị giả lập trả 401, lần thử lại rơi vào `route.continue()`, đi tới backend thật cùng token giả và nhận 401; `Promise.all` thất bại nên danh sách không hiển thị. Log yêu cầu ghi lại: sau `POST /auth/refresh -> 200`, `job-positions -> 200` và `departments -> 200` (đều giả lập) nhưng `probation-legal-groups/options -> 401`.
2. **Bản ghi vị trí giả thiếu các trường nay là bắt buộc.** Kiểu `JobPositionListItem` hiện có `assigned_department_ids`, `assigned_departments`, `is_shared` và `probation_legal_group`, `probation_legal_group_label`, `probation_days_limit` (thêm ở `fa4bdab`, 2026-06-25, khi vị trí có phạm vi nhiều đơn vị), còn bản ghi giả của spec không có. Bảng đọc `data.assigned_departments.length` (`PositionListView.vue:114`), gây `TypeError: Cannot read properties of undefined (reading 'length')` và `[App ErrorBoundary]`.

**Kiểm chứng bằng thí nghiệm (2026-10-31, bản sao của spec ở thư mục tạm, không sửa repo).**
- Chỉ thêm giả lập cho `probation-legal-groups/options` (trả `[]`, và vẫn tính 401 ở lần đầu như các endpoint khác): yêu cầu đó thành công, spec **vẫn đỏ**, và log chuyển sang lỗi ErrorBoundary ở trên (nguyên nhân 2).
- Thêm cả các trường còn thiếu vào bản ghi danh sách giả: spec **xanh**, và hai số đếm làm mới token của spec (`refreshCount` 1 rồi 3) vẫn đúng.
- Bản chỉ có hai thay đổi đó (không thêm trường nào vào bản ghi chi tiết giả) cũng **xanh**, nên hai thay đổi này là cần và đủ cho spec hiện tại. Thêm trường vào bản ghi chi tiết (`department_name`, `assigned_*`, `is_shared`, `probation_*`) cho khớp kiểu `JobPositionRead` cũng xanh nhưng không cần để qua.

**Không phải lỗi của sản phẩm.** Màn hình thật hiển thị đúng: spec e2e mới của LD-008 (`position-attachments.spec.ts`, backend thật) đi qua cùng màn, cùng hộp thoại chi tiết và tab tài liệu, và xanh.

**Cách đã sửa (2026-10-31).** Chỉ sửa `frontend/tests/e2e/org-position-auth-refresh.spec.ts`: thêm giả lập cho `GET /job-positions/probation-legal-groups/options` (trả `[]`, đặt trong cùng bộ xử lý `job-positions**` nên cũng bị 401 ở lần đầu như các endpoint khác), và thêm các trường còn thiếu vào bản ghi vị trí giả: `assigned_department_ids`, `assigned_departments`, `is_shared`, `probation_*` ở cả bản ghi danh sách lẫn bản ghi chi tiết (kèm `department_name` ở bản ghi chi tiết), theo đúng kiểu `JobPositionListItem` và `JobPositionRead` hiện tại. Không đụng mã sản phẩm.

**Đã kiểm (2026-10-31, stack cô lập, Chrome qua Playwright 1.60.0).** Spec nguyên bản đỏ (`getByText('Chuyên viên HR')` không thấy); sau khi sửa **xanh 3 lần trên 3**, và các khẳng định về làm mới token của chính spec vẫn đúng (`refreshCount` bằng 1 sau khi tải danh sách, bằng 3 sau khi mở tab tài liệu), nên spec vẫn kiểm đúng điều nó đặt ra (màn hình sống sót qua việc làm mới token). Spec LD-008 (`position-attachments.spec.ts`) cùng stack vẫn xanh; `vue-tsc --noEmit` không báo lỗi.

**Chưa kiểm.** Chỉ chạy trên stack cô lập, không phải stack dev (DB dev chỉ có tài khoản thật). Ba spec e2e khác cũng nhắc API vị trí công việc (`insurance-foundation-config.spec.ts`, `line-manager-department-scope.spec.ts`, `recruitment-offer-position-scope.spec.ts`) chưa được rà xem có lỗi thời tương tự không. Điểm yếu thiết kế của spec vẫn còn: các URL `job-positions` không nằm trong danh sách được giả lập sẽ bị `route.continue()` sang backend thật cùng token giả và trả 401 gây nhầm lẫn, nên một endpoint mới của màn hình sẽ lại làm spec đỏ theo cách khó đoán. Chưa có cách nào phát hiện sớm kiểu lỗi này, vì CI không chạy e2e.
