import React, { useEffect } from 'react';
import useRealtimeWS from '../hooks/useRealtimeWS';

export default function RealtimeRecorderSimple({onNewSegments}){
  const {status, captions, connectAndStart, stop} = useRealtimeWS();

  useEffect(()=>{
    if(!captions.length) return;
    const latest = captions[captions.length-1];
    if(latest && latest.segments && onNewSegments){
      onNewSegments(latest.segments.map(s=>({start:s.start, end:s.end, text:s.text})));
    }
  }, [captions, onNewSegments]);

  return (
    <div className="p-3 border rounded bg-white dark:bg-gray-800">
      <div className="flex items-center gap-2 mb-2">
        <button onClick={connectAndStart} disabled={status==='recording'||status==='starting'} className="px-3 py-1.5 rounded text-xs bg-green-600 text-white disabled:opacity-50">Start</button>
        <button onClick={stop} disabled={status!=='recording'&&status!=='starting'} className="px-3 py-1.5 rounded text-xs bg-red-600 text-white disabled:opacity-50">Stop</button>
        <span className="text-xs ml-2">{status}</span>
      </div>
      <p className="text-[11px] text-gray-500">Live audio chunks stream to backend; partial transcripts appended.</p>
    </div>
  );
}