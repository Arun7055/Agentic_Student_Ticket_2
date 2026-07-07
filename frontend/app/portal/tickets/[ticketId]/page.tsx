"use client";

import { useState, useRef, useEffect } from "react";
import { useAuth } from "@clerk/nextjs";
import { useParams } from "next/navigation";
import Link from "next/link";
import { Send, CheckCircle, Bot, User, Loader2, ArrowLeft } from "lucide-react";

type Message = { role: "user" | "ai"; content: string };

export default function TicketPage() {
  const { getToken } = useAuth();
  const params = useParams();
  const ticketId = params.ticketId as string;

  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [isLocked, setIsLocked] = useState(false); 
  const scrollRef = useRef<HTMLDivElement>(null);

  // Fetch Exact DB State
  const fetchHistory = async () => {
    if (!ticketId) return;
    try {
      const token = await getToken();
      const response = await fetch(`https://agentic-student-ticket-2.onrender.com/tickets/${ticketId}/messages`, {
        headers: { "Authorization": `Bearer ${token}` },
      });
      if (response.ok) {
        const data = await response.json();
        if (data.messages && data.messages.length > 0) {
          const formattedHistory = data.messages.map((msg: any) => ({
            role: msg.role === "human" || msg.role === "user" ? "user" : "ai",
            content: msg.content
          }));
          setMessages(formattedHistory);
        }
        if (data.department_slug) setIsLocked(true);
      }
    } catch (error) {
      console.error("Failed to fetch history:", error);
    }
  };

  useEffect(() => {
    fetchHistory();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ticketId, getToken]);

  useEffect(() => {
    if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
  }, [messages]);

  const sendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading || isLocked || !ticketId) return;

    const userMessage = input;
    setInput("");
    
    // Add User Message & Empty AI Bubble
    setMessages((prev) => [...prev, { role: "user", content: userMessage }, { role: "ai", content: "" }]);
    setIsLoading(true);

    try {
      const token = await getToken();
      const response = await fetch("https://agentic-student-ticket-2.onrender.com/ai/stream", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`,
        },
        body: JSON.stringify({ thread_id: ticketId, message: userMessage }),
      });

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`Backend Error ${response.status}: ${errorText}`);
      }

      // LIVE STREAMING TEXT PARSER
      if (response.body) {
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let aiResponse = "";
        let buffer = "";

        while (true) {
          const { value, done } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split("\n");
          buffer = lines.pop() || "";

          for (const line of lines) {
            const trimmedLine = line.trim();
            if (!trimmedLine) continue;
            
            const jsonString = trimmedLine.startsWith("data: ") ? trimmedLine.slice(6) : trimmedLine;

            try {
              const data = JSON.parse(jsonString);
              
              // Safely grab whatever text LangGraph sends
              const incomingText = data.agent_reply || data.content || data.message || data.text || "";
              
              if (incomingText) {
                // If it's the massive final payload, overwrite. Otherwise, append chunk.
                if (incomingText.length > 20 && !aiResponse.includes(incomingText.substring(0, 10))) {
                  aiResponse = incomingText;
                } else {
                  aiResponse += incomingText;
                }

                // Update the UI instantly
                setMessages((prev) => {
                  const newMessages = [...prev];
                  newMessages[newMessages.length - 1].content = aiResponse;
                  return newMessages;
                });
              }

              // Lock UI if final routing data is present
              if (data.department || data.department_slug || data.clipboard_complete === true) {
                setIsLocked(true);
              }
            } catch (e) {
              // Ignore partial JSON chunks
            }
          }
        }
      }

      // Sync with DB just in case stream missed something
      await fetchHistory();

    } catch (error) {
      console.error("Chat Error:", error);
      alert("Error: Check console for details.");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 flex flex-col items-center p-6 text-slate-100">
      <div className="w-full max-w-4xl mb-6">
        <Link href="/portal/support" className="inline-flex items-center text-slate-400 hover:text-indigo-400 transition-colors">
          <ArrowLeft className="w-4 h-4 mr-2" /> Back to Dashboard
        </Link>
      </div>

      <div className="flex flex-col h-[80vh] w-full max-w-4xl bg-slate-900 rounded-xl shadow-2xl border border-slate-800 overflow-hidden">
        <div className="bg-slate-950 border-b border-slate-800 p-4 flex items-center justify-between">
          <div>
            <h2 className="font-bold text-slate-100">IT Support Diagnostic</h2>
            <p className="text-xs text-slate-500 font-mono mt-1">Ticket ID: {ticketId}</p>
          </div>
          <div className="flex items-center gap-3">
            {isLocked && (
              <div className="flex items-center gap-2 px-3 py-1 bg-green-500/10 text-green-400 border border-green-500/20 rounded-full text-sm font-semibold animate-pulse">
                <CheckCircle className="w-4 h-4" /> Ticket Routed to Faculty
              </div>
            )}
          </div>
        </div>

        <div ref={scrollRef} className="flex-1 overflow-y-auto p-6 space-y-6">
          {messages.length === 0 && !isLoading && (
            <div className="text-center text-slate-500 mt-20">
              <Bot className="w-12 h-12 mx-auto mb-3 opacity-20" />
              <p>No messages found. Describe your issue to begin.</p>
            </div>
          )}
          
          {messages.map((msg, idx) => (
            <div key={idx} className={`flex gap-4 ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
              {msg.role === "ai" && <div className="w-8 h-8 rounded-full bg-indigo-500/20 border border-indigo-500/30 flex items-center justify-center shrink-0"><Bot className="w-5 h-5 text-indigo-400" /></div>}
              
              <div className={`px-4 py-3 rounded-2xl max-w-[80%] ${
                msg.role === "user" ? "bg-indigo-600 text-white rounded-tr-sm shadow-md" : "bg-slate-800 text-slate-200 border border-slate-700 rounded-tl-sm whitespace-pre-wrap shadow-sm"
              }`}>
                {/* Fallback typing indicator inside the bubble if text hasn't arrived yet */}
                {msg.role === "ai" && msg.content === "" && isLoading ? <Loader2 className="w-4 h-4 animate-spin text-indigo-400" /> : msg.content}
              </div>

              {msg.role === "user" && <div className="w-8 h-8 rounded-full bg-slate-800 border border-slate-700 flex items-center justify-center shrink-0"><User className="w-5 h-5 text-slate-400" /></div>}
            </div>
          ))}
        </div>

        <div className="p-4 bg-slate-950 border-t border-slate-800">
          <form onSubmit={sendMessage} className="flex gap-3">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              disabled={isLoading || isLocked}
              placeholder={isLocked ? "Ticket closed. Check your email for receipt." : "Type your issue here..."}
              className="flex-1 px-4 py-3 bg-slate-900 text-slate-100 rounded-lg border border-slate-700 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 disabled:bg-slate-900/50 disabled:text-slate-600 placeholder-slate-500 transition-colors"
            />
            <button type="submit" disabled={!input.trim() || isLoading || isLocked} className="px-6 py-3 bg-indigo-600 text-white rounded-lg font-medium hover:bg-indigo-500 disabled:bg-slate-800 disabled:text-slate-500 transition-colors flex items-center justify-center min-w-[100px]">
              {isLoading ? <Loader2 className="w-5 h-5 animate-spin" /> : <Send className="w-5 h-5" />}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}