import React from 'react';
import { useTranscript } from '../store/TranscriptStore';

export default function TranscriptViewerLive({onSeek}){
  const {segments} = useTranscript();

  const format = (sec)=>{
    if(sec==null) return '00:00';
    const m = Math.floor(sec/60).toString().padStart(2,'0');
    const s = Math.floor(sec%60).toString().padStart(2,'0');
    return `${m}:${s}`;
  }

  return (
    <div className="p-3 border rounded bg-white dark:bg-gray-800 max-h-80 overflow-auto text-[11px] space-y-1">
      <h3 className="font-medium text-xs mb-1">Live Transcript</h3>
      {segments.length===0 && <p className="text-gray-500">No transcript yet.</p>}
      {segments.map(seg=> (
        <div key={seg.id} className="px-1 py-1 rounded hover:bg-gray-100 dark:hover:bg-gray-700 cursor-pointer" onClick={()=>onSeek && onSeek(seg.start)}>
          <span className="text-gray-500 mr-2">[{format(seg.start)}]</span>{seg.text}
        </div>
      ))}
    </div>
  );
}