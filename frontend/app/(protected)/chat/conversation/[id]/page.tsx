"use client";
import React, { useState, useEffect, useRef } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { ArrowLeft, Send, Loader2, Database, FileUp, FileText, CheckCircle, XCircle } from "lucide-react";
import ReactMarkdown from "react-markdown";

export default function ConversationPage() {
  const params = useParams();
  const router = useRouter();
  const id = params?.id as string;
  const [conversation, setConversation] = useState<any>(null);
  const [messages, setMessages] = useState<any[]>([]);
  const [input, setInput] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const [isQuerying, setIsQuerying] = useState(false);
  const [statusMessage, setStatusMessage] = useState("Reading document context...");
  const [isUploading, setIsUploading] = useState(false);
  const [attachedFiles, setAttachedFiles] = useState<any[]>([]);
  const fileInputRef = useRef<HTMLInputElement>(null);
  
  const endRef = useRef<HTMLDivElement>(null);
  const hasTriggeredRef = useRef<string | null>(null);

  useEffect(() => {
    if (id) {
        hasTriggeredRef.current = null; // Reset for new ID
        fetchConversation();
    }
  }, [id]);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isStreaming, isQuerying]);

  const fetchConversation = async () => {
    try {
      const res = await fetch(`/api/chat/conversations/${id}`, {
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
        setConversation(data);
        const fetchedMessages = data.messages || [];
        setMessages(fetchedMessages);
        setAttachedFiles(data.files || []);

        // Auto-trigger analysis if this is a fresh conversation with only the initial user message
        if (fetchedMessages.length === 1 && fetchedMessages[0].role === "user" && !isStreaming && hasTriggeredRef.current !== id) {
            hasTriggeredRef.current = id as string;
            triggerAiResponse(fetchedMessages[0].content);
        }
      }
    } catch (e) {
      console.error(e);
    }
  };

  const uploadFile = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setIsUploading(true);
    const formData = new FormData();
    formData.append("file", file);

    try {
      const res = await fetch(`/api/chat/conversations/${id}/upload`, {
        method: "POST",
        headers: {
          "Authorization": `Bearer ${localStorage.getItem("fincore_token")}`
        },
        body: formData
      });

      if (res.ok) {
        const data = await res.json();
        setAttachedFiles(prev => [...prev, data]);
      } else {
        const err = await res.json();
        alert(err.error || "Upload failed");
      }
    } catch (e) {
      console.error(e);
      alert("Network error during upload");
    } finally {
      setIsUploading(true);
      if (fileInputRef.current) fileInputRef.current.value = "";
      setIsUploading(false);
    }
  };

  const triggerAiResponse = async (userContent: string) => {
    if (isStreaming) return;
    setIsStreaming(true);
    setIsQuerying(attachedFiles.length > 0 || true);
    setStatusMessage("Preparing analysis...");

    let assistantMsgContent = "";
    setMessages((prev) => [...prev, { id: "temp", role: "assistant", content: "" }]);

    try {
      const res = await fetch(`/api/chat/conversations/${id}/messages`, {
        method: "POST",
        headers: { 
            "Content-Type": "application/json",
            "Authorization": `Bearer ${localStorage.getItem("fincore_token")}`
        },
        body: JSON.stringify({ content: userContent }),
      });
      
      if (!res.body) throw new Error("No readable stream");
      const reader = res.body.getReader();
      const decoder = new TextDecoder();

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value);
        const lines = chunk.split("\n");
        for (const line of lines) {
          if (line.startsWith("data: ")) {
            const dataStr = line.slice(6);
            if (dataStr === "[DONE]") {
                setIsStreaming(false);
                setIsQuerying(false);
                break;
            }
            try {
              const data = JSON.parse(dataStr);
              if (data.type === "content_block_delta") {
                setIsQuerying(false);
                if (data.delta?.text) {
                  assistantMsgContent += data.delta.text;
                  setMessages((prev) => {
                    const newArr = [...prev];
                    newArr[newArr.length - 1] = { ...newArr[newArr.length - 1], content: assistantMsgContent };
                    return newArr;
                  });
                }
              } else if (data.type === "status") {
                setIsQuerying(true);
                setStatusMessage(data.content);
              }
            } catch (e) {}
          }
        }
      }
    } catch (e) {
      console.error(e);
    } finally {
      setIsStreaming(false);
      setIsQuerying(false);
    }
  };

  const sendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isStreaming) return;
    
    const userMsg = { id: Date.now().toString(), role: "user", content: input };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    triggerAiResponse(userMsg.content);
  };

  return (
    <div className="flex flex-col h-[calc(100vh-64px)] max-w-4xl mx-auto w-full border-x border-gray-100 bg-white">
      {/* Header */}
      <div className="p-4 border-b flex items-center bg-gray-50">
        <Link href="/chat" className="mr-4 text-gray-500 hover:text-black">
          <ArrowLeft className="w-5 h-5" />
        </Link>
        <h2 className="font-semibold">{conversation?.title || "Loading..."}</h2>
        <div className="ml-auto flex items-center gap-2">
            {attachedFiles.length > 0 && (
                <div className="flex -space-x-2">
                    {attachedFiles.map((f, i) => (
                        <div key={i} title={f.filename} className="w-8 h-8 rounded-full bg-ai-violet text-white flex items-center justify-center border-2 border-white text-[10px] font-bold">
                            {f.filename.slice(0, 1).toUpperCase()}
                        </div>
                    ))}
                </div>
            )}
            <button 
                onClick={() => fileInputRef.current?.click()}
                disabled={isUploading || isStreaming}
                className="p-2 rounded-lg hover:bg-gray-200 transition-colors text-gray-600 flex items-center gap-2"
            >
                {isUploading ? <Loader2 className="w-4 h-4 animate-spin" /> : <FileUp className="w-4 h-4" />}
                <span className="text-xs font-medium">Add File</span>
            </button>
            <input 
                type="file" 
                ref={fileInputRef} 
                onChange={uploadFile} 
                accept=".pdf,.xlsx,.xls" 
                className="hidden" 
            />
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-6">
        {messages.map((m, i) => (
          <div key={i} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div 
              className={`max-w-[80%] p-4 rounded-2xl ${
                m.role === 'user' 
                  ? 'bg-black text-white rounded-br-none' 
                  : 'bg-gray-100 text-gray-900 rounded-bl-none'
              }`}
            >
              {m.role === 'assistant' ? (
                <div className="prose prose-sm max-w-none">
                  <ReactMarkdown>{m.content}</ReactMarkdown>
                </div>
              ) : (
                <p className="whitespace-pre-wrap">{m.content}</p>
              )}
            </div>
          </div>
        ))}
        {isQuerying && (
          <div className="flex justify-start">
            <div className="max-w-[80%] p-3 rounded-2xl bg-ai-violet/5 text-ai-violet flex items-center text-sm border border-ai-violet/10">
              <Loader2 className="w-4 h-4 mr-2 animate-spin" />
              {statusMessage}
            </div>
          </div>
        )}
        <div ref={endRef} />
      </div>

      {/* Input */}
      <div className="p-4 border-t bg-white">
        <form onSubmit={sendMessage} className="relative">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                sendMessage(e);
              }
            }}
            placeholder={attachedFiles.length > 0 ? "Ask about the uploaded documents..." : "Upload a PDF or Excel to start asking questions..."}
            className="w-full border border-gray-300 rounded-xl p-3 pr-12 focus:outline-none focus:ring-2 focus:ring-black resize-none min-h-[56px] max-h-32"
            rows={1}
            disabled={isStreaming}
          />
          <button 
            type="submit"
            disabled={!input.trim() || isStreaming}
            className="absolute bottom-3 right-3 p-1.5 rounded-lg bg-black text-white disabled:opacity-50"
          >
            {isStreaming && !isQuerying ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
          </button>
        </form>
      </div>
    </div>
  );
}
