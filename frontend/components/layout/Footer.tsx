"use client";

export default function Footer() {
  return (
    <footer className="mt-auto border-t border-slate-800 bg-slate-900/50 py-4 px-8 flex items-center justify-between">
      <div className="flex items-center gap-3">
        {/* Fallback to simple styled text if the logo image fails to load during dev */}
        <div className="relative flex items-center justify-center">
            <img src="/logo.png" alt="Vyrenzo Logo" className="h-5 opacity-90 object-contain" onError={(e) => { e.currentTarget.style.display = 'none'; }} />
        </div>
        <span className="text-xs text-slate-400 font-medium tracking-wider uppercase ml-2 border-l border-slate-700 pl-3">
          Vyrenzo Powered by Vyrenzo.ai
        </span>
      </div>
      <div className="text-xs text-slate-500 font-medium">
        &copy; {new Date().getFullYear()} Vyrenzo. All rights reserved.
      </div>
    </footer>
  );
}
