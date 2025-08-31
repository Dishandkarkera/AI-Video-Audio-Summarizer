import React, { useState } from 'react';
import axios from 'axios';
import { Card, CardHeader, CardTitle, CardContent } from './ui/Card';
import { Mic, Send } from 'lucide-react';
import { useSpeechInput } from '../hooks/useSpeechInput';

export default function ChatPanel({media}){
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [mode, setMode] = useState('agent'); // agent | gpt | simple
  const [usage, setUsage] = useState(null);
  const { supported: speechSupported, listening, error: speechError, start: startSpeech, stop: stopSpeech } = useSpeechInput({ lang: 'en-US', interim: true });

  const handleMicClick = () => {
    if(!speechSupported) return;
    if(listening){
      stopSpeech();
    } else {
      startSpeech((text)=>{
        setInput(text);
      });
    }
  };

  const send = async () => {
    if(!media || !input.trim()) return;
    const userMsg = { role: 'user', content: input };
    setMessages(m => [...m, userMsg]);
    setInput('');
    setLoading(true);
    const apiBase = import.meta.env.VITE_API || 'http://localhost:8000';
    try {
      // Unified endpoint expects path /media/{media_id}/chat and payload with key 'question'
      const url = `${apiBase.replace(/\/$/, '')}/media/${media.id}/chat`;
  const res = await axios.post(url, { question: userMsg.content, mode });
  setMessages(m => [...m, { role: 'assistant', content: res.data.answer, refs: res.data.references || [] }]);
  if(res.data.usage) setUsage(res.data.usage);
    } catch (err) {
      // Provide clearer error message and keep references empty
      const msg = err?.response?.status === 404
        ? 'Error: chat endpoint not found (check backend running on correct port)'
        : 'Error: ' + (err.message || 'request failed');
      setMessages(m => [...m, { role: 'assistant', content: msg, refs: [] }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    // Remove fixed height overflow issue: allow flexible height while constraining max height for usability
  <Card className="flex flex-col relative animate-scale-in h-[26rem] sm:h-[28rem] lg:h-[34rem] overflow-hidden">
      <CardHeader className="animate-fade-in">
        <CardTitle>Chat</CardTitle>
      </CardHeader>
  <CardContent className="flex-1 flex flex-col min-h-0 animate-slide-up overflow-hidden">
        {/* Scrollable messages area */}
        <div className="flex-1 min-h-0 overflow-y-auto space-y-2 text-xs mb-2 pr-1 custom-scrollbar">
          {messages.map((m,i)=>(
            <div key={i} className={m.role==='user'? 'text-right space-y-1': 'space-y-1'}>
              <span className={"inline-block px-2 py-1 rounded max-w-full break-words "+(m.role==='user'? 'bg-blue-600 text-white':'bg-gray-200 dark:bg-gray-700')}>{m.content}</span>
              {m.refs && m.refs.length>0 && (
                <div className="flex flex-wrap gap-1 justify-start text-[10px]">{m.refs.map((r,ri)=>{
                  const t = r.start || 0; const mm = Math.floor(t/60).toString().padStart(2,'0'); const ss = Math.floor(t%60).toString().padStart(2,'0');
                  return (<span key={ri} className="px-1.5 py-0.5 bg-purple-100 dark:bg-purple-900/40 text-purple-700 dark:text-purple-300 rounded">[{mm}:{ss}]</span>)
                })}</div>
              )}
            </div>
          ))}
          {!messages.length && <p className="text-gray-500">Ask a question about the transcript.</p>}
        </div>
        {usage && (
          <div className="text-[10px] text-gray-500 mb-1 shrink-0">
            tokens: {usage.prompt_tokens}+{usage.completion_tokens}={usage.total_tokens}
          </div>
        )}
        {/* Fixed input row */}
        <div className="flex flex-wrap md:flex-nowrap gap-2 items-center shrink-0 pt-1 border-t border-gray-200 dark:border-gray-700 w-full">
          <button type="button" onClick={handleMicClick} disabled={!speechSupported} className={`p-2 rounded ${listening? 'bg-red-600 text-white':'bg-gray-200 dark:bg-gray-700'} disabled:opacity-40`} title={speechSupported? (listening? 'Stop listening':'Start voice input'):'Speech not supported'}>
            <Mic className="w-4 h-4" />
          </button>
          <input value={input} onChange={e=>setInput(e.target.value)} onKeyDown={e=>e.key==='Enter' && send()} placeholder="Ask..." className="flex-1 min-w-[8rem] px-2 py-2 rounded bg-gray-100 dark:bg-gray-700 text-xs" />
          <select value={mode} onChange={e=>setMode(e.target.value)} className="text-xs bg-gray-100 dark:bg-gray-700 px-2 py-2 rounded shrink-0">
            <option value="agent">Agent</option>
            <option value="gpt">GPT</option>
            <option value="simple">Simple</option>
          </select>
          <button type="button" onClick={async ()=>{ if(!media) return; await axios.delete(`${(import.meta.env.VITE_API||'http://localhost:8000').replace(/\/$/,'')}/media/${media.id}/chat/history`); setMessages([]); }} className="px-2 py-2 rounded bg-gray-300 dark:bg-gray-600 text-xs shrink-0">Clear</button>
          <button onClick={send} disabled={!media || loading} className="px-3 py-2 rounded bg-green-600 text-white disabled:opacity-50 flex items-center gap-1 text-xs shrink-0"><Send className="w-3 h-3"/>Send</button>
        </div>
        {speechError && <div className="text-[10px] text-red-500 mt-1">Speech error: {speechError}</div>}
      </CardContent>
    </Card>
  )
}
