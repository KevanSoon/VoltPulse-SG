"use client";

import { Navbar } from "../components/navbar";
import { Footer } from "../components/footer";
import Chatbot from "../components/Chatbot";

export default function AnalyticsLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="min-h-screen bg-white flex flex-col">
      <Navbar />
      <main className="flex-1 max-w-7xl mx-auto py-8 px-6 w-full">{children}</main>
      <Footer />
      <Chatbot />
    </div>
  );
}
