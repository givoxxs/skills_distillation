# Hướng dẫn cài đặt MemPalace cho Claude Code

**MemPalace** là hệ thống bộ nhớ dài hạn cho AI, chạy hoàn toàn offline trên máy cục bộ.
Nó lưu code, hội thoại, quyết định vào một vector database (ChromaDB) và cung cấp context
cho Claude qua MCP protocol khi bắt đầu session mới.

- **Repo chính thức:** [github.com/MemPalace/mempalace](https://github.com/MemPalace/mempalace)
- **Docs:** [mempalaceofficial.com](https://mempalaceofficial.com)
- **Hướng dẫn Claude Code:** [mempalace.tech/guides/setup](https://www.mempalace.tech/guides/setup)

---

## Yêu cầu

- Python 3.10+
- Claude Code CLI
- `pipx` hoặc `uv` (khuyến nghị hơn pip để tránh conflict)

---

## Bước 1 — Cài đặt MemPalace

```bash
# Dùng pipx (khuyến nghị)
pipx install mempalace

# Hoặc dùng uv
uv tool install mempalace

# Xác nhận
mempalace --version
# → MemPalace 3.3.3
```

> **Tại sao pipx/uv?** Chúng tạo virtual environment riêng, tránh conflict với Python system.

---

## Bước 2 — Đăng ký MCP server với Claude Code

```bash
claude mcp add mempalace -- mempalace-mcp
```

Lệnh này ghi vào `~/.claude.json` (hoặc project-local config nếu chạy từ trong project):

```json
{
  "mcpServers": {
    "mempalace": {
      "command": "mempalace-mcp",
      "args": []
    }
  }
}
```

> Muốn palace ở đường dẫn tùy chọn:
> ```bash
> claude mcp add mempalace -- mempalace-mcp --palace /đường/dẫn/tùy/chọn
> ```

---

## Bước 3 — Bật MCP server trong settings.json

Mở `~/.claude/settings.json` và thêm `enabledMcpjsonServers`:

```json
{
  "enabledMcpjsonServers": ["mempalace"]
}
```

Nếu file đã có các key khác, chỉ thêm dòng `enabledMcpjsonServers` vào — không ghi đè toàn bộ file.

---

## Bước 4 — Cài đặt Stop Hook (auto-save sau mỗi session)

Hook này tự động lưu diary sau mỗi session Claude Code kết thúc.
Thêm vào `~/.claude/settings.json`:

```json
{
  "enabledMcpjsonServers": ["mempalace"],
  "hooks": {
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "/home/<username>/.local/bin/mempalace hook run --hook stop --harness claude-code",
            "timeout": 60
          }
        ]
      }
    ]
  }
}
```

Thay `<username>` bằng username thực. Kiểm tra đường dẫn chính xác:

```bash
which mempalace
# → /home/sangnguyen/.local/bin/mempalace
```

---

## Bước 5 — Khởi tạo palace cho từng project

Chạy lệnh này trong thư mục project:

```bash
cd /path/to/your/project
mempalace init .
```

MemPalace sẽ tự phát hiện cấu trúc thư mục và tạo file `mempalace.yaml`, ví dụ:

```yaml
wing: model_training
rooms:
  - name: scripts
    description: Files from scripts/
    keywords: [scripts]
  - name: documentation
    description: Files from docs/
    keywords: [docs]
  - name: docker
    description: Files from docker/
    keywords: [docker]
  - name: general
    description: Files that don't fit other rooms
    keywords: []
```

> Dùng `--yes` để bỏ qua confirm: `mempalace init . --yes`

---

## Bước 6 — Mine code vào palace

```bash
# Mine toàn bộ project
mempalace mine .

# Giới hạn số file (project lớn)
mempalace mine . --limit 1000

# Xem trước, không ghi
mempalace mine . --dry-run
```

Sau khi mine, kiểm tra trạng thái:

```bash
mempalace status
# Hiển thị số drawers theo wing/room
```

---

## Bước 7 — Cấu hình Permission (giảm prompt xác nhận)

Tạo hoặc chỉnh `.claude/settings.local.json` trong project:

```json
{
  "permissions": {
    "allow": [
      "mcp__mempalace__mempalace_status",
      "mcp__mempalace__mempalace_search",
      "mcp__mempalace__mempalace_kg_query",
      "mcp__mempalace__mempalace_diary_read",
      "mcp__mempalace__mempalace_diary_write",
      "mcp__mempalace__mempalace_add_drawer",
      "mcp__mempalace__mempalace_kg_add"
    ]
  }
}
```

---

## Bước 8 — Thêm Memory Protocol vào CLAUDE.md

Thêm đoạn này vào `CLAUDE.md` của project (hoặc `~/.claude/CLAUDE.md` để áp dụng toàn bộ):

```markdown
## MemPalace Memory Protocol

Apply when MCP server `mempalace` is available.

1. **ON WAKE-UP:** Call `mempalace_status` to load palace overview.
2. **BEFORE RESPONDING** about any person, project, or past event: call `mempalace_kg_query` or `mempalace_search` FIRST.
3. **IF UNSURE** about a fact: say "let me check" and query the palace.
4. **AFTER EACH SESSION:** Call `mempalace_diary_write` to record what happened.
5. **WHEN FACTS CHANGE:** Call `mempalace_kg_invalidate` then `mempalace_kg_add`.
```

---

## Kiểm tra toàn bộ setup

```bash
# 1. Binary hoạt động
mempalace --version

# 2. Trạng thái palace
mempalace status

# 3. Xem lệnh MCP server
mempalace mcp

# 4. Test search
mempalace search "tên function hoặc concept"
```

Trong Claude Code, restart session rồi chạy `/mcp` — sẽ thấy `mempalace` trong danh sách tools.

---

## Flow hoạt động

```
Lần đầu setup:
  pipx install mempalace
      ↓
  claude mcp add mempalace -- mempalace-mcp
      ↓
  cập nhật settings.json  (bật server + Stop hook)
      ↓
  mempalace init .         (tạo mempalace.yaml)
      ↓
  mempalace mine .         (nạp code vào palace)

Mỗi session Claude Code:
  Claude bắt đầu  →  mempalace_status (load overview)
      ↓
  Claude làm việc →  search/query palace khi cần context
      ↓
  Claude kết thúc →  Stop hook → mempalace_diary_write (tự động)
```

---

## Troubleshooting

| Triệu chứng | Nguyên nhân | Fix |
|---|---|---|
| `mcp__mempalace__*` không xuất hiện trong `/mcp` | `enabledMcpjsonServers` thiếu hoặc MCP chưa đăng ký | Kiểm tra `settings.json` và chạy lại `claude mcp add` |
| Stop hook không chạy | Đường dẫn `mempalace` sai | Chạy `which mempalace` để lấy đúng path |
| `mempalace mine` rất chậm | Project quá lớn | Dùng `--limit 1000` để mine từng phần |
| Palace trống sau khi mine | `.gitignore` filter quá mạnh | Dùng `--include-ignored path/` |
| Segfault sau update | ChromaDB index corrupt | Chạy `mempalace repair` |
| `/mcp` thấy server nhưng tools lỗi | Server chưa restart sau cài | Restart Claude Code hoàn toàn |

---

## Tài liệu tham khảo

- [GitHub Repo](https://github.com/MemPalace/mempalace)
- [Official Docs](https://mempalaceofficial.com)
- [Setup Guide (mempalace.tech)](https://www.mempalace.tech/guides/setup)
- [Blog: Add Persistent Memory to Claude Code](https://www.mempalace.tech/blog/add-memory-to-claude-code)
- [MCP Tools Reference](https://mempalaceofficial.com/reference/mcp-tools)
- [Claude Code MCP Docs](https://code.claude.com/docs/en/mcp)
