import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Free DNA — Your Dota habits, made visible",
  description: "A personal portrait built from the way you actually play Dota.",
  robots: { index: false, follow: false }
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body className="app-body">{children}</body>
    </html>
  );
}
