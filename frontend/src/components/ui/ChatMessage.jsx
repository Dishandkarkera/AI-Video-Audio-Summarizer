import React from 'react';
export function ChatMessage({role, children}){
  const mine = role==='user';
  return (
    <div className={mine? 'text-right':'text-left'}>
      <span className={`inline-block px-3 py-1.5 rounded-lg text-xs leading-relaxed max-w-[80%] ${mine? 'bg-blue-600 text-white':'bg-gray-100 dark:bg-gray-700 dark:text-gray-100'}`}>{children}</span>
    </div>
  );
}
