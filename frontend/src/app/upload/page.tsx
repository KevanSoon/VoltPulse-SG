"use client";

import { useState, useCallback, useMemo } from "react";
import { useDropzone, FileRejection } from "react-dropzone";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Navbar } from "../components/navbar";
import { Footer } from "../components/footer";
import { Breadcrumb } from "../components/Breadcrumb";
import { ProgressIndicator } from "../components/ProgressIndicator";

import { MessageCircleMore, ChartNoAxesCombined, Sparkles, X, CheckCircle, AlertCircle, FileImage, Upload as UploadIcon, HelpCircle } from 'lucide-react';

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

const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10MB
const ACCEPTED_TYPES = ["image/png", "image/jpg", "image/jpeg", "image/gif", "image/bmp", "image/webp"];

const uploadSteps = [
    { id: "upload", label: "Upload", description: "Select bill image" },
    { id: "process", label: "Process", description: "AI extraction" },
    { id: "analyze", label: "Analyze", description: "View insights" },
];

export default function Upload() {
    const router = useRouter();
    const [file, setFile] = useState<File | null>(null);
    const [preview, setPreview] = useState<string | null>(null);
    const [loading, setLoading] = useState(false);
    const [uploadProgress, setUploadProgress] = useState(0);
    const [results, setResults] = useState<OCRResponse | null>(null);
    const [error, setError] = useState<string | null>(null);
    const [fileError, setFileError] = useState<string | null>(null);
    const [redirecting, setRedirecting] = useState(false);

    const currentStep = useMemo(() => {
        if (results || redirecting) return 2;
        if (loading) return 1;
        return 0;
    }, [results, redirecting, loading]);

    const validateFile = useCallback((file: File): string | null => {
        if (!ACCEPTED_TYPES.includes(file.type)) {
            return "Please upload an image file (PNG, JPG, GIF, BMP, or WebP)";
        }
        if (file.size > MAX_FILE_SIZE) {
            return `File size must be less than 10MB. Your file is ${(file.size / 1024 / 1024).toFixed(1)}MB`;
        }
        return null;
    }, []);

    const onDrop = useCallback((acceptedFiles: File[], rejectedFiles: FileRejection[]) => {
        setFileError(null);
        setError(null);
        
        if (rejectedFiles.length > 0) {
            const rejection = rejectedFiles[0];
            if (rejection.errors[0]?.code === "file-too-large") {
                setFileError("File is too large. Maximum size is 10MB.");
            } else if (rejection.errors[0]?.code === "file-invalid-type") {
                setFileError("Invalid file type. Please upload an image.");
            } else {
                setFileError(rejection.errors[0]?.message || "File rejected");
            }
            return;
        }

        const selectedFile = acceptedFiles[0];
        if (selectedFile) {
            const validationError = validateFile(selectedFile);
            if (validationError) {
                setFileError(validationError);
                return;
            }
            setFile(selectedFile);
            setPreview(URL.createObjectURL(selectedFile));
            setResults(null);
        }
    }, [validateFile]);

    const { getRootProps, getInputProps, isDragActive } = useDropzone({
        onDrop,
        accept: {
            "image/*": [".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"],
        },
        maxFiles: 1,
        maxSize: MAX_FILE_SIZE,
    });

    const handleUpload = async () => {
        if (!file) return;

        setLoading(true);
        setError(null);
        setUploadProgress(0);

        // Simulate progress for better UX
        const progressInterval = setInterval(() => {
            setUploadProgress((prev) => Math.min(prev + 10, 90));
        }, 500);

        try {
            const formData = new FormData();
            formData.append("file", file);

            const response = await fetch("/api/ocr", {
                method: "POST",
                body: formData,
            });

            clearInterval(progressInterval);
            setUploadProgress(100);

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
            clearInterval(progressInterval);
            setUploadProgress(0);
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
        setFileError(null);
        setUploadProgress(0);
    };

    return (
        <main className="min-h-screen bg-white flex flex-col" id="main-content">
            <Navbar />

            <main className="flex-1 p-8">
                <div className="max-w-4xl mx-auto">
                    {/* Breadcrumb */}
                    <Breadcrumb
                        items={[{ label: "Upload Bills", current: true }]}
                        className="mb-6"
                    />

                    {/* Progress Indicator */}
                    <div className="mb-8">
                        <ProgressIndicator steps={uploadSteps} currentStep={currentStep} />
                    </div>

                    <div className="text-center mb-8">
                        <h1 className="text-4xl font-bold text-gray-900 mb-2">
                            Upload Your Utility Bill
                        </h1>
                        <p className="text-gray-600">
                            Upload an image of your SP bill and let our AI analyze your consumption pattern
                        </p>
                    </div>

                    {/* Helper Tips */}
                    <div className="bg-teal-50 border border-teal-200 rounded-xl p-4 mb-6">
                        <div className="flex gap-3">
                            <HelpCircle className="w-5 h-5 text-teal-600 flex-shrink-0 mt-0.5" aria-hidden="true" />
                            <div>
                                <h3 className="font-medium text-teal-900 mb-1">Tips for best results</h3>
                                <ul className="text-sm text-teal-800 space-y-1">
                                    <li>• Ensure the bill is clearly visible and well-lit</li>
                                    <li>• Include all pages showing consumption data and charts</li>
                                    <li>• Supported formats: PNG, JPG, WebP (max 10MB)</li>
                                </ul>
                            </div>
                        </div>
                    </div>

                    {/* Dropzone */}
                    <div
                        {...getRootProps()}
                        className={`border-2 border-dashed rounded-xl p-12 md:p-16 text-center cursor-pointer transition-all duration-200 ${
                            isDragActive
                                ? "border-teal-500 bg-teal-50"
                                : fileError
                                    ? "border-red-400 bg-red-50"
                                    : "border-teal-400 hover:border-teal-500 bg-teal-50/50"
                        }`}
                        role="button"
                        aria-label="Upload bill image"
                        tabIndex={0}
                    >
                        <input {...getInputProps()} aria-label="File input" />
                        {preview ? (
                            <div className="space-y-4">
                                <img
                                    src={preview}
                                    alt="Bill preview"
                                    className="max-h-64 mx-auto rounded-lg shadow-lg"
                                />
                                <div className="flex items-center justify-center gap-2 text-gray-600">
                                    <FileImage className="w-4 h-4" aria-hidden="true" />
                                    <p>{file?.name}</p>
                                    <span className="text-gray-400">•</span>
                                    <p className="text-sm text-gray-500">
                                        {file && (file.size / 1024 / 1024).toFixed(2)}MB
                                    </p>
                                </div>
                            </div>
                        ) : (
                            <div className="space-y-4">
                                <div className="w-16 h-16 mx-auto text-teal-500 bg-teal-100 rounded-full flex items-center justify-center">
                                    <UploadIcon className="w-8 h-8" aria-hidden="true" />
                                </div>
                                <div className="pt-4">
                                    <p className="text-xl text-gray-700">
                                        {isDragActive
                                            ? "Drop the image here..."
                                            : "Drag & drop your bill here"}
                                    </p>
                                    <p className="text-gray-500 mt-2">or click to select a file</p>
                                    <p className="text-xs text-gray-400 mt-2">PNG, JPG, WebP up to 10MB</p>
                                </div>
                            </div>
                        )}
                    </div>

                    {/* File Validation Error */}
                    {fileError && (
                        <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-lg" role="alert">
                            <div className="flex items-center gap-2">
                                <AlertCircle className="w-5 h-5 text-red-600" aria-hidden="true" />
                                <p className="text-red-600 font-medium">{fileError}</p>
                            </div>
                        </div>
                    )}

                    {/* Action Buttons */}
                    {file && !fileError && (
                        <div className="flex gap-4 mt-6 justify-center">
                            <button
                                onClick={handleUpload}
                                disabled={loading}
                                className="px-6 py-3 bg-teal-600 hover:bg-teal-700 disabled:bg-teal-400 disabled:cursor-not-allowed text-white font-semibold rounded-lg transition-colors flex items-center gap-2 min-w-[200px] justify-center"
                                aria-busy={loading}
                            >
                                {loading ? (
                                    <>
                                        <svg
                                            className="animate-spin h-5 w-5"
                                            viewBox="0 0 24 24"
                                            aria-hidden="true"
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
                                        Processing... {uploadProgress}%
                                    </>
                                ) : (
                                    <>
                                        <Sparkles className="w-5 h-5" aria-hidden="true" />
                                        Extract Information
                                    </>
                                )}
                            </button>
                            <button
                                onClick={clearFile}
                                disabled={loading}
                                className="px-6 py-3 bg-gray-200 hover:bg-gray-300 disabled:opacity-50 text-gray-700 font-semibold rounded-lg transition-colors"
                            >
                                Clear
                            </button>
                        </div>
                    )}

                    {/* Upload Progress Bar */}
                    {loading && (
                        <div className="mt-6">
                            <div className="flex justify-between text-sm text-gray-600 mb-2">
                                <span>Processing your bill...</span>
                                <span>{uploadProgress}%</span>
                            </div>
                            <div className="w-full bg-gray-200 rounded-full h-2 overflow-hidden">
                                <div
                                    className="bg-teal-600 h-2 rounded-full transition-all duration-300"
                                    style={{ width: `${uploadProgress}%` }}
                                    role="progressbar"
                                    aria-valuenow={uploadProgress}
                                    aria-valuemin={0}
                                    aria-valuemax={100}
                                />
                            </div>
                            <p className="text-xs text-gray-500 mt-2 text-center">
                                Our AI is extracting consumption data, charts, and billing information...
                            </p>
                        </div>
                    )}

                    {/* Error Message */}
                    {error && (
                        <div className="mt-6 p-4 bg-red-100 border border-red-200 rounded-lg" role="alert">
                            <div className="flex items-start gap-3">
                                <X className="text-red-600 w-5 h-5 flex-shrink-0 mt-0.5" aria-hidden="true" />
                                <div>
                                    <p className="text-red-800 font-medium">Upload Failed</p>
                                    <p className="text-red-600 text-sm mt-1">{error}</p>
                                    <button
                                        onClick={handleUpload}
                                        className="mt-2 text-sm text-red-700 underline hover:no-underline"
                                    >
                                        Try again
                                    </button>
                                </div>
                            </div>
                        </div>
                    )}

                    {/* Results */}
                    {results && (
                        <div className="mt-8 space-y-6">
                            {/* Success & Redirect Message */}
                            <div className="bg-gradient-to-r from-teal-50 to-cyan-50 rounded-xl p-7 border border-teal-300">
                                <div className="text-center">
                                    <div className="flex justify-center mb-4">
                                        <div className="w-16 h-16 bg-teal-100 rounded-full flex items-center justify-center">
                                            <CheckCircle size={32} className="text-teal-600" />
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
                                                <div className="animate-spin w-6 h-6 border-2 border-teal-500 border-t-transparent rounded-full" />
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
                                                    className="inline-flex justify-center gap-2 px-6 py-3 bg-teal-600 hover:bg-teal-700 text-white font-medium rounded-lg transition-colors items-center"
                                                >
                                                    <ChartNoAxesCombined size={18} /> View Dashboard
                                                </Link>
                                                <Link
                                                    href="/chat"
                                                    className="inline-flex justify-center gap-2 px-6 py-3 bg-white border border-gray-300 hover:border-teal-500 text-gray-600 font-medium rounded-lg transition-colors items-center"
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
        </main>
    );
}
