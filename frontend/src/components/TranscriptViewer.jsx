import React, { useEffect, useState, useRef, useMemo } from 'react';
import axios from 'axios';
import { Card, CardHeader, CardTitle, CardContent } from './ui/Card';

export default function TranscriptViewer({media}){
  // NOTE: All hooks MUST run on every render (no early returns before last hook) to avoid React hook order mismatch.
  const [current, setCurrent] = useState(media);
  const [polling, setPolling] = useState(false); // kept for future status display
  const [segments, setSegments] = useState([]);
  const [fullText, setFullText] = useState('');
  const [progress, setProgress] = useState(null); // null = indeterminate, number = precise percent
  const videoRef = useRef(null);
  const [query, setQuery] = useState('');
  const listRef = useRef(null);
  // IMPORTANT: backend default port is 8000, so use that as fallback (5000 was wrong causing silent polling failures)
  const apiBase = import.meta.env.VITE_API || 'http://localhost:8000';

  // Sync prop -> state
  useEffect(()=>{ setCurrent(media); }, [media]);

  // Poll status & transcript
  useEffect(()=>{
    if(!current?.id) return; // still run effect (no-op) to keep hook order stable
    setPolling(true);
    const fetchOnce = async ()=>{
      try {
        const res = await axios.get(`${apiBase}/media/${current.id}`);
        setCurrent(res.data);
        const tr = await axios.get(`${apiBase}/media/${current.id}/transcript`);
        const segs = tr.data.segments || [];
        if(segs.length){
          setSegments(segs);
          if(progress !== 100) setProgress(100);
        }
        // Capture any provided raw transcript text (different backends might send 'transcript' or 'text')
        if(tr.data.transcript || tr.data.text){
          setFullText(tr.data.transcript || tr.data.text || '');
        } else if(segs.length && !fullText){
          setFullText(segs.map(s=>s.text).join(' '));
        }
        if(res.data.status === 'transcribed') setProgress(100);
      } catch {/* swallow polling errors */}
    };
    // Initial immediate fetch for quicker UI response
    fetchOnce();
    const id = setInterval(fetchOnce, 4000);
    return ()=>{ clearInterval(id); setPolling(false);} ;
    // We intentionally do NOT include progress/fullText in deps to avoid recreating interval.
  }, [current?.id, apiBase]);

  const filtered = useMemo(()=>{
    if(!query.trim()) return segments;
    const ql = query.toLowerCase();
    return segments.map(s => ({...s, match: s.text.toLowerCase().includes(ql)}));
  }, [segments, query]);

  // Auto scroll to first match
  useEffect(()=>{
    if(!query.trim()) return;
    const firstIdx = filtered.findIndex(s=>s.match);
    if(firstIdx>=0 && listRef.current){
      const el = listRef.current.querySelector(`[data-idx='${firstIdx}']`);
      if(el) el.scrollIntoView({behavior:'smooth', block:'center'});
    }
  }, [query, filtered]);

  const exportPdf = async ()=>{
    if(!current?.id) return;
    try {
      const res = await axios.get(`${apiBase}/media/${current.id}/export/pdf`, {responseType:'blob'});
      const url = window.URL.createObjectURL(res.data instanceof Blob ? res.data : new Blob([res.data]));
      const a = document.createElement('a'); a.href = url; a.download = `transcript_${current.id}.pdf`; a.click();
    } catch(e){ alert('Export failed'); }
  };
  const exportTxt = async ()=>{
    if(!current?.id) return; const res = await axios.get(`${apiBase}/media/${current.id}/export/txt`, {responseType:'blob'}); const url = URL.createObjectURL(res.data); const a=document.createElement('a'); a.href=url; a.download=`transcript_${current.id}.txt`; a.click();
  };
  const exportSrt = async ()=>{
    if(!current?.id) return; const res = await axios.get(`${apiBase}/media/${current.id}/export/srt`, {responseType:'blob'}); const url = URL.createObjectURL(res.data); const a=document.createElement('a'); a.href=url; a.download=`transcript_${current.id}.srt`; a.click();
  };

  // Render placeholder when no media yet
  if(!current){
    return (
      <Card>
        <CardHeader><CardTitle>Transcript</CardTitle></CardHeader>
        <CardContent><p className="text-sm text-gray-500">No media selected.</p></CardContent>
      </Card>
    );
  }

  const displayStatus = segments.length>0 || progress === 100 ? 'transcribed' : 'processing';
  return (
    <Card className="animate-scale-in">
      <CardHeader className="animate-fade-in">
        <CardTitle>Transcript {current?.language && <span className="ml-2 text-xs align-middle opacity-70">({current.language})</span>}</CardTitle>
        <div className="flex items-center gap-2">
          <span className="text-xs px-2 py-1 rounded bg-gray-100 dark:bg-gray-700 capitalize">{displayStatus}</span>
          {segments.length > 0 && (
            <div className="flex gap-1">
              <button onClick={exportPdf} className="text-xs px-2 py-1 bg-purple-600 text-white rounded">PDF</button>
              <button onClick={exportTxt} className="text-xs px-2 py-1 bg-purple-600/80 text-white rounded">TXT</button>
              <button onClick={exportSrt} className="text-xs px-2 py-1 bg-purple-600/60 text-white rounded">SRT</button>
            </div>
          )}
        </div>
      </CardHeader>
  <CardContent className="animate-slide-up">
        {segments.length > 0 && (
          <div className="mb-2">
            <input value={query} onChange={e=>setQuery(e.target.value)} placeholder="Search..." className="w-full text-xs px-2 py-1 rounded bg-gray-100 dark:bg-gray-800" />
          </div>
        )}
        {displayStatus !== 'transcribed' && segments.length === 0 && (
          <div className="mb-3 space-y-1">
            <div className="w-full h-2 rounded bg-gray-200 dark:bg-gray-700 overflow-hidden relative">
              <div className="absolute inset-0 animate-pulse bg-gradient-to-r from-blue-400 via-blue-600 to-blue-400"></div>
            </div>
            <p className="text-[10px] text-gray-500">Transcribing...</p>
          </div>
        )}
        {segments.length > 0 ? (
          <div ref={listRef} className="space-y-1 max-h-80 overflow-auto text-[11px] leading-snug">
            {filtered.length ? filtered.map((s,i)=>{
              const total = s.start || 0; const mm = Math.floor(total/60).toString().padStart(2,'0'); const ss = Math.floor(total%60).toString().padStart(2,'0');
              return (
                <div key={i} data-idx={i} className={`cursor-pointer px-1 rounded ${s.match? 'bg-yellow-200 dark:bg-yellow-600/40':''} hover:bg-blue-50 dark:hover:bg-gray-700/40`} onClick={()=>{ if(videoRef.current){ videoRef.current.currentTime = s.start; } }}>
                  <span className="text-gray-500 mr-2">[{mm}:{ss}]</span>
                  {s.text}
                </div>
              );
            }) : <pre className="whitespace-pre-wrap">{fullText || 'No transcript text available.'}</pre>}
          </div>
        ) : (
          <p className="text-sm italic">
            {current.status === 'transcribed' ? 'Transcript not yet available. Retrying...' : 'Processing transcription...'}
          </p>
        )}
      </CardContent>
    </Card>
  );
}
