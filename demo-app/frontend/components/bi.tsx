"use client";

import { useLang } from "./language-provider";

/* Bilingual switcher — renders `vi` or `en` based on current language.
 * Technical terms (SKILL.md, hybrid, R1…) are kept verbatim in both texts
 * by the calling site — this component never translates.
 *
 * Accepts the legacy `showEn` prop and ignores it: callers using the old
 * VN-lead/EN-sub pattern still compile but now switch instead of stack. */

export function Bi({
  vi,
  en,
}: {
  vi: React.ReactNode;
  en?: React.ReactNode | null;
  showEn?: boolean;
}) {
  const { lang } = useLang();
  if (lang === "en" && en) return <>{en}</>;
  return <>{vi}</>;
}
