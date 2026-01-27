"use client";

import { Upload, Cpu, LineChart, Sparkles } from "lucide-react";

const steps = [
  {
    number: "01",
    icon: Upload,
    title: "Upload Your Bill",
    description:
      "Simply upload your SP utility bill as a PDF or image. Our AI will extract all the data automatically.",
  },
  {
    number: "02",
    icon: Cpu,
    title: "AI Analysis",
    description:
      "Our Agentic AI analyzes your consumption patterns, benchmarks against national data, and identifies savings opportunities.",
  },
  {
    number: "03",
    icon: LineChart,
    title: "Get Insights",
    description:
      "Receive personalized recommendations, eligible vouchers, and actionable tips to reduce your energy footprint.",
  },
  {
    number: "04",
    icon: Sparkles,
    title: "Start Saving",
    description:
      "Apply for vouchers, adjust your habits, and watch your bills decrease while helping Singapore reach net zero.",
  },
];

export function HowItWorksSection() {
  return (
    <section id="how-it-works" className="py-20 lg:py-28 bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900">
      <div className="container mx-auto px-4 lg:px-8">
        <div className="max-w-3xl mx-auto text-center mb-16">
          <h2 className="text-3xl md:text-4xl font-bold text-foreground mb-4 text-white">
            How It Works
          </h2>
          <p className="text-lg text-muted-foreground text-pretty text-gray-400">
            Get started in minutes. Our AI handles the heavy lifting so you can
            focus on saving.
          </p>
        </div>

        <div className="max-w-5xl mx-auto">
          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-8">
            {steps.map((step, index) => (
              <div key={index} className="relative">
                {/* Connector Line (hidden on mobile, visible on lg) */}
                {index < steps.length - 1 && (
                  <div className="hidden lg:block absolute top-12 left-[calc(50%+40px)] w-[calc(100%-48px)] h-[2px] bg-border" />
                )}

                <div className="flex flex-col items-center text-center">
                  {/* Step Number & Icon */}
                  <div className="relative mb-6">
                    <div className="flex h-24 w-24 items-center justify-center rounded-2xl bg-green-200 border-2 border-green-400">
                      <step.icon className="h-10 w-10 text-primary" />
                    </div>
                    <div className="absolute -top-2 -right-2 flex h-8 w-8 items-center justify-center rounded-full bg-green-500 text-sm font-bold">
                      {step.number}
                    </div>
                  </div>

                  {/* Content */}
                  <h3 className="font-semibold text-lg text-white mb-2">
                    {step.title}
                  </h3>
                  <p className="text-sm text-gray-300 leading-relaxed">
                    {step.description}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
