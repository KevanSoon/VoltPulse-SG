"use client";

import Link from "next/link";
import { Zap, ExternalLink, Github } from "lucide-react";

export function Footer() {
    // Use a static year to avoid hydration mismatch between server and client
    const currentYear = 2026;
    
    return (
        <footer 
            className="bg-teal-800 border-t border-teal-700"
            role="contentinfo"
            aria-label="Site footer"
        >
            <div className="container mx-auto px-4 lg:px-8 py-12">
                <div className="grid grid-cols-2 md:grid-cols-4 gap-8 mb-12">
                    {/* Product */}
                    <div>
                        <h4 className="font-medium text-white text-sm mb-4">Product</h4>
                        <ul className="space-y-3 text-sm" role="list">
                            <li>
                                <Link href="/upload" className="text-teal-200 hover:text-white transition-colors">
                                    Upload Bill
                                </Link>
                            </li>
                            <li>
                                <Link href="/analytics" className="text-teal-200 hover:text-white transition-colors">
                                    Dashboard
                                </Link>
                            </li>
                            <li>
                                <Link href="/chat" className="text-teal-200 hover:text-white transition-colors">
                                    AI Assistant
                                </Link>
                            </li>
                        </ul>
                    </div>

                    {/* Resources */}
                    <div>
                        <h4 className="font-medium text-white text-sm mb-4">Resources</h4>
                        <ul className="space-y-3 text-sm" role="list">
                            <li>
                                <a
                                    href="https://www.nea.gov.sg/our-services/climate-change-energy-efficiency/climate-friendly-households-programme"
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="text-teal-200 hover:text-white transition-colors inline-flex items-center gap-1"
                                >
                                    Climate Vouchers
                                    <ExternalLink className="w-3 h-3" />
                                </a>
                            </li>
                            <li>
                                <a
                                    href="https://www.ema.gov.sg/consumers/electricity"
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="text-teal-200 hover:text-white transition-colors inline-flex items-center gap-1"
                                >
                                    EMA Guide
                                    <ExternalLink className="w-3 h-3" />
                                </a>
                            </li>
                            <li>
                                <a
                                    href="https://www.pub.gov.sg/watersupply/conservewater"
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="text-teal-200 hover:text-white transition-colors inline-flex items-center gap-1"
                                >
                                    PUB Water Tips
                                    <ExternalLink className="w-3 h-3" />
                                </a>
                            </li>
                        </ul>
                    </div>

                    {/* Legal */}
                    <div>
                        <h4 className="font-medium text-white text-sm mb-4">Legal</h4>
                        <ul className="space-y-3 text-sm" role="list">
                            <li>
                                <Link href="#" className="text-teal-200 hover:text-white transition-colors">
                                    Privacy
                                </Link>
                            </li>
                            <li>
                                <Link href="#" className="text-teal-200 hover:text-white transition-colors">
                                    Terms of use
                                </Link>
                            </li>
                        </ul>
                    </div>

                    {/* Connect */}
                    <div>
                        <h4 className="font-medium text-white text-sm mb-4">Connect</h4>
                        <ul className="space-y-3 text-sm" role="list">
                            <li>
                                <a
                                    href="https://github.com"
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="text-teal-200 hover:text-white transition-colors inline-flex items-center gap-2"
                                >
                                    <Github className="w-4 h-4" />
                                    GitHub
                                </a>
                            </li>
                        </ul>
                    </div>
                </div>

                {/* Bottom bar */}
                <div className="pt-8 border-t border-teal-700 flex flex-col sm:flex-row justify-between items-center gap-4">
                    <div className="flex items-center gap-2">
                        <div className="bg-white/20 p-1 rounded">
                            <Zap className="w-4 h-4 text-white" />
                        </div>
                        <span className="text-sm font-medium text-white">VoltPulse</span>
                    </div>
                    <p className="text-sm text-teal-300">
                        © {currentYear} VoltPulse SG
                    </p>
                </div>
            </div>
        </footer>
    );
}