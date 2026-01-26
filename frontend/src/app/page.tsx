"use client";

import { useState, useCallback } from "react";
import { useDropzone } from "react-dropzone";

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

export default function Home() {
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<OCRResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

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
    <main className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900 p-8">
      <div className="max-w-4xl mx-auto">
        <h1 className="text-4xl font-bold text-white mb-2 text-center">
          VoltPulse OCR
        </h1>
        <p className="text-gray-400 text-center mb-8">
          Upload an image to extract text using PaddleOCR
        </p>

        {/* Dropzone */}
        <div
          {...getRootProps()}
          className={`border-2 border-dashed rounded-xl p-12 text-center cursor-pointer transition-all duration-200 ${
            isDragActive
              ? "border-blue-500 bg-blue-500/10"
              : "border-gray-600 hover:border-gray-500 bg-gray-800/50"
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
              <p className="text-gray-300">{file?.name}</p>
            </div>
          ) : (
            <div className="space-y-4">
              <div className="w-16 h-16 mx-auto text-gray-500">
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
              <div>
                <p className="text-xl text-gray-300">
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
              className="px-6 py-3 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-800 disabled:cursor-not-allowed text-white font-semibold rounded-lg transition-colors flex items-center gap-2"
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
                "Extract Text"
              )}
            </button>
            <button
              onClick={clearFile}
              className="px-6 py-3 bg-gray-700 hover:bg-gray-600 text-white font-semibold rounded-lg transition-colors"
            >
              Clear
            </button>
          </div>
        )}

        {/* Error Message */}
        {error && (
          <div className="mt-6 p-4 bg-red-900/50 border border-red-700 rounded-lg">
            <p className="text-red-300">{error}</p>
          </div>
        )}

        {/* Results */}
        {results && (
          <div className="mt-8 space-y-6">
            <div className="bg-gray-800/50 rounded-xl p-6 border border-gray-700">
              <h2 className="text-xl font-semibold text-white mb-4 flex items-center gap-2">
                <svg
                  className="w-6 h-6 text-green-500"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
                  />
                </svg>
                Extracted Text
              </h2>
              <div className="space-y-2">
                {results.extracted_texts.map((text, index) => (
                  <div
                    key={index}
                    className="p-3 bg-gray-900/50 rounded-lg text-gray-300 font-mono"
                  >
                    {text}
                  </div>
                ))}
              </div>
            </div>

            <div className="bg-gray-800/50 rounded-xl p-6 border border-gray-700">
              <h2 className="text-xl font-semibold text-white mb-4">
                Storage Status
              </h2>
              <div className="flex items-center gap-3">
                <span
                  className={`w-3 h-3 rounded-full ${
                    results.embedding_stored ? "bg-green-500" : "bg-yellow-500"
                  }`}
                />
                <span className="text-gray-300">
                  {results.embedding_stored
                    ? "Embedding stored in Supabase"
                    : "Embedding pending"}
                </span>
              </div>
              <p className="text-gray-500 text-sm mt-2">
                Source ID: {results.source_id}
              </p>
            </div>

            <div className="bg-gray-800/50 rounded-xl p-6 border border-gray-700">
              <h2 className="text-xl font-semibold text-white mb-4">
                Full OCR Response
              </h2>
              <pre className="text-sm text-gray-400 overflow-x-auto p-4 bg-gray-900 rounded-lg">
                {JSON.stringify(results.ocr_results, null, 2)}
              </pre>
            </div>
          </div>
        )}
      </div>
    </main>
  );
}
