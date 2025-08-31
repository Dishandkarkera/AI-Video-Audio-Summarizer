import React, { useState, useRef, useEffect } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from './ui/Card';

// Helper to pick the best supported mime type for MediaRecorder
function pickAudioMime(){
  const preferred = [
    'audio/webm;codecs=opus',
    'audio/webm;codecs=vorbis',
    'audio/webm',
    'audio/ogg;codecs=opus'
  ];
  for(const t of preferred){
    if(window.MediaRecorder && MediaRecorder.isTypeSupported && MediaRecorder.isTypeSupported(t)) return t;
  }
  return undefined; // let browser choose
}

export default function LiveCapture(){
  const [recording, setRecording] = useState(false);
  const [socketState, setSocketState] = useState('idle');
  const [partial, setPartial] = useState('');
  const [segments, setSegments] = useState([]);
  const wsRef = useRef(null);
  const mediaRecRef = useRef(null);

  const apiBase = import.meta.env.VITE_API || 'http://localhost:8000';
  // Backend route is versioned: /v1/ws/capture
  const wsUrl = apiBase.replace(/^http/i,'ws') + '/v1/ws/capture';

  useEffect(()=>{
    return ()=>{
      if(mediaRecRef.current && mediaRecRef.current.state === 'recording') mediaRecRef.current.stop();
      if(wsRef.current) try{ wsRef.current.close(); }catch{}
    };
  },[]);

  const start = async ()=>{
    if(recording) return;
    try {
      // Explicit audio constraints (mono). Remove echoCancellation/noiseSuppression if they cause artifacts.
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          channelCount: 1,
          noiseSuppression: true,
          echoCancellation: true,
          sampleRate: 48000
        }
      });
      const ws = new WebSocket(wsUrl);
      ws.binaryType = 'arraybuffer';
      wsRef.current = ws;
      ws.onopen = ()=>{ 
        setSocketState('open');
        // Send start control message required by backend
        ws.send(JSON.stringify({ type: 'start', buffer_seconds: 3.0 }));
      };
      ws.onclose = ()=>{ setSocketState('closed'); };
      ws.onerror = (e)=>{ console.error('WS error', e); setSocketState('error'); };
      ws.onmessage = (ev)=>{
        try {
          const msg = JSON.parse(ev.data);
          if(msg.type==='partial'){
            setPartial(msg.text || '');
            if(Array.isArray(msg.segments)) setSegments(prev=>{ 
              const merged = [...prev];
              msg.segments.forEach(s=>{
                if(!merged.find(m=>Math.abs((m.start||0) - (s.start||0)) < 0.25)) merged.push(s);
              });
              return merged.sort((a,b)=>(a.start||0)-(b.start||0));
            });
          } else if(msg.type==='final'){
            setPartial(msg.text || '');
          } else if(msg.type==='error'){
            console.warn('Backend error:', msg.message);
          }
        } catch(err){
          // Non-json messages
        }
      };

      const mimeType = pickAudioMime();
      const rec = new MediaRecorder(stream, mimeType? {mimeType}:{ });
      mediaRecRef.current = rec;
      rec.ondataavailable = e=>{
        if(e.data.size && ws.readyState===1){
          e.data.arrayBuffer().then(buf=>{
            ws.send(buf); // arraybuffer direct
          });
        }
      };
      rec.onstop = ()=>{
        if(ws.readyState===1){
          ws.send(JSON.stringify({ type: 'stop' }));
        }
      };
      // Smaller timeslice for lower latency
      rec.start(750); // ~0.75s chunks
      setRecording(true);
    } catch(e){
      console.error(e);
      alert('Mic error: '+ e.message);
    }
  };

  const stop = ()=>{
    if(mediaRecRef.current && mediaRecRef.current.state==='recording'){ mediaRecRef.current.stop(); }
    if(wsRef.current && wsRef.current.readyState===1){ try{ wsRef.current.send(JSON.stringify({type:'stop'})); }catch{} }
    setRecording(false);
  };

  return (
    <Card className="h-96 flex flex-col">
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle>Live Capture</CardTitle>
          <button onClick={recording? stop: start} className={`text-xs px-2 py-1 rounded ${recording? 'bg-red-600':'bg-green-600'} text-white`}>{recording? 'Stop':'Start'}</button>
        </div>
      </CardHeader>
      <CardContent className="flex-1 overflow-auto text-[11px] space-y-2">
        <p className="text-gray-500">State: {socketState}</p>
        <div className="whitespace-pre-wrap text-xs bg-gray-50 dark:bg-gray-800 p-2 rounded min-h-[120px]">
          {partial || '...'}
        </div>
        {segments.length>0 && <div className="space-y-1">
          <p className="font-medium text-xs">Recent Segments</p>
          {segments.slice(-8).map((s,i)=>{ const t = s.start || 0; const mm = Math.floor(t/60).toString().padStart(2,'0'); const ss = Math.floor(t%60).toString().padStart(2,'0'); return (<div key={i} className="text-[10px]"><span className="text-gray-500 mr-1">[{mm}:{ss}]</span>{s.text}</div>); })}
        </div>}
      </CardContent>
    </Card>
  )
}