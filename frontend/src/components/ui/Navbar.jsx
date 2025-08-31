import React from 'react';

export function Navbar({ dark, onToggleDark }){
  return (
    <nav className="sticky top-0 z-20 backdrop-blur bg-white/70 dark:bg-gray-900/70 border-b border-gray-200 dark:border-gray-700 transition-colors">
      <div className="container mx-auto grid grid-cols-3 items-center px-4 h-14">
        {/* Center group (placed in second column via col-span) */}
        <div className="col-span-3 flex items-center justify-center pointer-events-auto">
          <span className="font-semibold tracking-tight select-none text-center">AI Summarizer</span>
        </div>
        {/* Right theme button (original) placed via absolute container overlay */}
        <button
          type="button"
          onClick={onToggleDark}
          className="absolute right-4 top-1/2 -translate-y-1/2 w-10 h-10 rounded-full overflow-hidden group focus:outline-none focus:ring-2 focus:ring-blue-500/60 border border-gray-300 dark:border-gray-600"
          aria-label="Toggle theme"
        >
          <span className="absolute inset-0 flex items-center justify-center">
            {/* Sun */}
            <svg className={`w-5 h-5 text-yellow-500 transition-all duration-500 ${dark ? 'scale-0 rotate-90 opacity-0' : 'scale-100 rotate-0 opacity-100'}`} xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
              <circle cx="12" cy="12" r="4" />
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 2v2m0 16v2M4.93 4.93l1.42 1.42M15.66 15.66l1.41 1.41M2 12h2m16 0h2M6.35 17.66l1.42-1.42M16.24 7.76l1.42-1.42" />
            </svg>
            {/* Moon */}
            <svg className={`absolute w-5 h-5 text-blue-400 transition-all duration-500 ${dark ? 'scale-100 rotate-0 opacity-100' : 'scale-0 -rotate-90 opacity-0'}`} xmlns="http://www.w3.org/2000/svg" fill="currentColor" viewBox="0 0 24 24">
              <path d="M21 12.79A9 9 0 0 1 11.21 3 7 7 0 1 0 21 12.79z" />
            </svg>
          </span>
          {/* Ripple / glow animation */}
          <span className="absolute inset-0 pointer-events-none opacity-0 group-hover:opacity-100 transition-opacity duration-500">
            <span className="absolute inset-0 animate-ping rounded-full bg-gradient-to-tr from-blue-400 via-purple-400 to-pink-400 opacity-30" />
          </span>
          <span className="sr-only">Toggle dark mode</span>
        </button>
      </div>
    </nav>
  );
}
