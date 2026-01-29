"use client";

import { useState, useRef, useEffect } from "react";
import Image from "next/image";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { ThumbsUp, ThumbsDown, Copy, Share2, RotateCcw, Sparkles } from "lucide-react";

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
  feedback?: "positive" | "negative";
}

interface ChatbotProps {
  userId?: string;
  threadId?: string;
}

const quickActions = [
  "Show me energy-saving tips",
  "Explain my bill breakdown",
  "Find Climate Voucher retailers",
  "Compare to national average",
];

export default function Chatbot({ userId = "default_user", threadId = "default_thread" }: ChatbotProps) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [isOpen, setIsOpen] = useState(false);
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    if (isOpen && inputRef.current) {
      inputRef.current.focus();
    }
  }, [isOpen]);

  const sendMessage = async (messageText?: string) => {
    const text = messageText || input.trim();
    if (!text || isLoading) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      role: "user",
      content: text,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setIsLoading(true);

    try {
      const response = await fetch("/api/chat", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          message: userMessage.content,
          user_id: userId,
          thread_id: threadId,
        }),
      });

      if (!response.ok) {
        throw new Error("Failed to get response");
      }

      const data = await response.json();

      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: data.response || "Sorry, I couldn't process your request.",
        timestamp: new Date(),
      };

      setMessages((prev) => [...prev, assistantMessage]);
    } catch {
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: "Sorry, something went wrong. Please try again.",
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const handleFeedback = (messageId: string, feedback: "positive" | "negative") => {
    setMessages((prev) =>
      prev.map((msg) =>
        msg.id === messageId ? { ...msg, feedback } : msg
      )
    );
    // Could send feedback to backend here
  };

  const copyToClipboard = async (content: string, messageId: string) => {
    await navigator.clipboard.writeText(content);
    setCopiedId(messageId);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const clearChat = () => {
    setMessages([]);
  };

  return (
    <>
      {/* Chat Toggle Button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="fixed bottom-6 right-6 w-14 h-14 bg-gradient-to-br from-teal-500 to-teal-600 hover:from-teal-600 hover:to-teal-700 text-white rounded-full shadow-lg shadow-teal-500/25 flex items-center justify-center transition-all duration-200 z-50 no-print"
        aria-label={isOpen ? "Close chat assistant" : "Open chat assistant"}
        aria-expanded={isOpen}
      >
        {isOpen ? (
          <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        ) : (
          <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"
            />
          </svg>
        )}
      </button>

      {/* Chat Window */}
      {isOpen && (
        <div 
          className="fixed bottom-24 right-6 w-96 h-[520px] bg-white rounded-xl shadow-2xl flex flex-col overflow-hidden border border-slate-200 z-50 no-print"
          role="dialog"
          aria-label="Chat assistant"
        >
          {/* Header */}
          <div className="bg-gradient-to-r from-teal-600 to-teal-700 px-4 py-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <Image
                  src="/volt.png"
                  alt="VoltPulse Logo"
                  width={40}
                  height={40}
                  className="rounded-full"
                  unoptimized
                />
                <div>
                  <h3 className="text-white font-semibold">VoltPulse Assistant</h3>
                  <p className="text-teal-100 text-xs">AI-powered energy advisor</p>
                </div>
              </div>
              <button
                onClick={clearChat}
                className="text-white/70 hover:text-white p-1 rounded"
                aria-label="Clear chat history"
                title="Clear chat"
              >
                <RotateCcw className="w-4 h-4" />
              </button>
            </div>
          </div>

          {/* Messages */}
          <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-slate-50">
            {messages.length === 0 && (
              <div className="text-center py-6">
                <div className="w-16 h-16 bg-teal-100 rounded-full flex items-center justify-center mx-auto mb-4">
                  <Sparkles className="w-8 h-8 text-teal-600" />
                </div>
                <p className="text-slate-600 mb-4">How can I help you save energy today?</p>
                
                {/* Quick Actions */}
                <div className="space-y-2">
                  {quickActions.map((action) => (
                    <button
                      key={action}
                      onClick={() => sendMessage(action)}
                      className="w-full text-left px-3 py-2 text-sm bg-white border border-slate-200 rounded-lg hover:border-teal-400 hover:bg-teal-50 transition-colors text-slate-700"
                    >
                      {action}
                    </button>
                  ))}
                </div>
              </div>
            )}
            
            {messages.map((message) => (
              <div
                key={message.id}
                className={`flex ${message.role === "user" ? "justify-end" : "justify-start"}`}
              >
                <div className="max-w-[85%] space-y-1">
                  <div
                    className={`px-4 py-2 rounded-2xl ${
                      message.role === "user"
                        ? "bg-gradient-to-r from-teal-600 to-teal-500 text-white rounded-br-md"
                        : "bg-white text-slate-800 rounded-bl-md border border-slate-200 shadow-sm overflow-hidden"
                    }`}
                  >
                    {message.role === "assistant" ? (
                      <div className="prose prose-sm max-w-none text-sm
                        prose-p:my-1 prose-p:leading-relaxed
                        prose-ul:my-1 prose-ol:my-1
                        prose-li:my-0
                        prose-headings:mt-2 prose-headings:mb-1
                        prose-a:text-teal-600
                      ">
                        <ReactMarkdown
                          remarkPlugins={[remarkGfm]}
                          components={{
                            table: ({ children }) => (
                              <div className="overflow-x-auto -mx-2 px-2 my-2">
                                <table className="min-w-full text-xs border-collapse border border-slate-200 rounded overflow-hidden">
                                  {children}
                                </table>
                              </div>
                            ),
                            thead: ({ children }) => (
                              <thead className="bg-slate-50">{children}</thead>
                            ),
                            th: ({ children }) => (
                              <th className="px-2 py-1.5 text-left text-xs font-semibold text-slate-700 border-b border-slate-200 whitespace-nowrap">
                                {children}
                              </th>
                            ),
                            td: ({ children }) => (
                              <td className="px-2 py-1.5 text-slate-700 border-b border-slate-100 whitespace-nowrap">
                                {children}
                              </td>
                            ),
                          }}
                        >
                          {message.content}
                        </ReactMarkdown>
                      </div>
                    ) : (
                      <p className="whitespace-pre-wrap text-sm">{message.content}</p>
                    )}
                  </div>
                  
                  {/* Message Actions (for assistant messages) */}
                  {message.role === "assistant" && (
                    <div className="flex items-center gap-1 px-1">
                      <button
                        onClick={() => handleFeedback(message.id, "positive")}
                        className={`p-1 rounded hover:bg-slate-200 transition-colors ${
                          message.feedback === "positive" ? "text-teal-600" : "text-slate-400"
                        }`}
                        aria-label="Helpful response"
                        aria-pressed={message.feedback === "positive"}
                      >
                        <ThumbsUp className="w-3.5 h-3.5" />
                      </button>
                      <button
                        onClick={() => handleFeedback(message.id, "negative")}
                        className={`p-1 rounded hover:bg-slate-200 transition-colors ${
                          message.feedback === "negative" ? "text-red-600" : "text-slate-400"
                        }`}
                        aria-label="Not helpful response"
                        aria-pressed={message.feedback === "negative"}
                      >
                        <ThumbsDown className="w-3.5 h-3.5" />
                      </button>
                      <button
                        onClick={() => copyToClipboard(message.content, message.id)}
                        className="p-1 rounded hover:bg-slate-200 transition-colors text-slate-400"
                        aria-label="Copy response"
                      >
                        <Copy className="w-3.5 h-3.5" />
                        {copiedId === message.id && (
                          <span className="text-xs text-teal-600 ml-1">Copied!</span>
                        )}
                      </button>
                      <button
                        onClick={() => {
                          navigator.share?.({
                            title: "VoltPulse Insight",
                            text: message.content,
                          });
                        }}
                        className="p-1 rounded hover:bg-slate-200 transition-colors text-slate-400"
                        aria-label="Share response"
                      >
                        <Share2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  )}
                </div>
              </div>
            ))}
            
            {isLoading && (
              <div className="flex justify-start">
                <div className="bg-white text-slate-800 px-4 py-3 rounded-2xl rounded-bl-md border border-slate-200 shadow-sm">
                  <div className="flex gap-1.5" aria-label="Loading response">
                    <span className="w-2 h-2 bg-teal-400 rounded-full animate-bounce" style={{ animationDelay: "0ms" }} />
                    <span className="w-2 h-2 bg-teal-400 rounded-full animate-bounce" style={{ animationDelay: "150ms" }} />
                    <span className="w-2 h-2 bg-teal-400 rounded-full animate-bounce" style={{ animationDelay: "300ms" }} />
                  </div>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Quick Actions After Response */}
          {messages.length > 0 && messages[messages.length - 1]?.role === "assistant" && !isLoading && (
            <div className="px-4 py-2 border-t border-slate-100 bg-white">
              <div className="flex gap-2 overflow-x-auto pb-1">
                {["Tell me more", "How to apply?", "Other options"].map((action) => (
                  <button
                    key={action}
                    onClick={() => sendMessage(action)}
                    className="flex-shrink-0 px-3 py-1.5 text-xs bg-slate-100 hover:bg-teal-100 text-slate-700 rounded-full transition-colors"
                  >
                    {action}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Input */}
          <div className="p-4 border-t border-slate-200 bg-white">
            <div className="flex gap-2">
              <input
                ref={inputRef}
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Ask about energy savings..."
                disabled={isLoading}
                className="flex-1 bg-slate-100 text-slate-800 px-4 py-2.5 rounded-full focus:outline-none focus:ring-2 focus:ring-teal-500 disabled:opacity-50 placeholder-slate-500 text-sm"
                aria-label="Type your message"
              />
              <button
                onClick={() => sendMessage()}
                disabled={!input.trim() || isLoading}
                className="p-2.5 bg-gradient-to-r from-teal-600 to-teal-500 hover:from-teal-700 hover:to-teal-600 disabled:from-slate-300 disabled:to-slate-300 disabled:cursor-not-allowed text-white rounded-full transition-all"
                aria-label="Send message"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8"
                  />
                </svg>
              </button>
            </div>
            <p className="text-xs text-slate-400 text-center mt-2">
              Powered by VoltPulse AI • <span className="text-teal-500">●</span> Memory enabled
            </p>
          </div>
        </div>
      )}
    </>
  );
}
