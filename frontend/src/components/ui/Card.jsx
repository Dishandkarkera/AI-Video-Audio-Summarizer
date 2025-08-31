import React from 'react';
export function Card({children, className=''}){ return <div className={`rounded border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 shadow-sm ${className}`}>{children}</div>; }
export function CardHeader({children,className=''}){ return <div className={`px-4 py-2 border-b border-gray-100 dark:border-gray-700 flex items-center justify-between ${className}`}>{children}</div>; }
export function CardTitle({children,className=''}){ return <h3 className={`font-semibold text-sm ${className}`}>{children}</h3>; }
export function CardContent({children,className=''}){ return <div className={`p-4 space-y-2 text-sm ${className}`}>{children}</div>; }
