"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
import { useTheme } from "next-themes";
import { Bi } from "./bi";
import { Icon } from "./icon";
import { skillList } from "@/lib/mock-data";

export function Sidebar({ bilingual = true }: { bilingual?: boolean }) {
  const pathname = usePathname();
  const [skillsOpen, setSkillsOpen] = useState(true);
  const { theme, setTheme } = useTheme();

  const isActive = (p: string) => pathname === p;
  const isSkillActive = (skill: string) => pathname === "/skills/" + skill;
  const skillsHighlighted = pathname?.startsWith("/skills");

  return (
    <aside className="sidebar">
      <div className="sidebar-brand">
        <div className="brand-mark">S</div>
        <div className="brand-name">
          Skill Distillation Lab
          <span className="sub">Đồ án tốt nghiệp · 2026</span>
        </div>
      </div>

      <nav className="nav" aria-label="Primary navigation">
        <div className="nav-section">
          <Bi vi="Điều hướng" en={bilingual ? "Navigation" : null} showEn={bilingual} />
        </div>

        <Link
          className={"nav-item" + (isActive("/") ? " active" : "")}
          href="/"
          aria-current={isActive("/") ? "page" : undefined}
        >
          <Icon name="home" />
          <Bi vi="Tổng quan" en={bilingual ? "Overview" : null} showEn={bilingual} />
        </Link>

        <button
          className={"nav-item" + (skillsHighlighted ? " active" : "")}
          style={{ textAlign: "left", width: "100%", background: "transparent", border: "1px solid transparent" }}
          onClick={() => setSkillsOpen((o) => !o)}
        >
          <Icon name="layers" />
          <Bi vi="Các skill" en={bilingual ? "Skills" : null} showEn={bilingual} />
          <span style={{ marginLeft: "auto", display: "inline-flex", color: "var(--fg-faint)" }}>
            <Icon name={skillsOpen ? "chev-d" : "chev-r"} size={14} />
          </span>
        </button>

        {skillsOpen && (
          <div className="nav-sub">
            {skillList.map((s) => (
              <Link
                key={s}
                className={"nav-item" + (isSkillActive(s) ? " active" : "")}
                href={`/skills/${s}`}
                aria-current={isSkillActive(s) ? "page" : undefined}
              >
                <span className="mono" style={{ fontSize: 12 }}>
                  {s}
                </span>
              </Link>
            ))}
          </div>
        )}

        <Link
          className={"nav-item" + (isActive("/run") ? " active" : "")}
          href="/run"
          aria-current={isActive("/run") ? "page" : undefined}
        >
          <Icon name="play" />
          <Bi vi="Chạy thử" en={bilingual ? "Live run" : null} showEn={bilingual} />
        </Link>

        <Link
          className={"nav-item" + (isActive("/about") ? " active" : "")}
          href="/about"
          aria-current={isActive("/about") ? "page" : undefined}
        >
          <Icon name="info" />
          <Bi vi="Giới thiệu" en={bilingual ? "About" : null} showEn={bilingual} />
        </Link>
      </nav>

      <div className="sidebar-footer">
        <span style={{ fontSize: 12, color: "var(--fg-subtle)" }}>
          {theme === "dark" ? "Chế độ tối" : "Chế độ sáng"}
        </span>
        <button
          className="btn btn-ghost btn-icon"
          aria-label="Toggle theme"
          onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
          title="Toggle dark / light"
        >
          <Icon name={theme === "dark" ? "sun" : "moon"} size={16} />
        </button>
      </div>
    </aside>
  );
}
