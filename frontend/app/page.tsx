import { auth } from "@clerk/nextjs/server";
import { redirect } from "next/navigation";
import Link from "next/link";
import { ArrowRight, ShieldCheck, Zap } from "lucide-react";

export default async function LandingPage() {
  // 1. AWAIT the auth() promise in v5
  const { userId } = await auth();
  
  if (userId) {
    redirect("/portal");
  }

  // 2. If not logged in, show the public hero section
  return (
    <main className="flex min-h-screen flex-col items-center justify-center bg-slate-50 p-6">
      <div className="max-w-3xl text-center space-y-8">
        
        <div className="space-y-4">
          <h1 className="text-5xl font-extrabold tracking-tight text-slate-900">
            Campus IT <span className="text-indigo-600">Gateway</span>
          </h1>
          <p className="text-lg text-slate-600 max-w-xl mx-auto">
            Agentic AI triage and instant routing for university infrastructure. 
            Log in to manage your campus requests.
          </p>
        </div>

        <div className="flex flex-col sm:flex-row gap-4 justify-center mt-8">
          <Link 
            href="/sign-in" 
            className="flex items-center justify-center gap-2 rounded-lg bg-indigo-600 px-8 py-4 text-sm font-semibold text-white shadow-sm hover:bg-indigo-500 transition-all"
          >
            Access Portal <ArrowRight className="w-4 h-4" />
          </Link>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-6 mt-16 text-left">
          <div className="p-6 bg-white rounded-xl shadow-sm border border-slate-100">
            <Zap className="w-8 h-8 text-indigo-600 mb-4" />
            <h3 className="font-semibold text-slate-900">For Students</h3>
            <p className="text-sm text-slate-500 mt-2">Chat with our AI diagnostic agent to instantly route your issue to the correct department.</p>
          </div>
          <div className="p-6 bg-white rounded-xl shadow-sm border border-slate-100">
            <ShieldCheck className="w-8 h-8 text-indigo-600 mb-4" />
            <h3 className="font-semibold text-slate-900">For Faculty</h3>
            <p className="text-sm text-slate-500 mt-2">Access your automated dossiers, review student chat logs, and resolve tickets efficiently.</p>
          </div>
        </div>

      </div>
    </main>
  );
}