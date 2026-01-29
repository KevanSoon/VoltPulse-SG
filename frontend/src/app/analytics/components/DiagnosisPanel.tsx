"use client";

import { DiagnosisResult, AnomalyFlag, EfficiencyIssue, TrendWarning, Recommendation, Severity } from "../types";

interface DiagnosisPanelProps {
  diagnosis: DiagnosisResult | null;
}

function getSeverityColor(severity: Severity): { bg: string; text: string; border: string } {
  switch (severity) {
    case "high":
      return { bg: "bg-red-50", text: "text-red-700", border: "border-red-200" };
    case "medium":
      return { bg: "bg-yellow-50", text: "text-yellow-700", border: "border-yellow-200" };
    case "low":
      return { bg: "bg-blue-50", text: "text-blue-700", border: "border-blue-200" };
    default:
      return { bg: "bg-gray-50", text: "text-gray-700", border: "border-gray-200" };
  }
}

function getGradeColor(grade: string): string {
  switch (grade) {
    case "A":
      return "text-teal-600 bg-teal-100";
    case "B":
      return "text-green-600 bg-green-100";
    case "C":
      return "text-yellow-600 bg-yellow-100";
    case "D":
      return "text-orange-600 bg-orange-100";
    case "F":
      return "text-red-600 bg-red-100";
    default:
      return "text-gray-600 bg-gray-100";
  }
}

function HealthScoreCircle({ score, grade }: { score: number; grade: string }) {
  const circumference = 2 * Math.PI * 40;
  const strokeDashoffset = circumference - (score / 100) * circumference;

  return (
    <div className="relative inline-flex items-center justify-center">
      <svg className="w-24 h-24 transform -rotate-90">
        <circle
          cx="48"
          cy="48"
          r="40"
          stroke="currentColor"
          strokeWidth="8"
          fill="transparent"
          className="text-gray-200"
        />
        <circle
          cx="48"
          cy="48"
          r="40"
          stroke="currentColor"
          strokeWidth="8"
          fill="transparent"
          strokeDasharray={circumference}
          strokeDashoffset={strokeDashoffset}
          strokeLinecap="round"
          className={score >= 80 ? "text-teal-500" : score >= 60 ? "text-yellow-500" : "text-red-500"}
        />
      </svg>
      <div className="absolute flex flex-col items-center">
        <span className={`text-2xl font-bold px-2 py-0.5 rounded ${getGradeColor(grade)}`}>
          {grade}
        </span>
        <span className="text-xs text-gray-500 mt-1">{score.toFixed(0)}/100</span>
      </div>
    </div>
  );
}

function AnomalyCard({ anomaly }: { anomaly: AnomalyFlag }) {
  const colors = getSeverityColor(anomaly.severity);

  return (
    <div className={`p-4 rounded-lg border ${colors.bg} ${colors.border}`}>
      <div className="flex items-start gap-3">
        <div className={`p-1.5 rounded ${colors.bg}`}>
          <svg className={`w-5 h-5 ${colors.text}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
          </svg>
        </div>
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-1">
            <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${colors.bg} ${colors.text}`}>
              {anomaly.severity.toUpperCase()}
            </span>
            <span className="text-xs text-gray-500 capitalize">{anomaly.affected_utility}</span>
          </div>
          <p className={`text-sm font-medium ${colors.text}`}>{anomaly.description}</p>
          {anomaly.deviation_percent && (
            <p className="text-xs text-gray-500 mt-1">
              {anomaly.deviation_percent > 0 ? "+" : ""}{anomaly.deviation_percent.toFixed(1)}% deviation
            </p>
          )}
        </div>
      </div>
    </div>
  );
}

function EfficiencyCard({ issue }: { issue: EfficiencyIssue }) {
  const colors = getSeverityColor(issue.severity);

  return (
    <div className={`p-4 rounded-lg border ${colors.bg} ${colors.border}`}>
      <div className="flex items-start justify-between">
        <div>
          <p className="text-sm font-medium text-gray-900 capitalize">{issue.utility_type}</p>
          <p className="text-xs text-gray-500 mt-0.5">
            {issue.current_value} vs {issue.national_average} (national avg)
          </p>
        </div>
        <div className={`text-right ${colors.text}`}>
          <p className="text-lg font-bold">+{issue.deviation_percent.toFixed(0)}%</p>
          <p className="text-xs">above average</p>
        </div>
      </div>
      <div className="mt-3 pt-3 border-t border-gray-200">
        <p className="text-sm text-gray-600">
          Potential savings: <span className="font-medium text-teal-600">${issue.potential_monthly_savings_sgd.toFixed(2)}/month</span>
        </p>
      </div>
    </div>
  );
}

function TrendCard({ warning }: { warning: TrendWarning }) {
  const colors = getSeverityColor(warning.severity);
  const isIncreasing = warning.trend_direction === "increasing";

  return (
    <div className={`p-4 rounded-lg border ${colors.bg} ${colors.border}`}>
      <div className="flex items-start gap-3">
        <div className={`p-1.5 rounded ${colors.bg}`}>
          {isIncreasing ? (
            <svg className={`w-5 h-5 ${colors.text}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
            </svg>
          ) : (
            <svg className={`w-5 h-5 ${colors.text}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 17h8m0 0v-8m0 8l-8-8-4 4-6-6" />
            </svg>
          )}
        </div>
        <div>
          <p className={`text-sm font-medium ${colors.text}`}>{warning.description}</p>
          {warning.average_monthly_change_percent && (
            <p className="text-xs text-gray-500 mt-1">
              Avg. change: {warning.average_monthly_change_percent > 0 ? "+" : ""}{warning.average_monthly_change_percent.toFixed(1)}%/month
            </p>
          )}
        </div>
      </div>
    </div>
  );
}

function RecommendationCard({ recommendation }: { recommendation: Recommendation }) {
  const categoryIcons: Record<string, JSX.Element> = {
    appliance: (
      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 3v2m6-2v2M9 19v2m6-2v2M5 9H3m2 6H3m18-6h-2m2 6h-2M7 19h10a2 2 0 002-2V7a2 2 0 00-2-2H7a2 2 0 00-2 2v10a2 2 0 002 2zM9 9h6v6H9V9z" />
      </svg>
    ),
    behavior: (
      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
      </svg>
    ),
    maintenance: (
      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
      </svg>
    ),
    monitoring: (
      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
      </svg>
    ),
  };

  return (
    <div className="p-4 bg-white rounded-lg border border-gray-200 hover:border-teal-300 transition-colors">
      <div className="flex items-start gap-3">
        <div className="p-2 bg-teal-50 rounded-lg text-teal-600">
          {categoryIcons[recommendation.category] || categoryIcons.monitoring}
        </div>
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs font-medium px-2 py-0.5 rounded-full bg-gray-100 text-gray-600 capitalize">
              {recommendation.category}
            </span>
            <span className="text-xs text-gray-400">Priority {recommendation.priority}</span>
          </div>
          <p className="font-medium text-gray-900">{recommendation.title}</p>
          <p className="text-sm text-gray-600 mt-1">{recommendation.description}</p>
          {recommendation.potential_savings_percent && (
            <p className="text-xs text-teal-600 mt-2 font-medium">
              Potential savings: ~{recommendation.potential_savings_percent}%
            </p>
          )}
        </div>
      </div>
    </div>
  );
}

export default function DiagnosisPanel({ diagnosis }: DiagnosisPanelProps) {
  if (!diagnosis) {
    return null;
  }

  const hasIssues = diagnosis.anomalies.length > 0 ||
                    diagnosis.efficiency_issues.length > 0 ||
                    diagnosis.trend_warnings.length > 0;

  return (
    <div className="space-y-6">
      {/* Health Score Header */}
      <div className="bg-white rounded-xl p-6 border border-gray-200">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-lg font-semibold text-gray-900">Bill Health Score</h3>
            <p className="text-sm text-gray-500 mt-1">{diagnosis.summary}</p>
            {diagnosis.total_potential_annual_savings_sgd > 0 && (
              <p className="text-sm text-teal-600 font-medium mt-2">
                Potential annual savings: ${diagnosis.total_potential_annual_savings_sgd.toFixed(2)}
              </p>
            )}
          </div>
          <HealthScoreCircle score={diagnosis.overall_health_score} grade={diagnosis.health_grade} />
        </div>
      </div>

      {/* Issues Section */}
      {hasIssues && (
        <div className="space-y-4">
          <h4 className="font-semibold text-gray-900">Issues Detected</h4>

          {/* Anomalies */}
          {diagnosis.anomalies.length > 0 && (
            <div className="space-y-3">
              {diagnosis.anomalies.map((anomaly, idx) => (
                <AnomalyCard key={idx} anomaly={anomaly} />
              ))}
            </div>
          )}

          {/* Efficiency Issues */}
          {diagnosis.efficiency_issues.length > 0 && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {diagnosis.efficiency_issues.map((issue, idx) => (
                <EfficiencyCard key={idx} issue={issue} />
              ))}
            </div>
          )}

          {/* Trend Warnings */}
          {diagnosis.trend_warnings.length > 0 && (
            <div className="space-y-3">
              {diagnosis.trend_warnings.map((warning, idx) => (
                <TrendCard key={idx} warning={warning} />
              ))}
            </div>
          )}
        </div>
      )}

      {/* Recommendations */}
      {diagnosis.recommendations.length > 0 && (
        <div className="space-y-4">
          <h4 className="font-semibold text-gray-900">Recommendations</h4>
          <div className="space-y-3">
            {diagnosis.recommendations.map((rec, idx) => (
              <RecommendationCard key={idx} recommendation={rec} />
            ))}
          </div>
        </div>
      )}

      {/* No Issues Message */}
      {!hasIssues && (
        <div className="bg-teal-50 rounded-xl p-6 border border-teal-100 text-center">
          <div className="inline-flex items-center justify-center w-12 h-12 bg-teal-100 rounded-full mb-3">
            <svg className="w-6 h-6 text-teal-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
          </div>
          <p className="text-teal-800 font-medium">Your energy consumption looks healthy!</p>
          <p className="text-teal-600 text-sm mt-1">No significant issues detected.</p>
        </div>
      )}
    </div>
  );
}
