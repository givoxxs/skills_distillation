/* Display labels — the real summary.json doesn't carry vi/en, so we keep a
   static lookup keyed by skill name. */

export type DisplayMeta = {
  vi: string;
  en: string;
};

export const skillDisplayMeta: Record<string, DisplayMeta> = {
  docx: {
    vi: "Tạo & chỉnh sửa văn bản .docx",
    en: "Author and edit .docx documents",
  },
  "internal-comms": {
    vi: "Soạn thông báo nội bộ",
    en: "Draft internal communications",
  },
  "slack-gif-creator": {
    vi: "Tạo GIF Slack từ mô tả",
    en: "Create Slack GIFs from a prompt",
  },
};

export function displayMetaFor(skill: string): DisplayMeta {
  return (
    skillDisplayMeta[skill] || {
      vi: skill,
      en: skill,
    }
  );
}
