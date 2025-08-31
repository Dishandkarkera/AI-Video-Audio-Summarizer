import React, { useState, useEffect } from 'react';
import axios from 'axios';

const API = import.meta.env.VITE_API || 'http://localhost:8000';

export default function App(){
  const [file, setFile] = useState(null);
  const [session, setSession] = useState(null);
  const [polling, setPolling] = useState(false);

  const upload = async ()=>{
    if(!file) return;
    const form = new FormData();
    form.append('file', file);
    const { data } = await axios.post(`${API}/sessions`, form);
    setSession(data);
  };

  useEffect(()=>{
    if(!session || session.status === 'complete') return;
    setPolling(true);
    const id = setInterval(async ()=>{
      try {
        const { data } = await axios.get(`${API}/sessions/${session.id}`);
        setSession(data);
      } catch{}
    }, 1200);
    return ()=>{ clearInterval(id); setPolling(false); };
  }, [session?.id, session?.status]);

  return (
    <div className="max-w-3xl mx-auto p-6 space-y-6">
      <h1 className="text-2xl font-semibold">Summarizer Skeleton</h1>
      <div className="border rounded p-4 bg-white shadow-sm">
        <input type="file" onChange={e=>setFile(e.target.files[0])} />
        <button onClick={upload} disabled={!file} className="ml-2 px-3 py-1 bg-blue-600 text-white rounded disabled:opacity-50">Upload</button>
      </div>
      {session && (
        <div className="border rounded p-4 bg-white shadow-sm space-y-3">
          <div className="flex justify-between text-sm"><span>File:</span><span>{session.original_filename}</span></div>
          <div className="flex justify-between text-sm"><span>Status:</span><span className="font-mono">{session.status}</span></div>
          {session.summary && (
            <div>
              <h2 className="font-medium mb-1">Summary</h2>
              <p className="text-sm whitespace-pre-wrap">{session.summary}</p>
            </div>
          )}
        </div>
      )}
      <p className="text-xs text-gray-500">Mock pipeline. Replace endpoints with real Whisper & Gemini later.</p>
    </div>
  );
}
