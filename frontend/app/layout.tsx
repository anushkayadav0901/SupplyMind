import type { Metadata } from "next";
import { Geist } from "next/font/google";
import "./globals.css";
import { Shell } from "@/components/layout/shell";

const geist = Geist({
  subsets: ["latin"],
  variable: "--font-sans",
});

export const metadata: Metadata = {
  title: "SupplyMind — Procurement Intelligence",
  description:
    "AI-powered procurement and vendor intelligence platform. Upload documents, extract data, assess vendor risk, and ask questions over your procurement corpus.",
  keywords: [
    "procurement",
    "vendor management",
    "supply chain",
    "AI",
    "document intelligence",
  ],
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={geist.variable}>
      <body>
        <Shell>{children}</Shell>
      </body>
    </html>
  );
}
