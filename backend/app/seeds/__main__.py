"""
Entry point cho seeder. Chạy bằng lệnh:

  # Chỉ seed dữ liệu bắt buộc (required):
  docker compose exec backend python -m app.seeds

  # Seed thêm dữ liệu bootstrap vận hành:
  docker compose exec backend python -m app.seeds --bootstrap

  # Seed thêm user local mặc định:
  docker compose exec backend python -m app.seeds --local-users

  # Bootstrap tài khoản admin đầu tiên (đọc từ env):
  BOOTSTRAP_ADMIN_EMAIL=owner@example.com \
  BOOTSTRAP_ADMIN_PASSWORD='StrongPass#2026' \
  BOOTSTRAP_ADMIN_FULL_NAME='System Owner' \
  docker compose exec backend python -m app.seeds --bootstrap-admin

  # Seed dữ liệu bắt buộc + dữ liệu mẫu dev (sample):
  docker compose exec backend python -m app.seeds --sample

  # Chạy trực tiếp ngoài Docker (cần PYTHONPATH đúng):
  cd backend && python -m app.seeds [--bootstrap] [--local-users] [--bootstrap-admin] [--sample]
"""

import asyncio
import os
import sys

from app.core.database import AsyncSessionLocal
from app.seeds import bootstrap, bootstrap_admin, required, rbac, sample


def _bootstrap_admin_env() -> tuple[str, str, str]:
    email = os.getenv("BOOTSTRAP_ADMIN_EMAIL", "").strip()
    password = os.getenv("BOOTSTRAP_ADMIN_PASSWORD", "").strip()
    full_name = os.getenv("BOOTSTRAP_ADMIN_FULL_NAME", "").strip()
    missing = [
        name
        for name, value in (
            ("BOOTSTRAP_ADMIN_EMAIL", email),
            ("BOOTSTRAP_ADMIN_PASSWORD", password),
            ("BOOTSTRAP_ADMIN_FULL_NAME", full_name),
        )
        if not value
    ]
    if missing:
        raise SystemExit(
            "Thiếu biến môi trường cho --bootstrap-admin (đọc từ container env / .env): "
            + ", ".join(missing)
        )
    return email, password, full_name


async def main(
    with_bootstrap: bool,
    with_sample: bool,
    with_local_users: bool,
    with_bootstrap_admin: bool,
) -> None:
    print("═" * 50)
    print("  Hồng Hà HRMS — Database Seeder")
    print("═" * 50)

    async with AsyncSessionLocal() as session:
        print("\n▶ Required data (mọi môi trường):")
        await required.run(session)

        print("\n▶ RBAC core (roles, permissions):")
        await rbac.run(session, include_users=False)

        if with_bootstrap or with_sample:
            print("\n▶ Bootstrap data (khởi tạo vận hành):")
            await bootstrap.run(session)
        else:
            print("\n  (Bỏ qua bootstrap data — truyền --bootstrap để seed thêm)")

        if with_local_users or with_sample:
            print("\n▶ Local users (dev/test only):")
            await rbac.seed_users(session)
            await session.commit()
        else:
            print("\n  (Bỏ qua local users — truyền --local-users để seed thêm)")

        if with_bootstrap_admin:
            print("\n▶ Bootstrap admin (production first login):")
            email, password, full_name = _bootstrap_admin_env()
            await bootstrap_admin.run(
                session,
                email=email,
                full_name=full_name,
                password=password,
            )
        else:
            print("\n  (Bỏ qua bootstrap admin — truyền --bootstrap-admin để seed thêm)")

        if with_sample:
            print("\n▶ Sample data (chỉ dùng cho dev/test):")
            await sample.run(session)
        else:
            print("\n  (Bỏ qua sample data — truyền --sample để seed thêm)")

    print("\n✓ Seeder hoàn thành.")
    print("═" * 50)


if __name__ == "__main__":
    with_bootstrap = "--bootstrap" in sys.argv
    with_sample = "--sample" in sys.argv
    with_local_users = "--local-users" in sys.argv
    with_bootstrap_admin = "--bootstrap-admin" in sys.argv
    asyncio.run(main(with_bootstrap, with_sample, with_local_users, with_bootstrap_admin))
