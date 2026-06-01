"""
Entry point cho seeder. Chạy bằng lệnh:

  # Chỉ seed dữ liệu bắt buộc (required):
  docker compose exec backend python -m app.seeds

  # Seed thêm dữ liệu bootstrap vận hành:
  docker compose exec backend python -m app.seeds --bootstrap

  # Seed thêm user local mặc định:
  docker compose exec backend python -m app.seeds --local-users

  # Seed dữ liệu bắt buộc + dữ liệu mẫu dev (sample):
  docker compose exec backend python -m app.seeds --sample

  # Chạy trực tiếp ngoài Docker (cần PYTHONPATH đúng):
  cd backend && python -m app.seeds [--bootstrap] [--local-users] [--sample]
"""

import asyncio
import sys

from app.core.database import AsyncSessionLocal
from app.seeds import bootstrap, required, rbac, sample


async def main(with_bootstrap: bool, with_sample: bool, with_local_users: bool) -> None:
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
    asyncio.run(main(with_bootstrap, with_sample, with_local_users))
