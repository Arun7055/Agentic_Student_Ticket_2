"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@clerk/nextjs";
import { fetchDashboardTickets } from "@/lib/api";
import { Plus, Ticket as TicketIcon, Clock, AlertCircle, Loader2 } from "lucide-react";
import ChatModal from "@/components/ChatModal"; // Import the modal

type Ticket = {
  id: string;
  status: string;
  department: string | null;
  severity: string | null;
  created_at: string;
  structured_payload: {
    issue_summary?: string;
  } | null;
};

export default function StudentDashboard() {
  const { getToken } = useAuth();
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  
  // NEW STATE TO CONTROL MODAL VISIBILITY
  const [isChatOpen, setIsChatOpen] = useState(false);

  // We abstract the fetch into a reusable function so we can call it when the modal closes
  const loadTickets = async () => {
    try {
      const token = await getToken();
      const data = await fetchDashboardTickets(token);
      setTickets(data);
    } catch (error) {
      console.error("Failed to load tickets:", error);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadTickets();
  }, [getToken]);

  const getStatusColor = (status: string) => {
    switch (status) {
      case "OPEN": return "bg-green-500/10 text-green-400 border-green-500/20";
      case "AI_TRIAGE": return "bg-indigo-500/10 text-indigo-400 border-indigo-500/20";
      case "CLOSED": return "bg-slate-500/10 text-slate-400 border-slate-500/20";
      default: return "bg-slate-500/10 text-slate-400 border-slate-500/20";
    }
  };

  const handleCloseModal = () => {
    setIsChatOpen(false);
    loadTickets(); // Refresh tickets in the background just in case they created one!
  };

  return (
    <div className="max-w-5xl mx-auto flex flex-col gap-6">
      
      {/* Header Section */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-100">My IT Support Tickets</h1>
          <p className="text-slate-400 text-sm mt-1">View your past requests or start a new triage session.</p>
        </div>
        <button 
          onClick={() => setIsChatOpen(true)}
          className="flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white font-medium rounded-lg transition-colors"
        >
          <Plus className="w-4 h-4" />
          New Ticket
        </button>
      </div>

      {/* Loading State */}
      {isLoading ? (
        <div className="flex flex-col items-center justify-center py-20 text-slate-500">
          <Loader2 className="w-8 h-8 animate-spin mb-4 text-indigo-500" />
          <p>Loading your ticket history...</p>
        </div>
      ) : (
        /* Ticket Grid */
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {tickets.length === 0 ? (
            <div className="col-span-full bg-slate-900 border border-slate-800 rounded-xl p-12 text-center text-slate-400">
              <TicketIcon className="w-12 h-12 mx-auto mb-4 opacity-20" />
              <p>You haven't submitted any IT tickets yet.</p>
            </div>
          ) : (
            tickets.map((ticket) => (
              <div key={ticket.id} className="bg-slate-900 border border-slate-800 rounded-xl p-5 hover:border-slate-700 transition-colors shadow-sm flex flex-col">
                <div className="flex justify-between items-start mb-4">
                  <div className={`px-2.5 py-0.5 rounded-full text-xs font-semibold border ${getStatusColor(ticket.status)}`}>
                    {ticket.status.replace("_", " ")}
                  </div>
                  <div className="text-xs text-slate-500 flex items-center gap-1">
                    <Clock className="w-3 h-3" />
                    {new Date(ticket.created_at).toLocaleDateString()}
                  </div>
                </div>
                
                <h3 className="text-slate-200 font-medium line-clamp-2 mb-3 flex-1">
                  {ticket.structured_payload?.issue_summary || "Awaiting AI categorization..."}
                </h3>
                
                <div className="flex items-center gap-4 text-xs text-slate-400 mt-auto border-t border-slate-800 pt-3">
                  {ticket.department && (
                    <div className="flex items-center gap-1">
                      <span className="font-semibold text-slate-300">Queue:</span> {ticket.department.toUpperCase()}
                    </div>
                  )}
                  {ticket.severity && (
                    <div className="flex items-center gap-1">
                      <AlertCircle className="w-3.5 h-3.5" />
                      <span className="font-semibold text-slate-300">Severity:</span> {ticket.severity}
                    </div>
                  )}
                </div>
              </div>
            ))
          )}
        </div>
      )}

      {/* MODAL OVERLAY */}
      {isChatOpen && <ChatModal onClose={handleCloseModal} />}

    </div>
  );
}