import React, { createContext, useContext, useState } from "react";

const TranscriptContext = createContext(null);

export function TranscriptProvider({ children }) {
  const [segments, setSegments] = useState([]); // {id, start, end, text}

  const addSegments = (newSegments) => {
    setSegments((prev) => {
      const mapped = newSegments.map((s, i) => ({
        id: `${Date.now()}_${Math.random().toString(36).slice(2,8)}_${i}`,
        start: s.start ?? 0,
        end: s.end ?? 0,
        text: s.text ?? ""
      }));
      return [...prev, ...mapped];
    });
  };

  const clear = () => setSegments([]);

  return (
    <TranscriptContext.Provider value={{ segments, addSegments, clear }}>
      {children}
    </TranscriptContext.Provider>
  );
}

export function useTranscript() {
  const ctx = useContext(TranscriptContext);
  if (!ctx) throw new Error("useTranscript must be used inside TranscriptProvider");
  return ctx;
}