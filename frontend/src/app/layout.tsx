import type { Metadata, Viewport } from "next";
import "./globals.css";
import { SkipLink } from "./components/SkipLink";

export const metadata: Metadata = {
  title: "VoltPulse SG - Smart Energy Savings for Singapore",
  description: "AI-powered utility bill analysis to help Singapore households reduce energy consumption and maximize government voucher savings.",
  keywords: ["energy savings", "Singapore", "utility bills", "climate voucher", "SP Group", "electricity"],
  authors: [{ name: "VoltPulse SG" }],
  openGraph: {
    title: "VoltPulse SG - Smart Energy Savings",
    description: "Analyze your utility bills with AI and save up to S$600/year",
    type: "website",
    locale: "en_SG",
  },
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  themeColor: "#16a34a",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="icon" href="/favicon.ico" sizes="any" />
      </head>
      <body className="antialiased bg-white">
        <SkipLink />
        {children}
      </body>
    </html>
  );
}
