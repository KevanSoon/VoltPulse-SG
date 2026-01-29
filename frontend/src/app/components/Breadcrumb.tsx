"use client";

import Link from "next/link";
import { ChevronRight, Home } from "lucide-react";

export interface BreadcrumbItem {
  label: string;
  href?: string;
  current?: boolean;
}

interface BreadcrumbProps {
  items: BreadcrumbItem[];
  className?: string;
}

export function Breadcrumb({ items, className = "" }: BreadcrumbProps) {
  return (
    <nav 
      aria-label="Breadcrumb" 
      className={`flex items-center text-sm ${className}`}
    >
      <ol className="flex items-center gap-1 flex-wrap" role="list">
        <li className="flex items-center">
          <Link
            href="/"
            className="text-slate-500 hover:text-teal-600 transition-colors flex items-center gap-1"
            aria-label="Home"
          >
            <Home className="w-4 h-4" />
            <span className="sr-only">Home</span>
          </Link>
        </li>
        
        {items.map((item, index) => (
          <li key={index} className="flex items-center">
            <ChevronRight className="w-4 h-4 text-slate-400 mx-1 flex-shrink-0" aria-hidden="true" />
            {item.current || !item.href ? (
              <span 
                className="text-slate-800 font-medium"
                aria-current={item.current ? "page" : undefined}
              >
                {item.label}
              </span>
            ) : (
              <Link
                href={item.href}
                className="text-slate-500 hover:text-teal-600 transition-colors"
              >
                {item.label}
              </Link>
            )}
          </li>
        ))}
      </ol>
    </nav>
  );
}
export default Breadcrumb;