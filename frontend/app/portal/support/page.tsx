"use client";

import { useState, useRef, useEffect } from "react";
import { useAuth } from "@clerk/nextjs";
import { Send, CheckCircle, Bot, User, Loader2 } from "lucide-react";

type Message = { role: "user" | "ai"; content: string };

export default function SupportPage() {
  const { getToken } = useAuth();
  
  // State Management
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [isLocked, setIsLocked] = useState(false); // Triggers when AI finishes triage
  
  // We generate a unique thread ID once when the component mounts
  const threadId = useRef(`ticket_${Math.random().toString(36).substring(7)}`);
  const scrollRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when messages update
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  const sendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading || isLocked) return;

    const userMessage = input;
    setInput("");
    setMessages((prev) => [...prev, { role: "user", content: userMessage }]);
    setIsLoading(true);

    try {
      const token = await getToken();
      
      const response = await fetch("http://localhost:8000/ai/stream", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`, // <-- The Bouncer Key
        },
        body: JSON.stringify({
          thread_id: threadId.current,
          message: userMessage,
        }),
      });

      if (!response.ok) {
        if (response.status === 409) {
           alert("Concurrency Lock: You already have a ticket open in another tab!");
        }
        throw new Error("Backend connection failed");
      }

      // Prepare to read the streaming response
      const reader = response.body?.getReader();
      const decoder = new TextDecoder();
      let aiResponse = "";

      // Add a blank AI message to the screen that we will update chunk-by-chunk
      setMessages((prev) => [...prev, { role: "ai", content: "" }]);

      if (reader) {
        while (true) {
          const { value, done } = await reader.read();
          if (done) break;
          
          const chunk = decoder.decode(value);
          const lines = chunk.split("\n");

          for (const line of lines) {
            if (line.startsWith("data: ")) {
              const data = JSON.parse(line.replace("data: ", ""));

              // 1. If it's a content chunk, append it to the screen
              if (data.content) {
                aiResponse += data.content;
                setMessages((prev) => {
                  const newMessages = [...prev];
                  newMessages[newMessages.length - 1].content = aiResponse;
                  return newMessages;
                });
              }

              // 2. If the AI declares the clipboard is complete, lock the chat!
              if (data.is_done && data.clipboard_complete) {
                setIsLocked(true);
              }
            }
          }
        }
      }
    } catch (error) {
      console.error("Chat Error:", error);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-[85vh] max-w-4xl mx-auto bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
      
      {/* Header */}
      <div className="bg-slate-50 border-b border-slate-200 p-4 flex items-center justify-between">
        <div>
          <h2 className="font-bold text-slate-800">IT Support Diagnostic</h2>
          <p className="text-xs text-slate-500">Agentic Triage Engine Active</p>
        </div>
        {isLocked && (
          <div className="flex items-center gap-2 px-3 py-1 bg-green-100 text-green-700 rounded-full text-sm font-semibold animate-pulse">
            <CheckCircle className="w-4 h-4" /> Ticket Routed to Faculty
          </div>
        )}
      </div>

      {/* Chat Area */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto p-6 space-y-6">
        {messages.length === 0 && (
          <div className="text-center text-slate-400 mt-20 ">
            <Bot className="w-12 h-12 mx-auto mb-3 opacity-20" />
            <p>Describe your issue to begin triage.</p>
          </div>
        )}
        
        {messages.map((msg, idx) => (
          <div key={idx} className={`flex gap-4 ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
            {msg.role === "ai" && <div className="w-8 h-8 rounded-full bg-indigo-100 flex items-center justify-center shrink-0"><Bot className="w-5 h-5 text-indigo-600" /></div>}
            
            <div className={`px-4 py-3 rounded-2xl max-w-[80%] ${msg.role === "user" ? "bg-indigo-600 text-white rounded-tr-sm" : "bg-slate-100 text-slate-800 rounded-tl-sm whitespace-pre-wrap"}`}>
              {msg.content}
            </div>

            {msg.role === "user" && <div className="w-8 h-8 rounded-full bg-slate-200 flex items-center justify-center shrink-0"><User className="w-5 h-5 text-slate-600" /></div>}
          </div>
        ))}
      </div>

      {/* Input Box */}
<div className="p-4 bg-white border-t border-slate-200">
  <form onSubmit={sendMessage} className="flex gap-3">
    <input
      type="text"
      value={input}
      onChange={(e) => setInput(e.target.value)}
      disabled={isLoading || isLocked}
      placeholder={isLocked ? "Ticket closed. Check your email for receipt." : "Type your issue here..."}
      className="flex-1 px-4 py-3 bg-white text-slate-900 rounded-lg border border-slate-300 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 disabled:bg-slate-50 disabled:text-slate-400"
    />
    <button
      type="submit"
      disabled={!input.trim() || isLoading || isLocked}
      className="px-6 py-3 bg-indigo-600 text-white rounded-lg font-medium hover:bg-indigo-700 disabled:bg-slate-300 transition-colors flex items-center justify-center min-w-[100px]"
    >
      {isLoading ? <Loader2 className="w-5 h-5 animate-spin" /> : <Send className="w-5 h-5" />}
    </button>
  </form>
</div>
    </div>
  );
}