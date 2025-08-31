import React from "react";
import useRealtimeWS from "../hooks/useRealtimeWS";

/**
 * RealtimeRecorder component
 * - onNewSegments(newSegments) callback receives [{start,end,text}, ...] when partials arrive
 */
export default function RealtimeRecorder({ onNewSegments }) {
  const { status, captions, connectAndStart, stop } = useRealtimeWS();

  React.useEffect(() => {
    if (captions.length && onNewSegments) {
      const latest = captions[captions.length - 1];
      if (latest && latest.segments) {
        const normalized = latest.segments.map((s) => ({
          start: s.start ?? s['start'] ?? 0,
          end: s.end ?? s['end'] ?? 0,
          text: s.text ?? s['text'] ?? latest.text ?? ""
        }));
        onNewSegments(normalized);
      } else if (latest && latest.text && !latest.segments) {
        onNewSegments([{ start: 0, end: 0, text: latest.text }]);
      }
    }
  }, [captions, onNewSegments]);

  return (
    <div className="p-3 border rounded bg-white">
      <div className="flex items-center gap-3">
        <button onClick={() => connectAndStart()} className="px-3 py-2 bg-green-600 text-white rounded" disabled={status === "recording" || status === "starting"}>
          Start
        </button>
        <button onClick={() => stop()} className="px-3 py-2 bg-red-600 text-white rounded" disabled={status !== "recording" && status !== "starting"}>
          Stop
        </button>
        <div className="ml-2 text-sm">Status: {status}</div>
      </div>

      <div className="mt-3 max-h-44 overflow-auto bg-gray-50 p-2 rounded">
        {captions.length === 0 && <div className="text-sm text-gray-400">No live captions yet</div>}
        {captions.map((c, i) => (
          <div key={i} className={`p-2 ${c.final ? "bg-green-50" : "bg-white"} rounded mb-1`}>
            <div className="text-sm">{c.text}</div>
            {c.segments && c.segments.length > 0 && (
              <div className="text-xs text-gray-500 mt-1">
                {c.segments.slice(0,3).map((s, idx) => (
                  <span key={idx} className="mr-2">[{new Date((s.start||0)*1000).toISOString().substr(14,5)}]</span>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}