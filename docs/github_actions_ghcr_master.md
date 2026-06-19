# Hướng dẫn dùng GitHub Actions + GHCR cho repo `nguyencuonghut/HRMS`

Tài liệu này áp dụng cho repo:

- GitHub repository: `nguyencuonghut/HRMS`
- branch chạy chính: `master`

Tài liệu này được đối chiếu trực tiếp với:

- [.github/workflows/ci.yml](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/.github/workflows/ci.yml)
- [.env.example](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/.env.example)
- [docs/production_deploy_ubuntu_26_04.md](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/docs/production_deploy_ubuntu_26_04.md)
- [docs/deploy_noi_bo_lan_ubuntu_26_04.md](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/docs/deploy_noi_bo_lan_ubuntu_26_04.md)

Ngoài source local, các bước GitHub/GHCR bên dưới được đối chiếu với GitHub Docs chính thức:

- Publishing Docker images: https://docs.github.com/en/actions/tutorials/publish-packages/publish-docker-images
- Working with the Container registry: https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry
- Managing GitHub Actions settings for a repository: https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/enabling-features-for-your-repository/managing-github-actions-settings-for-a-repository
- Configuring a package's access control and visibility: https://docs.github.com/en/packages/learn-github-packages/configuring-a-packages-access-control-and-visibility

---

## 1. Mục tiêu

Sau khi làm xong, quy trình sẽ là:

1. push code lên branch `master`
2. GitHub Actions chạy test backend + type check frontend
3. nếu pass, workflow build và push 3 Docker image lên `ghcr.io`
4. server production hoặc LAN pull image từ GHCR để deploy

Image đích hiện tại theo source:

- `ghcr.io/nguyencuonghut/hrms/hrms-backend`
- `ghcr.io/nguyencuonghut/hrms/hrms-frontend`
- `ghcr.io/nguyencuonghut/hrms/hrms-backup`

---

## 2. Điều đã được xác nhận từ source hiện tại

Trong [.github/workflows/ci.yml](/run/media/cuong/DATA/02_Project/166_HonghaHRM/HRMS/.github/workflows/ci.yml):

- workflow chạy trên branch `master`
- job build/push chỉ chạy khi `push` vào `master`
- workflow dùng `docker/login-action`, `docker/setup-buildx-action`, `docker/build-push-action`
- workflow push 3 image:
  - backend
  - frontend
  - backup

Đã xác nhận thêm bằng kiểm tra runtime cục bộ:

- branch hiện tại của repo local là `master`
- image ref dùng chữ hoa ở phần repo path sẽ lỗi định dạng OCI/Docker

Vì repo của bạn là `nguyencuonghut/HRMS`, workflow hiện đã được sửa để dùng namespace lowercase:

- `nguyencuonghut/hrms`

không dùng trực tiếp `${{ github.repository }}` cho tên image.

---

## 3. GitHub Actions và GHCR dùng để làm gì

### GitHub Actions

GitHub Actions là nơi chạy CI/CD tự động:

- test backend
- kiểm tra frontend
- build Docker image
- push image
- có thể deploy tiếp sang staging/production

### GHCR

GHCR là GitHub Container Registry tại domain:

```text
ghcr.io
```

Nơi này lưu Docker image để server của bạn pull về chạy.

Trong bài toán HRMS này:

- GitHub repo lưu source code
- GHCR lưu artifact deploy

---

## 4. One-time setup trên GitHub

### 4.1. Bật GitHub Actions cho repo

Vào:

`GitHub repo -> Settings -> Actions -> General`

Đảm bảo:

- Actions được phép chạy cho repo

### 4.2. Kiểm tra quyền của `GITHUB_TOKEN`

Theo GitHub Docs, repository có phần:

`Settings -> Actions -> General -> Workflow permissions`

Điểm cần kiểm tra:

- nếu repo đang để `Read and write permissions` thì workflow dễ chạy hơn
- nếu repo đang để mặc định restricted, workflow vẫn cần khai báo `permissions` đúng trong YAML

Workflow hiện tại đã khai báo:

- `contents: read`
- `packages: write` cho job build/push
- `packages: read` cho job deploy-staging

### 4.3. Kiểm tra Packages visibility

Sau khi image được push lần đầu, vào:

`GitHub -> Your profile -> Packages`

Kiểm tra 3 package:

- `hrms-backend`
- `hrms-frontend`
- `hrms-backup`

Với repo public, nếu muốn server nội bộ pull mà không cần auth thì đặt package ở trạng thái `public`.

Theo GitHub Docs đã đối chiếu:

- với Container registry, package public có thể pull ẩn danh

### 4.4. Nếu package đã từng push sai namespace/quyền

GitHub Docs xác nhận:

- package đã publish trước đó nhưng chưa link đúng repository có thể làm `GITHUB_TOKEN` không push được

Nếu gặp lỗi kiểu denied/permission khi workflow push image:

1. vào package đang bị lỗi
2. mở `Package settings`
3. kiểm tra package có linked đúng repo `nguyencuonghut/HRMS` chưa
4. nếu có mục `Manage Actions access`, bảo đảm repo này có quyền
5. nếu có mục `Inherit access from repository`, bật inheritance

---

## 5. Cấu hình secrets cần có

### 5.1. Nếu chỉ build/push lên GHCR

Không cần tạo PAT riêng để workflow push image nếu dùng:

- `GITHUB_TOKEN`

Workflow hiện tại đang dùng `GITHUB_TOKEN` cho bước login GHCR.

### 5.2. Nếu dùng job deploy-staging qua SSH

Workflow hiện tại có job `deploy-staging`, nên cần các secrets sau:

- `STAGING_HOST`
- `STAGING_USER`
- `STAGING_SSH_KEY`

Nếu bạn chưa có staging server, job này có thể giữ nguyên nhưng sẽ chỉ dùng được khi bạn khai báo đủ secrets.

---

## 6. Cách workflow hiện tại hoạt động

Khi push lên `master`, workflow chạy theo thứ tự:

### Bước 1 — Backend Tests

- dựng Postgres và Redis service trong GitHub Actions runner
- chạy `alembic upgrade head`
- chạy `pytest`

### Bước 2 — Frontend Type Check

- `npm ci`
- `npx vue-tsc --noEmit`

### Bước 3 — Build & Push Images

Chỉ chạy khi:

- event là `push`
- branch là `master`

Workflow push các tag:

```text
ghcr.io/nguyencuonghut/hrms/hrms-backend:latest
ghcr.io/nguyencuonghut/hrms/hrms-backend:<github.sha>
ghcr.io/nguyencuonghut/hrms/hrms-backup:latest
ghcr.io/nguyencuonghut/hrms/hrms-backup:<github.sha>
ghcr.io/nguyencuonghut/hrms/hrms-frontend:latest
ghcr.io/nguyencuonghut/hrms/hrms-frontend:<github.sha>
```

### Bước 4 — Deploy staging

Nếu có khai báo secrets staging, workflow SSH vào server rồi:

- `docker login ghcr.io`
- `docker compose pull`
- `docker compose up -d`
- `alembic upgrade head`

---

## 7. Cách dùng hằng ngày

### Cách 1 — push code rồi để workflow tự build image

```bash
git checkout master
git add .
git commit -m "your message"
git push origin master
```

Sau đó vào tab `Actions` trên GitHub để theo dõi pipeline.

Nếu pipeline pass, image mới sẽ có:

- tag `latest`
- tag bằng commit SHA

### Cách 2 — deploy server theo commit cụ thể

Trên server, set:

```env
IMAGE_TAG=<commit-sha>
```

rồi pull/deploy:

```bash
docker compose -f docker-compose.prod.yml pull
docker compose -f docker-compose.prod.yml up -d
```

Cách này tránh việc deploy nhầm `latest`.

---

## 8. Cách xác nhận image đã lên GHCR

### Cách 1 — trên giao diện GitHub

Vào:

- repo `nguyencuonghut/HRMS`
- hoặc profile `nguyencuonghut`
- tab `Packages`

Kiểm tra có đủ:

- `hrms-backend`
- `hrms-frontend`
- `hrms-backup`

### Cách 2 — pull thử trên máy có Docker

Ví dụ:

```bash
docker pull ghcr.io/nguyencuonghut/hrms/hrms-backend:latest
docker pull ghcr.io/nguyencuonghut/hrms/hrms-frontend:latest
docker pull ghcr.io/nguyencuonghut/hrms/hrms-backup:latest
```

Nếu package để public thì pull được mà không cần login.

---

## 9. Các lỗi thường gặp và cách xử lý

### Lỗi 1 — image name invalid

Biểu hiện:

- Docker báo invalid reference format

Nguyên nhân đã được xác nhận bằng kiểm tra runtime:

- OCI/Docker image ref không chấp nhận phần repository path có chữ hoa

Trong repo này, lỗi sẽ xảy ra nếu dùng:

```text
ghcr.io/nguyencuonghut/HRMS/...
```

Phải dùng:

```text
ghcr.io/nguyencuonghut/hrms/...
```

### Lỗi 2 — workflow push GHCR bị denied

Kiểm tra lần lượt:

1. repo Actions có đang bật không
2. workflow job có `packages: write` không
3. package đã link đúng về repo `nguyencuonghut/HRMS` chưa
4. package có bị publish từ namespace cũ/sai trước đó không
5. nếu package private, server pull có đang login đúng không

### Lỗi 3 — server pull image không được

Nếu package private:

```bash
echo '<token>' | docker login ghcr.io -u <github-username> --password-stdin
```

Nếu package public mà vẫn pull fail:

1. kiểm tra lại đúng tên image
2. kiểm tra đúng tag
3. kiểm tra package visibility trên GitHub

### Lỗi 4 — workflow pass test nhưng server chưa chạy code mới

Kiểm tra:

1. `.env` trên server đang dùng `IMAGE_TAG` nào
2. đã `docker compose pull` chưa
3. đã `docker compose up -d` chưa
4. container hiện tại đang chạy image digest nào

---

## 10. Quy trình khuyến nghị cho bạn

Với hiện trạng repo của bạn, quy trình gọn nhất là:

1. giữ branch release chính là `master`
2. push code lên `master`
3. để GitHub Actions build/push 3 image lên GHCR
4. package để `public` nếu server nội bộ chỉ cần pull, không muốn quản lý auth
5. trên server production/LAN, deploy bằng `IMAGE_TAG=<commit-sha>`
6. chỉ dùng `latest` cho môi trường thử nhanh, không dùng cho go-live chính thức

---

## 11. Việc nên làm tiếp ngay

1. Push workflow hiện tại lên GitHub.
2. Vào `Actions` chạy pipeline đầu tiên trên branch `master`.
3. Kiểm tra 3 package có xuất hiện trên GHCR hay chưa.
4. Chốt package visibility là `public` hay `private`.
5. Nếu bạn muốn, bước tiếp theo nên là tạo thêm:
   - workflow chỉ build khi tag release
   - workflow deploy production thủ công bằng `workflow_dispatch`
   - hướng dẫn set secrets/staging/production chi tiết cho repo này
