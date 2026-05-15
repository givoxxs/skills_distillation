import type { Metadata } from "next";
import { Be_Vietnam_Pro, Source_Serif_4, JetBrains_Mono } from "next/font/google";
import { ThemeProvider } from "@/components/theme-provider";
import { Sidebar } from "@/components/sidebar";
import "./globals.css";

const beVietnamPro = Be_Vietnam_Pro({
  subsets: ["latin", "vietnamese"],
  weight: ["400", "500", "600", "700"],
  variable: "--font-be-vietnam-pro",
  display: "swap",
});

const sourceSerif = Source_Serif_4({
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
  style: ["normal", "italic"],
  variable: "--font-source-serif",
  display: "swap",
});

const jetbrainsMono = JetBrains_Mono({
  subsets: ["latin"],
  weight: ["400", "500", "600"],
  variable: "--font-jetbrains-mono",
  display: "swap",
});

export const metadata: Metadata = {
  title: "Skill Distillation Lab — Thesis Demo",
  description:
    "Dashboard demo cho đồ án Skill Distillation — chưng cất SKILL.md xuống mô hình nhỏ qua vòng lặp Teacher–Student–Judge.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html
      lang="vi"
      suppressHydrationWarning
      className={`${beVietnamPro.variable} ${sourceSerif.variable} ${jetbrainsMono.variable}`}
    >
      <body>
        <ThemeProvider>
          <div className="app">
            <Sidebar bilingual={true} />
            <main className="main">{children}</main>
          </div>
        </ThemeProvider>
      </body>
    </html>
  );
}
