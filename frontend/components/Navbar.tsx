import { UserButton } from "@clerk/nextjs";
import Link from "next/link";

export default function Navbar() {
  return (
    <header className="sticky top-0 z-50 w-full border-b border-slate-800 bg-slate-900/80 backdrop-blur-md shadow-sm">
      <div className="container mx-auto flex h-16 items-center justify-between px-4 md:px-6">
        <div className="flex items-center gap-6">
          <Link href="/portal" className="font-bold text-xl text-indigo-400 tracking-tight">
            Gateway.
          </Link>
        </div>
        
        <div className="flex items-center gap-4">
          <UserButton />
        </div>
      </div>
    </header>
  );
}