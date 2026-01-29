"use client";

import Link from "next/link";
import { Zap, Upload, MessageSquare, TrendingDown, Award, BarChart3, Lightbulb, FileText, ArrowRight } from "lucide-react";

import Chatbot from "./components/ChatbotEnhanced";
import { Navbar } from "./components/navbar";
import { Footer } from "./components/footer";

const features = [
  {
    icon: Upload,
    title: "Bill Upload & OCR",
    description: "Simply upload your SP utility bill as PDF or image. Our AI extracts all data automatically with high accuracy.",
  },
  {
    icon: BarChart3,
    title: "Consumption Analytics",
    description: "View detailed breakdowns of your electricity and water usage with interactive charts and trend analysis.",
  },
  {
    icon: TrendingDown,
    title: "National Benchmarking",
    description: "Compare your consumption against Singapore's national averages and see how you rank in your district.",
  },
  {
    icon: Lightbulb,
    title: "Smart Recommendations",
    description: "Receive AI-powered, personalized tips to reduce your energy footprint based on your usage patterns.",
  },
  {
    icon: Award,
    title: "Climate Vouchers",
    description: "Discover eligible government rebates and find authorized retailers near you to maximize savings.",
  },
  {
    icon: MessageSquare,
    title: "AI Chat Assistant",
    description: "Ask questions about your bills, get instant answers, and receive guidance on reducing consumption.",
  },
];

const stats = [
  { value: "15,000+", label: "Bills Analyzed" },
  { value: "S$2.4M", label: "Total Savings Identified" },
  { value: "98%", label: "OCR Accuracy" },
  { value: "4.8/5", label: "User Rating" },
];

const howItWorks = [
  {
    step: "01",
    title: "Upload your bill",
    description: "Take a photo or upload your SP utility bill PDF. Our system accepts various formats.",
  },
  {
    step: "02",
    title: "AI analyzes your data",
    description: "Our Agentic AI extracts and processes your consumption data in seconds.",
  },
  {
    step: "03",
    title: "Get insights & save",
    description: "View your personalized dashboard, recommendations, and start saving immediately.",
  },
];

export default function Home() {
  return (
    <main className="min-h-screen bg-white" id="main-content">
      <Navbar />

      {/* Hero Section - Clean with teal color scheme */}
      <section className="relative bg-gradient-to-br from-teal-600 via-teal-700 to-cyan-800 overflow-hidden">
        {/* Subtle grid pattern */}
        <div className="absolute inset-0 bg-[linear-gradient(to_right,#ffffff08_1px,transparent_1px),linear-gradient(to_bottom,#ffffff08_1px,transparent_1px)] bg-[size:32px_32px]" />
        
        {/* Gradient orbs */}
        <div className="absolute top-0 left-1/4 w-96 h-96 bg-white/10 rounded-full blur-3xl" />
        <div className="absolute bottom-0 right-1/4 w-96 h-96 bg-cyan-400/10 rounded-full blur-3xl" />

        <div className="relative container mx-auto px-4 lg:px-8 py-24 lg:py-32">
          <div className="max-w-4xl mx-auto text-center">
            {/* Badge */}
            <div className="inline-flex items-center gap-2 px-4 py-2 bg-white/10 backdrop-blur-sm border border-white/20 rounded-full text-sm text-teal-100 mb-8">
              <Zap className="w-4 h-4" />
              <span>Powered by Agentic AI</span>
            </div>

            {/* Main Headline */}
            <h1 className="text-4xl md:text-5xl lg:text-6xl font-bold text-white tracking-tight mb-6">
              Analyze your utility bills.
              <br />
              <span className="text-teal-200">
                Save money instantly.
              </span>
            </h1>

            {/* Subheadline */}
            <p className="text-lg md:text-xl text-teal-100 max-w-2xl mx-auto mb-10 leading-relaxed">
              Upload your SP bill and get instant insights on your consumption, 
              personalized savings recommendations, and access to government vouchers.
            </p>

            {/* Single Primary CTA */}
            <div className="flex flex-col sm:flex-row items-center justify-center gap-4 mb-12">
              <Link
                href="/upload"
                className="group inline-flex items-center gap-3 px-8 py-4 bg-white hover:bg-teal-50 text-teal-700 font-semibold rounded-lg transition-all text-lg shadow-lg"
              >
                Start analyzing your bills
                <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
              </Link>
            </div>

            {/* Trust Line */}
            <p className="text-sm text-teal-200">
              Free to use · No sign-up required · Your data stays private
            </p>
          </div>
        </div>
      </section>

      {/* Stats Bar */}
      <section className="bg-teal-50 border-y border-teal-100">
        <div className="container mx-auto px-4 lg:px-8 py-8">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-8">
            {stats.map((stat, index) => (
              <div key={index} className="text-center">
                <div className="text-2xl md:text-3xl font-bold text-teal-700">{stat.value}</div>
                <div className="text-sm text-teal-600 mt-1">{stat.label}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Features Grid - Clean cards */}
      <section className="py-20 lg:py-28 bg-white">
        <div className="container mx-auto px-4 lg:px-8">
          <div className="max-w-3xl mx-auto text-center mb-16">
            <h2 className="text-3xl md:text-4xl font-bold text-slate-900 mb-4">
              Our features
            </h2>
            <p className="text-lg text-slate-600">
              Everything you need to understand and reduce your utility consumption.
            </p>
          </div>

          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6 max-w-6xl mx-auto">
            {features.map((feature, index) => (
              <div
                key={index}
                className="group p-6 bg-white border border-slate-200 rounded-xl hover:border-teal-300 hover:shadow-lg hover:shadow-teal-500/10 transition-all duration-200"
              >
                <div className="w-12 h-12 bg-teal-50 rounded-lg flex items-center justify-center mb-4 group-hover:bg-teal-100 transition-colors">
                  <feature.icon className="w-6 h-6 text-teal-600" />
                </div>
                <h3 className="text-lg font-semibold text-slate-900 mb-2">
                  {feature.title}
                </h3>
                <p className="text-slate-600 text-sm leading-relaxed">
                  {feature.description}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* How It Works - Numbered steps */}
      <section className="py-20 lg:py-28 bg-slate-50">
        <div className="container mx-auto px-4 lg:px-8">
          <div className="max-w-3xl mx-auto text-center mb-16">
            <h2 className="text-3xl md:text-4xl font-bold text-slate-900 mb-4">
              How it works
            </h2>
            <p className="text-lg text-slate-600">
              Get started in under a minute. No sign-up required.
            </p>
          </div>

          <div className="max-w-4xl mx-auto">
            <div className="grid md:grid-cols-3 gap-8">
              {howItWorks.map((item, index) => (
                <div key={index} className="relative">
                  {/* Connector line */}
                  {index < howItWorks.length - 1 && (
                    <div className="hidden md:block absolute top-8 left-[calc(50%+60px)] w-[calc(100%-60px)] h-[2px] bg-teal-200" />
                  )}
                  
                  <div className="text-center">
                    <div className="inline-flex items-center justify-center w-16 h-16 bg-teal-600 text-white rounded-full text-xl font-bold mb-4">
                      {item.step}
                    </div>
                    <h3 className="text-lg font-semibold text-slate-900 mb-2">
                      {item.title}
                    </h3>
                    <p className="text-slate-600 text-sm">
                      {item.description}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* Government Resources */}
      <section className="py-20 lg:py-28 bg-slate-50">
        <div className="container mx-auto px-4 lg:px-8">
          <div className="max-w-3xl mx-auto text-center mb-12">
            <h2 className="text-3xl md:text-4xl font-bold text-slate-900 mb-4">
              Official government resources
            </h2>
            <p className="text-lg text-slate-600">
              Access official Singapore government programs for energy savings.
            </p>
          </div>

          <div className="grid md:grid-cols-3 gap-6 max-w-4xl mx-auto">
            <a
              href="https://www.nea.gov.sg/our-services/climate-change-energy-efficiency/climate-friendly-households-programme"
              target="_blank"
              rel="noopener noreferrer"
              className="group p-6 bg-white border border-slate-200 rounded-xl hover:border-teal-300 hover:shadow-md transition-all"
            >
              <div className="text-sm text-teal-600 font-medium mb-2">NEA</div>
              <h3 className="font-semibold text-slate-900 mb-2 group-hover:text-teal-700 transition-colors">
                Climate Friendly Households Programme
              </h3>
              <p className="text-sm text-slate-500">
                $300 vouchers for energy-efficient appliances
              </p>
            </a>

            <a
              href="https://www.ema.gov.sg/consumers/electricity"
              target="_blank"
              rel="noopener noreferrer"
              className="group p-6 bg-white border border-slate-200 rounded-xl hover:border-teal-300 hover:shadow-md transition-all"
            >
              <div className="text-sm text-teal-600 font-medium mb-2">EMA</div>
              <h3 className="font-semibold text-slate-900 mb-2 group-hover:text-teal-700 transition-colors">
                Energy Efficiency Guide
              </h3>
              <p className="text-sm text-slate-500">
                Official tips for reducing electricity consumption
              </p>
            </a>

            <a
              href="https://www.pub.gov.sg/watersupply/conservewater"
              target="_blank"
              rel="noopener noreferrer"
              className="group p-6 bg-white border border-slate-200 rounded-xl hover:border-teal-300 hover:shadow-md transition-all"
            >
              <div className="text-sm text-teal-600 font-medium mb-2">PUB</div>
              <h3 className="font-semibold text-slate-900 mb-2 group-hover:text-teal-700 transition-colors">
                Water Conservation Tips
              </h3>
              <p className="text-sm text-slate-500">
                Learn how to reduce water usage at home
              </p>
            </a>
          </div>
        </div>
      </section>

      {/* Final CTA */}
      <section className="py-20 lg:py-28 bg-gradient-to-br from-teal-600 via-teal-700 to-cyan-800">
        <div className="container mx-auto px-4 lg:px-8">
          <div className="max-w-3xl mx-auto text-center">
            <h2 className="text-3xl md:text-4xl font-bold text-white mb-6">
              Start saving on your utility bills today.
            </h2>
            <p className="text-lg text-teal-100 mb-10">
              Join thousands of Singapore households already using VoltPulse to reduce their energy costs.
            </p>
            <Link
              href="/upload"
              className="inline-flex items-center gap-3 px-8 py-4 bg-white hover:bg-teal-50 text-teal-700 font-semibold rounded-lg transition-all text-lg shadow-lg"
            >
              <FileText className="w-5 h-5" />
              Upload your first bill
            </Link>
          </div>
        </div>
      </section>

      <Footer />
      <Chatbot />
    </main>
  );
}