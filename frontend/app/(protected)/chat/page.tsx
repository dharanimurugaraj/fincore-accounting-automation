"use client";
import React, { useState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { 
    MessageSquare, 
    Plus, 
    ArrowRight, 
    Clock, 
    Sparkles, 
    Loader2, 
    FileText, 
    ShieldCheck, 
    FileUp, 
    XCircle 
} from "lucide-react";

export default function ChatLandingPage() {
  const router = useRouter();
  const [firstMessage, setFirstMessage] = useState("");
  const [loading, setLoading] = useState(false);
  const [conversations, setConversations] = useState<any[]>([]);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    fetchConversations();
  }, []);

  const fetchConversations = async () => {
    try {
      const res = await fetch("/api/chat/conversations", {
        headers: {
            "Authorization": `Bearer ${localStorage.getItem("fincore_token")}`
        }
      });
      if (res.status === 403) {
         router.push("/dashboard");
         return;
      }
      if (res.ok) {
        const data = await res.json();
        setConversations(data);
      }
    } catch (e) {
      console.error("Failed to fetch conversations", e);
    }
  };

  const startNewChat = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!firstMessage.trim()) return;
    
    setLoading(true);
    try {
      // 1. Create Conversation
      const res = await fetch("/api/chat/conversations", {
        method: "POST",
        headers: { 
          "Content-Type": "application/json",
          "Authorization": `Bearer ${localStorage.getItem("fincore_token")}`
        },
        body: JSON.stringify({ firstMessage })
      });
      
      if (!res.ok) throw new Error("Failed to create conversation");
      const data = await res.json();
      const convId = data.conversationId;

      // 2. Upload File if selected
      if (selectedFile) {
        const formData = new FormData();
        formData.append("file", selectedFile);
        await fetch(`/api/chat/conversations/${convId}/upload`, {
          method: "POST",
          headers: {
            "Authorization": `Bearer ${localStorage.getItem("fincore_token")}`
          },
          body: formData
        });
      }

      // 3. Dispatch Refresh Event for Sidebar & Redirect
      window.dispatchEvent(new Event('refreshChatHistory'));
      router.push(`/chat/conversation/${convId}`);
    } catch (e) {
      console.error(e);
      setLoading(false);
    }
  };

  return (
    <div className="h-full flex flex-col items-center justify-center p-8 text-center max-w-2xl mx-auto">
      <div className="w-16 h-16 bg-ai-violet/10 flex items-center justify-center rounded-2xl mb-6">
        <Sparkles className="w-8 h-8 text-ai-violet" />
      </div>
      
      <div className="flex flex-col items-center gap-2 mb-4">
        <h1 className="text-4xl font-bold text-gray-900 tracking-tight">
          Document Intelligence AI
        </h1>
        <div className="flex items-center gap-1.5 px-3 py-1 bg-amber-50/50 border border-amber-100 rounded-full">
            <div className="w-1.5 h-1.5 rounded-full bg-amber-400 animate-pulse" />
            <span className="text-[10px] font-bold text-amber-600 uppercase tracking-widest">Dev in progress - Not fully implemented</span>
        </div>
      </div>
      <p className="text-gray-500 mb-12 text-lg">
        Advanced PDF & Excel extraction. Upload your bank statements or financial reports for instant analysis, audit validation, and summary.
      </p>

      <div className="w-full space-y-4">
        <form onSubmit={startNewChat} className="relative shadow-2xl shadow-ai-violet/10 rounded-3xl overflow-hidden border border-gray-200 bg-white group focus-within:border-ai-violet transition-all">
          <textarea 
            className="w-full p-6 pr-20 resize-none h-32 text-lg focus:outline-none bg-transparent"
            placeholder="e.g. Compare the CC interest of our various bank accounts for last 6 months..."
            value={firstMessage}
            onChange={(e) => setFirstMessage(e.target.value)}
            disabled={loading}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                startNewChat(e);
              }
            }}
          />
          <button 
            type="submit"
            disabled={loading || !firstMessage.trim()}
            className="absolute bottom-6 right-6 bg-ai-violet text-white h-12 w-12 flex items-center justify-center rounded-2xl disabled:opacity-50 hover:scale-105 active:scale-95 transition-all shadow-lg z-10"
          >
            {loading ? <Loader2 className="w-6 h-6 animate-spin" /> : <ArrowRight className="w-6 h-6" />}
          </button>

          {/* Inline Upload Toggle */}
          <div className="absolute bottom-6 left-6 flex items-center gap-3">
              <button
                type="button"
                onClick={() => fileInputRef.current?.click()}
                className={`flex items-center gap-2 px-3 py-1.5 rounded-xl border text-[11px] font-bold transition-all ${
                    selectedFile 
                    ? "bg-ai-violet/10 border-ai-violet/30 text-ai-violet" 
                    : "bg-gray-50 border-gray-200 text-gray-500 hover:bg-gray-100"
                }`}
              >
                  <FileUp className="w-3.5 h-3.5" />
                  {selectedFile ? selectedFile.name : "Attach Document (PDF/XLS)"}
              </button>
              {selectedFile && (
                  <button 
                    type="button"
                    onClick={() => setSelectedFile(null)}
                    className="p-1.5 hover:bg-red-50 text-red-500 rounded-lg transition-colors"
                  >
                      <XCircle className="w-3.5 h-3.5" />
                  </button>
              )}
          </div>
          <input 
            type="file" 
            ref={fileInputRef} 
            onChange={(e) => setSelectedFile(e.target.files?.[0] || null)}
            className="hidden"
            accept=".pdf,.xlsx,.xls"
          />
        </form>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pt-6">
          {[
            "Summarize the banking report I'm about to upload",
            "What was our total principal payment this month?",
            "Calculate the average CC utilization for Axis Bank",
            "Show me all forex transactions exceeding $10,000"
          ].map(prompt => (
            <button 
              key={prompt} 
              onClick={() => setFirstMessage(prompt)}
              className="px-4 py-3 bg-gray-50 border border-gray-100 rounded-2xl text-left text-gray-600 hover:border-ai-violet/30 hover:bg-ai-violet/[0.02] transition-all text-xs font-medium"
            >
              {prompt}
            </button>
          ))}
        </div>
      </div>

      <div className="mt-16 flex items-center gap-6 text-gray-400">
        <div className="flex items-center gap-2">
           <FileText className="w-4 h-4" />
           <span className="text-[11px] font-bold uppercase tracking-widest">PDF & Excel Parser</span>
        </div>
        <div className="w-1.5 h-1.5 rounded-full bg-gray-200" />
        <div className="flex items-center gap-2">
           <ShieldCheck className="w-4 h-4 text-status-success" />
           <span className="text-[11px] font-bold uppercase tracking-widest">Audit Logs Active</span>
        </div>
      </div>
    </div>
  );
}
