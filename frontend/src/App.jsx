import React, { useState, useEffect } from 'react';
import UploadArea from './components/UploadArea';
import TranscriptViewer from './components/TranscriptViewer';
import SummaryPanel from './components/SummaryPanel';
import ChatPanel from './components/ChatPanel';
import MediaPlayer from './components/MediaPlayer';
import { TranscriptProvider, useTranscript } from './store/TranscriptStore';
import { Navbar } from './components/ui/Navbar';
import { Footer } from './components/ui/Footer';

function AppInner(){
  const [media, setMedia] = useState(null);
  const [summary, setSummary] = useState(null);
  const [dark, setDark] = useState(false);
  const apiBase = import.meta.env.VITE_API || 'http://localhost:5000';

  const triggerSummarize = async ()=>{
    if(!media) return;
    try {
      const res = await fetch(`${apiBase}/media/summarize`, {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({media_id: media.id})});
      if(!res.ok) throw new Error('Failed');
      const data = await res.json();
      setSummary(data);
    } catch(e){ console.error(e); }
  };

  useEffect(()=>{
    if(dark){
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
  }, [dark]);

  return (
    <div className="min-h-screen flex flex-col">
  <Navbar dark={dark} onToggleDark={()=>setDark(d=>!d)} />
      <main className="flex-1 container mx-auto px-4 py-6 grid gap-6 lg:grid-cols-3">
        <section className="space-y-6 lg:col-span-2">
          <UploadArea onUploaded={setMedia} onSummarize={triggerSummarize} />
          <div className="grid md:grid-cols-2 gap-6">
            <TranscriptViewer media={media} />
            <div className="space-y-6">
              <MediaPlayer media={media} />
            </div>
          </div>
        </section>
        <section className="space-y-6">
          <SummaryPanel media={media} summary={summary} setSummary={setSummary} />
          <ChatPanel media={media} />
        </section>
      </main>
      <Footer />
    </div>
  );
}

export default function App(){
  return (
    <TranscriptProvider>
      <AppInner />
    </TranscriptProvider>
  );
}
