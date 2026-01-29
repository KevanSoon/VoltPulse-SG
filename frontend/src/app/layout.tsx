import type { Metadata, Viewport } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { SkipLink } from "./components/SkipLink";

const inter = Inter({
  subsets: ["latin"],
  display: "swap",
  variable: "--font-inter",
});

export const metadata: Metadata = {
  title: "VoltPulse SG - Smart Energy Savings for Singapore",
  description: "AI-powered utility bill analysis to help Singapore households reduce energy consumption and maximize government voucher savings.",
  keywords: ["energy savings", "Singapore", "utility bills", "climate voucher", "SP Group", "electricity"],
  authors: [{ name: "VoltPulse SG" }],
  icons: {
    icon: "/volt.png",
    shortcut: "/volt.png",
    apple: "/volt.png",
  },
  openGraph: {
    title: "VoltPulse SG - Smart Energy Savings",
    description: "Analyze your utility bills with AI and save up to S$600/year",
    type: "website",
    locale: "en_SG",
    images: ["/volt.png"],
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
    <html lang="en" className={inter.variable}>
      <body className={`${inter.className} antialiased bg-white`}>
        <SkipLink />
        {children}
      </body>
    </html>
  );
}
