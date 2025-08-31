// Temporary module shims to satisfy editor until full type resolution works
// React 18 & axios real types are installed; this avoids false negatives from analyzer.
declare module 'react';
declare module 'react/jsx-runtime';
declare module 'axios';
