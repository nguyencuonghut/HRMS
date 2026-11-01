"""Bộ kiểm tra tương thích S3 cho kho tệp ứng dụng (kế hoạch 15.7, Slice 1).

Kiểm đúng các thao tác ứng dụng dùng (put/get/stat/list/remove/bucket_exists/make_bucket) cùng các
trường hợp biên mà dữ liệu production chưa thể hiện, bằng chính SDK S3 của ứng dụng.

Giao diện chính là `run_checks(client, bucket)`: nhận một client có cùng giao diện với SDK S3 của ứng dụng
(có thể là máy chủ S3 giả khi test) và trả về danh sách kết quả, mỗi kiểm tra độc lập với nhau.
Mọi object thử nằm dưới một tiền tố riêng của lần chạy và được dọn sau khi kiểm xong (trừ khi `keep`).
"""
from __future__ import annotations

import argparse
import hashlib
import io
import os
import sys
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

from minio.error import S3Error

MISSING_BUCKET = "no-such-bucket-xyz"


@dataclass(frozen=True)
class CheckResult:
    name: str
    ok: bool
    detail: str = ""
    seconds: float = 0.0


# Họ mã lỗi "không tìm thấy". HEAD không có thân phản hồi nên SDK tự suy mã từ trạng thái 404:
# với tên object kèm theo, SDK báo NoSuchKey kể cả khi chính bucket mới là thứ thiếu (quan sát trên Garage).
NOT_FOUND_CODES = ("NoSuchKey", "NoSuchBucket")


def _assert_not_found(exc: S3Error, allowed: tuple[str, ...]) -> None:
    assert exc.code in allowed, f"mã lỗi {exc.code!r}, mong đợi một trong {allowed}"


def _read_all(client, bucket: str, name: str) -> bytes:
    response = client.get_object(bucket, name)
    try:
        return response.read()
    finally:
        response.close()
        response.release_conn()


def run_checks(
    client,
    bucket: str,
    *,
    fallback_bucket: str | None = None,
    keep: bool = False,
    many_objects: int = 1050,
    big_bytes: int = 12 * 1024 * 1024,
) -> list[CheckResult]:
    results: list[CheckResult] = []
    prefix = f"s3-probe-{os.urandom(4).hex()}/"
    created_bucket = False

    def check(name: str, fn: Callable[[], str | None]) -> bool:
        started = time.monotonic()
        try:
            detail, ok = fn() or "", True
        except Exception as exc:  # noqa: BLE001 — mỗi kiểm tra phải báo lỗi chứ không làm dừng cả bộ
            detail, ok = f"{type(exc).__name__}: {exc}"[:200], False
        results.append(CheckResult(name, ok, detail, time.monotonic() - started))
        return ok

    def missing_bucket_is_false() -> None:
        assert client.bucket_exists(MISSING_BUCKET) is False, "bucket_exists báo True cho bucket không tồn tại"

    check("bucket_exists(missing bucket) is False", missing_bucket_is_false)

    def create_bucket() -> None:
        nonlocal created_bucket
        client.make_bucket(bucket)
        created_bucket = True
        assert client.bucket_exists(bucket) is True, "bucket vừa tạo nhưng bucket_exists không thấy"

    if not check("make_bucket + bucket_exists", create_bucket):
        if fallback_bucket is None:
            return results
        bucket = fallback_bucket

        def fallback_bucket_exists() -> None:
            # Đúng phép kiểm ensure_bucket() của ứng dụng chạy khi khởi động với bucket tạo sẵn.
            assert client.bucket_exists(bucket) is True, "bucket có sẵn nhưng bucket_exists không thấy"

        check("bucket_exists(existing bucket) is True", fallback_bucket_exists)

    small_key = f"{prefix}s/small.bin"

    def small_round_trip() -> str:
        payload = os.urandom(1024)
        client.put_object(bucket, small_key, io.BytesIO(payload), len(payload), content_type="application/pdf")
        stat = client.stat_object(bucket, small_key)
        assert stat.size == len(payload), f"stat.size={stat.size}"
        assert _read_all(client, bucket, small_key) == payload, "nội dung đọc lại khác nội dung đã ghi"
        return f"content_type={stat.content_type}"

    check("put/stat/get small object (content-type kept)", small_round_trip)

    def multipart_round_trip() -> str:
        big = os.urandom(big_bytes)
        expected = hashlib.sha256(big).hexdigest()
        big_key = f"{prefix}s/big.bin"
        client.put_object(bucket, big_key, io.BytesIO(big), len(big), content_type="application/octet-stream")
        stat = client.stat_object(bucket, big_key)
        assert stat.size == len(big), f"stat.size={stat.size}"
        response = client.get_object(bucket, big_key)
        digest = hashlib.sha256()
        try:
            for chunk in response.stream(1024 * 1024):
                digest.update(chunk)
        finally:
            response.close()
            response.release_conn()
        assert digest.hexdigest() == expected, "sha256 của nội dung đọc lại khác nội dung đã ghi"
        return f"{big_bytes // (1024 * 1024)} MiB, sha256 khớp"

    check(f"put {big_bytes // (1024 * 1024)} MiB (multipart) + streamed get, identical sha256", multipart_round_trip)

    # Ứng dụng đặt tên object bằng nguyên tên tệp người dùng tải lên, nên thử cả các ký tự dễ hỏng khi mã hóa URL.
    awkward_names = (
        "Hợp đồng lao động (bản 1) #2.pdf",
        "a+b c%20d.pdf",
        "q&a?x=1'.pdf",
    )

    def unicode_name_round_trip() -> str:
        payload = os.urandom(256)
        for awkward in awkward_names:
            name = f"{prefix}hop-dong/{awkward}"
            client.put_object(bucket, name, io.BytesIO(payload), len(payload))
            listed = {o.object_name for o in client.list_objects(bucket, prefix=f"{prefix}hop-dong/", recursive=True)}
            assert name in listed, f"tên {awkward!r} không được liệt kê lại nguyên vẹn"
            assert _read_all(client, bucket, name) == payload, f"nội dung của {awkward!r} đọc lại khác nội dung đã ghi"
        return f"{len(awkward_names)} tên (có dấu, khoảng trắng, # ( ) + % & ? ') đều nguyên vẹn"

    check("unicode/space/#()+%&?' object names round-trip", unicode_name_round_trip)

    def overwrite_same_key() -> None:
        client.put_object(bucket, small_key, io.BytesIO(b"x" * 10), 10)
        size = client.stat_object(bucket, small_key).size
        assert size == 10, f"sau khi ghi đè stat.size={size}, mong đợi 10"

    check("overwrite same key", overwrite_same_key)

    def many_objects_listing() -> str:
        def put(index: int) -> None:
            client.put_object(bucket, f"{prefix}many/{index:05d}.txt", io.BytesIO(b"a"), 1)

        with ThreadPoolExecutor(8) as pool:
            list(pool.map(put, range(many_objects)))
        listed = sum(1 for _ in client.list_objects(bucket, prefix=f"{prefix}many/", recursive=True))
        assert listed == many_objects, f"listed {listed} of {many_objects}"
        return f"listed {listed}/{many_objects}"

    check(f"{many_objects} objects: concurrent put + paginated list", many_objects_listing)

    def list_non_recursive() -> str:
        for key in ("a/x", "a/y", "b/z"):
            client.put_object(bucket, f"{prefix}tree/{key}", io.BytesIO(b"1"), 1)
        names = sorted(o.object_name for o in client.list_objects(bucket, prefix=f"{prefix}tree/", recursive=False))
        assert names == [f"{prefix}tree/a/", f"{prefix}tree/b/"], f"nhận được {names}"
        return "trả về các thư mục con, không trả từng object"

    check("list non-recursive (common prefixes)", list_non_recursive)

    def remove_then_stat() -> str:
        client.remove_object(bucket, small_key)
        try:
            client.stat_object(bucket, small_key)
        except S3Error as exc:
            _assert_not_found(exc, ("NoSuchKey",))
            return f"stat sau khi xóa -> code={exc.code}"
        raise AssertionError("object vẫn còn sau khi xóa")

    check("remove_object then stat raises S3Error", remove_then_stat)

    def get_missing_key() -> str:
        try:
            client.get_object(bucket, f"{prefix}does/not/exist")
        except S3Error as exc:
            _assert_not_found(exc, ("NoSuchKey",))
            return f"get khóa không tồn tại -> code={exc.code}"
        raise AssertionError("đọc khóa không tồn tại mà không báo lỗi")

    check("get missing key raises S3Error", get_missing_key)

    def stat_missing_bucket() -> str:
        try:
            client.stat_object(MISSING_BUCKET, "k")
        except S3Error as exc:
            _assert_not_found(exc, NOT_FOUND_CODES)
            return f"stat trên bucket không tồn tại -> code={exc.code}"
        raise AssertionError("stat trên bucket không tồn tại mà không báo lỗi")

    check("stat on missing bucket raises S3Error", stat_missing_bucket)

    def cleanup() -> str:
        names = [o.object_name for o in client.list_objects(bucket, prefix=prefix, recursive=True)]
        with ThreadPoolExecutor(8) as pool:
            list(pool.map(lambda name: client.remove_object(bucket, name), names))
        if created_bucket:
            client.remove_bucket(bucket)
            return f"đã xóa {len(names)} object thử và bucket {bucket}"
        return f"đã xóa {len(names)} object thử, giữ nguyên bucket {bucket} có từ trước"

    if not keep:
        check("cleanup (probe objects and bucket removed)", cleanup)
    return results


def _make_client(*, endpoint: str, access_key: str, secret_key: str, secure: bool, region: str | None):
    from minio import Minio

    return Minio(endpoint, access_key=access_key, secret_key=secret_key, secure=secure, region=region)


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Kiểm tra một máy chủ S3 có tương thích với các thao tác kho tệp ứng dụng dùng hay không. "
        "Khóa truy cập đọc từ biến môi trường S3_PROBE_ACCESS_KEY và S3_PROBE_SECRET_KEY (không nhận qua tham số).",
    )
    parser.add_argument("--endpoint", required=True, help="host:port của máy chủ S3, ví dụ garage:3900")
    parser.add_argument("--secure", action="store_true", help="dùng HTTPS (mặc định HTTP)")
    parser.add_argument("--region", default=None, help="chỉ đặt khi cần ép region; mặc định để SDK tự dò")
    parser.add_argument("--bucket", default=None, help="bucket thử sẽ được tạo rồi xóa (mặc định: tên ngẫu nhiên)")
    parser.add_argument("--fallback-bucket", default=None, help="bucket có sẵn để thử tiếp nếu khóa không được tạo bucket")
    parser.add_argument("--keep", action="store_true", help="không dọn object/bucket thử sau khi chạy")
    parser.add_argument("--many-objects", type=int, default=1050)
    parser.add_argument("--big-mib", type=int, default=12)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None, *, make_client=_make_client) -> int:
    args = _parse_args(argv)
    access_key = os.environ.get("S3_PROBE_ACCESS_KEY")
    secret_key = os.environ.get("S3_PROBE_SECRET_KEY")
    if not access_key or not secret_key:
        print("Thiếu biến môi trường S3_PROBE_ACCESS_KEY và/hoặc S3_PROBE_SECRET_KEY.", file=sys.stderr)
        return 2

    client = make_client(
        endpoint=args.endpoint, access_key=access_key, secret_key=secret_key, secure=args.secure, region=args.region
    )
    bucket = args.bucket or f"s3-probe-{os.urandom(4).hex()}"
    results = run_checks(
        client,
        bucket,
        fallback_bucket=args.fallback_bucket,
        keep=args.keep,
        many_objects=args.many_objects,
        big_bytes=args.big_mib * 1024 * 1024,
    )
    for result in results:
        print(f"{'PASS' if result.ok else 'FAIL'}  {result.name}  ({result.seconds:.2f}s)  {result.detail}".rstrip())
    failed = [r for r in results if not r.ok]
    print(f"\nKẾT QUẢ: {len(results) - len(failed)}/{len(results)} đạt" + (f"; hỏng: {len(failed)}" if failed else ""))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
