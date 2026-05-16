# Screenshots — capture guide

Cần 4 ảnh PNG chèn vào root `README.md` (đường dẫn đã có sẵn — chỉ thiếu file).

## Chuẩn bị

Mở `https://skills-distillation.vercel.app` ở Chrome / Safari, viewport
≥ 1280 px chiều ngang (toàn màn hình laptop là OK). Theme **light** cho
ảnh ra sạch nhất.

## 5 ảnh cần chụp

| Tên file | URL | Khung hình bao trùm | Kích thước gợi ý |
|---|---|---|---|
| `01_overview.png` | `/` | Toàn page: 3 KPI card + section "Ba skill, ba quỹ đạo học" với 3 skill card (sparkline) | 1280 × 1024 |
| `02_skill_detail_learning_curve.png` | `/skills/docx` | Header stats + Panel 1 learning curve (peak R5 amber) | 1280 × 800 |
| `02_skill_detail_diff.png` | `/skills/docx` | Panel 2 diff side-by-side với selector From R0 / To R5 | 1280 × 800 |
| `03_live_run.png` | `/run` đang chạy giữa chừng | Stepper đang ở "running" hoặc "judging", learning curve đã có vài round, log stream visible | 1280 × 1200 |
| `04_about.png` | `/about` | Toàn page: thông tin đề tài + abstract + tech stack badges | 1280 × 900 |

## Tools chụp

- **macOS:** Cmd-Shift-4 → Space → click cửa sổ; hoặc Cmd-Shift-5 → "Capture Selected Window"
- **Chrome DevTools:** Cmd-Shift-P → "Capture full size screenshot" cho ảnh đầy đủ kể cả khu vực phải scroll
- **Sau khi chụp:** chạy `sips -Z 1280 *.png` để resize về tối đa 1280 px (giảm dung lượng repo)

## Đặt file

```
docs/screenshots/
├── README.md          ← file này
├── 01_overview.png
├── 02_skill_detail.png
├── 03_live_run.png
└── 04_about.png
```

Đường dẫn từ root README đã chốt — chỉ cần đúng tên file là hiển thị.

## Tuỳ chọn — Social preview image cho GitHub

GitHub repo → Settings → Social preview: tải lên 1 ảnh 1280 × 640 px,
nội dung gợi ý: header dashboard + tên thesis + số `R1 → 0.921 (peak)`.
Khi link repo share lên Twitter / Facebook sẽ hiển thị đẹp.
