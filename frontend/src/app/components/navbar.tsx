"use client";

import Link from "next/link";
import Image from "next/image";
import { usePathname } from "next/navigation";
import { useState, useEffect } from "react";
import { Menu, X, BarChart3, MessageSquare, Upload } from "lucide-react";

interface NavItem {
  href: string;
  label: string;
  icon: React.ReactNode;
}

const navItems: NavItem[] = [
  { href: "/upload", label: "Upload Bill", icon: <Upload className="w-4 h-4" /> },
  { href: "/analytics", label: "Dashboard", icon: <BarChart3 className="w-4 h-4" /> },
  { href: "/chat", label: "Chat", icon: <MessageSquare className="w-4 h-4" /> },
];

export function Navbar() {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);
  const pathname = usePathname();

  useEffect(() => {
    const handleScroll = () => {
      setScrolled(window.scrollY > 10);
    };
    window.addEventListener("scroll", handleScroll);
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  useEffect(() => {
    setMobileMenuOpen(false);
  }, [pathname]);

  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === "Escape") setMobileMenuOpen(false);
    };
    document.addEventListener("keydown", handleEscape);
    return () => document.removeEventListener("keydown", handleEscape);
  }, []);

  const isActive = (href: string) => {
    if (href === "/") return pathname === "/";
    return pathname.startsWith(href);
  };

  return (
    <nav 
      className={`sticky top-0 z-50 bg-teal-700 transition-all ${
        scrolled ? "shadow-lg shadow-teal-900/20" : ""
      }`}
      role="navigation"
      aria-label="Main navigation"
    >
      <div className="container mx-auto px-4 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <Link 
            href="/" 
            className="flex items-center gap-2.5 hover:opacity-90 transition-opacity focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white focus-visible:ring-offset-2 focus-visible:ring-offset-teal-700 rounded-lg"
            aria-label="VoltPulse - Go to homepage"
          >
            <Image
              src="/volt.png"
              alt="VoltPulse Logo"
              width={32}
              height={32}
              className="rounded-lg"
              priority
              unoptimized
            />
            <span className="text-lg font-semibold text-white tracking-tight">VoltPulse</span>
          </Link>

          {/* Desktop Navigation */}
          <div className="hidden md:flex items-center gap-6" role="menubar">
            {navItems.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                role="menuitem"
                className={`flex items-center gap-2 text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white rounded px-1 py-0.5 ${
                  isActive(item.href)
                    ? "text-white"
                    : "text-teal-100 hover:text-white"
                }`}
                aria-current={isActive(item.href) ? "page" : undefined}
              >
                {item.label}
              </Link>
            ))}
            
            {/* Login/CTA Button */}
            <Link
              href="/upload"
              className="ml-2 px-4 py-2 bg-white hover:bg-teal-50 text-teal-700 text-sm font-medium rounded-md transition-colors"
            >
              Get Started
            </Link>
          </div>

          {/* Mobile Menu Button */}
          <button
            className="md:hidden text-teal-100 hover:text-white p-2 rounded-lg transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white"
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            aria-label={mobileMenuOpen ? "Close menu" : "Open menu"}
            aria-expanded={mobileMenuOpen}
            aria-controls="mobile-menu"
          >
            {mobileMenuOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
          </button>
        </div>

        {/* Mobile Menu */}
        <div 
          id="mobile-menu"
          className={`md:hidden overflow-hidden transition-all duration-200 ${
            mobileMenuOpen ? "max-h-80 pb-4" : "max-h-0"
          }`}
          role="menu"
          aria-hidden={!mobileMenuOpen}
        >
          <div className="flex flex-col gap-1 border-t border-teal-600 pt-4">
            {navItems.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                role="menuitem"
                className={`flex items-center gap-3 px-4 py-3 rounded-lg transition-colors ${
                  isActive(item.href)
                    ? "bg-teal-600 text-white"
                    : "text-teal-100 hover:bg-teal-600 hover:text-white"
                }`}
                aria-current={isActive(item.href) ? "page" : undefined}
                tabIndex={mobileMenuOpen ? 0 : -1}
              >
                {item.icon}
                {item.label}
              </Link>
            ))}
            <Link
              href="/upload"
              className="mt-2 mx-4 px-4 py-3 bg-white hover:bg-teal-50 text-teal-700 text-center font-medium rounded-lg transition-colors"
              tabIndex={mobileMenuOpen ? 0 : -1}
            >
              Get Started
            </Link>
          </div>
        </div>
      </div>
    </nav>
  );
}