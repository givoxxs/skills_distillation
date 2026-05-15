import type { ApiCall, EvalEntry, Kpis, SkillSummary } from "./types";

/* Deterministic PRNG (mulberry32) */
function rng(seed: number) {
  let s = seed | 0;
  return function () {
    s = (s + 0x6d2b79f5) | 0;
    let t = Math.imul(s ^ (s >>> 15), 1 | s);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

export const summaries: Record<string, SkillSummary> = {
  docx: {
    skill: "docx",
    vi: "Tạo & chỉnh sửa văn bản .docx",
    en: "Author and edit .docx documents",
    student_model: "google/gemma-3-26b-it",
    teacher_model: "anthropic/claude-sonnet-4.5",
    judge_model: "anthropic/claude-sonnet-4.5",
    batch_size: 3,
    rounds_run: 8,
    final_score: 0.877,
    best_round: 5,
    best_score: 0.921,
    score_history: [
      { round: 1, avg_score: 0.793 },
      { round: 2, avg_score: 0.812 },
      { round: 3, avg_score: 0.864 },
      { round: 4, avg_score: 0.901 },
      { round: 5, avg_score: 0.921 },
      { round: 6, avg_score: 0.904 },
      { round: 7, avg_score: 0.889 },
      { round: 8, avg_score: 0.877 },
    ],
    rubric_cache_keys: {
      create: "sha256:8c3a…",
      edit: "sha256:b1d4…",
      validate: "sha256:9e22…",
    },
    last_run: "2026-05-12",
    seed: 11,
  },
  "internal-comms": {
    skill: "internal-comms",
    vi: "Soạn thông báo nội bộ",
    en: "Draft internal communications",
    student_model: "google/gemma-3-26b-it",
    teacher_model: "anthropic/claude-sonnet-4.5",
    judge_model: "anthropic/claude-sonnet-4.5",
    batch_size: 3,
    rounds_run: 8,
    final_score: 0.822,
    best_round: 3,
    best_score: 0.823,
    score_history: [
      { round: 1, avg_score: 0.735 },
      { round: 2, avg_score: 0.781 },
      { round: 3, avg_score: 0.823 },
      { round: 4, avg_score: 0.818 },
      { round: 5, avg_score: 0.806 },
      { round: 6, avg_score: 0.811 },
      { round: 7, avg_score: 0.815 },
      { round: 8, avg_score: 0.822 },
    ],
    rubric_cache_keys: {
      compose: "sha256:7f10…",
      validate: "sha256:c0aa…",
    },
    last_run: "2026-05-13",
    seed: 23,
  },
  "slack-gif-creator": {
    skill: "slack-gif-creator",
    vi: "Tạo GIF Slack từ mô tả",
    en: "Create Slack GIFs from a prompt",
    student_model: "google/gemma-3-26b-it",
    teacher_model: "anthropic/claude-sonnet-4.5",
    judge_model: "anthropic/claude-sonnet-4.5",
    batch_size: 3,
    rounds_run: 10,
    final_score: 0.865,
    best_round: 9,
    best_score: 0.886,
    score_history: [
      { round: 1, avg_score: 0.716 },
      { round: 2, avg_score: 0.742 },
      { round: 3, avg_score: 0.78 },
      { round: 4, avg_score: 0.806 },
      { round: 5, avg_score: 0.835 },
      { round: 6, avg_score: 0.851 },
      { round: 7, avg_score: 0.868 },
      { round: 8, avg_score: 0.88 },
      { round: 9, avg_score: 0.886 },
      { round: 10, avg_score: 0.865 },
    ],
    rubric_cache_keys: {
      create: "sha256:1aa9…",
      optimize: "sha256:e57c…",
    },
    last_run: "2026-05-14",
    seed: 47,
  },
};

export const skillList = Object.keys(summaries);

export const workflowsBySkill: Record<string, string[]> = {
  docx: ["create", "read", "edit", "convert", "edge", "compose", "optimize", "validate"],
  "internal-comms": ["create", "edit", "compose", "validate"],
  "slack-gif-creator": ["create", "edit", "convert", "optimize", "edge"],
};

type Seed = [string, string, string, string];

const tcSeeds: Record<string, Seed[]> = {
  docx: [
    [
      "create",
      "Tạo một báo cáo .docx 3 chương về thị trường cà phê Việt Nam Q1/2026, kèm bảng số liệu và mục lục tự động.",
      "Đã tạo `bao-cao-ca-phe-q1-2026.docx` với heading style cấp 1–2, bảng số liệu 3 cột (Vùng, Sản lượng, Giá FOB), trang bìa và mục lục tự động. Khi mở trong Word, mục lục cập nhật được qua F9.",
      "Output is a syntactically valid .docx with a working TOC field. Headings use Heading 1/2 styles so the TOC populates. The table has correct grid borders. The student followed the rule to use python-docx's add_heading API instead of run-level styling. Minor: cover page is sparse but acceptable.",
    ],
    [
      "edit",
      "Mở `kpi-marketing-2026.docx`, thay tất cả 'Q1' bằng 'Quý 1' chỉ trong các đoạn văn (không động đến bảng).",
      "Đã quét toàn bộ paragraph, bỏ qua các cell trong table. Thay 47 lần, giữ nguyên formatting run. Xuất file `kpi-marketing-2026.v2.docx`.",
      "Correctly scoped to paragraphs only. The student preserved run-level formatting (a common failure mode in R1). Hits the rule 'never replace inside table cells unless asked'.",
    ],
    [
      "convert",
      "Chuyển `presentation.pdf` sang `.docx` giữ cấu trúc tiêu đề.",
      "Đã trích văn bản qua pdfplumber, suy heading từ font size > 16pt + bold, ghi ra docx với Heading 1/2 tương ứng. Cảnh báo: 2 trang chứa ảnh không OCR được.",
      "Heuristic for headings is reasonable. Warning about un-OCRed images is the correct refusal.",
    ],
    [
      "validate",
      "Kiểm tra file `hop-dong-mau.docx` xem có headers/footers, page numbers và mục lục không.",
      "Báo cáo: có header (tiêu đề công ty), không có footer, có page number ở cuối trang (field PAGE), có TOC ở trang 2. ✓ 3/4 yêu cầu.",
      "Correct enumeration of features. Score is hybrid because rule_score covered structural checks; judge added context on which feature is missing.",
    ],
    [
      "edge",
      "Sửa file `corrupted.docx` (báo lỗi 'bad zip').",
      "Không thể đọc file: phần header ZIP bị lỗi. Đề xuất: thử khôi phục bằng Word repair hoặc cung cấp bản backup.",
      "Correctly refuses to invent content. Suggests the right recovery path.",
    ],
    [
      "compose",
      "Hợp nhất 3 file `chuong-1.docx`, `chuong-2.docx`, `chuong-3.docx` thành một báo cáo có mục lục.",
      "Đã merge theo thứ tự, giữ nguyên style mỗi file, insert page break giữa các chương, tạo TOC ở đầu. Output: `bao-cao-tong-hop.docx`.",
      "Correct ordering and page breaks. TOC inserted at top, not bottom — matches the rule added in R3.",
    ],
    [
      "read",
      "Trích xuất toàn bộ bảng từ `bao-cao-tai-chinh.docx` ra JSON.",
      "Trả về JSON [{ table_index, rows, cells: [[...]] }]. Phát hiện 5 bảng, 2 bảng có merged cells (được flag).",
      "Good handling of merged cells (flagged rather than silently flattened).",
    ],
    [
      "optimize",
      "File `tai-lieu-300-trang.docx` đang 42 MB. Giảm dung lượng.",
      "Nén ảnh > 96 dpi xuống 96 dpi (giảm 31 MB), bỏ font embedding không dùng (giảm 4 MB). Tổng: 42 → 7 MB. Không đổi nội dung văn bản.",
      "Strong adherence to 'never alter text content' rule.",
    ],
  ],
  "internal-comms": [
    [
      "create",
      "Viết thông báo cho toàn công ty: đường truyền internet sẽ ngắt 02:00–04:00 thứ Bảy để bảo trì.",
      "Subject: Lịch bảo trì hạ tầng mạng — thứ Bảy 02:00–04:00\n\nXin chào team,\n\nĐội Hạ tầng sẽ tiến hành bảo trì định kỳ trong khoảng 02:00–04:00 sáng thứ Bảy. Trong khoảng này, kết nối VPN, email và Slack có thể gián đoạn ~10 phút.\n\nKhuyến nghị: lưu công việc trước 01:50.\n\nLiên hệ: ops@…",
      "Hits all 4 rules: clear subject, exact time window, affected services enumerated, action item for reader, contact channel. Tone is calm, no exclamation.",
    ],
    [
      "edit",
      "Rút gọn email dưới đây xuống tối đa 80 từ, giữ nguyên 3 điểm chính.",
      "Bản rút gọn:\n\n> Đội Sản phẩm sẽ chuyển sang chu kỳ release 2 tuần từ tháng 6. Mỗi release sẽ có changelog đăng trên #product-updates. Bug fix khẩn cấp vẫn deploy ngay không chờ chu kỳ.\n\n(74 từ — đã giữ 3 điểm: chu kỳ mới, kênh changelog, ngoại lệ khẩn cấp.)",
      "Hit the word count target (74 ≤ 80). All three points preserved. Confirmation line at bottom builds trust.",
    ],
    [
      "compose",
      "Viết email gửi hội đồng kỹ thuật: đề xuất pause dự án X 2 tuần để debug.",
      "Subject: Đề xuất pause dự án X (2 tuần) để xử lý regression\n\nKính gửi hội đồng,\n\nDự án X gặp 3 regression nghiêm trọng trong sprint vừa rồi (link tickets). Em đề xuất pause feature work 2 tuần để root-cause và bổ sung regression test.\n\nLý do: …\nRủi ro nếu không pause: …\nKế hoạch sau pause: …\n\nMong nhận phản hồi trước 17:00 thứ Sáu.\n\nTrân trọng,\n…",
      "Strong escalation structure: subject summarizes ask, body has rationale/risk/plan blocks, deadline for response. Tone respectful, not panicked.",
    ],
    [
      "validate",
      "Kiểm tra thông báo này có vi phạm policy 'không nêu tên cá nhân chịu trách nhiệm' không.",
      "Phát hiện vi phạm tại dòng 4: '...do Nam (Backend) gây ra'. Đề xuất sửa thành 'do một thay đổi ở dịch vụ Backend gây ra'.",
      "Correctly flags the named-person violation and proposes a depersonalized rewrite.",
    ],
    [
      "edit",
      "Email dưới đây có tone trách móc. Viết lại trung tính.",
      "Bản trung tính:\n\n> Dashboard hiển thị sai số liệu doanh thu từ 14:00 hôm nay. Đội Data đã xác định nguyên nhân là ETL job bị fail. Bản fix dự kiến deploy 18:00. Trong thời gian này, vui lòng dùng báo cáo Looker thay thế.\n\nĐã loại bỏ 4 chỗ buộc tội, thay bằng mô tả tình huống.",
      "All accusatory phrases removed. The substitute report channel is mentioned (rule: always give a workaround).",
    ],
  ],
  "slack-gif-creator": [
    [
      "create",
      "Tạo Slack GIF: dòng chữ 'shipped it!' nhảy lên xuống, nền vàng, 480x270, 2s loop.",
      "Đã render GIF 480×270, 24 fps, 48 frame. Text 'shipped it!' với keyframe bounce ±18px, easing cubic-out. Palette tối ưu 64 màu. Kích thước: 184 KB (dưới ngưỡng 256 KB của Slack).",
      "Hits all hard constraints (size ≤ 256KB, dimensions, fps, loop). The bounce uses cubic-out — better than linear from R1.",
    ],
    [
      "edit",
      "Lấy GIF đã có, đổi nền từ vàng sang xanh `#1e40af`, giữ nguyên animation.",
      "Đã giữ nguyên keyframe, chỉ tái render với background = #1e40af. Đảm bảo text contrast: dùng white text với stroke 1.5px đen. Output: 191 KB.",
      "Correct preservation of motion data. Auto-adjusted text fill for contrast (a rule the teacher added in R4).",
    ],
    [
      "convert",
      "Chuyển GIF 1.4 MB này thành Slack-compatible (≤ 256 KB).",
      "Đã giảm fps 30 → 18, palette 256 → 64, dimensions 720 → 480px. Output: 237 KB. Cảnh báo: motion sẽ choppy hơn bản gốc.",
      "Multi-step optimization in the right order: dimensions → fps → palette. Warning is honest.",
    ],
    [
      "optimize",
      "GIF dài 4s, kích thước 380 KB. Giảm còn ≤ 256 KB nhưng vẫn loop mượt.",
      "Phương án: cắt còn 2.5s (loop point chọn tại frame giống nhau nhất bằng SSIM), giảm 12 fps. Output: 218 KB. Loop seamless.",
      "Strong: chose loop point by SSIM rather than blindly trimming. Result is seamless.",
    ],
    [
      "edge",
      "Tạo GIF có dòng chữ tiếng Nhật 「ありがとう」 trên nền hoa anh đào.",
      "Sử dụng Noto Sans JP weight 700, fallback Be Vietnam Pro nếu thiếu glyph. Background hoa anh đào dạng particle (24 cánh, drift down). Output: 244 KB.",
      "Correctly handled CJK font fallback. Particle count tuned to stay under size budget.",
    ],
  ],
};

function genEval(skill: string, summary: SkillSummary): Record<number, EvalEntry[]> {
  const seeds = tcSeeds[skill];
  const r = rng(summary.seed ?? 0);
  const rounds = summary.score_history.map((s) => s.round);
  const out: Record<number, EvalEntry[]> = {};

  for (const round of rounds) {
    const targetAvg = summary.score_history.find((s) => s.round === round)!.avg_score;
    const entries: EvalEntry[] = [];
    for (let i = 0; i < 12; i++) {
      const seed = seeds[i % seeds.length];
      const wf = seed[0];
      const promptText = seed[1];
      const outputText = seed[2];
      const rationaleText = seed[3];

      const drift = (r() - 0.5) * 0.18;
      let hybrid = Math.max(0.3, Math.min(0.99, targetAvg + drift));
      const rule = Math.max(0.3, Math.min(1.0, hybrid + (r() - 0.4) * 0.16));
      const judge = rule < 0.6 ? null : Math.max(0.4, Math.min(1.0, hybrid + (r() - 0.5) * 0.1));
      if (judge !== null) hybrid = 0.4 * rule + 0.6 * judge;

      const checks = [
        { name: "schema_valid", passed: r() > 0.05, reason: "Output parses as expected structure" },
        { name: "no_invented_data", passed: r() > 0.1, reason: "All claims grounded in input" },
        { name: "tone_neutral", passed: r() > 0.15, reason: "No accusatory language" },
        { name: "respects_size_budget", passed: r() > 0.12, reason: "Within hard limits stated in SKILL.md" },
        { name: "rule_disclosed", passed: r() > 0.2, reason: "Restated constraints before acting" },
      ];

      const id = `tc_${"abcdefghij"[round % 10]}${String(i + 1).padStart(2, "0")}`;
      entries.push({
        round,
        test_case_id: id,
        workflow: wf,
        rule_score: +rule.toFixed(3),
        llm_judge_score: judge === null ? null : +judge.toFixed(3),
        hybrid_score: +hybrid.toFixed(3),
        judge_rationale: rationaleText,
        rule_checks: checks,
        prompt: promptText,
        output: outputText,
      });
    }
    out[round] = entries;
  }
  return out;
}

function genApiCalls(skill: string, summary: SkillSummary): ApiCall[] {
  const r = rng((summary.seed ?? 0) + 100);
  const out: ApiCall[] = [];
  const models = {
    student: "google/gemma-3-26b-it",
    judge: "anthropic/claude-sonnet-4.5",
    teacher: "anthropic/claude-sonnet-4.5",
  };
  const pricing: Record<string, { in: number; out: number }> = {
    "google/gemma-3-26b-it": { in: 0.2, out: 0.6 },
    "anthropic/claude-sonnet-4.5": { in: 3.0, out: 15.0 },
  };

  for (const sh of summary.score_history) {
    const round = sh.round;
    for (let i = 0; i < 12; i++) {
      const pt = 1200 + Math.floor(r() * 800);
      const ct = 400 + Math.floor(r() * 600);
      const m = models.student;
      const p = pricing[m];
      out.push({
        round,
        stage: "student",
        model: m,
        prompt_tokens: pt,
        completion_tokens: ct,
        total_tokens: pt + ct,
        cost_usd: +((pt * p.in + ct * p.out) / 1e6).toFixed(4),
        latency_ms: 1400 + Math.floor(r() * 1800),
        timestamp: `2026-05-${10 + round}T0${i % 9}:0${i % 6}:00Z`,
      });
    }
    for (let i = 0; i < 10; i++) {
      const pt = 1800 + Math.floor(r() * 1200);
      const ct = 600 + Math.floor(r() * 800);
      const m = models.judge;
      const p = pricing[m];
      out.push({
        round,
        stage: "judge",
        model: m,
        prompt_tokens: pt,
        completion_tokens: ct,
        total_tokens: pt + ct,
        cost_usd: +((pt * p.in + ct * p.out) / 1e6).toFixed(4),
        latency_ms: 2800 + Math.floor(r() * 2400),
        timestamp: `2026-05-${10 + round}T0${i % 9}:1${i % 6}:00Z`,
      });
    }
    const pt = 6000 + Math.floor(r() * 3000);
    const ct = 2400 + Math.floor(r() * 1200);
    const m = models.teacher;
    const p = pricing[m];
    out.push({
      round,
      stage: "teacher",
      model: m,
      prompt_tokens: pt,
      completion_tokens: ct,
      total_tokens: pt + ct,
      cost_usd: +((pt * p.in + ct * p.out) / 1e6).toFixed(4),
      latency_ms: 9000 + Math.floor(r() * 4000),
      timestamp: `2026-05-${10 + round}T0${round % 9}:30:00Z`,
    });
  }
  return out;
}

/* SKILL.md per round — same content as design data.js */
function genSkillMdDocx(rounds: number): Record<number, string> {
  const out: Record<number, string> = {};
  out[0] = `---
name: docx
description: Create, read, edit, and convert Microsoft Word .docx files. Use when the user asks to author a report, modify a document, extract content, or convert between formats.
---

# docx

Anthropic's official skill for working with Microsoft Word documents.

## When to use

Use this skill when the user references a .docx file or asks to produce one.

## Approach

1. Read the file with \`python-docx\` if it exists.
2. Apply the requested change.
3. Save to a new path; never overwrite without confirmation.

## Conversions

For PDF → docx, extract text and re-author. Image-only pages cannot be recovered without OCR.

## Bundled scripts

- \`scripts/extract_text.py\` — dump text from a .docx
- \`scripts/merge_docs.py\` — concatenate multiple .docx files
`;

  out[1] = `---
name: docx
description: Create, read, edit, and convert Microsoft Word .docx files. Use when the user asks to author a report, modify a document, extract content, or convert between formats.
---

# docx

Anthropic's official skill for working with Microsoft Word documents.

## When to use

Use this skill when the user references a .docx file or asks to produce one.

## Approach

1. **Read the file with \`python-docx\` if it exists.** Do not guess the file's structure.
2. Apply the requested change.
3. Save to a new path; never overwrite without confirmation.

## Hard rules

- Never invent file content. If the file cannot be opened, report the failure.
- Preserve run-level formatting when editing paragraphs.

## Conversions

For PDF → docx, extract text and re-author. Image-only pages cannot be recovered without OCR — flag them.

## Bundled scripts

- \`scripts/extract_text.py\` — dump text from a .docx
- \`scripts/merge_docs.py\` — concatenate multiple .docx files
`;

  out[3] = `---
name: docx
description: Create, read, edit, and convert Microsoft Word .docx files. Use when the user asks to author a report, modify a document, extract content, or convert between formats.
---

# docx

Anthropic's official skill for working with Microsoft Word documents.

## When to use

Use this skill when the user references a .docx file or asks to produce one.

## Approach

1. **Read the file with \`python-docx\` if it exists.** Do not guess the file's structure.
2. **Restate the constraints back to the user before acting** (file path, scope, output path).
3. Apply the requested change in the smallest scope that satisfies the ask.
4. Save to a new path with a versioned suffix (\`.v2.docx\`); never overwrite without confirmation.

## Hard rules

- Never invent file content. If the file cannot be opened, report the failure verbatim.
- Preserve run-level formatting when editing paragraphs.
- **When asked to replace text in paragraphs, do not touch table cells unless explicitly asked.**
- When merging multiple files, insert a page break between sources and put the TOC at the top.

## Headings & TOC

Use \`add_heading(text, level=1|2)\` so the auto-TOC field populates. Do not style runs manually.

## Conversions

For PDF → docx, extract text and re-author. Heuristic for headings: font-size > 16pt + bold ⇒ Heading 1; > 13pt + bold ⇒ Heading 2. Image-only pages cannot be recovered without OCR — flag them, do not hallucinate text.

## Bundled scripts

- \`scripts/extract_text.py\` — dump text from a .docx
- \`scripts/merge_docs.py\` — concatenate multiple .docx files
- \`scripts/optimize_size.py\` — compress images, prune unused fonts
`;

  out[5] = `---
name: docx
description: Create, read, edit, and convert Microsoft Word .docx files. Use when the user asks to author a report, modify a document, extract content, or convert between formats. Reads files with python-docx; never invents content.
---

# docx

Anthropic's official skill for working with Microsoft Word documents.

## When to use

Use this skill when the user references a .docx file or asks to produce one. Do not use it for .doc (legacy binary) — refuse and ask the user to convert.

## Approach

Follow these steps in order. **Do not skip step 2.**

1. **Read the file with \`python-docx\` if it exists.** Do not guess structure.
2. **Restate the constraints back to the user before acting.** Include: file path, scope (paragraphs / tables / both), output path, any formatting to preserve.
3. Apply the requested change in the smallest scope that satisfies the ask.
4. Save to a new path with a versioned suffix (\`.v2.docx\`); never overwrite without confirmation.

## Hard rules

- Never invent file content. If the file cannot be opened, report the failure verbatim and stop.
- Preserve run-level formatting when editing paragraphs (font, size, bold/italic, color).
- **When asked to replace text in paragraphs, do not touch table cells unless explicitly asked.**
- When merging multiple files, insert a page break between sources and put the TOC at the top.
- Never alter text content during size optimization — only compress images and prune unused fonts.

## Headings & TOC

Use \`add_heading(text, level=1|2)\` so the auto-TOC field populates. Do not style runs manually for headings — Word's TOC field reads style names, not visual formatting.

After inserting/changing headings, insert a TOC field with \`Update Fields on Open\` so the user sees a populated TOC when they open the file.

## Tables

- Preserve merged cells when extracting; flag rather than flatten.
- When the user says "table", clarify whether they mean a Word table or content laid out with tabs — these are different in .docx.

## Conversions

For PDF → docx, extract text via pdfplumber and re-author. Heuristic for headings: font-size > 16pt + bold ⇒ Heading 1; > 13pt + bold ⇒ Heading 2. **Image-only pages cannot be recovered without OCR — flag them, do not hallucinate text.**

## Refusals

- Corrupted ZIP header in a .docx → suggest Word repair or backup; do not invent content.
- .doc (legacy) input → ask the user to convert to .docx first.
- Passwords-protected files → cannot open without the password; ask for it.

## Bundled scripts

- \`scripts/extract_text.py\` — dump text from a .docx
- \`scripts/merge_docs.py\` — concatenate multiple .docx files
- \`scripts/optimize_size.py\` — compress images, prune unused fonts
- \`scripts/scan_features.py\` — report whether a doc has headers, footers, page numbers, TOC
`;

  out[8] = out[5].replace(
    "## Refusals",
    `## Common pitfalls (from training data)

- Forgetting to update the TOC field after adding headings — always call \`update_fields()\` on the document object.
- Running a global replace that touches tables. Scope to paragraphs unless asked.

## Refusals`
  );

  for (let i = 0; i <= rounds; i++) {
    if (!out[i]) {
      let prior = i;
      while (!out[prior] && prior >= 0) prior--;
      out[i] = out[prior] || out[0];
    }
  }
  return out;
}

function genSkillMdInternalComms(rounds: number): Record<number, string> {
  const out: Record<number, string> = {};

  out[0] = `---
name: internal-comms
description: Draft clear, calm internal communications — outage notices, policy updates, team announcements, escalation emails.
---

# internal-comms

## When to use

Use this skill when the user asks for an internal message intended for a team, all-hands, or escalation audience.

## Approach

1. Identify audience and intent.
2. Draft.
3. Review tone.

## Style

Calm, neutral, no exclamation points.
`;

  out[1] = `---
name: internal-comms
description: Draft clear, calm internal communications — outage notices, policy updates, team announcements, escalation emails.
---

# internal-comms

## When to use

Use this skill when the user asks for an internal message intended for a team, all-hands, or escalation audience.

## Required elements (every message)

- A subject line that summarizes the ask.
- The audience explicitly identified.
- The action item for the reader.
- A contact channel.

## Approach

1. Identify audience and intent.
2. Draft.
3. Review tone.

## Style

Calm, neutral, no exclamation points. **Never name an individual as the cause of a problem** — depersonalize to the system or change that caused it.
`;

  out[3] = `---
name: internal-comms
description: Draft clear, calm internal communications — outage notices, policy updates, team announcements, escalation emails. Always names a workaround when reporting a disruption.
---

# internal-comms

## When to use

Use this skill when the user asks for an internal message intended for a team, all-hands, or escalation audience.

## Required elements (every message)

- A subject line that summarizes the ask in ≤ 12 words.
- The audience explicitly identified.
- The exact time window (with timezone) for any disruption.
- The affected services enumerated.
- The action item for the reader.
- A contact channel.
- **A workaround** if the message reports a disruption.

## Approach

1. Identify audience and intent (announcement / outage / escalation / policy).
2. Draft using the matching template in \`templates/\`.
3. Review tone against the style rules below.
4. Run \`scripts/check_policy.py\` to scan for named individuals and accusatory phrases.

## Style

Calm, neutral, no exclamation points. **Never name an individual as the cause of a problem** — depersonalize to the system or change that caused it. Replace "X caused" with "a change in service X caused".

## Escalation emails specifically

Structure: \`Ask → Why → Risk if not done → Plan after → Response deadline.\` One sentence per block where possible.

## Bundled

- \`templates/outage.md\`
- \`templates/policy_update.md\`
- \`templates/escalation.md\`
- \`scripts/check_policy.py\`
`;

  for (let i = 0; i <= rounds; i++) {
    if (!out[i]) {
      let prior = i;
      while (!out[prior] && prior >= 0) prior--;
      out[i] = out[prior] || out[0];
    }
  }
  return out;
}

function genSkillMdSlackGif(rounds: number): Record<number, string> {
  const out: Record<number, string> = {};

  out[0] = `---
name: slack-gif-creator
description: Generate Slack-compatible animated GIFs from a text prompt. Outputs ≤ 256 KB, ≤ 480px wide, looping.
---

# slack-gif-creator

## When to use

When the user asks for a small celebratory GIF (e.g. "shipped it", "thanks", "deploy day") suitable for posting in Slack.

## Hard constraints

- File size ≤ 256 KB.
- Width ≤ 480px.
- Loops seamlessly.

## Approach

1. Render frames with Pillow.
2. Encode as GIF with palette quantization.
3. Confirm size before returning.
`;

  out[2] = `---
name: slack-gif-creator
description: Generate Slack-compatible animated GIFs from a text prompt. Outputs ≤ 256 KB, ≤ 480px wide, looping seamlessly.
---

# slack-gif-creator

## When to use

When the user asks for a small celebratory GIF (e.g. "shipped it", "thanks", "deploy day") suitable for posting in Slack.

## Hard constraints

- File size ≤ 256 KB. **This is a Slack limit, not a guideline.**
- Width ≤ 480px.
- Frame rate ≤ 24 fps.
- Loops seamlessly (start frame == end frame, or pick a seamless loop point).

## Approach

1. Render frames with Pillow at the requested dimensions.
2. Pick an easing curve appropriate to the motion (cubic-out for "snap-into-place", sinusoidal for "breathing").
3. Encode as GIF with palette quantization (start at 64 colors).
4. **Confirm size before returning.** If over budget, drop dimensions → fps → palette colors, in that order.

## Refusals

Do not generate GIFs with text mocking a named individual.
`;

  out[5] = `---
name: slack-gif-creator
description: Generate Slack-compatible animated GIFs from a text prompt. Outputs ≤ 256 KB, ≤ 480px wide, looping seamlessly. Auto-adjusts text contrast when background changes.
---

# slack-gif-creator

## When to use

When the user asks for a small celebratory GIF (e.g. "shipped it", "thanks", "deploy day") suitable for posting in Slack.

## Hard constraints

- File size ≤ 256 KB. **This is a Slack limit, not a guideline.**
- Width ≤ 480px.
- Frame rate ≤ 24 fps.
- Loops seamlessly. When trimming an existing GIF, pick the loop point using SSIM between candidate frames — do not blindly trim.

## Approach

1. Render frames with Pillow at the requested dimensions.
2. Pick an easing curve appropriate to the motion (cubic-out for "snap-into-place", sinusoidal for "breathing").
3. **Auto-adjust text color for contrast against the background** — WCAG AA against the dominant pixel of the text area.
4. Encode as GIF with palette quantization (start at 64 colors).
5. **Confirm size before returning.** If over budget, drop dimensions → fps → palette colors, in that order.

## Text & fonts

- For CJK (Japanese, Korean, Chinese) text, use Noto Sans JP/KR/SC; fall back to Be Vietnam Pro if a glyph is missing.
- Stroke text 1.5px in the contrasting color when over a busy background.

## Refusals

- Do not generate GIFs with text mocking a named individual.
- Do not exceed the size budget; offer a downscale plan instead.

## Bundled scripts

- \`scripts/render_text.py\` — render text with bounce/fade keyframes
- \`scripts/optimize_gif.py\` — palette + frame skip + dimension downscale
- \`scripts/find_loop.py\` — SSIM-based seamless loop point detection
`;

  out[9] =
    out[5] +
    `

## Common pitfalls (from training data)

- Forgetting to check contrast after a background swap — always re-run the AA check.
- Picking a loop point by length instead of similarity — the GIF will visibly jump.
- Starting at 256 colors. 64 is almost always enough; 32 often works for flat designs.
`;

  for (let i = 0; i <= rounds; i++) {
    if (!out[i]) {
      let prior = i;
      while (!out[prior] && prior >= 0) prior--;
      out[i] = out[prior] || out[0];
    }
  }
  return out;
}

export const evalBySkill: Record<string, Record<number, EvalEntry[]>> = {
  docx: genEval("docx", summaries.docx),
  "internal-comms": genEval("internal-comms", summaries["internal-comms"]),
  "slack-gif-creator": genEval("slack-gif-creator", summaries["slack-gif-creator"]),
};

export const apiCallsBySkill: Record<string, ApiCall[]> = {
  docx: genApiCalls("docx", summaries.docx),
  "internal-comms": genApiCalls("internal-comms", summaries["internal-comms"]),
  "slack-gif-creator": genApiCalls("slack-gif-creator", summaries["slack-gif-creator"]),
};

export const skillMdBySkill: Record<string, Record<number, string>> = {
  docx: genSkillMdDocx(summaries.docx.rounds_run),
  "internal-comms": genSkillMdInternalComms(summaries["internal-comms"].rounds_run),
  "slack-gif-creator": genSkillMdSlackGif(summaries["slack-gif-creator"].rounds_run),
};

export const kpis: Kpis = (() => {
  const list = Object.values(summaries);
  const totalImprovement =
    list.reduce((acc, s) => {
      const r1 = s.score_history[0].avg_score;
      return acc + (s.best_score - r1) / r1;
    }, 0) / list.length;
  const best = list.reduce((a, b) => (a.best_score > b.best_score ? a : b));
  return {
    skills_count: list.length,
    total_improvement_pct: +(totalImprovement * 100).toFixed(1),
    best_peak: { skill: best.skill, score: best.best_score, round: best.best_round },
    total_cost: +list
      .reduce((acc, s) => acc + (apiCallsBySkill[s.skill] || []).reduce((c, a) => c + a.cost_usd, 0), 0)
      .toFixed(2),
  };
})();
