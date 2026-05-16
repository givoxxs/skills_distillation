import type { Metadata } from "next";
import { Be_Vietnam_Pro, Source_Serif_4, JetBrains_Mono } from "next/font/google";
import { ThemeProvider } from "@/components/theme-provider";
import { LanguageProvider } from "@/components/language-provider";
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

// Pre-paint theme bootstrap — runs synchronously in <head> before React
// hydrates, so the user never sees the wrong theme flash. Allowed here
// because <head> in a Server Component renders as plain HTML, not as a
// client React tree (which is what Next 16 forbids for <script> tags).
const THEME_BOOTSTRAP = `(function(){try{var t=localStorage.getItem('sdl:theme');if(t==='dark'||t==='light'){document.documentElement.setAttribute('data-theme',t);}}catch(e){}})();`;

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html
      lang="vi"
      suppressHydrationWarning
      className={`${beVietnamPro.variable} ${sourceSerif.variable} ${jetbrainsMono.variable}`}
    >
      <head>
        <script dangerouslySetInnerHTML={{ __html: THEME_BOOTSTRAP }} />
      </head>
      <body>
        <ThemeProvider>
          <LanguageProvider>
            <div className="app">
              <Sidebar />
              <main className="main">{children}</main>
            </div>
          </LanguageProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
