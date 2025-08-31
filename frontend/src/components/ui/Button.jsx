import React from 'react';
import { clsx } from 'clsx';
export function Button({children, className='', variant='primary', size='sm', ...rest}){
  const base = 'inline-flex items-center justify-center font-medium rounded transition disabled:opacity-50 disabled:cursor-not-allowed';
  const variants = {
    primary: 'bg-blue-600 text-white hover:bg-blue-700',
    outline: 'border border-gray-300 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-700',
    subtle: 'bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600'
  };
  const sizes = { sm: 'text-xs px-3 py-1.5', md: 'text-sm px-4 py-2'};
  return <button className={clsx(base, variants[variant], sizes[size], className)} {...rest}>{children}</button>
}
