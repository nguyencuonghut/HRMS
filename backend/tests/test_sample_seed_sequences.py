"""Test đặt lại sequence id của seed mẫu (LD-007).

Trên DB sạch (như job CI), bảng `employees` còn rỗng khi seed đặt lại sequence. Nếu id đầu tiên là 2 thì mọi test
giả định `employee_id=1` có sẵn đều đỏ, nên id kế tiếp phải là MAX(id)+1 và là 1 khi bảng rỗng.
"""

from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import settings
from app.seeds.sample import reset_id_sequence


def _make_session():
    engine = create_async_engine(settings.DATABASE_URL, connect_args={"ssl": False})
    return async_sessionmaker(engine, expire_on_commit=False)


async def _next_id_after_reset(table: str, existing_ids: list[int]) -> int:
    async with _make_session()() as session:
        try:
            await session.execute(text(f"CREATE TEMP TABLE {table} (id serial PRIMARY KEY)"))
            for existing_id in existing_ids:
                await session.execute(text(f"INSERT INTO {table} (id) VALUES ({existing_id})"))
            await reset_id_sequence(session, f"{table}_id_seq", table)
            return (await session.execute(text(f"SELECT nextval('{table}_id_seq')"))).scalar_one()
        finally:
            await session.rollback()


async def test_reset_id_sequence_on_empty_table_starts_at_one():
    assert await _next_id_after_reset("ld007_seq_empty", []) == 1


async def test_reset_id_sequence_continues_after_highest_id():
    assert await _next_id_after_reset("ld007_seq_filled", [5, 9]) == 10
