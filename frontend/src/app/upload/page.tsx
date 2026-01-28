"use client";

import { useState, useCallback } from "react";
import { useDropzone } from "react-dropzone";
import { useRouter } from "next/navigation";
import Link from "next/link";
import Chatbot from "../components/Chatbot";
import { Navbar } from "../components/navbar";
import { Footer } from "../components/footer";

import { MessageCircleMore, ChartNoAxesCombined, Sparkles, X, CheckCircle } from 'lucide-react';

interface OCRResult {
    text: string;
    box: number[][];
}

interface OCRResponse {
    ocr_results: Record<string, OCRResult>;
    extracted_texts: string[];
    embedding_stored: boolean;
    source_id: string;
}

export default function Upload() {
    const router = useRouter();
    const [file, setFile] = useState<File | null>(null);
    const [preview, setPreview] = useState<string | null>(null);
    const [loading, setLoading] = useState(false);
    const [results, setResults] = useState<OCRResponse | null>(null);
    const [error, setError] = useState<string | null>(null);
    const [redirecting, setRedirecting] = useState(false);

    const onDrop = useCallback((acceptedFiles: File[]) => {
        const selectedFile = acceptedFiles[0];
        if (selectedFile) {
            setFile(selectedFile);
            setPreview(URL.createObjectURL(selectedFile));
            setResults(null);
            setError(null);
        }
    }, []);

    const { getRootProps, getInputProps, isDragActive } = useDropzone({
        onDrop,
        accept: {
            "image/*": [".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"],
        },
        maxFiles: 1,
    });

    const handleUpload = async () => {
        if (!file) return;

        setLoading(true);
        setError(null);

        try {
            const formData = new FormData();
            formData.append("file", file);

            const response = await fetch("/api/ocr", {
                method: "POST",
                body: formData,
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || "OCR processing failed");
            }

            const data: OCRResponse = await response.json();
            setResults(data);

            // Store the source_id in localStorage for the analytics page
            if (data.source_id) {
                localStorage.setItem("ocr_source_id", data.source_id);
            }

            // Show success briefly then redirect to analytics
            setRedirecting(true);
            setTimeout(() => {
                router.push("/analytics");
            }, 1500);
        } catch (err) {
            setError(err instanceof Error ? err.message : "An error occurred");
        } finally {
            setLoading(false);
        }
    };

    const clearFile = () => {
        setFile(null);
        setPreview(null);
        setResults(null);
        setError(null);
    };

    return (
        <main className="min-h-screen bg-background flex flex-col">
            <Navbar />

            <main className="flex-1 p-8">
                <div className="max-w-4xl mx-auto">
                    <div className="mb-8">
                        <Link
                            href="/"
                            className="text-gray-500 hover:text-green-600 flex items-center gap-2 transition-colors"
                            title="Back to Home"
                        >
                            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
                            </svg>
                            Back to Home
                        </Link>
                    </div>

                    <div className="text-center mb-8">
                        <h1 className="text-4xl font-bold text-gray-900 mb-2">
                            Upload Your Utility Bill
                        </h1>
                        <p className="text-gray-600">
                            Upload an image of your bill and let our AI analyze your consumption pattern
                        </p>
                    </div>

                    {/* Dropzone */}
                    <div
                        {...getRootProps()}
                        className={`border-2 border-dashed rounded-xl p-24 text-center cursor-pointer transition-all duration-200 ${isDragActive
                            ? "border-green-500 bg-green-50"
                            : "border-green-400 hover:border-green-500 bg-green-50/50"
                            }`}
                    >
                        <input {...getInputProps()} />
                        {preview ? (
                            <div className="space-y-4">
                                <img
                                    src={preview}
                                    alt="Preview"
                                    className="max-h-64 mx-auto rounded-lg shadow-lg"
                                />
                                <p className="text-gray-600">{file?.name}</p>
                            </div>
                        ) : (
                            <div className="space-y-4">
                                <div className="w-16 h-16 mx-auto text-green-500">
                                    <svg
                                        fill="none"
                                        stroke="currentColor"
                                        viewBox="0 0 24 24"
                                        xmlns="http://www.w3.org/2000/svg"
                                    >
                                        <path
                                            strokeLinecap="round"
                                            strokeLinejoin="round"
                                            strokeWidth={2}
                                            d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"
                                        />
                                    </svg>
                                </div>
                                <div className="pt-4">
                                    <p className="text-xl text-gray-700">
                                        {isDragActive
                                            ? "Drop the image here..."
                                            : "Drag & drop an image here"}
                                    </p>
                                    <p className="text-gray-500 mt-2">or click to select a file</p>
                                </div>
                            </div>
                        )}
                    </div>

                    {/* Action Buttons */}
                    {file && (
                        <div className="flex gap-4 mt-6 justify-center">
                            <button
                                onClick={handleUpload}
                                disabled={loading}
                                className="px-6 py-3 bg-green-600 hover:bg-green-700 disabled:bg-green-400 disabled:cursor-not-allowed text-white font-semibold rounded-lg transition-colors flex items-center gap-2"
                            >
                                {loading ? (
                                    <>
                                        <svg
                                            className="animate-spin h-5 w-5"
                                            viewBox="0 0 24 24"
                                        >
                                            <circle
                                                className="opacity-25"
                                                cx="12"
                                                cy="12"
                                                r="10"
                                                stroke="currentColor"
                                                strokeWidth="4"
                                                fill="none"
                                            />
                                            <path
                                                className="opacity-75"
                                                fill="currentColor"
                                                d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                                            />
                                        </svg>
                                        Processing...
                                    </>
                                ) : (
                                    "Extract Information"
                                )}
                            </button>
                            <button
                                onClick={clearFile}
                                className="px-6 py-3 bg-gray-200 hover:bg-gray-300 text-gray-700 font-semibold rounded-lg transition-colors"
                            >
                                Clear
                            </button>
                        </div>
                    )}

                    {/* Error Message */}
                    {error && (
                        <div className="mt-6 p-4 bg-red-100 border border-red-200 rounded-lg">
                            <div className="flex inline-flex gap-2 items-center">
                                <X className="text-red-600" />
                                <p className="text-red-600">{error}</p>
                            </div>
                        </div>
                    )}

                    {/* Results */}
                    {results && (
                        <div className="mt-8 space-y-6">
                            {/* Success & Redirect Message */}
                            <div className="bg-gradient-to-r from-green-50 to-emerald-50 rounded-xl p-7 border border-emerald-300">
                                <div className="text-center">
                                    <div className="flex justify-center mb-4">
                                        <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center">
                                            <CheckCircle size={32} className="text-green-600" />
                                        </div>
                                    </div>
                                    <h3 className="text-xl font-semibold text-gray-900 mb-2">
                                        Bill Processed Successfully!
                                    </h3>
                                    {redirecting ? (
                                        <div className="space-y-3">
                                            <p className="text-gray-600">
                                                Redirecting to your dashboard...
                                            </p>
                                            <div className="flex justify-center">
                                                <div className="animate-spin w-6 h-6 border-2 border-green-500 border-t-transparent rounded-full" />
                                            </div>
                                        </div>
                                    ) : (
                                        <div className="space-y-4">
                                            <p className="text-gray-600">
                                                Your bill data has been extracted and saved.
                                            </p>
                                            <div className="flex flex-col sm:flex-row gap-4 justify-center">
                                                <Link
                                                    href="/analytics"
                                                    className="inline-flex justify-center gap-2 px-6 py-3 bg-green-500 hover:bg-green-700 text-white font-medium rounded-lg transition-colors items-center"
                                                >
                                                    <ChartNoAxesCombined size={18} /> View Dashboard
                                                </Link>
                                                <Link
                                                    href="/chat"
                                                    className="inline-flex justify-center gap-2 px-6 py-3 bg-white border border-gray-300 hover:border-green-500 text-gray-600 font-medium rounded-lg transition-colors items-center"
                                                >
                                                    <MessageCircleMore size={18} /> Chat with AI
                                                </Link>
                                            </div>
                                        </div>
                                    )}
                                </div>
                            </div>
                        </div>
                    )}
                </div>
            </main>

            <Footer />
            <Chatbot />
        </main>
    );
}
