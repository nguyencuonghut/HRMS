# SLA — Hồng Hà HRMS

**Version:** 1.0 | **Ngày hiệu lực:** 2026-05-29

---

## 1. Mục tiêu dịch vụ (SLO)

| Metric | Target | Đo bằng |
|---|---|---|
| **Availability** | ≥ 99.5% / tháng | Uptime monitoring (healthchecks.io) |
| **API response p95** | < 800ms | Sentry Performance |
| **Export file (5000 dòng)** | < 60 giây | Celery task duration |
| **Login response** | < 500ms | Sentry Performance |

> 99.5% / tháng = tối đa **3.65 giờ downtime** cho phép mỗi tháng.

---

## 2. Recovery Targets

| Metric | Target | Ghi chú |
|---|---|---|
| **RTO** (Recovery Time Objective) | ≤ 4 giờ | Thời gian từ khi xác nhận sự cố đến restore xong |
| **RPO** (Recovery Point Objective) | ≤ 24 giờ | Dữ liệu tối đa bị mất (daily backup) |

---

## 3. Incident Response

### Phân loại sự cố

| Severity | Mô tả | Response Time | Resolution Target |
|---|---|---|---|
| **P1 — Critical** | Hệ thống down hoàn toàn, không login được | 15 phút | 4 giờ |
| **P2 — High** | Tính năng core bị lỗi (tạo nhân viên, hợp đồng) | 30 phút | 8 giờ |
| **P3 — Medium** | Tính năng phụ bị ảnh hưởng, workaround có | 2 giờ | 24 giờ |
| **P4 — Low** | Cosmetic / minor, không ảnh hưởng workflow | 1 ngày làm việc | 1 tuần |

### Quy trình xử lý sự cố

```
1. Alert nhận được (Sentry / Uptime monitor / User báo)
2. Acknowledge trong vòng Response Time (ghi vào incident log)
3. Điều tra root cause → cập nhật status page
4. Fix + verify (staging trước, prod sau)
5. Post-mortem trong vòng 48h (P1/P2)
```

### Kênh liên lạc

| Kênh | Dùng cho |
|---|---|
| Sentry Alerts | Lỗi backend/frontend tự động |
| Healthchecks.io | Uptime alert khi hệ thống down > 5 phút |
| Email nội bộ | Escalation P1/P2 |

---

## 4. Backup & Disaster Recovery

| Item | Lịch | Retention | Script |
|---|---|---|---|
| PostgreSQL backup | 02:00 hàng ngày | 90 ngày | `scripts/backup_db.sh` |
| MinIO mirror | 03:00 hàng ngày | 90 ngày | `scripts/backup_minio.sh` |
| Test restore | Mỗi tháng 1 lần (staging) | — | `scripts/restore_procedure.md` |

---

## 5. Maintenance Windows

| Type | Lịch | Thông báo trước |
|---|---|---|
| Planned maintenance | Thứ Bảy 23:00 – 01:00 | 24 giờ |
| Emergency patch | Bất kỳ | Ngay khi có thể |
| DB migration | Ngoài giờ cao điểm | 1 giờ |

Downtime có lịch **không tính** vào SLA nếu đã thông báo đúng hạn.

---

## 6. Môi trường

| Environment | URL | Mục đích |
|---|---|---|
| Development | `http://localhost:8000` | Dev local |
| Staging | `https://hrms-staging.hongha.vn` | Test trước production |
| Production | `https://hrms.hongha.vn` | Live |

---

## 7. Checklist trước go-live Production

- [ ] `SECRET_KEY` và `ENCRYPTION_KEY` là random, không phải default
- [ ] `SENTRY_DSN` được set và nhận events
- [ ] `HEALTHCHECK_PING_URL` được set, uptime monitor active
- [ ] Backup chạy ít nhất 1 lần thành công
- [ ] Restore drill đã thực hiện trên staging
- [ ] `DEBUG=false`, `ENVIRONMENT=production`
- [ ] CORS origins chỉ cho phép domain production
- [ ] MinIO `MINIO_SECURE=true` với TLS certificate
- [ ] Load test k6 pass (p95 < 800ms / 200 users)
- [ ] Production seed đã chạy đúng flow: `python -m app.seeds` rồi `python -m app.seeds --bootstrap`
- [ ] Không chạy `--local-users` hoặc `--sample` trên production
