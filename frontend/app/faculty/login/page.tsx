"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { ShieldAlert, Loader2, KeyRound } from "lucide-react";

export default function FacultyLogin() {
  const router = useRouter();
  const [staffId, setStaffId] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError("");

    try {
      const response = await fetch("https://agentic-student-ticket-2.onrender.com/auth/faculty/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ 
          staff_id: staffId, // Sending staff_id instead of email
          password: password 
        }),
      });

      if (!response.ok) {
        throw new Error("Invalid credentials");
      }

      const data = await response.json();
      localStorage.setItem("faculty_token", data.access_token);
      router.push("/faculty");
      
    } catch (err) {
      setError("Invalid Staff ID or password. Access denied.");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex items-center justify-center min-h-[80vh]">
      <div className="w-full max-w-md p-8 bg-slate-900 border border-slate-800 rounded-xl shadow-2xl">
        <div className="flex flex-col items-center mb-8 text-center">
          <div className="w-12 h-12 bg-indigo-500/20 text-indigo-400 rounded-full flex items-center justify-center mb-4 border border-indigo-500/30">
            <ShieldAlert className="w-6 h-6" />
          </div>
          <h1 className="text-2xl font-bold text-slate-100">Staff Portal</h1>
          <p className="text-slate-400 text-sm mt-1">Authorized faculty access only.</p>
        </div>

        {error && (
          <div className="mb-6 p-3 bg-red-500/10 border border-red-500/20 text-red-400 text-sm rounded-lg text-center">
            {error}
          </div>
        )}

        <form onSubmit={handleLogin} className="space-y-5">
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-1">Department ID</label>
            <input
              type="text" // Changed from email to text
              value={staffId}
              onChange={(e) => setStaffId(e.target.value)}
              className="w-full px-4 py-3 bg-slate-950 text-slate-100 rounded-lg border border-slate-800 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-colors"
              placeholder="e.g. hostel, admin, it"
              required
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-1">Password</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full px-4 py-3 bg-slate-950 text-slate-100 rounded-lg border border-slate-800 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-colors"
              placeholder="••••••••"
              required
            />
          </div>
          <button
            type="submit"
            disabled={isLoading}
            className="w-full flex items-center justify-center gap-2 py-3 bg-indigo-600 hover:bg-indigo-500 text-white font-medium rounded-lg transition-colors disabled:opacity-50"
          >
            {isLoading ? <Loader2 className="w-5 h-5 animate-spin" /> : <KeyRound className="w-5 h-5" />}
            Authenticate
          </button>
        </form>
      </div>
    </div>
  );
}