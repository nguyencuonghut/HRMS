# HRMS Hồng Hà — Lưu trữ tệp và sao lưu

Hệ thống quản trị nhân sự nội bộ của Hồng Hà. Tài liệu này chỉ ghi các thuật ngữ về nơi lưu tệp và việc sao lưu/khôi phục, theo cách người quản trị gọi trên giao diện Backup Console.

## Language

**Kho tệp ứng dụng**:
Nơi lưu mọi tệp người dùng tải lên: tệp đính kèm hồ sơ, hợp đồng, mẫu văn bản, khen thưởng, kỷ luật, chứng chỉ.
_Avoid_: MinIO, Garage, object storage, bucket, kho S3

**Đích sao lưu**:
Nơi ghi các bản sao lưu của cơ sở dữ liệu và của **Kho tệp ứng dụng**.
_Avoid_: kho backup, backup bucket

**Tác vụ sao lưu**:
Một lần chạy sao lưu, thủ công hoặc theo lịch, cho cơ sở dữ liệu hoặc cho **Kho tệp ứng dụng**.
_Avoid_: job, backup job

**Bộ sao lưu đầy đủ**:
Một lần sao lưu cơ sở dữ liệu rồi đến **Kho tệp ứng dụng**, chạy tuần tự như một đơn vị.
_Avoid_: full backup, backup set

**Khôi phục sang đích mới**:
Khôi phục dữ liệu vào một cơ sở dữ liệu hoặc kho tệp mới, không ghi đè dữ liệu đang chạy.
_Avoid_: restore, khôi phục đè

## Relationships

- Một **Bộ sao lưu đầy đủ** gồm hai **Tác vụ sao lưu**: một cho cơ sở dữ liệu, một cho **Kho tệp ứng dụng**
- Mỗi **Tác vụ sao lưu** thành công ghi một kết quả vào **Đích sao lưu**
- Việc khôi phục chỉ diễn ra qua **Khôi phục sang đích mới**; hệ thống từ chối nếu đích trùng với dữ liệu production hiện tại

## Example dialogue

> **Dev:** "Quản trị viên chạy **Bộ sao lưu đầy đủ** lúc 02:00 nhưng chỉ thấy một **Tác vụ sao lưu** chạy. Có lỗi không?"
> **Chuyên gia:** "Cơ sở dữ liệu được sao lưu trước. Nếu tác vụ đó lỗi thì tác vụ của **Kho tệp ứng dụng** không chạy, và cả bộ bị đánh dấu thất bại."

## Flagged ambiguities

- Nhãn cũ "Kho tệp ứng dụng trên MinIO" gắn tên công nghệ vào thuật ngữ. Đã quyết định (2026-10-30): chỉ dùng **Kho tệp ứng dụng**, để lần đổi công nghệ sau không phải sửa giao diện, test và dữ liệu hiển thị. Code và test e2e hiện vẫn dùng nhãn cũ; đổi ở Slice 3 của `docs/plan_15.7_chuyen_minio_sang_garage.md`.
