import Link from "next/link";
import { GraduationCap, Briefcase, ArrowRight } from "lucide-react";

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-slate-950 flex flex-col items-center justify-center p-6 text-slate-100">
      
      {/* Header */}
      <div className="text-center mb-16">
        <h1 className="text-5xl md:text-6xl font-extrabold tracking-tight mb-6 text-transparent bg-clip-text bg-gradient-to-r from-indigo-400 to-purple-400">
          Agentic Support Gateway
        </h1>
        <p className="text-slate-400 max-w-xl mx-auto text-lg">
          Select your portal to access the AI-powered service desk.
        </p>
      </div>

      {/* Login Options Container */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 w-full max-w-4xl">
        
        {/* Student Card (Routes to Clerk) */}
        {/* Note: Clerk Middleware automatically catches this /portal/support route and forces sign-in! */}
        <Link 
          href="/portal/support" 
          className="group flex flex-col bg-slate-900 border border-slate-800 hover:border-indigo-500/50 rounded-2xl p-8 transition-all hover:shadow-[0_0_30px_-5px_rgba(99,102,241,0.15)]"
        >
          <div className="w-14 h-14 bg-indigo-500/10 text-indigo-400 rounded-xl flex items-center justify-center mb-6 border border-indigo-500/20 group-hover:scale-110 transition-transform">
            <GraduationCap className="w-7 h-7" />
          </div>
          <h2 className="text-2xl font-bold mb-3 text-slate-100">Login as Student</h2>
          <p className="text-slate-400 mb-8 leading-relaxed flex-1">
            Submit IT support tickets, chat with the AI diagnostic engine, and track the status of your active requests.
          </p>
          <div className="flex items-center text-indigo-400 font-medium">
            Access Student Portal <ArrowRight className="w-4 h-4 ml-2 group-hover:translate-x-1 transition-transform" />
          </div>
        </Link>

        {/* Faculty Card (Routes to Custom DB Login) */}
        <Link 
          href="/faculty/login" 
          className="group flex flex-col bg-slate-900 border border-slate-800 hover:border-emerald-500/50 rounded-2xl p-8 transition-all hover:shadow-[0_0_30px_-5px_rgba(16,185,129,0.15)]"
        >
          <div className="w-14 h-14 bg-emerald-500/10 text-emerald-400 rounded-xl flex items-center justify-center mb-6 border border-emerald-500/20 group-hover:scale-110 transition-transform">
            <Briefcase className="w-7 h-7" />
          </div>
          <h2 className="text-2xl font-bold mb-3 text-slate-100">Login as Staff</h2>
          <p className="text-slate-400 mb-8 leading-relaxed flex-1">
            Access the command center, review AI-generated issue summaries, and resolve tickets routed to your department queue.
          </p>
          <div className="flex items-center text-emerald-400 font-medium">
            Access Staff Portal <ArrowRight className="w-4 h-4 ml-2 group-hover:translate-x-1 transition-transform" />
          </div>
        </Link>

      </div>
    </div>
  );
}