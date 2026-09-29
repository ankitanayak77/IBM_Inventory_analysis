import type { Metadata } from "next";
import "./globals.css";

// Note: the default template used next/font/google (Geist), which requires
// fetching fonts.googleapis.com at build time. This dev sandbox's egress
// proxy blocks that domain, so the system-font stack below is used instead
// — a real deployment target (e.g. Vercel) has no such restriction and
// next/font/google could be reintroduced there if desired.

export const metadata: Metadata = {
  title: "Inventory Analysis",
  description:
    "Fast / Slow / Non-moving classification, ABC analysis and reorder-risk detection.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className="h-full antialiased">
      <body className="min-h-full flex flex-col font-sans">{children}</body>
    </html>
  );
}
