# ElectroMart
ElectroMart E-commerce Website
## Khởi tạo dữ liệu

```bash
python Database/seed_data.py       # danh mục, thương hiệu, sản phẩm
python Database/seed_accounts.py   # tài khoản admin + khách + B2B (CV41/CV43)
python Database/seed_sales.py      # đơn hàng mẫu + mã giảm giá (CV40)
```

`seed_accounts.py` chạy lại được nhiều lần (khớp theo email rồi cập nhật, không
tạo trùng, không xoá tài khoản ai đã tự đăng ký). Thêm `--reset` nếu muốn xoá
sạch `users / addresses / wholesale_profiles / quotations` trước khi seed.

### Tài khoản demo

| Loại | Email | Mật khẩu |
| --- | --- | --- |
| Admin | `admin@electromart.vn` | `Admin@1234` |
| Khách lẻ (7 tài khoản) | `an.nguyen@example.com`, … | `Demo@1234` |
| B2B đã duyệt | `mua.hang@techviet.vn`, `sales@dienlanhmienbac.vn` | `Demo@1234` |
| B2B chờ duyệt | `info@robotics-lab.vn` | `Demo@1234` |
| B2B bị từ chối | `contact@linhkien-abc.vn` | `Demo@1234` |

Tài khoản seed được đánh dấu `is_active=True` sẵn, bỏ qua bước xác thực email
(chưa cấu hình SMTP thì `mailer` chỉ in link ra console).

## Gửi email thật (đăng ký & quên mật khẩu)

`Backend/electromart/env.py` nạp file `.env` vào `os.environ` trước khi
`settings.py` đọc — trước đây thiếu bước này nên mọi giá trị trong `.env` đều
bị bỏ qua.

Điền **cả hai** dòng sau vào `.env` là email được gửi thật; để trống thì hệ
thống in email ra terminal:

```env
EMAIL_HOST_USER=tenban@gmail.com
EMAIL_HOST_PASSWORD=abcd efgh ijkl mnop
```

Lấy app password của Gmail: bật **2-Step Verification** cho tài khoản Google,
rồi vào https://myaccount.google.com/apppasswords tạo mật khẩu ứng dụng 16 ký
tự. Đây **không** phải mật khẩu Gmail thường — Google đã chặn đăng nhập SMTP
bằng mật khẩu thường. Khoảng trắng trong app password được tự động loại bỏ.

Kiểm tra cấu hình mà không cần đăng ký tài khoản:

```bash
python Backend/manage.py sendtestmail email-cua-ban@gmail.com
```

Lệnh này in ra cấu hình đang có hiệu lực rồi gửi thử một email, và nếu lỗi thì
in nguyên văn lỗi SMTP kèm nguyên nhân thường gặp (sai app password / cổng 587
bị chặn / lẫn TLS với SSL).

Dùng nhà cung cấp khác thì đổi `EMAIL_HOST`, `EMAIL_PORT` trong `.env`; cổng
465 cần `EMAIL_USE_SSL=1` và `EMAIL_USE_TLS=0`.

Khi deploy, đặt `SITE_BASE_URL` thành domain thật — link kích hoạt và link đặt
lại mật khẩu trong email được dựng từ giá trị này.

> `.env` chứa app password nên **không** được commit. File này đã được bỏ khỏi
> git index; khi thêm biến mới hãy cập nhật `.env.example` (không chứa giá trị
> thật) để cả nhóm biết cần điền gì.

## Trang quản trị

Đăng nhập bằng tài khoản admin ở bảng trên, rồi bấm **🛠 Admin** trên header
để vào Dashboard. Từ đó thanh menu admin có mặt ở **mọi** trang admin nên đi
lại giữa 7 trang của cả 3 module chỉ bằng chuột.

Toàn bộ trang admin nằm dưới `/admin/...` và dùng chung một menu
(`Frontend/templates/admin/_admin_nav.html`), một layout
(`admin/base_admin.html`) và một cơ chế đăng nhập — `@admin_required` của
`accounts/decorators.py`. Menu tự tô sáng trang hiện tại dựa vào
`request.path`, nên gắn `{% include %}` vào một trang là xong, không cần sửa
view.

| Trang | URL | Module |
| --- | --- | --- |
| Dashboard & báo cáo | `/admin/dashboard/` | Sales (Tín) |
| Quản lý đơn hàng | `/admin/orders/` | Sales (Tín) |
| Chi tiết đơn | `/admin/orders/<id>/` | Sales (Tín) |
| Khuyến mãi | `/admin/promotions/` | Sales (Tín) |
| Danh mục / Sản phẩm / Tồn kho | `/admin/categories/` … | Catalogue (Minh) |
| Người dùng & duyệt B2B | `/admin/users/` | Accounts (Lộc) |

Ba URL cũ `/admin-dashboard/`, `/admin-orders/`, `/admin-promotions/` được
redirect sang URL mới nên link cũ không bị 404.

### Dữ liệu

Đơn hàng và mã giảm giá nằm ở 2 collection `orders` và `coupons`
(`Backend/sales/`). Trước đây chúng nằm trong `localStorage` của trình duyệt
nên admin không bao giờ thấy đơn khách đặt. Luồng hiện tại:

`/cart/` (giỏ vẫn ở localStorage) → `/checkout/` → POST `/checkout/place-order/`
→ ghi vào `orders` → hiện ngay ở `/admin/orders/` và tra được ở `/tracking/`.

Giá và phí ship do **server** tính lại từ collection `products`, không tin số
mà trình duyệt gửi lên.
