"use client";

import { Navbar } from "../components/navbar";
import { Footer } from "../components/footer";
import Chatbot from "../components/ChatbotEnhanced";

export default function AnalyticsLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="h-screen bg-white flex flex-col overflow-hidden">
      <Navbar />
      <main className="flex-1 max-w-7xl mx-auto py-4 px-6 w-full overflow-auto">{children}</main>
      <Chatbot />
    </div>
  );
}
