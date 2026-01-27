"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

function NavLink({
  href,
  children,
}: {
  href: string;
  children: React.ReactNode;
}) {
  const pathname = usePathname();
  const isActive = pathname === href;

  return (
    <Link
      href={href}
      className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
        isActive
          ? "bg-blue-600 text-white"
          : "text-gray-400 hover:text-white hover:bg-gray-700"
      }`}
    >
      {children}
    </Link>
  );
}

export default function AnalyticsLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900">
      {/* Navigation Header */}
      <header className="bg-gray-800/50 backdrop-blur-sm border-b border-gray-700 px-6 py-4 sticky top-0 z-50">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link
              href="/"
              className="text-gray-400 hover:text-white transition-colors"
              title="Back to Home"
            >
              <svg
                xmlns="http://www.w3.org/2000/svg"
                className="h-5 w-5"
                viewBox="0 0 20 20"
                fill="currentColor"
              >
                <path
                  fillRule="evenodd"
                  d="M9.707 16.707a1 1 0 01-1.414 0l-6-6a1 1 0 010-1.414l6-6a1 1 0 011.414 1.414L5.414 9H17a1 1 0 110 2H5.414l4.293 4.293a1 1 0 010 1.414z"
                  clipRule="evenodd"
                />
              </svg>
            </Link>
            <div>
              <h1 className="text-xl font-bold text-white">
                Urban Planner Analytics
              </h1>
              <p className="text-xs text-gray-400">
                District consumption analysis & anomaly detection
              </p>
            </div>
          </div>
          <nav className="flex gap-2">
            <NavLink href="/analytics">Dashboard</NavLink>
          </nav>
        </div>
      </header>

      <main className="max-w-7xl mx-auto py-8 px-6">{children}</main>

      {/* Footer */}
      <footer className="border-t border-gray-700 py-4 mt-8">
        <div className="max-w-7xl mx-auto px-6 text-center text-gray-500 text-sm">
          Statistical methodology: 95% Confidence Intervals (z = 1.96) | Paired
          t-tests for intervention analysis
        </div>
      </footer>
    </div>
  );
}
