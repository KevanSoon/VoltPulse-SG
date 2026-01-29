"use client";

import { useState, useEffect } from "react";
import { ChevronLeft, ChevronRight, Quote } from "lucide-react";

const testimonials = [
  {
    id: 1,
    name: "Ahmad Rahman",
    location: "Tampines, HDB 4-room",
    avatar: "AR",
    quote: "VoltPulse helped me identify that my old fridge was using 3x the energy it should. Used my Climate Voucher to upgrade and now I'm saving S$40 monthly!",
    savings: "S$480/year",
  },
  {
    id: 2,
    name: "Sarah Tan",
    location: "Bedok, HDB 5-room",
    avatar: "ST",
    quote: "The AI recommendations were spot on. I didn't know setting my AC to 25°C could make such a big difference. My family's bills dropped by 20%.",
    savings: "S$360/year",
  },
  {
    id: 3,
    name: "Kumar Rajan",
    location: "Jurong West, HDB 3-room",
    avatar: "KR",
    quote: "Finally understand my SP bill! The breakdown is so clear, and I love comparing my usage to my neighbors. Great for staying accountable.",
    savings: "S$240/year",
  },
  {
    id: 4,
    name: "Mei Ling Wong",
    location: "Ang Mo Kio, Condo",
    avatar: "MW",
    quote: "The heatmap showed me our estate was one of the highest consumers. Started a community initiative thanks to VoltPulse insights!",
    savings: "S$600/year",
  },
];

export function Testimonials() {
  const [activeIndex, setActiveIndex] = useState(0);
  const [isAutoPlaying, setIsAutoPlaying] = useState(true);

  useEffect(() => {
    if (!isAutoPlaying) return;
    
    const interval = setInterval(() => {
      setActiveIndex((prev) => (prev + 1) % testimonials.length);
    }, 5000);

    return () => clearInterval(interval);
  }, [isAutoPlaying]);

  const goToPrevious = () => {
    setIsAutoPlaying(false);
    setActiveIndex((prev) => (prev - 1 + testimonials.length) % testimonials.length);
  };

  const goToNext = () => {
    setIsAutoPlaying(false);
    setActiveIndex((prev) => (prev + 1) % testimonials.length);
  };

  const activeTestimonial = testimonials[activeIndex];

  return (
    <section className="py-16 lg:py-24 bg-gradient-to-b from-white to-slate-50">
      <div className="container mx-auto px-4 lg:px-8">
        <div className="max-w-3xl mx-auto text-center mb-12">
          <h2 className="text-3xl md:text-4xl font-bold text-slate-800 mb-4">
            Real Savings from Real Singaporeans
          </h2>
          <p className="text-lg text-slate-600">
            Join thousands of households already reducing their energy bills
          </p>
        </div>

        <div className="max-w-4xl mx-auto">
          <div 
            className="bg-white rounded-2xl shadow-xl p-8 md:p-12 relative border border-slate-100"
            role="region"
            aria-roledescription="carousel"
            aria-label="Customer testimonials"
          >
            {/* Quote icon */}
            <div className="absolute top-6 left-6 text-teal-100">
              <Quote className="w-16 h-16" />
            </div>

            <div className="relative z-10">
              {/* Testimonial content */}
              <div 
                key={activeTestimonial.id}
                className="fade-in"
              >
                <blockquote className="text-xl md:text-2xl text-slate-700 mb-8 leading-relaxed">
                  &ldquo;{activeTestimonial.quote}&rdquo;
                </blockquote>

                <div className="flex items-center justify-between flex-wrap gap-4">
                  <div className="flex items-center gap-4">
                    <div 
                      className="w-14 h-14 rounded-full bg-gradient-to-br from-teal-500 to-teal-600 flex items-center justify-center text-white font-bold text-lg shadow-md"
                      aria-hidden="true"
                    >
                      {activeTestimonial.avatar}
                    </div>
                    <div>
                      <p className="font-semibold text-slate-800">{activeTestimonial.name}</p>
                      <p className="text-slate-500 text-sm">{activeTestimonial.location}</p>
                    </div>
                  </div>
                  <div className="bg-amber-100 px-4 py-2 rounded-full">
                    <span className="text-amber-700 font-semibold">
                      Saved {activeTestimonial.savings}
                    </span>
                  </div>
                </div>
              </div>
            </div>

            {/* Navigation */}
            <div className="flex items-center justify-between mt-8 pt-6 border-t border-slate-100">
              <div className="flex gap-2">
                {testimonials.map((_, index) => (
                  <button
                    key={index}
                    onClick={() => {
                      setIsAutoPlaying(false);
                      setActiveIndex(index);
                    }}
                    className={`w-2.5 h-2.5 rounded-full transition-colors ${
                      index === activeIndex ? "bg-teal-600" : "bg-slate-300 hover:bg-slate-400"
                    }`}
                    aria-label={`Go to testimonial ${index + 1}`}
                    aria-current={index === activeIndex}
                  />
                ))}
              </div>
              
              <div className="flex gap-2">
                <button
                  onClick={goToPrevious}
                  className="p-2 rounded-full border border-slate-200 hover:border-teal-500 hover:bg-teal-50 transition-colors"
                  aria-label="Previous testimonial"
                >
                  <ChevronLeft className="w-5 h-5 text-slate-600" />
                </button>
                <button
                  onClick={goToNext}
                  className="p-2 rounded-full border border-slate-200 hover:border-teal-500 hover:bg-teal-50 transition-colors"
                  aria-label="Next testimonial"
                >
                  <ChevronRight className="w-5 h-5 text-slate-600" />
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
