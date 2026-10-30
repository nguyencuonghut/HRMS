"""Hành vi của bộ kiểm tra tương thích S3, kiểm bằng các máy chủ S3 giả trong bộ nhớ.

Máy chủ giả đóng vai hệ thống bên ngoài (một kho S3). Mỗi máy chủ giả đúng ở mọi điểm
trừ một lỗi cố ý, và bộ kiểm tra phải chỉ đúng lỗi đó. Không cần Docker hay mạng.
"""
from __future__ import annotations

from dataclasses import dataclass

import pytest
from minio.error import S3Error

from app.scripts.s3_conformance_probe import main, run_checks


def _s3_error(code: str) -> S3Error:
    # minio 7.2: tham số đầu của S3Error là `response`, không phải `code`.
    return S3Error(None, code, code, "/", "req-id", "host-id")


@dataclass
class _Stat:
    size: int
    content_type: str | None


@dataclass
class _Listed:
    object_name: str
    size: int
    is_dir: bool


class _Response:
    def __init__(self, data: bytes) -> None:
        self._data = data

    def read(self) -> bytes:
        return self._data

    def stream(self, amt: int = 1024 * 1024):
        for start in range(0, len(self._data), amt):
            yield self._data[start : start + amt]

    def close(self) -> None:
        pass

    def release_conn(self) -> None:
        pass


class FakeS3:
    """Một kho S3 đúng đắn trong bộ nhớ, đủ cho các thao tác ứng dụng dùng."""

    def __init__(self) -> None:
        self.buckets: dict[str, dict[str, tuple[bytes, str | None]]] = {}

    def bucket_exists(self, bucket: str) -> bool:
        return bucket in self.buckets

    def make_bucket(self, bucket: str) -> None:
        self.buckets[bucket] = {}

    def put_object(self, bucket, name, data, length, content_type="application/octet-stream"):
        self.buckets[bucket][name] = (data.read(length), content_type)

    def _objects(self, bucket: str) -> dict[str, tuple[bytes, str | None]]:
        if bucket not in self.buckets:
            raise _s3_error("NoSuchBucket")
        return self.buckets[bucket]

    def stat_object(self, bucket, name) -> _Stat:
        objects = self._objects(bucket)
        if name not in objects:
            raise _s3_error("NoSuchKey")
        body, content_type = objects[name]
        return _Stat(len(body), content_type)

    def get_object(self, bucket, name) -> _Response:
        objects = self._objects(bucket)
        if name not in objects:
            raise _s3_error("NoSuchKey")
        return _Response(objects[name][0])

    def remove_object(self, bucket, name) -> None:
        self._objects(bucket).pop(name, None)

    def remove_bucket(self, bucket: str) -> None:
        if self._objects(bucket):
            raise _s3_error("BucketNotEmpty")
        del self.buckets[bucket]

    def list_objects(self, bucket, prefix=None, recursive=False):
        prefix = prefix or ""
        folders: set[str] = set()
        for name in sorted(n for n in self.buckets[bucket] if n.startswith(prefix)):
            remainder = name[len(prefix) :]
            if not recursive and "/" in remainder:
                folder = prefix + remainder.split("/", 1)[0] + "/"
                if folder not in folders:
                    folders.add(folder)
                    yield _Listed(folder, 0, True)
                continue
            yield _Listed(name, len(self.buckets[bucket][name][0]), False)


class FlatListingS3(FakeS3):
    """Lỗi: bỏ qua recursive=False, luôn trả danh sách phẳng thay vì các thư mục."""

    def list_objects(self, bucket, prefix=None, recursive=False):
        return super().list_objects(bucket, prefix, True)


class TruncatingListS3(FakeS3):
    """Lỗi: danh sách bị cắt ở 1.000 đối tượng, không có trang kế tiếp."""

    def list_objects(self, bucket, prefix=None, recursive=False):
        for index, listed in enumerate(super().list_objects(bucket, prefix, recursive)):
            if index >= 1000:
                return
            yield listed


class CorruptingLargeObjectsS3(FakeS3):
    """Lỗi: đối tượng lớn hơn 5 MiB (đường multipart) đọc lại sai một byte."""

    def get_object(self, bucket, name) -> _Response:
        data = super().get_object(bucket, name).read()
        if len(data) > 5 * 1024 * 1024:
            data = data[:-1] + bytes([data[-1] ^ 1])
        return _Response(data)


class FailingRemoveS3(FakeS3):
    """Lỗi: remove_object luôn thất bại (kho hỏng hoặc thiếu quyền xóa)."""

    def remove_object(self, bucket, name) -> None:
        raise _s3_error("InternalError")


class AlwaysExistsS3(FakeS3):
    """Lỗi: bucket_exists luôn trả True, kể cả với bucket không tồn tại."""

    def bucket_exists(self, bucket: str) -> bool:
        return True


class NoopRemoveS3(FakeS3):
    """Lỗi: remove_object báo thành công nhưng không xóa gì."""

    def remove_object(self, bucket, name) -> None:
        return None


class RejectsMissingKeyReadsWithWrongCodeS3(FakeS3):
    """Lỗi: đọc khóa không tồn tại báo lỗi nhưng sai mã (ví dụ lỗi chữ ký thay vì NoSuchKey)."""

    def get_object(self, bucket, name) -> _Response:
        try:
            return super().get_object(bucket, name)
        except S3Error as exc:
            raise _s3_error("AuthorizationHeaderMalformed") from exc


class RejectsMissingBucketStatWithWrongCodeS3(FakeS3):
    """Lỗi: stat trên bucket không tồn tại báo lỗi nhưng sai mã (AccessDenied thay vì không tìm thấy)."""

    def stat_object(self, bucket, name) -> _Stat:
        if bucket not in self.buckets:
            raise _s3_error("AccessDenied")
        return super().stat_object(bucket, name)


class LenientGetS3(FakeS3):
    """Lỗi: đọc khóa không tồn tại trả về dữ liệu rỗng thay vì báo lỗi."""

    def get_object(self, bucket, name) -> _Response:
        try:
            return super().get_object(bucket, name)
        except S3Error:
            return _Response(b"")


class FoldingNamesS3(FakeS3):
    """Lỗi: tên object bị bỏ các ký tự ngoài ASCII khi lưu."""

    def put_object(self, bucket, name, data, length, content_type="application/octet-stream"):
        super().put_object(bucket, name.encode("ascii", "ignore").decode(), data, length, content_type)


class PlusBecomesSpaceS3(FakeS3):
    """Lỗi: danh sách trả dấu + thành khoảng trắng (mã hóa URL không đúng ở một phía)."""

    def list_objects(self, bucket, prefix=None, recursive=False):
        for listed in super().list_objects(bucket, prefix, recursive):
            yield _Listed(listed.object_name.replace("+", " "), listed.size, listed.is_dir)


class IgnoresOverwriteS3(FakeS3):
    """Lỗi: ghi đè lên khóa đã có bị bỏ qua, nội dung cũ vẫn giữ nguyên."""

    def put_object(self, bucket, name, data, length, content_type="application/octet-stream"):
        if name in self.buckets[bucket]:
            data.read(length)
            return
        super().put_object(bucket, name, data, length, content_type)


class ForbidMakeBucketS3(FakeS3):
    """Lỗi: khóa không được phép tạo bucket (như Garage khi chưa cấp quyền tạo bucket)."""

    def __init__(self, precreated: str) -> None:
        super().__init__()
        self.buckets[precreated] = {}

    def make_bucket(self, bucket: str) -> None:
        raise _s3_error("AccessDenied")


class HidesExistingBucketS3(ForbidMakeBucketS3):
    """Lỗi: bucket có sẵn nhưng bucket_exists báo False (khóa chỉ có quyền đọc/ghi bị từ chối HEAD bucket)."""

    def bucket_exists(self, bucket: str) -> bool:
        return False


def _result(results, name_part: str):
    matches = [r for r in results if name_part in r.name]
    assert matches, f"không có kết quả nào có tên chứa {name_part!r}: {[r.name for r in results]}"
    return matches[0]


def test_correct_s3_passes_small_object_round_trip():
    results = run_checks(FakeS3(), "probe-bucket")

    assert _result(results, "put/stat/get small").ok


def test_correct_s3_creates_and_finds_the_bucket():
    results = run_checks(FakeS3(), "probe-bucket")

    assert _result(results, "make_bucket").ok


def test_forbidden_bucket_creation_is_reported_and_checks_continue_in_the_fallback_bucket():
    s3 = ForbidMakeBucketS3(precreated="hrms-attachments-prod")

    results = run_checks(s3, "probe-bucket", fallback_bucket="hrms-attachments-prod")

    creation = _result(results, "make_bucket")
    assert not creation.ok
    assert "AccessDenied" in creation.detail
    assert _result(results, "put/stat/get small").ok


def test_fallback_bucket_is_confirmed_to_exist_the_way_the_app_checks_it_at_startup():
    s3 = ForbidMakeBucketS3(precreated="hrms-attachments-prod")

    results = run_checks(s3, "probe-bucket", fallback_bucket="hrms-attachments-prod")

    assert _result(results, "bucket_exists(existing").ok


def test_existing_bucket_reported_as_missing_is_flagged():
    s3 = HidesExistingBucketS3(precreated="hrms-attachments-prod")

    results = run_checks(s3, "probe-bucket", fallback_bucket="hrms-attachments-prod")

    assert not _result(results, "bucket_exists(existing").ok


def test_forbidden_bucket_creation_without_a_fallback_bucket_stops_cleanly():
    results = run_checks(ForbidMakeBucketS3(precreated="anything"), "probe-bucket")

    assert any(not r.ok and "make_bucket" in r.name for r in results)
    assert not any("small" in r.name for r in results)


def test_correct_s3_reports_missing_things_as_s3_errors():
    results = run_checks(FakeS3(), "probe-bucket")

    assert _result(results, "bucket_exists(missing").ok
    assert _result(results, "remove_object then stat").ok
    assert _result(results, "get missing key").ok
    assert _result(results, "stat on missing bucket").ok


def test_server_that_claims_every_bucket_exists_is_flagged():
    results = run_checks(AlwaysExistsS3(), "probe-bucket")

    assert not _result(results, "bucket_exists(missing").ok


def test_delete_that_removes_nothing_is_flagged():
    results = run_checks(NoopRemoveS3(), "probe-bucket")

    removal = _result(results, "remove_object then stat")
    assert not removal.ok
    assert "vẫn còn" in removal.detail


def test_missing_key_that_yields_data_instead_of_an_error_is_flagged():
    results = run_checks(LenientGetS3(), "probe-bucket")

    assert not _result(results, "get missing key").ok


def test_missing_key_read_that_fails_with_an_unrelated_error_code_is_flagged():
    results = run_checks(RejectsMissingKeyReadsWithWrongCodeS3(), "probe-bucket")

    missing = _result(results, "get missing key")
    assert not missing.ok
    assert "AuthorizationHeaderMalformed" in missing.detail


def test_stat_on_a_missing_bucket_that_fails_with_an_unrelated_error_code_is_flagged():
    results = run_checks(RejectsMissingBucketStatWithWrongCodeS3(), "probe-bucket")

    assert not _result(results, "stat on missing bucket").ok


def test_correct_s3_round_trips_a_vietnamese_name_with_spaces_and_symbols():
    results = run_checks(FakeS3(), "probe-bucket")

    assert _result(results, "unicode").ok


def test_names_that_lose_non_ascii_characters_are_flagged():
    results = run_checks(FoldingNamesS3(), "probe-bucket")

    named = _result(results, "unicode")
    assert not named.ok
    assert _result(results, "put/stat/get small").ok


def test_names_whose_plus_sign_comes_back_as_a_space_are_flagged():
    results = run_checks(PlusBecomesSpaceS3(), "probe-bucket")

    named = _result(results, "unicode")
    assert not named.ok
    assert "+" in named.detail


def test_correct_s3_overwrites_an_existing_key():
    results = run_checks(FakeS3(), "probe-bucket")

    assert _result(results, "overwrite").ok


def test_server_that_ignores_overwrites_is_flagged():
    results = run_checks(IgnoresOverwriteS3(), "probe-bucket")

    assert not _result(results, "overwrite").ok


def test_correct_s3_round_trips_a_multipart_sized_object_with_identical_sha256():
    results = run_checks(FakeS3(), "probe-bucket")

    assert _result(results, "12 MiB").ok


def test_corrupted_large_object_is_flagged_by_sha256_while_small_objects_still_pass():
    results = run_checks(CorruptingLargeObjectsS3(), "probe-bucket")

    large = _result(results, "12 MiB")
    assert not large.ok
    assert "sha256" in large.detail
    assert _result(results, "put/stat/get small").ok


def test_probe_removes_everything_it_created_including_the_bucket_it_made():
    s3 = FakeS3()

    results = run_checks(s3, "probe-bucket")

    assert _result(results, "cleanup").ok
    assert s3.buckets == {}


def test_probe_leaves_a_pre_existing_fallback_bucket_in_place_but_free_of_probe_objects():
    s3 = ForbidMakeBucketS3(precreated="hrms-attachments-prod")
    s3.buckets["hrms-attachments-prod"]["contracts/1/real-file.pdf"] = (b"real data", "application/pdf")

    run_checks(s3, "probe-bucket", fallback_bucket="hrms-attachments-prod")

    assert list(s3.buckets["hrms-attachments-prod"]) == ["contracts/1/real-file.pdf"]


def test_keep_flag_leaves_the_probe_objects_for_inspection():
    s3 = FakeS3()

    run_checks(s3, "probe-bucket", keep=True, many_objects=3)

    assert s3.buckets["probe-bucket"], "mong đợi các object thử vẫn còn khi keep=True"


def test_cleanup_failure_is_reported_as_a_result_instead_of_raising():
    results = run_checks(FailingRemoveS3(), "probe-bucket", many_objects=3)

    assert any(not r.ok and "cleanup" in r.name for r in results)


def test_correct_s3_lists_folders_when_not_recursive():
    results = run_checks(FakeS3(), "probe-bucket")

    assert _result(results, "non-recursive").ok


def test_flat_listing_that_ignores_non_recursive_is_flagged():
    results = run_checks(FlatListingS3(), "probe-bucket")

    assert not _result(results, "non-recursive").ok


def test_correct_s3_lists_more_than_a_thousand_objects():
    results = run_checks(FakeS3(), "probe-bucket")

    assert _result(results, "paginated list").ok


def test_listing_that_stops_at_a_thousand_objects_is_flagged_without_hiding_other_checks():
    results = run_checks(TruncatingListS3(), "probe-bucket")

    listing = _result(results, "paginated list")
    assert not listing.ok
    assert "1000 of 1050" in listing.detail
    assert _result(results, "put/stat/get small").ok


@pytest.fixture
def credentials(monkeypatch):
    monkeypatch.setenv("S3_PROBE_ACCESS_KEY", "GKtestaccess")
    monkeypatch.setenv("S3_PROBE_SECRET_KEY", "testsecret-do-not-print")


def test_cli_prints_a_pass_line_per_check_and_exits_zero_for_a_correct_s3(credentials, capsys):
    exit_code = main(["--endpoint", "garage:3900"], make_client=lambda **_: FakeS3())

    out = capsys.readouterr().out
    assert exit_code == 0
    assert "PASS" in out and "FAIL" not in out
    assert "cleanup" in out


def test_cli_exits_one_and_names_the_failing_check_for_a_defective_s3(credentials, capsys):
    exit_code = main(["--endpoint", "garage:3900"], make_client=lambda **_: TruncatingListS3())

    out = capsys.readouterr().out
    assert exit_code == 1
    assert "FAIL" in out and "1000 of 1050" in out


def test_cli_refuses_to_run_without_credentials_and_explains_why(monkeypatch, capsys):
    monkeypatch.delenv("S3_PROBE_ACCESS_KEY", raising=False)
    monkeypatch.delenv("S3_PROBE_SECRET_KEY", raising=False)

    exit_code = main(["--endpoint", "garage:3900"], make_client=lambda **_: FakeS3())

    assert exit_code == 2
    assert "S3_PROBE_ACCESS_KEY" in capsys.readouterr().err


def test_cli_never_prints_the_secret_key(credentials, capsys):
    main(["--endpoint", "garage:3900"], make_client=lambda **_: FakeS3())

    captured = capsys.readouterr()
    assert "testsecret-do-not-print" not in captured.out + captured.err
