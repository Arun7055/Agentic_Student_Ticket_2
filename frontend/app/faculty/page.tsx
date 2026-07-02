"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { fetchDashboardTickets, resolveTicket } from "@/lib/api";
import { CheckCircle, Clock, AlertTriangle, MessageSquare, LogOut } from "lucide-react";

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

export default function FacultyDashboard() {
  const router = useRouter();
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [resolvingId, setResolvingId] = useState<string | null>(null);
  const [resolutionNote, setResolutionNote] = useState("");

  useEffect(() => {
    const token = localStorage.getItem("faculty_token");
    if (!token) {
      router.push("/faculty/login");
      return;
    }

    loadTickets(token);
  }, [router]);

  const loadTickets = async (token: string) => {
    try {
      const data = await fetchDashboardTickets(token);
      setTickets(data);
    } catch (error) {
      console.error("Failed to load department tickets", error);
      // If token is invalid/expired, boot them back to login
      localStorage.removeItem("faculty_token");
      router.push("/faculty/login");
    } finally {
      setIsLoading(false);
    }
  };

  const handleResolve = async (ticketId: string) => {
    const token = localStorage.getItem("faculty_token");
    if (!token) return;

    try {
      await resolveTicket(ticketId, token, resolutionNote);
      setResolvingId(null);
      setResolutionNote("");
      loadTickets(token); // Refresh the list
    } catch (error) {
      alert("Failed to resolve ticket. Please try again.");
    }
  };

  const handleLogout = () => {
    localStorage.removeItem("faculty_token");
    router.push("faculty/login");
  };

  if (isLoading) return <div className="text-center py-20 text-slate-500">Loading Command Center...</div>;

  const activeTickets = tickets.filter(t => t.status !== "CLOSED");
  const closedTickets = tickets.filter(t => t.status === "CLOSED");

  return (
    <div className="max-w-6xl mx-auto flex flex-col gap-8">
      
      <div className="flex items-center justify-between border-b border-slate-800 pb-6">
        <div>
          <h1 className="text-2xl font-bold text-slate-100">Department Command Center</h1>
          <p className="text-slate-400 mt-1">Manage and resolve escalated student issues.</p>
        </div>
        <button 
          onClick={handleLogout}
          className="flex items-center gap-2 px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg transition-colors"
        >
          <LogOut className="w-4 h-4" /> Sign Out
        </button>
      </div>

      <div>
        <h2 className="text-lg font-semibold text-slate-200 mb-4 flex items-center gap-2">
          <AlertTriangle className="w-5 h-5 text-amber-500" /> Action Required ({activeTickets.length})
        </h2>
        
        <div className="grid grid-cols-1 gap-4">
          {activeTickets.length === 0 ? (
             <div className="bg-slate-900 border border-slate-800 rounded-xl p-8 text-center text-slate-500">
               No active tickets for your department. Great job!
             </div>
          ) : (
            activeTickets.map(ticket => (
              <div key={ticket.id} className="bg-slate-900 border border-slate-700 rounded-xl p-6 shadow-lg flex flex-col md:flex-row gap-6 items-start md:items-center">
                <div className="flex-1">
                  <div className="flex items-center gap-3 mb-2">
                    <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/20">
                      {ticket.severity} PRIORITY
                    </span>
                    <span className="text-xs text-slate-500 flex items-center gap-1">
                      <Clock className="w-3 h-3" /> {new Date(ticket.created_at).toLocaleDateString()}
                    </span>
                  </div>
                  <h3 className="text-lg font-medium text-slate-100 mb-1">
                    {ticket.structured_payload?.issue_summary}
                  </h3>
                </div>
                
                {resolvingId === ticket.id ? (
                  <div className="flex w-full md:w-auto gap-2">
                    <input 
                      type="text" 
                      placeholder="Resolution note (e.g., Electrician fixed fan)"
                      value={resolutionNote}
                      onChange={(e) => setResolutionNote(e.target.value)}
                      className="px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-sm text-slate-100 focus:outline-none focus:border-green-500"
                    />
                    <button 
                      onClick={() => handleResolve(ticket.id)}
                      className="px-4 py-2 bg-green-600 hover:bg-green-500 text-white text-sm font-medium rounded-lg"
                    >
                      Confirm
                    </button>
                    <button 
                      onClick={() => setResolvingId(null)}
                      className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 text-sm rounded-lg"
                    >
                      Cancel
                    </button>
                  </div>
                ) : (
                  <button 
                    onClick={() => setResolvingId(ticket.id)}
                    className="flex items-center gap-2 px-5 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white font-medium rounded-lg transition-colors w-full md:w-auto justify-center"
                  >
                    <CheckCircle className="w-4 h-4" /> Resolve Issue
                  </button>
                )}
              </div>
            ))
          )}
        </div>
      </div>
      
      {/* Closed Tickets Section (Optional/Brief view) */}
      {closedTickets.length > 0 && (
        <div className="mt-8 opacity-75">
          <h2 className="text-lg font-semibold text-slate-400 mb-4">Recently Closed</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {closedTickets.map(ticket => (
              <div key={ticket.id} className="bg-slate-950 border border-slate-800 rounded-xl p-4">
                <h3 className="text-slate-300 font-medium text-sm truncate">{ticket.structured_payload?.issue_summary}</h3>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}