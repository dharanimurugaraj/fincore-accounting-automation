"use client";
import React, { useState, useEffect } from "react";
import Link from "next/link";
import { useParams, useRouter, usePathname } from "next/navigation";
import { 
  Plus, 
  MessageSquare, 
  LayoutDashboard, 
  History, 
  Search,
  MessageCircle
} from "lucide-react";

export default function ChatSidebar() {
  const router = useRouter();
  const pathname = usePathname();
  const params = useParams();
  const currentId = params?.id as string;
  const [conversations, setConversations] = useState<any[]>([]);
  const [searchTerm, setSearchTerm] = useState("");

  useEffect(() => {
    fetchConversations();
    // Listen for custom events to refresh history
    window.addEventListener('refreshChatHistory', fetchConversations);
    return () => window.removeEventListener('refreshChatHistory', fetchConversations);
  }, []);

  const fetchConversations = async () => {
    try {
      const res = await fetch("/api/chat/conversations", {
        headers: {
            "Authorization": `Bearer ${localStorage.getItem("fincore_token")}`
        }
      });
      if (res.ok) {
        const data = await res.json();
        setConversations(data);
      }
    } catch (e) {
      console.error("Failed to fetch conversations", e);
    }
  };

  const filteredConversations = conversations.filter(c => 
    c.title?.toLowerCase().includes(searchTerm.toLowerCase()) ||
    c.lastMessage?.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <aside className="w-80 border-r border-neutral-border bg-neutral-card flex flex-col h-full bg-white">
      {/* Action Buttons */}
      <div className="p-4 space-y-2">
        <Link 
          href="/dashboard"
          className="flex items-center gap-3 w-full px-4 py-3 bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-xl transition-all text-sm font-semibold"
        >
          <LayoutDashboard className="w-4 h-4" />
          Back to Dashboard
        </Link>
        
        <Link 
          href="/chat"
          className="flex items-center gap-3 w-full px-4 py-3 bg-ai-violet text-white hover:bg-ai-violet/90 rounded-xl transition-all shadow-sm text-sm font-semibold"
        >
          <Plus className="w-4 h-4" />
          New Document Chat
        </Link>
      </div>

      <div className="px-4 mb-4">
        <div className="relative group">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-gray-400 group-focus-within:text-ai-violet transition-colors" />
          <input 
            type="text"
            placeholder="Search history..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full bg-gray-50 border border-neutral-border text-xs rounded-lg pl-9 pr-4 py-2 outline-none focus:border-ai-violet transition-all"
          />
        </div>
      </div>

      {/* History List */}
      <div className="flex-1 overflow-y-auto px-2 pb-4 space-y-1 scrollbar-hide">
        <div className="px-3 mb-2 flex items-center justify-between">
          <span className="text-[10px] uppercase tracking-widest text-gray-400 font-bold flex items-center gap-2">
            <History className="w-3 h-3" />
            Recent History
          </span>
        </div>

        {filteredConversations.length === 0 ? (
          <div className="p-8 text-center">
            <MessageSquare className="w-8 h-8 text-gray-200 mx-auto mb-2" />
            <p className="text-xs text-gray-400">No conversations found</p>
          </div>
        ) : (
          filteredConversations.map((c) => {
            const isActive = currentId === c.id;
            return (
              <Link
                key={c.id}
                href={`/chat/conversation/${c.id}`}
                className={`group flex flex-col p-3 rounded-xl transition-all ${
                  isActive 
                    ? "bg-ai-violet/10 border-ai-violet/20" 
                    : "hover:bg-gray-50 border-transparent"
                } border`}
              >
                <div className="flex items-start justify-between gap-2">
                  <span className={`text-[13px] font-semibold truncate ${isActive ? "text-ai-violet" : "text-gray-700"}`}>
                    {c.title || "New Thread"}
                  </span>
                  <span className="text-[9px] text-gray-400 whitespace-nowrap mt-1">
                    {new Date(c.createdAt).toLocaleDateString([], { month: 'short', day: 'numeric' })}
                  </span>
                </div>
                <p className="text-[11px] text-gray-400 truncate mt-0.5">
                  {c.lastMessage || "Click to open..."}
                </p>
              </Link>
            );
          })
        )}
      </div>
    </aside>
  );
}
