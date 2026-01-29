"use client";

import { useState, useRef, useEffect, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import Image from "next/image";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import Link from "next/link";
import { ThumbsUp, ThumbsDown, Copy, Share2, RotateCcw, Brain, Sparkles } from "lucide-react";

import { Navbar } from "../components/navbar";
import Breadcrumb from "../components/Breadcrumb";

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
  feedback?: "positive" | "negative";
}

interface QuickAction {
  label: string;
  query: string;
  icon: React.ReactNode;
}

const quickActions: QuickAction[] = [
  {
    label: "Analyze Bill",
    query: "Analyze my latest electricity bill",
    icon: <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" /></svg>,
  },
  {
    label: "Save Energy",
    query: "How can I reduce my electricity usage?",
    icon: <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" /></svg>,
  },
  {
    label: "Compare Usage",
    query: "Compare my usage to the national average",
    icon: <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" /></svg>,
  },
  {
    label: "Climate Voucher",
    query: "Help me find eligible retailers for Climate Voucher",
    icon: <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>,
  },
];

const breadcrumbItems = [
  { label: "Chat", href: "/chat" },
];

// Generate anonymous session ID (no user tracking)
function generateAnonymousSessionId(): string {
  return `anon_${Date.now()}_${Math.random().toString(36).substring(2, 11)}`;
}

function ChatContent() {
  const searchParams = useSearchParams();
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [hasProcessedQuery, setHasProcessedQuery] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Anonymous session - no user tracking
  const [sessionId] = useState(() => generateAnonymousSessionId());

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 200)}px`;
    }
  }, [input]);

  // Function to send a message directly (for pre-filled queries)
  const sendMessageDirect = async (messageContent: string) => {
    if (!messageContent.trim() || isLoading) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      role: "user",
      content: messageContent.trim(),
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setIsLoading(true);

    try {
      const response = await fetch("/api/chat", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          message: userMessage.content,
          user_id: "anonymous",
          thread_id: sessionId,
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
    } catch (error) {
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

  // Handle pre-filled query from URL parameters (e.g., from ROI Calculator)
  useEffect(() => {
    const query = searchParams.get("query");
    if (query && !hasProcessedQuery && messages.length === 0) {
      setHasProcessedQuery(true);
      // Small delay to ensure the component is fully mounted
      setTimeout(() => {
        sendMessageDirect(decodeURIComponent(query));
      }, 100);
    }
  }, [searchParams, hasProcessedQuery, messages.length]);

  const sendMessage = async () => {
    if (!input.trim() || isLoading) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      role: "user",
      content: input.trim(),
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
          user_id: "anonymous",
          thread_id: sessionId,
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
    } catch (error) {
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

  const clearChat = () => {
    setMessages([]);
  };

  // Copy message to clipboard
  const copyMessage = async (id: string, content: string) => {
    try {
      await navigator.clipboard.writeText(content);
      setCopiedId(id);
      setTimeout(() => setCopiedId(null), 2000);
    } catch (err) {
      console.error("Failed to copy:", err);
    }
  };

  // Share message
  const shareMessage = async (content: string) => {
    if (navigator.share) {
      try {
        await navigator.share({
          title: "VoltPulse Energy Insight",
          text: content.substring(0, 280),
          url: window.location.href,
        });
      } catch (err) {
        console.log("Share cancelled");
      }
    } else {
      await navigator.clipboard.writeText(content);
      alert("Response copied to clipboard!");
    }
  };

  // Provide feedback on message
  const provideFeedback = (id: string, feedback: "positive" | "negative") => {
    setMessages(prev => prev.map(msg => 
      msg.id === id ? { ...msg, feedback } : msg
    ));
    // TODO: Send feedback to backend for improvement
  };

  // Regenerate last response
  const regenerateResponse = async () => {
    const lastUserMessage = [...messages].reverse().find(m => m.role === "user");
    if (!lastUserMessage) return;
    
    // Remove last assistant message
    setMessages(prev => {
      const newMessages = [...prev];
      if (newMessages[newMessages.length - 1]?.role === "assistant") {
        newMessages.pop();
      }
      return newMessages;
    });
    
    setInput(lastUserMessage.content);
    // Re-trigger send after state updates
    setTimeout(() => {
      setInput("");
      sendMessage();
    }, 0);
  };

  return (
    <div className="min-h-screen bg-white flex flex-col">
      <Navbar />

      {/* Header with Breadcrumb */}
      <header className="bg-white border-b border-gray-200 py-4 px-6">
        <div className="max-w-4xl mx-auto">
          <Breadcrumb items={breadcrumbItems} />
          <div className="flex items-center justify-between mt-3">
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
                <h1 className="text-gray-900 font-semibold text-lg">VoltPulse Assistant</h1>
                <div className="flex items-center gap-2 text-gray-500 text-sm">
                  <Brain className="w-3 h-3" />
                  <span>Memory enabled</span>
                  <span className="w-1 h-1 bg-gray-300 rounded-full" />
                  <span className="text-teal-600 flex items-center gap-1">
                    <span className="w-2 h-2 bg-teal-500 rounded-full animate-pulse" />
                    Online
                  </span>
                </div>
              </div>
            </div>
            <button
              onClick={clearChat}
              className="text-gray-500 hover:text-gray-700 transition-colors px-3 py-2 rounded-lg hover:bg-gray-100 flex items-center gap-2"
              title="Clear chat"
              aria-label="Clear chat history"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
              </svg>
              <span className="hidden sm:inline text-sm">Clear</span>
            </button>
          </div>
        </div>
      </header>

      {/* Messages Area */}
      <main className="flex-1 overflow-y-auto bg-gray-50">
        <div className="max-w-4xl mx-auto py-6 px-4">
          {messages.length === 0 ? (
            <div className="text-center mt-16">
              <div className="w-20 h-20 bg-teal-100 rounded-full flex items-center justify-center mx-auto mb-6">
                <Sparkles className="w-10 h-10 text-teal-600" />
              </div>
              <h2 className="text-xl font-semibold text-gray-900 mb-2">Welcome to VoltPulse Assistant</h2>
              <p className="text-gray-600 max-w-md mx-auto mb-8">
                I can help you understand your electricity bills, analyze your consumption patterns, and provide tips to reduce your energy usage.
              </p>
              
              {/* Quick Actions */}
              <div className="flex flex-wrap justify-center gap-2 mb-8">
                {quickActions.map((action) => (
                  <button
                    key={action.label}
                    onClick={() => {
                      setInput(action.query);
                      textareaRef.current?.focus();
                    }}
                    className="flex items-center gap-2 px-4 py-2 bg-white border border-gray-200 hover:border-teal-400 hover:shadow-sm rounded-full text-sm text-gray-700 transition-all"
                  >
                    {action.icon}
                    {action.label}
                  </button>
                ))}
              </div>
              
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 max-w-2xl mx-auto">
                {[
                  "Analyze my latest electricity bill",
                  "How can I reduce my electricity usage?",
                  "Compare my usage to the national average",
                  "What appliances use the most power?",
                ].map((suggestion) => (
                  <button
                    key={suggestion}
                    onClick={() => {
                      setInput(suggestion);
                      textareaRef.current?.focus();
                    }}
                    className="text-left p-4 bg-white border border-gray-200 hover:border-teal-400 hover:shadow-sm rounded-xl text-sm text-gray-700 transition-all"
                  >
                    {suggestion}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <div className="space-y-6">
              {messages.map((message) => (
                <div key={message.id} className={`flex ${message.role === "user" ? "justify-end" : "justify-start"} items-start group`}>
                  {message.role === "assistant" && (
                    <div className="w-8 h-8 bg-teal-600 rounded-full flex items-center justify-center mr-3 flex-shrink-0 mt-1">
                      <svg className="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                      </svg>
                    </div>
                  )}
                  <div className="flex flex-col max-w-3xl">
                    <div
                      className={`${message.role === "user"
                        ? "bg-teal-600 text-white px-4 py-3 rounded-2xl rounded-br-md"
                        : "bg-white text-gray-900 px-5 py-4 rounded-2xl rounded-bl-md border border-gray-200 shadow-sm"
                        }`}
                    >
                      {message.role === "assistant" ? (
                        <div className="prose prose-sm max-w-none overflow-hidden
                            prose-headings:text-gray-900 prose-headings:font-semibold prose-headings:mt-4 prose-headings:mb-2
                          prose-h2:text-lg prose-h2:border-b prose-h2:border-gray-200 prose-h2:pb-2
                          prose-h3:text-base
                          prose-p:text-gray-700 prose-p:my-2 prose-p:leading-relaxed
                          prose-strong:text-gray-900 prose-strong:font-semibold
                          prose-ul:my-2 prose-ul:space-y-1
                          prose-ol:my-2 prose-ol:space-y-1
                          prose-li:text-gray-700 prose-li:my-0
                          prose-blockquote:border-l-4 prose-blockquote:border-teal-500 prose-blockquote:bg-teal-50 prose-blockquote:pl-4 prose-blockquote:py-2 prose-blockquote:my-3 prose-blockquote:italic prose-blockquote:text-gray-700
                          prose-code:bg-gray-100 prose-code:text-teal-700 prose-code:px-1.5 prose-code:py-0.5 prose-code:rounded prose-code:text-sm prose-code:before:content-none prose-code:after:content-none
                          prose-pre:bg-slate-100 prose-pre:text-slate-800 prose-pre:p-4 prose-pre:rounded-lg prose-pre:overflow-x-auto prose-pre:border prose-pre:border-slate-200
                          prose-hr:border-gray-200 prose-hr:my-4
                          prose-a:text-teal-600 prose-a:no-underline hover:prose-a:underline
                        ">
                          <ReactMarkdown 
                            remarkPlugins={[remarkGfm]}
                            components={{
                              table: ({ children }) => (
                                <div className="overflow-x-auto -mx-2 px-2 my-4">
                                  <table className="min-w-full text-sm border-collapse border border-gray-200 rounded-lg overflow-hidden">
                                    {children}
                                  </table>
                                </div>
                              ),
                              thead: ({ children }) => (
                                <thead className="bg-gray-50">{children}</thead>
                              ),
                              th: ({ children }) => (
                                <th className="px-3 py-2 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider border-b border-gray-200 whitespace-nowrap">
                                  {children}
                                </th>
                              ),
                              td: ({ children }) => (
                                <td className="px-3 py-2 text-gray-700 border-b border-gray-100 whitespace-nowrap">
                                  {children}
                                </td>
                              ),
                            }}
                          >
                            {message.content}
                          </ReactMarkdown>
                        </div>
                      ) : (
                        <p className="whitespace-pre-wrap">{message.content}</p>
                      )}
                    </div>
                    
                    {/* Message Actions for assistant messages */}
                    {message.role === "assistant" && (
                      <div className="flex items-center gap-1 mt-2 opacity-0 group-hover:opacity-100 transition-opacity">
                        <button
                          onClick={() => copyMessage(message.id, message.content)}
                          className={`p-1.5 rounded-lg transition-colors ${copiedId === message.id ? 'bg-teal-100 text-teal-600' : 'hover:bg-gray-100 text-gray-400 hover:text-gray-600'}`}
                          aria-label="Copy response"
                          title="Copy"
                        >
                          <Copy className="w-4 h-4" />
                        </button>
                        <button
                          onClick={() => shareMessage(message.content)}
                          className="p-1.5 hover:bg-gray-100 rounded-lg text-gray-400 hover:text-gray-600 transition-colors"
                          aria-label="Share response"
                          title="Share"
                        >
                          <Share2 className="w-4 h-4" />
                        </button>
                        <button
                          onClick={() => provideFeedback(message.id, "positive")}
                          className={`p-1.5 rounded-lg transition-colors ${message.feedback === 'positive' ? 'bg-teal-100 text-teal-600' : 'hover:bg-gray-100 text-gray-400 hover:text-gray-600'}`}
                          aria-label="Good response"
                          title="Good response"
                        >
                          <ThumbsUp className="w-4 h-4" />
                        </button>
                        <button
                          onClick={() => provideFeedback(message.id, "negative")}
                          className={`p-1.5 rounded-lg transition-colors ${message.feedback === 'negative' ? 'bg-red-100 text-red-600' : 'hover:bg-gray-100 text-gray-400 hover:text-gray-600'}`}
                          aria-label="Bad response"
                          title="Bad response"
                        >
                          <ThumbsDown className="w-4 h-4" />
                        </button>
                      </div>
                    )}
                  </div>
                  
                  {message.role === "user" && (
                    <div className="w-8 h-8 bg-gray-300 rounded-full flex items-center justify-center ml-3 flex-shrink-0 mt-1">
                      <svg className="w-4 h-4 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                      </svg>
                    </div>
                  )}
                </div>
              ))}
              {isLoading && (
                <div className="flex justify-start">
                  <div className="w-8 h-8 bg-teal-600 rounded-full flex items-center justify-center mr-3 flex-shrink-0">
                    <svg className="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                    </svg>
                  </div>
                  <div className="bg-white text-gray-900 px-5 py-4 rounded-2xl rounded-bl-md border border-gray-200 shadow-sm">
                    <div className="flex gap-1.5">
                      <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: "0ms" }} />
                      <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: "150ms" }} />
                      <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: "300ms" }} />
                    </div>
                  </div>
                </div>
              )}
              
              {/* Regenerate button after conversation */}
              {messages.length > 0 && !isLoading && messages[messages.length - 1]?.role === "assistant" && (
                <div className="flex justify-center">
                  <button
                    onClick={regenerateResponse}
                    className="flex items-center gap-2 px-4 py-2 text-sm text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-lg transition-colors"
                  >
                    <RotateCcw className="w-4 h-4" />
                    Regenerate response
                  </button>
                </div>
              )}
              
              <div ref={messagesEndRef} />
            </div>
          )}
        </div>
      </main>

      {/* Input Area */}
      <footer className="bg-white border-t border-gray-200 p-4">
        <div className="max-w-4xl mx-auto">
          <div className="flex gap-3 items-end">
            <div className="flex-1 bg-gray-50 border border-gray-200 rounded-xl px-4 py-3 focus-within:border-teal-400 focus-within:ring-1 focus-within:ring-teal-400 transition-all">
              <textarea
                ref={textareaRef}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Ask about your electricity usage..."
                disabled={isLoading}
                rows={1}
                className="w-full bg-transparent resize-none focus:outline-none disabled:opacity-50 placeholder-gray-400 text-gray-900 align-middle"
                style={{ maxHeight: "200px" }}
              />
            </div>
            <button
              onClick={sendMessage}
              disabled={!input.trim() || isLoading}
              className="p-4 bg-teal-600 hover:bg-teal-700 disabled:bg-gray-300 disabled:cursor-not-allowed text-white rounded-xl transition-colors flex-shrink-0"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
              </svg>
            </button>
          </div>
          <p className="text-gray-400 text-xs mt-2 text-center">
            Press Enter to send, Shift+Enter for new line
          </p>
        </div>
      </footer>
    </div>
  );
}

// Wrap with Suspense for useSearchParams
export default function ChatPage() {
  return (
    <Suspense fallback={
      <div className="flex flex-col h-screen bg-white">
        <Navbar />
        <div className="flex-1 flex items-center justify-center">
          <div className="animate-spin w-8 h-8 border-2 border-teal-500 border-t-transparent rounded-full" />
        </div>
      </div>
    }>
      <ChatContent />
    </Suspense>
  );
}
