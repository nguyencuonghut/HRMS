# Biên bản Slice 0 - Kiểm kê và bảo toàn (kế hoạch 15.7)

Ngày lập: 2026-10-30

Trạng thái: **phía dev đã xong; phía production đã có số liệu về image, tệp lưu image, snapshot và cấu hình sao lưu (mục 3). Kiểm kê object qua API và đối chiếu số object với snapshot đã xong (3 = 3). Mirror image Garage lên ghcr đã xong và đã kiểm digest (mục 8). Còn thiếu duy nhất: thử `docker pull` theo digest từ một máy khác.** Tài liệu chỉ chứa số đếm, digest và quyền tệp; không chứa khóa hay dữ liệu cá nhân.

Kế hoạch gốc: [plan_15.7_chuyen_minio_sang_garage.md](plan_15.7_chuyen_minio_sang_garage.md) (Slice 0, mục 12.3 là nhật ký quyết định, Phụ lục D là script kiểm kê).

## 1. Quyết định liên quan đã chốt (2026-10-30)

- Chưa có nơi nào ngoài máy production để cất snapshot/bản sao lưu; **cho phép cutover, chấp nhận rủi ro**.
- Production đổi tên bucket tệp thành `hrms-attachments-prod` khi cutover.
- Giữ MinIO cũ (container dừng + volume) **7 ngày** sau cutover.
- D3 gỡ `mc`; D5 đổi tên `MINIO_*` để sau; D6 thêm Garage vào `docker-compose.prod.yml`.
- Slice 1: chủ hệ thống tự chạy script và gửi kết quả.
- Thuật ngữ giao diện: "Kho tệp ứng dụng" (xem `CONTEXT.md`).
- **Mặc định chưa được xác nhận:** hai khóa Garage riêng (`hrms-app`, `hrms-backup`); khung giờ cutover (D1) chốt sau Slice 7.

## 2. Kết quả phía dev (đã kiểm chứng, do agent thực hiện và được đối chiếu lại)

| Hạng mục | Kết quả |
|---|---|
| Image MinIO dev | `Id sha256:14cea493d9a3…`, `minio --version` = `RELEASE.2025-09-07T16-13-09Z`, kho ảnh `containerd` |
| Lưu và tải lại image (`docker save \| gzip` rồi `docker load`) | Tải lại được, `Id` trùng bản gốc, chạy `minio --version` cùng kết quả; mọi blob khớp `sha256`. **Chưa chứng minh được khôi phục vào kho ảnh trống** (phải giữ tag gốc) |
| Kiểm kê qua API (Phụ lục D) | 2 bucket, 42 object, 6,65 MiB; chạy lại độc lập cho cùng số liệu |
| Snapshot volume dev | 6.624.666 byte, `gzip -t` OK; giải nén sang volume tạm cho cùng số tệp và tổng byte; MinIO khởi động trên volume khôi phục thấy đúng 42 object |
| Image Garage `v2.5.0` | Manifest list `sha256:677e5b758e4425a325b811c425c026bf35a4bf42f7ddbaa773de3f4fd779a5a5`; chạy bằng root, không có nhãn OCI, tag có thể bị đổi |

Phát hiện cần áp dụng ở production:

1. Lệnh `tar` đơn thuần tạo tệp `root:root` quyền `644`; phải đặt `umask 077` và `chown` bên trong container (lệnh đã sửa nằm trong plan, mục "Gói lệnh production").
2. Snapshot volume MinIO **đang chạy** chỉ nhất quán ở mức crash-consistent; số mục thô của volume đang chạy có thể trôi trong vài phút. So sánh bằng script kiểm kê qua API, và chụp thêm snapshot sau khi dừng ứng dụng (plan, mục 10.2).
3. Máy dev đang đầy 90% đĩa (47 GB trống); chỉ ảnh hưởng nếu lưu tệp lớn ở đó.
4. Khi chạy snapshot lần đầu, production phải kéo `alpine:latest` từ Docker Hub (digest `sha256:be2656061b536c1883c4034790e21d0a09c5aaaf51968b89368a3c0371ea2c9a`). Image đó nay đã nằm sẵn trên production: **đừng chạy `docker image prune -a`**, và ở runbook cutover nên ghim `alpine@sha256:be265606…` để không phụ thuộc registry lúc nửa chừng.

## 3. Số liệu production (điền sau khi chạy gói lệnh trong plan, mục "Gói lệnh production")

| Hạng mục | Giá trị | Ghi chú |
|---|---|---|
| Kho ảnh Docker (`docker info --format '{{json .DriverStatus}}'`) | **`overlayfs`, `io.containerd.snapshotter.v1`** | Cùng loại với dev, nên `Id` của image trùng digest manifest |
| Image MinIO đang chạy (`Id`, `RepoDigests`, `Created`) | **`Id sha256:14cea493d9a34af32f524e538b8346cf79f3321eff8e708c1e2960462bd8936e`**, `RepoDigests minio/minio@sha256:14cea493…`, `Created 2025-09-07T18:42:37Z` | Container `hrms-minio-1` dùng đúng `Id` này (`config-image=minio/minio:latest`). **Trùng hoàn toàn với image MinIO trên máy dev** |
| Phiên bản MinIO (`minio --version`) | **`RELEASE.2025-09-07T16-13-09Z`** (commit `07c3a429bfed433e…`), go1.24.6 linux/amd64, AGPLv3 | |
| Tệp lưu image: kích thước, `sha256`, `gzip -t` | **61.906.155 byte, quyền `600`, `gzip -t` OK**, `sha256 b1cafb99aa6b9e82eec1e09627b5dcc1226c59e52603132982f33c2543063c7f` | `~/minio-image-20261030.tar.gz` trên production |
| Tên volume MinIO | **`hrms_minio_data`** (tự dò từ container, mount `/data`) | |
| Snapshot volume: quyền, kích thước, `sha256`, số mục | **quyền `600`, chủ `ubuntu`, 1.179.942 byte, `gzip -t` OK, 85 mục**, `sha256 cc72e5137197a699a1a7eee4aa747921f7ee7607f3fe32ff501001516b616ed1` | `~/minio-snapshots/minio_data_2026-10-30.tgz`. Nhỏ hơn nhiều so với dev (6,6 MB) |
| Kiểm kê: `hrms-attachments-dev` (số object, byte, trên 5 MiB, tên không ASCII) | **0 object, 0 byte** | **Kho tệp ứng dụng production đang trống** |
| Kiểm kê: `hrms-backup` (như trên) | **3 object, 1.233.158 byte (1,18 MiB)**; không có object trên 5 MiB, không có tên ngoài ASCII. Tiền tố `postgres`: 2 (616.622 và 616.378 byte), `files`: 1 (`files-20261030_025101/manifest.json`, 158 byte) | Khớp các tác vụ sao lưu thủ công sáng 30/10 (job 117-119). Bản sao lưu kho tệp chỉ có manifest vì nguồn trống |
| `backup_configs` (cột không bí mật) | **`db`**: endpoint nguồn/đích trống, `target_bucket hrms-backup`, `target_prefix postgres`, `target_secure f`. **`object_storage`**: `source_endpoint minio:9000`, `source_bucket hrms-attachments-dev`, `target_endpoint` trống, `target_bucket hrms-backup`, `target_prefix files`, `target_secure f` | **Trùng với bản sao DB trên dev**, xác nhận giả định của kế hoạch (mục 3.4) trên chính production |
| Mirror Garage lên ghcr: digest sau khi sao chép | _chưa làm_ | Phải khớp `sha256:677e5b75…` nếu sao chép nguyên manifest |

## 4. Cổng hoàn thành Slice 0

- [x] Diễn tập phía dev: định danh image, lưu/tải image, kiểm kê, snapshot và khôi phục, digest Garage.
- [x] Quyết định D1-D6 đã ghi (D1 hoãn có chủ đích đến sau Slice 7).
- [x] Số liệu production đã điền: kho ảnh, image, phiên bản, tệp lưu image, volume, snapshot, `backup_configs`.
- [x] Kiểm kê object production qua API (mục 3).
- [x] Snapshot production: quyền `600`, `gzip -t` OK.
- [x] Số object trong snapshot khớp số object từ API: **3 `xl.meta` trong thư mục hai bucket = 3 object từ kiểm kê** (production, 2026-10-30).
- [x] Image Garage đã mirror lên ghcr: `imagetools inspect` trên ghcr trả đúng manifest list `sha256:677e5b758e4425a325b811c425c026bf35a4bf42f7ddbaa773de3f4fd779a5a5` (digest giữ nguyên).
- [ ] `docker pull ghcr.io/nguyencuonghut/hrms/garage@sha256:677e5b75…` từ máy khác thành công (gói riêng tư nên cần `docker login` bằng token **chỉ đọc**).

## 5. Rủi ro còn mở sau Slice 0

- Không có bản sao lưu ngoài máy production (đã được chủ hệ thống chấp nhận cho cutover).
- Khôi phục image vào kho ảnh trống chưa được chứng minh; chỉ chứng minh được khi tải tệp sang một máy khác.
- Sao chép image sang ghcr: chế độ `--dry-run` của `docker buildx imagetools create` cho thấy manifest sẽ được đẩy **giống hệt từng byte** manifest nguồn (digest giữ nguyên, kiểm trên máy dev 2026-10-30). Chưa đẩy thật.
- Image Garage không có nhãn nguồn gốc; nguồn gốc dựa vào digest và ngày tạo do người vận hành ghi lại.

## 6. Phát hiện từ kiểm kê production

- **Kho tệp ứng dụng trống (0 object).** Chưa người dùng nào tải tệp lên production. Hệ quả: (1) không có tệp đính kèm nào để chép; dữ liệu thật cần chuyển chỉ là 3 object của `hrms-backup` (1,18 MiB); (2) việc đổi tên bucket thành `hrms-attachments-prod` không tốn gì về dữ liệu, chỉ là tạo bucket rỗng và đổi cấu hình; (3) rủi ro mất dữ liệu khi chép thấp hơn nhiều so với giả định ban đầu.
- **Mặt trái:** production **không thể hiện được các trường hợp biên** (object trên 5 MiB, tên có dấu tiếng Việt, hơn 1.000 object). Các trường hợp đó chỉ được kiểm bởi bộ test tương thích ở Slice 1 và dữ liệu thử ở Slice 4, nên hai slice đó càng quan trọng. Những tệp thật đầu tiên sẽ lần đầu được ghi vào Garage sau cutover.
- **Phải kiểm kê lại ngay trước cutover**, vì người dùng có thể tải tệp lên trong thời gian từ nay đến lúc đó.

## 7. Lệnh đối chiếu snapshot với kiểm kê (chạy trên production)

Chỉ đếm `xl.meta` trong thư mục của hai bucket. Không lọc thì kết quả lẫn các tệp hệ thống của MinIO (trên dev: 55 tổng, 42 trong thư mục bucket, 13 ở thư mục hệ thống; 42 bằng đúng số object từ API).

```bash
s=$(ls -1t ~/minio-snapshots/minio_data_*.tgz | head -1)
echo "xl.meta trong thư mục hai bucket (mong đợi 3): $(tar -tzf "$s" | grep -E '^\./(hrms-attachments-dev|hrms-backup)/.*xl\.meta$' | wc -l)"
```

Kết quả trên production (2026-10-30): **3**, khớp kiểm kê.

## 8. Mirror image Garage lên ghcr (người vận hành làm, cần tài khoản ghcr)

Chạy trên **máy dev**, không chạy trên production: `docker login` ghi thông tin đăng nhập vào `~/.docker/config.json`, và một token có quyền `write:packages` không nên nằm trên máy chủ production. Token GitHub cần quyền `write:packages`. Nhập token bằng `read -rs` để không vào lịch sử shell, và chạy `docker logout ghcr.io` khi xong. Gói mới trên ghcr thường mặc định ở chế độ riêng tư, nên production cần `docker login ghcr.io` (token chỉ đọc) trước khi kéo.

```bash
read -rs -p "GHCR token (write:packages): " GHCR_TOKEN; echo
echo "$GHCR_TOKEN" | docker login ghcr.io -u nguyencuonghut --password-stdin; unset GHCR_TOKEN
docker buildx imagetools create --tag ghcr.io/nguyencuonghut/hrms/garage:v2.5.0 docker.io/dxflrs/garage:v2.5.0
docker buildx imagetools inspect ghcr.io/nguyencuonghut/hrms/garage:v2.5.0 | grep -E '^(MediaType|Digest):'
# Mong đợi: Digest: sha256:677e5b758e4425a325b811c425c026bf35a4bf42f7ddbaa773de3f4fd779a5a5
```

Kiểm chứng cuối của Slice 0 (từ máy khác, hoặc sau khi đăng nhập): `docker pull ghcr.io/nguyencuonghut/hrms/garage@sha256:677e5b758e4425a325b811c425c026bf35a4bf42f7ddbaa773de3f4fd779a5a5` thành công.

Lần thử đầu (2026-10-30, chạy trên production): **thất bại, chưa có gì được đẩy lên ghcr.** Biến `GHCR_TOKEN` rỗng (`password is empty`) nên không đăng nhập, và `imagetools create` bị `403 Forbidden` khi lấy token. Log cho thấy máy production thấy đúng bốn manifest nền tảng đã ghi ở mục 2 (`32b5de84…`, `43369b8a…`, `e80db488…`, `23b16d34…`).

Lần thử thứ hai (2026-10-30): **thành công.** `docker login` thành công, `imagetools create` đẩy xong (11,1 giây), `imagetools inspect` trên ghcr trả `application/vnd.docker.distribution.manifest.list.v2+json` và `Digest: sha256:677e5b758e4425a325b811c425c026bf35a4bf42f7ddbaa773de3f4fd779a5a5`, **trùng với nguồn Docker Hub**. `docker logout ghcr.io` đã xóa thông tin đăng nhập khỏi `~/.docker/config.json`. Truy vấn **không đăng nhập** từ máy dev trả `401`: gói là **riêng tư**. Lệnh lần này lại chạy trên production (`/home/ubuntu`); thông tin đăng nhập đã được xóa nhưng token `write:packages` nên được thu hồi vì đã dùng một lần cho việc này.
