import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "VoltPulse OCR",
  description: "Upload images for OCR processing",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="antialiased">{children}</body>
    </html>
  );
}
