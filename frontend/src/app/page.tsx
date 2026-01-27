"use client";

import Link from "next/link";

import Chatbot from "./components/Chatbot";
import { Navbar } from "./components/navbar";
import { Footer } from "./components/footer";
import { HowItWorksSection } from "./components/how-it-works-section";
import { StatsSection } from "./components/stats-section";

export default function Home() {

  return (
    <main className="min-h-screen bg-background">
      {/* Navbar */}
      <Navbar />

      <section className="relative overflow-hidden">
        {/* Background Pattern */}
        <div className="absolute inset-0 bg-gradient-to-b from-primary/5 via-background to-background" />

        <div className="container relative mx-auto px-4 lg:px-8 pt-20 pb-10 lg:pt-32">
          <div className="max-w-4xl mx-auto text-center">

            {/* Headline */}
            <h1 className="text-4xl md:text-5xl lg:text-6xl font-bold tracking-tight text-foreground text-balance mb-6">
              Cut Your Energy Bills.
              <br />
              <span className="text-green-600">Save the Planet.</span>
            </h1>

            {/* Subheadline */}
            <p className="text-lg md:text-xl text-gray-600 max-w-2xl mx-auto mb-10 text-pretty">
              VoltPulse uses Agentic AI to analyze your utility bills, benchmark
              your consumption against national averages, and unlock personalized
              savings through government vouchers and smart recommendations.
            </p>

            {/* CTA Buttons */}
            <div className="flex flex-col sm:flex-row items-center justify-center gap-4 mb-16">
              <Link href="/upload" className="flex items-center gap-2 px-4 py-2 bg-green-600 hover:bg-green-700 text-white font-medium rounded-lg transition-colors">
                Upload Bills
              </Link>
              <Link href="/chat" className="flex items-center gap-2 px-4 py-2 bg-green-600 hover:bg-green-700 text-white font-medium rounded-lg transition-colors">
                Chat Assistant
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* Stats */}
      <StatsSection />

      {/* Steps on how to upload bills */}
      <HowItWorksSection />

      {/* footer */}
      <Footer />

      {/* Chatbot */}
      <Chatbot />
    </main>
  );
}