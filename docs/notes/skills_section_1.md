# Phân Tầng Skills Để Test Model: Hướng Dẫn Phân Biệt Năng Lực Model

Tài liệu này mô tả một phương pháp phân tầng các Skills để test năng lực của các mô hình LLM khác nhau, đặc biệt là để phân biệt sự khác biệt giữa các model "yếu" hơn so với Claude.

---

## Tổng Quan

Ý tưởng chính của phương pháp này là: **Phân tách Skills theo độ khó + Đánh giá có thể lượng hóa được**.

Thông qua việc chia Skills thành 3 tầng, chúng ta có thể:

1. **Lọc nhanh**: Dùng các task đơn giản để loại bỏ các model có năng lực không đủ
2. **Phân biệt sâu**: Dùng các task phức tạp để xác minh năng lực thực sự của model
3. **Đánh giá tự động**: Cố gắng dùng script để tự động đánh giá pass/fail, giảm thiểu can thiệp thủ công

---

## Danh Sách Skills Và Yêu Cầu Năng Lực

Trước khi đi vào chi tiết từng tầng, hãy xem qua 17 Skills và yêu cầu năng lực của chúng:

| Skill | Yêu cầu năng lực chính | Độ khó đánh giá |
|-------|------------------------|-----------------|
| slack-gif-creator | Tuân thủ nghiêm ngặt ràng buộc kỹ thuật | ⭐⭐⭐ Dễ |
| xlsx | Xử lý công thức, mô hình dữ liệu | ⭐⭐⭐ Dễ |
| docx | Cấu trúc tài liệu, định dạng | ⭐⭐ Trung bình |
| webapp-testing | Phân tích DOM, viết code, debug | ⭐⭐ Trung bình |
| pdf | Thao tác PDF (nâng cao) | ⭐⭐ Trung bình |
| mcp-builder | Tích hợp API, thiết kế kiến trúc | ⭐ Khó |
| frontend-design | Thẩm mỹ, tư duy thiết kế | ⭐ Chủ quan |
| algorithmic-art | Tư duy thuật toán, sáng tạo | ⭐ Chủ quan |
| Các skill khác | Năng lực hỗn hợp | Tùy trường hợp |

---

## Tầng 1: Test Tuân Thủ Format

### Mục Tiêu

Test xem model có thể **tuân thủ nghiêm ngặt các ràng buộc kỹ thuật rõ ràng** hay không. Đây là bài test cơ bản nhất, kiểm tra xem model có hiểu và thực thi "quy tắc" hay không.

### Skill Đề Xuất

#### 1. slack-gif-creator (Khuyến Nghị Mạnh)

**Tại sao chọn:**

- Ràng buộc cực kỳ rõ ràng và có thể đo lường được
- Slack có yêu cầu kỹ thuật nghiêm ngặt cho file GIF (dung lượng, kích thước, frame rate)
- Dễ dàng tự động verify

**Bảng ràng buộc kỹ thuật:**

| Thông số | Slack Emoji GIF | Slack Message GIF |
|----------|-----------------|-------------------|
| Kích thước | 128×128 px | 480×480 px |
| Dung lượng file | < 1 MB | < 1 MB |
| Frame rate | 10-30 FPS | 10-30 FPS |
| Thời lượng | ≤ 3 giây | ≤ 3 giây |
| Số màu | 48-128 | 48-128 |

**Cách test:**

```
Prompt: "Tạo một icon GIF loading để dùng cho Slack"
```

**Cách model yếu sẽ fail:**

- Quên không resize về đúng kích thước, để 800×800 pixel
- Không nén file, để dung lượng 5MB+
- Frame rate quá cao dẫn đến file quá lớn
- Sử dụng sai color mode

**Cách đánh giá:**

```python
from PIL import Image
import os

def validate_slack_gif(filepath):
    img = Image.open(filepath)

    # Kiểm tra kích thước
    if img.size not in [(128, 128), (480, 480)]:
        return False, f"Kích thước sai: {img.size}"

    # Kiểm tra dung lượng file
    if os.path.getsize(filepath) > 1024 * 1024:
        return False, f"File quá lớn: {os.path.getsize(filepath)} bytes"

    # Kiểm tra số frame/thời lượng
    duration = img.info.get('duration', 0)
    n_frames = getattr(img, 'n_frames', 1)
    if n_frames * duration / 1000 > 3:
        return False, f"Thời lượng quá 3 giây"

    return True, "Pass"
```

---

#### 2. xlsx (Khuyến Nghị Mạnh)

**Tại sao chọn:**

- Excel có tiêu chuẩn ngành rõ ràng (mã màu, quy tắc công thức)
- Có thể tự động phát hiện lỗi công thức
- Financial model là một test case tốt

**Bảng ràng buộc kỹ thuật:**

| Yếu tố | Quy tắc |
|--------|---------|
| Font | Arial hoặc Times New Roman |
| Lỗi công thức | Zero tolerance (#REF!, #DIV/0!, #VALUE!, #N/A, #NAME?) |
| Màu xanh dương | Giá trị input được hardcode |
| Màu đen | Công thức và tính toán |
| Màu xanh lục | Tham chiếu trong cùng workbook |

**Cách test:**

```
Prompt: "Tạo một financial model từ dữ liệu sau, gồm: income statement, balance sheet, cash flow statement"
```

**Cách model yếu sẽ fail:**

- Công thức bị lỗi #REF! hoặc #DIV/0!
- Mã màu lộn xộn (nên dùng đen lại dùng xanh dương)
- Circular reference không được giải quyết
- Dùng giá trị hardcode thay vì công thức

**Cách đánh giá:**

```python
from openpyxl import load_workbook

def validate_xlsx(filepath):
    wb = load_workbook(filepath, data_only=False)

    # Kiểm tra lỗi công thức
    for sheet in wb:
        for row in sheet.iter_rows():
            for cell in row:
                if cell.value and isinstance(cell.value, str):
                    if any(err in str(cell.value) for err in ['#REF!', '#DIV/0!', '#VALUE!', '#N/A', '#NAME?']):
                        return False, f"Lỗi công thức tại {cell.coordinate}: {cell.value}"

    return True, "Pass"
```

---

#### 3. docx (Tùy Chọn)

**Tại sao chọn:**

- Test khả năng cấu trúc tài liệu
- Word format đa dạng (table of contents, header/footer, styles)

**Cách test:**

```
Prompt: "Chuyển đoạn text dưới đây thành file Word với: tiêu đề H1, mục lục ở trang 1, có header/footer"
```

**Cách model yếu sẽ fail:**

- Cấu trúc mục lục không đúng
- Thiếu metadata
- Mất style
- Mất nội dung (do hallucinate)

**Cách đánh giá:**

Cần unpack file .docx (thực chất là ZIP) và parse XML để kiểm tra cấu trúc.

---

### Tóm Tắt Tầng 1

| Skill | Mức độ tự động | Ưu tiên |
|-------|----------------|---------|
| slack-gif-creator | ⭐⭐⭐ Hoàn toàn tự động | ⭐⭐⭐ Cao nhất |
| xlsx | ⭐⭐⭐ Hoàn toàn tự động | ⭐⭐⭐ Cao nhất |
| docx | ⭐⭐ Tự động một phần | ⭐⭐ Trung bình |

---

## Tầng 2: Test Tư Duy Lập Trình Và Web

### Mục Tiêu

Test xem model có thể **viết code có thể chạy được**, hiểu cấu trúc DOM, và sử dụng đúng tools và frameworks.

### Skill Đề Xuất

#### webapp-testing (Khuyến Nghị Mạnh)

**Tại sao chọn:**

- Yêu cầu model đọc tài liệu, hiểu tools mà hệ thống cung cấp
- Cần phân tích HTML DOM và viết selectors
- Code có thể chạy được hay không rõ ràng (pass/fail)
- Phân biệt rõ nhất giữa "biết code" và "biết code chạy được"

**Cách test:**

1. Cung cấp một file HTML đơn giản (chứa form đăng nhập)
2. Prompt:
   ```
   Sử dụng script helper scripts/with_server.py được cung cấp trong skill này,
   viết một Playwright test script để test form đăng nhập này:
   - Nhập username và password
   - Click nút đăng nhập
   - Verify đăng nhập thành công
   ```

**Cách model yếu sẽ fail:**

| Loại lỗi | Biểu hiện cụ thể |
|----------|------------------|
| Selector sai | Bịa đặt ID/class không tồn tại trong HTML (ví dụ `id="btn"` nhưng thực tế là `<button class="submit">`) |
| Bỏ qua tool | Không dùng `scripts/with_server.py`, tự viết code khởi động server, dễ bị lỗi |
| Lỗi cú pháp | Dùng sai Playwright API |
| Timeout | Không tìm được element dẫn đến `TimeoutError` |

**Cách model tốt (Claude) sẽ làm:**

- Đọc tài liệu của skill trước để hiểu cách dùng tool
- Dùng semantic selectors như `text=` hoặc `role=`
- Gọi đúng helper script
- Code结构清晰, dễ debug

**Cách đánh giá:**

```bash
# Chạy trực tiếp script mà model tạo ra
python test_script.py

# Kiểm tra exit code
if $? == 0: echo "Pass"
else: echo "Fail"
```

```python
# Hoặc dùng Python để kiểm tra
import subprocess

result = subprocess.run(
    ['python', 'test_script.py'],
    capture_output=True,
    timeout=30
)

if result.returncode == 0:
    print("✅ Test pass")
else:
    print(f"❌ Test fail: {result.stderr}")
```

---

#### Biến thể nâng cao: web-artifacts-builder

Nếu muốn test năng lực frontend phức tạp hơn, có thể dùng skill này:

- Yêu cầu tạo project React + Tailwind
- Có state management, routing
- Cuối cùng bundle thành một file HTML

**Cách model yếu sẽ fail:**

- Lỗi cài đặt dependencies
- Lỗi khi bundle
- Lỗi khi chạy

---

### Tóm Tắt Tầng 2

| Skill | Mức độ tự động | Ưu tiên |
|-------|----------------|---------|
| webapp-testing | ⭐⭐⭐ Hoàn toàn tự động | ⭐⭐⭐ Cao nhất |
| web-artifacts-builder | ⭐⭐ Tự động một phần | ⭐⭐ Trung bình |

---

## Tầng 3: Test Tư Duy Trừu Tượng Và Thẩm Mỹ

### Mục Tiêu

Test năng lực **hiểu khái niệm trừu tượng** và **thẩm mỹ** của model. Tầng này rất khó đánh giá tự động, nhưng sự khác biệt có thể nhìn thấy bằng mắt thường.

### Skill Đề Xuất

#### 1. frontend-design (Khuyến Nghị Mạnh)

**Tại sao chọn:**

- Nghiêm cấm tuyệt đối thẩm mỹ "AI slop" (layout giữa màn hình, font Inter, nền trắng chữ xám)
- Yêu cầu hướng thiết kế "Bold" (mạnh mẽ, phá cách)
- Kiểm tra khả năng hiểu khái niệm trừu tượng (Brutalist, Minimalist, Retro-futuristic, etc.)

**Cách test:**

```
Prompt: "Thiết kế một Landing Page bán đồng hồ xa xỉ, phong cách Brutalist (thô mộc)"
```

**Cách model yếu sẽ fail:**

- Dù có bảo "làm cho khác biệt đi", vẫn ra Bootstrap style
- Header màu xanh dương, nền trắng, căn giữa
- Không hiểu được các khái niệm trừu tượng như "thô mộc", "tinh tế", "hỗn loạn có kiểm soát"
- Trang web nhìn như bài tập của sinh viên năm 1

**Cách model tốt (Claude) sẽ làm:**

- Hiểu hướng thiết kế và chọn font, màu phù hợp
- Phá vỡ layout truyền thống
- Chi tiết tinh tế (animation, spacing, depth)

**Cách đánh giá:**

- Đánh giá thủ công (hoặc dùng visual regression testing)
- Chỉ tiêu quan trọng: Nhìn có giống "AI generate" hay "design chuyên nghiệp"

---

#### 2. algorithmic-art

**Tại sao chọn:**

- Cần hiểu tư duy thuật toán (particle systems, flow fields, noise functions)
- Cần khả năng sáng tạo
- Artwork đầu ra khác biệt rõ rệt

**Cách test:**

```
Prompt: "Tạo một tác phẩm nghệ thuật thuật toán, chủ đề 'quantum fluctuations'"
```

**Cách model yếu sẽ fail:**

- Xuất ảnh tĩnh thay vì generative art
- Thuật toán quá đơn giản (chỉ là các chấm ngẫu nhiên)
- Thiếu biểu đạt chủ đề

---

### Tóm Tắt Tầng 3

| Skill | Cách đánh giá | Ưu tiên |
|-------|---------------|---------|
| frontend-design | Thủ công/Visual regression | ⭐⭐ Cần người |
| algorithmic-art | Thủ công/Visual regression | ⭐⭐ Cần người |

---

## Quy Trình Test Hoàn Chỉnh Đề Xuất

### Thứ Tự Test Đề Xuất

```
Tầng 1 (Bắt buộc)
    ↓
Pass → Qua Tầng 2
Fail → Dừng lại (Model năng lực không đủ)

Tầng 2 (Bắt buộc)
    ↓
Pass → Qua Tầng 3 (Tùy chọn)
Fail → Dừng lại (Model năng lực logic không đủ)

Tầng 3 (Tùy chọn)
    ↓
Đánh giá thẩm mỹ thiết kế
```

### Khung Script Test Tự Động

```python
#!/usr/bin/env python3
"""Khung test phân tầng Skills"""

import os
import sys
import subprocess
import tempfile
from pathlib import Path

def test_tier_1_slack_gif():
    """Tầng 1: Test Slack GIF"""
    print("\n🧪 Test Tầng 1: slack-gif-creator")

    # 1. Gọi model để tạo GIF
    prompt = "Tạo một GIF loading cho Slack, 128x128 pixels"
    # ... code gọi model ...

    # 2. Validate kết quả
    from PIL import Image
    img = Image.open("output.gif")

    checks = {
        "Kích thước": img.size == (128, 128),
        "Dung lượng": os.path.getsize("output.gif") < 1024*1024,
    }

    for name, passed in checks.items():
        status = "✅" if passed else "❌"
        print(f"  {status} {name}")

    return all(checks.values())

def test_tier_2_webapp():
    """Tầng 2: Test Web App"""
    print("\n🧪 Test Tầng 2: webapp-testing")

    # 1. Tạo HTML test
    html_file = create_login_form()

    # 2. Gọi model tạo test script
    prompt = f"Viết Playwright test cho form đăng nhập này: {html_file}"
    # ... code gọi model ...

    # 3. Chạy test script
    result = subprocess.run(
        ['python', 'test_login.py'],
        capture_output=True,
        timeout=30
    )

    passed = result.returncode == 0
    status = "✅" if passed else "❌"
    print(f"  {status} Chạy test: {'Pass' if passed else 'Fail'}")

    if not passed:
        print(f"  Lỗi: {result.stderr.decode()}")

    return passed

def main():
    print("=" * 50)
    print("Khung Test Phân Tầng Skills")
    print("=" * 50)

    # Tầng 1
    if not test_tier_1_slack_gif():
        print("\n⚠️ Tầng 1 fail, dừng test")
        return

    # Tầng 2
    if not test_tier_2_webapp():
        print("\n⚠️ Tầng 2 fail, dừng test")
        return

    print("\n🎉 Tất cả test pass!")

if __name__ == "__main__":
    main()
```

---

## Tổng Kết

| Tầng | Skill | Kiểm tra | Tự động | Ưu tiên |
|------|-------|----------|---------|---------|
| 1 | slack-gif-creator | Tuân thủ quy tắc | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| 1 | xlsx | Chuẩn công thức | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| 1 | docx | Cấu trúc tài liệu | ⭐⭐ | ⭐⭐⭐ |
| 2 | webapp-testing | Năng lực lập trình | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| 2 | web-artifacts-builder | Phát triển frontend | ⭐⭐ | ⭐⭐⭐ |
| 3 | frontend-design | Năng lực thẩm mỹ | ⭐ | ⭐⭐⭐ |
| 3 | algorithmic-art | Tính sáng tạo | ⭐ | ⭐⭐ |

### Gợi Ý Quan Trọng

1. **Bắt đầu từ Tầng 1**: Lọc nhanh, dễ tự động hóa
2. **webapp-testing là test tối thượng**: Code có thể chạy là thước đo cứng, không thể giả dối
3. **Tầng 3 cần can thiệp thủ công**: Nhưng có thể phát hiện khoảng cách về "gu thẩm mỹ" và "hiểu khái niệm trừu tượng"
4. **Chọn model để so sánh**: Nên dùng Claude 3 Haiku, GPT-4o mini, Gemini Flash làm baseline để so sánh
