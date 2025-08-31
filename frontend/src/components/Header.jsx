import React from 'react';

export default function Header({dark, setDark}){
  return (
    <header className="border-b bg-white/70 dark:bg-gray-800/70 backdrop-blur sticky top-0 z-10">
      <div className="container mx-auto flex items-center justify-between p-4">
        <h1 className="font-semibold text-lg">AI Video & Audio Summarizer</h1>
        <div className="flex items-center gap-4">
          <button onClick={()=>setDark(!dark)} className="px-3 py-1 rounded bg-gray-200 dark:bg-gray-700 text-sm">{dark? 'Light':'Dark'}</button>
        </div>
      </div>
    </header>
  )
}
