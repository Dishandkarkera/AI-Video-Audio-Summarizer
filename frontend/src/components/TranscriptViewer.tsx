import React, { useEffect, useState } from 'react';
import axios from 'axios';

export default function TranscriptViewer({ mediaId }: any){
  const [segments, setSegments] = useState([] as any);
  const api = (import.meta as any).env.VITE_API || '/api';
  useEffect(()=>{
    if(!mediaId) return;
    axios.get(`${api}/media/${mediaId}/transcript`).then(res=>{
      setSegments(res.data.segments || []);
    });
  },[mediaId]);
  return (
    <div className="mt-4">
      <h2 className="font-semibold">Transcript</h2>
      <ul className="space-y-2">
        {segments.map((s,idx)=>(
          <li key={idx} className="p-2 hover:bg-gray-100 cursor-pointer">
            <span className="text-sm text-gray-500">[{(s.start||0).toFixed(2)}s]</span> {s.text}
          </li>
        ))}
      </ul>
    </div>
  );
}
