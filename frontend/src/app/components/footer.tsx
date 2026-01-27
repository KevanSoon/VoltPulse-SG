"use client";

import Link from "next/link";
import { Zap } from "lucide-react";

export function Footer() {
    return (
        <footer className="bg-secondary/30 border-t border-border bg-black lg:px-24">
            <div className="container mx-auto px-5 lg:px-12 py-12">
                <div className="grid grid-cols-1 md:grid-cols-3 gap-16 mb-8">
                    {/* Brand */}
                    <div className="md:col-span-2">
                        <Link href="/" className="flex items-center gap-2 mb-4">
                            <div className="text-white p-2 rounded-lg">
                                <Zap className="w-5 h-5 text-primary-foreground" />
                            </div>
                            <span className="text-lg font-bold text-white">VoltPulse</span>
                        </Link>
                        <p className="text-sm text-gray-400">
                            Agentic AI platform to analyze your utility bills, benchmark your consumption against national averages
                            for urban sustainability and liveability in Singapore.
                        </p>
                    </div>

                    {/* Platform */}
                    <div>
                        <h4 className="font-semibold text-white mb-4">Quick Links</h4>
                        <ul className="space-y-2 text-sm text-gray-400">
                            <li>
                                <Link
                                    href="/"
                                    className="hover:text-white transition-colors"
                                >
                                    Dashboard
                                </Link>
                            </li>
                            <li>
                                <Link
                                    href="/upload"
                                    className="hover:text-white transition-colors"
                                >
                                    Upload Bills
                                </Link>
                            </li>
                            <li>
                                <Link
                                    href="/chat"
                                    className="hover:text-white transition-colors"
                                >
                                    Chat Assistant
                                </Link>
                            </li>
                        </ul>
                    </div>
                </div>

                <div className="pt-6 justify-items-center items-center text-sm text-gray-400">
                    <p>© 2026 EcoSave SG. Built for Singapore&apos;s sustainable future.</p>
                </div>
            </div>
        </footer>
    );
}