"use client";

import { useState, useRef, useEffect } from "react";
import { useAuth } from "@clerk/nextjs";
import { Send, CheckCircle, Bot, User, Loader2, X } from "lucide-react";

type Message = { role: "user" | "ai"; content: string };

interface ChatModalProps {
  onClose: () => void;
}

export default function ChatModal({ onClose }: ChatModalProps) {
  const { getToken } = useAuth();
  
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [isLocked, setIsLocked] = useState(false); 
  
  const threadId = useRef(`ticket_${Math.random().toString(36).substring(7)}`);
  const scrollRef = useRef<HTMLDivElement>(null);

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
            "Authorization": `Bearer ${token}`,
          },
          body: JSON.stringify({
            thread_id: threadId.current,
            message: userMessage,
          }),
        });
  
        if (!response.ok) {
          if (response.status === 409) {
             alert("Concurrency Lock: You already have a ticket open!");
          }
          throw new Error("Backend connection failed");
        }
  
        const reader = response.body?.getReader();
        const decoder = new TextDecoder();
        let aiResponse = "";
        let buffer = ""; // <-- NEW: Buffer to hold half-cut network chunks
  
        setMessages((prev) => [...prev, { role: "ai", content: "" }]);
  
        if (reader) {
          while (true) {
            const { value, done } = await reader.read();
            if (done) break;
            
            // Decode the new chunk and add it to whatever was left over in the buffer
            buffer += decoder.decode(value, { stream: true });
            
            // Split by newlines
            const lines = buffer.split("\n");
            
            // IMPORTANT: Keep the very last line in the buffer because it might be incomplete!
            buffer = lines.pop() || ""; 
  
            for (const line of lines) {
              const trimmedLine = line.trim();
              if (!trimmedLine) continue;
  
              // Strip "data: " if it exists, otherwise just read the raw line
              const jsonString = trimmedLine.startsWith("data: ") 
                ? trimmedLine.slice(6) 
                : trimmedLine;
  
                try {
                    const data = JSON.parse(jsonString);
      
                    // NEW: Handle both streaming tokens (content) AND the final full payload (agent_reply)
                    if (data.agent_reply) {
                      // If the backend sends the fully formed final reply, overwrite the buffer
                      aiResponse = data.agent_reply; 
                    } else if (data.content) {
                      // If it's standard streaming, append the word chunks
                      aiResponse += data.content; 
                    }
                    
                    // If either condition above updated the text, trigger the React state update
                    if (data.content || data.agent_reply) {
                      setMessages((prev) => {
                        const newMessages = [...prev];
                        newMessages[newMessages.length - 1].content = aiResponse;
                        return newMessages;
                      });
                    }
      
                    // NEW: Broadened lock conditions to ensure it catches the final state
                    if (data.is_done || data.is_clipboard_complete || data.department) {
                      setIsLocked(true);
                    }
                  } catch (e) {
                    // Silently ignore partial JSON parse errors that happen naturally during network streaming
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
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-slate-950/80 backdrop-blur-sm p-4">
      <div className="flex flex-col h-[85vh] w-full max-w-4xl bg-slate-900 rounded-xl shadow-2xl border border-slate-800 overflow-hidden">
        
        {/* Header */}
        <div className="bg-slate-950 border-b border-slate-800 p-4 flex items-center justify-between">
          <div>
            <h2 className="font-bold text-slate-100">IT Support Diagnostic</h2>
            <p className="text-xs text-indigo-400">Agentic Triage Engine Active</p>
          </div>
          <div className="flex items-center gap-3">
            {isLocked && (
              <div className="flex items-center gap-2 px-3 py-1 bg-green-500/10 text-green-400 border border-green-500/20 rounded-full text-sm font-semibold animate-pulse">
                <CheckCircle className="w-4 h-4" /> Ticket Routed to Faculty
              </div>
            )}
            {/* TRIGGERS PROP FUNCTION INSTEAD OF ROUTING */}
            <button onClick={onClose} className="p-2 text-slate-400 hover:text-slate-200 hover:bg-slate-800 rounded-full transition-colors">
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Chat Area */}
        <div ref={scrollRef} className="flex-1 overflow-y-auto p-6 space-y-6">
          {messages.length === 0 && (
            <div className="text-center text-slate-500 mt-20">
              <Bot className="w-12 h-12 mx-auto mb-3 opacity-20" />
              <p>Describe your issue to begin triage.</p>
            </div>
          )}
          
          {messages.map((msg, idx) => (
            <div key={idx} className={`flex gap-4 ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
              {msg.role === "ai" && <div className="w-8 h-8 rounded-full bg-indigo-500/20 border border-indigo-500/30 flex items-center justify-center shrink-0"><Bot className="w-5 h-5 text-indigo-400" /></div>}
              
              <div className={`px-4 py-3 rounded-2xl max-w-[80%] ${
                msg.role === "user" 
                  ? "bg-indigo-600 text-white rounded-tr-sm shadow-md" 
                  : "bg-slate-800 text-slate-200 border border-slate-700 rounded-tl-sm whitespace-pre-wrap shadow-sm"
                }`}>
                {msg.content}
              </div>

              {msg.role === "user" && <div className="w-8 h-8 rounded-full bg-slate-800 border border-slate-700 flex items-center justify-center shrink-0"><User className="w-5 h-5 text-slate-400" /></div>}
            </div>
          ))}
        </div>

        {/* Input Box */}
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
            <button
              type="submit"
              disabled={!input.trim() || isLoading || isLocked}
              className="px-6 py-3 bg-indigo-600 text-white rounded-lg font-medium hover:bg-indigo-500 disabled:bg-slate-800 disabled:text-slate-500 transition-colors flex items-center justify-center min-w-[100px]"
            >
              {isLoading ? <Loader2 className="w-5 h-5 animate-spin" /> : <Send className="w-5 h-5" />}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}