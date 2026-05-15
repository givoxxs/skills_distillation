import Link from "next/link";
import type { ReactNode } from "react";

export type Crumb = { label: ReactNode; href?: string };

export function TopBar({ crumbs, actions }: { crumbs: Crumb[]; actions?: ReactNode }) {
  return (
    <header className="topbar">
      <nav className="crumbs" aria-label="Breadcrumb">
        {crumbs.map((c, i) => (
          <span key={i} style={{ display: "inline-flex", alignItems: "center", gap: 8 }}>
            {i > 0 && <span className="sep">/</span>}
            {c.href ? (
              <Link href={c.href}>{c.label}</Link>
            ) : (
              <span className={i === crumbs.length - 1 ? "current" : ""}>{c.label}</span>
            )}
          </span>
        ))}
      </nav>
      <div className="topbar-actions">{actions}</div>
    </header>
  );
}
