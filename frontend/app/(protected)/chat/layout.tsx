"use client";
import React from "react";
import ChatSidebar from "./ChatSidebar";

export default function ChatLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex h-[calc(100vh-64px)] overflow-hidden bg-neutral-app">
      <ChatSidebar />
      <main className="flex-1 overflow-hidden relative bg-white">
        {children}
      </main>
    </div>
  );
}
