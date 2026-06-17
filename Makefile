# ─── Hồng Hà HRMS — Makefile ────────────────────────────────────────────────
# Yêu cầu: Docker Compose đang chạy (docker compose up -d)
# Dùng: make <target>

.PHONY: help \
        migrate migrate-down migrate-refresh migrate-history migrate-status migrate-new \
        seed seed-required seed-bootstrap seed-bootstrap-admin seed-local-users seed-sample \
        db-reset db-shell \
        logs logs-be logs-fe shell-be restart-be

# Hiện danh sách lệnh khi gõ `make` không có target
help:
	@echo ""
	@echo "  Hồng Hà HRMS — Lệnh phát triển"
	@echo "  ──────────────────────────────────────────────────"
	@echo ""
	@echo "  Database / Migration:"
	@echo "    make migrate           Áp dụng tất cả migration còn pending"
	@echo "    make migrate-down      Rollback 1 migration gần nhất"
	@echo "    make migrate-refresh   Rollback toàn bộ rồi migrate lại từ đầu"
	@echo "    make migrate-status    Xem migration hiện tại đang ở đâu"
	@echo "    make migrate-history   Xem toàn bộ lịch sử migration"
	@echo "    make migrate-new m=tên Tạo file migration mới (VD: make migrate-new m=add_users)"
	@echo ""
	@echo "  Seeder:"
	@echo "    make seed              Alias dev: required + bootstrap + local-users + sample"
	@echo "    make seed-required     Seed baseline production (required + RBAC core)"
	@echo "    make seed-bootstrap    Seed thêm dữ liệu bootstrap vận hành"
	@echo "    make seed-bootstrap-admin Tạo admin đầu tiên từ BOOTSTRAP_ADMIN_* trong .env"
	@echo "    make seed-local-users  Seed 5 tài khoản local cho dev/test"
	@echo "    make seed-sample       Seed full dev/test data"
	@echo ""
	@echo "  Dev:"
	@echo "    make logs              Theo dõi log tất cả service"
	@echo "    make logs-be           Theo dõi log backend"
	@echo "    make logs-fe           Theo dõi log frontend"
	@echo "    make shell-be          Mở bash vào container backend"
	@echo "    make db-shell          Mở psql vào container database"
	@echo "    make restart-be        Restart backend service"
	@echo ""
	@echo "  ⚠  Nguy hiểm:"
	@echo "    make db-reset          Rollback toàn bộ + migrate lại + seed toàn bộ (chỉ dùng dev)"
	@echo ""


# ─── Migration ───────────────────────────────────────────────────────────────

migrate:
	docker compose exec backend alembic upgrade head

migrate-down:
	docker compose exec backend alembic downgrade -1

migrate-refresh:
	docker compose exec backend alembic downgrade base
	docker compose exec backend alembic upgrade head

migrate-status:
	docker compose exec backend alembic current

migrate-history:
	docker compose exec backend alembic history --verbose

# Tạo migration mới. Dùng: make migrate-new m=ten_migration
migrate-new:
	@test -n "$(m)" || (echo "❌ Thiếu tên migration. Dùng: make migrate-new m=ten_migration" && exit 1)
	docker compose exec backend alembic revision --autogenerate -m "$(m)"


# ─── Seeder ──────────────────────────────────────────────────────────────────

seed:
	docker compose exec backend python -m app.seeds --sample

seed-required:
	docker compose exec backend python -m app.seeds

seed-bootstrap:
	docker compose exec backend python -m app.seeds --bootstrap

seed-bootstrap-admin:
	docker compose exec backend python -m app.seeds --bootstrap-admin

seed-local-users:
	docker compose exec backend python -m app.seeds --local-users

seed-sample:
	docker compose exec backend python -m app.seeds --sample


# ─── Database shell ──────────────────────────────────────────────────────────

db-shell:
	docker compose exec db psql -U $${POSTGRES_USER:-postgres} -d $${POSTGRES_DB:-hrms}


# ─── Dev shortcuts ───────────────────────────────────────────────────────────

logs:
	docker compose logs -f

logs-be:
	docker compose logs -f backend

logs-fe:
	docker compose logs -f frontend

shell-be:
	docker compose exec backend bash

restart-be:
	docker compose restart backend


# ─── ⚠ Nguy hiểm — chỉ dùng trên dev ───────────────────────────────────────

db-reset:
	@echo "⚠  Xóa toàn bộ schema và tạo lại. Nhấn Ctrl+C trong 5 giây để hủy..."
	@sleep 5
	$(MAKE) migrate-refresh
	docker compose exec backend python -m app.seeds --sample
	@echo "✓ db-reset hoàn thành."
