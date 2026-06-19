# Hướng dẫn thiết lập GitHub Secrets cho staging/production

Tài liệu này mô tả các secret cần khai báo trên GitHub để các workflow hiện tại của repo chạy đúng.

Tài liệu này được đối chiếu trực tiếp với:

- [.github/workflows/ci.yml](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/.github/workflows/ci.yml)
- [.github/workflows/deploy-production.yml](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/.github/workflows/deploy-production.yml)
- [docker-compose.prod.yml](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/docker-compose.prod.yml)
- [docker-compose.lan.yml](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/docker-compose.lan.yml)
- [.env.example](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/.env.example)

---

## 1. Các workflow hiện có

Repo hiện có 2 workflow liên quan đến build/deploy:

1. [ci.yml](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/.github/workflows/ci.yml)
2. [deploy-production.yml](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/.github/workflows/deploy-production.yml)

Vai trò của từng workflow:

- `ci.yml`
  - chạy test backend
  - chạy type check frontend
  - build/push image lên GHCR khi push vào `master`
  - deploy staging qua SSH nếu đã khai báo đủ secret staging

- `deploy-production.yml`
  - chỉ chạy thủ công bằng `workflow_dispatch`
  - deploy production hoặc LAN qua SSH
  - cho phép chọn `compose_file`, `deploy_path`, `image_tag`, và có chạy migrate hay không

---

## 2. Không cần secret nào cho bước build/push GHCR

Theo [ci.yml](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/.github/workflows/ci.yml), job build/push hiện dùng:

- `secrets.GITHUB_TOKEN`

Đây là token do GitHub Actions cấp sẵn cho workflow. Bạn không cần tự tạo thêm secret để push image lên GHCR, miễn là:

- GitHub Actions được bật cho repo
- workflow có `packages: write`

Hai điều này đã được phản ánh trong workflow hiện tại.

---

## 3. Secrets cho staging

Theo [ci.yml](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/.github/workflows/ci.yml), job `deploy-staging` đang dùng đúng 3 secret sau:

- `STAGING_HOST`
- `STAGING_USER`
- `STAGING_SSH_KEY`

### Ý nghĩa

- `STAGING_HOST`
  - IP hoặc hostname của server staging
  - ví dụ: `172.16.2.120` hoặc `staging.hrms.honghafeed.com.vn`

- `STAGING_USER`
  - user SSH để deploy
  - ví dụ: `ubuntu` hoặc `deploy`

- `STAGING_SSH_KEY`
  - private key dạng PEM/OpenSSH để GitHub Actions SSH vào server staging

### Điều kiện kèm theo ở server staging

Workflow hiện tại đang cố định:

```bash
cd /opt/hrms-staging
docker compose -f docker-compose.prod.yml ...
```

Nghĩa là server staging phải có:

- source nằm ở `/opt/hrms-staging`
- file `.env`
- file `docker-compose.prod.yml`
- Docker và Docker Compose plugin

---

## 4. Secrets cho production

Theo [deploy-production.yml](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/.github/workflows/deploy-production.yml), workflow deploy production dùng:

- `PRODUCTION_HOST`
- `PRODUCTION_USER`
- `PRODUCTION_SSH_KEY`

và có thêm 2 secret tùy chọn:

- `PRODUCTION_GHCR_USERNAME`
- `PRODUCTION_GHCR_TOKEN`

### 4.1. Secrets bắt buộc

- `PRODUCTION_HOST`
  - IP hoặc hostname server production
  - ví dụ: `172.16.2.100`

- `PRODUCTION_USER`
  - user SSH deploy
  - ví dụ: `ubuntu` hoặc `deploy`

- `PRODUCTION_SSH_KEY`
  - private key để GitHub Actions SSH vào server production

### 4.2. Secrets tùy chọn cho GHCR private

- `PRODUCTION_GHCR_USERNAME`
- `PRODUCTION_GHCR_TOKEN`

Workflow hiện tại xử lý như sau:

- nếu 2 secret này có giá trị, server sẽ `docker login ghcr.io`
- nếu để trống, workflow bỏ qua bước login GHCR

Nên dùng khi:

- package GHCR là `private`

Có thể bỏ trống khi:

- package GHCR là `public`
- server pull anonymous được

### 4.3. Quyền của `PRODUCTION_GHCR_TOKEN`

Nếu phải dùng token để pull package private, token cần tối thiểu quyền:

- `read:packages`

Nếu dùng Personal Access Token classic, không cần cấp thêm quyền không liên quan.

---

## 5. Nên lưu ở Repository secrets hay Environment secrets

Trên GitHub có 2 chỗ thường dùng:

1. `Repository secrets`
2. `Environment secrets`

Khuyến nghị:

- staging secrets để ở environment `staging`
- production secrets để ở environment `production`

Lý do:

- dễ khóa quyền review/approval cho production
- dễ tách người được phép deploy staging và production

Workflow hiện tại đã khai báo:

- `environment: staging` trong job deploy staging
- `environment: production` trong workflow deploy production

---

## 6. Cách tạo secrets trên GitHub

Vào repo `nguyencuonghut/HRMS`:

### Nếu dùng repository secrets

`Settings -> Secrets and variables -> Actions -> New repository secret`

### Nếu dùng environment secrets

1. `Settings -> Environments`
2. tạo environment `staging` hoặc `production`
3. vào environment đó
4. chọn `Add secret`

---

## 7. Bộ secrets khuyến nghị đầy đủ

### Tối thiểu để build + deploy staging

```text
STAGING_HOST
STAGING_USER
STAGING_SSH_KEY
```

### Tối thiểu để deploy production workflow thủ công

```text
PRODUCTION_HOST
PRODUCTION_USER
PRODUCTION_SSH_KEY
```

### Thêm nếu GHCR private

```text
PRODUCTION_GHCR_USERNAME
PRODUCTION_GHCR_TOKEN
```

---

## 8. Cách chạy workflow production

Sau khi tạo secrets:

1. vào tab `Actions`
2. chọn workflow `Deploy Production`
3. bấm `Run workflow`
4. chọn branch `master`
5. nhập:
   - `image_tag`
   - `compose_file`
   - `deploy_path`
   - `run_migrate`

### Giá trị gợi ý

#### Production Internet/HTTPS

- `image_tag`: commit SHA cần deploy
- `compose_file`: `docker-compose.prod.yml`
- `deploy_path`: `/opt/hrms`
- `run_migrate`: `true`

#### LAN nội bộ HTTP-only

- `image_tag`: commit SHA cần deploy
- `compose_file`: `docker-compose.lan.yml`
- `deploy_path`: `/opt/hrms`
- `run_migrate`: `true`

---

## 9. Các điểm cần có sẵn trên server trước khi dùng workflow

Workflow SSH chỉ deploy artifact. Nó không tự bootstrap toàn bộ server từ đầu.

Server phải có sẵn:

1. Docker Engine
2. Docker Compose plugin
3. source code đã clone vào đúng `deploy_path`
4. file `.env`
5. file compose tương ứng
6. Nginx/certificate/file mount đúng theo mode production hoặc LAN

Phần này đã được mô tả ở:

- [production_deploy_ubuntu_26_04.md](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/docs/production_deploy_ubuntu_26_04.md)
- [deploy_noi_bo_lan_ubuntu_26_04.md](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/docs/deploy_noi_bo_lan_ubuntu_26_04.md)

---

## 10. Các lỗi cấu hình secret thường gặp

### Lỗi SSH connect fail

Kiểm tra:

1. `HOST` đúng chưa
2. `USER` đúng chưa
3. private key có khớp public key trên server không
4. firewall có mở SSH không

### Lỗi pull image fail

Kiểm tra:

1. `image_tag` có tồn tại trên GHCR không
2. package đang public hay private
3. nếu private, `PRODUCTION_GHCR_USERNAME` và `PRODUCTION_GHCR_TOKEN` đã khai báo chưa

### Lỗi deploy vào sai thư mục

Kiểm tra input:

- `deploy_path`

Workflow production không hard-code `/opt/hrms`, nên nếu nhập sai path thì sẽ fail ngay ở bước `cd`.

### Lỗi compose file không tồn tại

Kiểm tra input:

- `compose_file`

Workflow chỉ hỗ trợ 2 giá trị:

- `docker-compose.prod.yml`
- `docker-compose.lan.yml`

---

## 11. Khuyến nghị vận hành

1. Dùng `image_tag` là commit SHA, không dùng `latest` cho production chính thức.
2. Giữ `deploy-production.yml` là workflow thủ công, không auto deploy production khi push.
3. Dùng environment protection rule cho `production` nếu nhiều người cùng thao tác.
4. Với LAN nội bộ, nếu package GHCR đang public thì không cần lưu token pull trên server.
5. Khi đổi key SSH hoặc đổi server, cập nhật lại secret ngay thay vì sửa workflow.
