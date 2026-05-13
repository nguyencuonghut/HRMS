"""
Entry point cho seeder. Chạy bằng lệnh:

  # Chỉ seed dữ liệu bắt buộc (required):
  docker compose exec backend python -m app.seeds

  # Seed dữ liệu bắt buộc + dữ liệu mẫu dev (sample):
  docker compose exec backend python -m app.seeds --sample

  # Chạy trực tiếp ngoài Docker (cần PYTHONPATH đúng):
  cd backend && python -m app.seeds [--sample]
"""

import asyncio
import sys

from app.core.database import AsyncSessionLocal
from app.seeds import required, sample


async def main(with_sample: bool) -> None:
    print("═" * 50)
    print("  Hồng Hà HRMS — Database Seeder")
    print("═" * 50)

    async with AsyncSessionLocal() as session:
        print("\n▶ Required data (mọi môi trường):")
        await required.run(session)

        if with_sample:
            print("\n▶ Sample data (chỉ dùng cho dev/test):")
            await sample.run(session)
        else:
            print("\n  (Bỏ qua sample data — truyền --sample để seed thêm)")

    print("\n✓ Seeder hoàn thành.")
    print("═" * 50)


if __name__ == "__main__":
    with_sample = "--sample" in sys.argv
    asyncio.run(main(with_sample))
