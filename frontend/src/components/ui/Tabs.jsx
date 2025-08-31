import React from 'react';
export function Tabs({tabs, current, onChange}){
  return (
    <div className="flex border-b border-gray-200 dark:border-gray-700 text-xs">
      {tabs.map(t=> (
        <button key={t}
          onClick={()=>onChange(t)}
          className={`px-3 py-2 -mb-px border-b-2 ${current===t? 'border-blue-600 text-blue-600':'border-transparent hover:border-gray-300'}`}>{t}</button>
      ))}
    </div>
  );
}
