import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Dota Report Card — Your Dota history, with the receipts",
  description: "Turn available public Dota match history into a short, evidence-backed report.",
  robots: { index: false, follow: false }
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body className="app-body">{children}</body>
    </html>
  );
}
