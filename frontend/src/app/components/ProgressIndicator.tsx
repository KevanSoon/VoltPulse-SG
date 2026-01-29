"use client";

import { Check } from "lucide-react";

export interface ProgressStep {
  id: string;
  label: string;
  description?: string;
}

interface ProgressIndicatorProps {
  steps: ProgressStep[];
  currentStep: number;
  className?: string;
}

export function ProgressIndicator({ steps, currentStep, className = "" }: ProgressIndicatorProps) {
  return (
    <nav aria-label="Progress" className={className}>
      <ol className="flex items-center justify-between w-full" role="list">
        {steps.map((step, index) => {
          const isCompleted = index < currentStep;
          const isCurrent = index === currentStep;
          
          return (
            <li 
              key={step.id} 
              className={`flex items-center ${index < steps.length - 1 ? 'flex-1' : ''}`}
            >
              <div className="flex flex-col items-center">
                <div className="flex items-center">
                  <div
                    className={`
                      flex items-center justify-center w-10 h-10 rounded-full border-2 transition-colors
                      ${isCompleted 
                        ? 'bg-teal-600 border-teal-600 text-white' 
                        : isCurrent 
                          ? 'border-teal-600 text-teal-600 bg-white' 
                          : 'border-slate-300 text-slate-400 bg-white'
                      }
                    `}
                    aria-current={isCurrent ? "step" : undefined}
                  >
                    {isCompleted ? (
                      <Check className="w-5 h-5" aria-hidden="true" />
                    ) : (
                      <span className="font-semibold">{index + 1}</span>
                    )}
                  </div>
                </div>
                <div className="mt-2 text-center">
                  <p 
                    className={`text-sm font-medium ${isCurrent ? 'text-teal-600' : isCompleted ? 'text-slate-800' : 'text-slate-500'}`}
                  >
                    {step.label}
                  </p>
                  {step.description && (
                    <p className="text-xs text-gray-500 mt-0.5 max-w-[100px]">
                      {step.description}
                    </p>
                  )}
                </div>
              </div>
              
              {/* Connector line */}
              {index < steps.length - 1 && (
                <div 
                  className={`flex-1 h-0.5 mx-4 ${isCompleted ? 'bg-teal-600' : 'bg-slate-200'}`}
                  aria-hidden="true"
                />
              )}
            </li>
          );
        })}
      </ol>
    </nav>
  );
}
export default ProgressIndicator;