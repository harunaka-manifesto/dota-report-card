import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Dota Report Card",
  description: "Evidence-backed OpenDota player insights",
  robots: { index: false, follow: false }
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}

