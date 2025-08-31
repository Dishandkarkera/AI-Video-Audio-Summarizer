import { useCallback, useEffect, useRef, useState } from 'react';

// Simple Web Speech API hook (Chrome/Edge). Fallback: none.
export function useSpeechInput({ lang = 'en-US', interim = true } = {}) {
  const recognitionRef = useRef(null);
  const [supported, setSupported] = useState(false);
  const [listening, setListening] = useState(false);
  const [error, setError] = useState(null);

  useEffect(()=>{
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if(!SpeechRecognition){ setSupported(false); return; }
    setSupported(true);
    const rec = new SpeechRecognition();
    rec.lang = lang;
    rec.continuous = false; // single utterance
    rec.interimResults = interim;
    rec.maxAlternatives = 1;

    rec.onstart = ()=>{ setListening(true); setError(null); };
    rec.onend = ()=>{ setListening(false); };
    rec.onerror = (e)=>{ setError(e.error || 'speech-error'); };

    recognitionRef.current = rec;
    return ()=>{ rec.onstart=null; rec.onend=null; rec.onerror=null; rec.onresult=null; try{ rec.stop(); }catch{} };
  }, [lang, interim]);

  const start = useCallback((onResult)=>{
    if(!recognitionRef.current) return;
    recognitionRef.current.onresult = (ev)=>{
      let full='';
      for(const res of ev.results){
        full += res[0].transcript;
      }
      onResult && onResult(full.trim());
    };
    try { recognitionRef.current.start(); } catch(e){ /* already started */ }
  },[]);

  const stop = useCallback(()=>{ try{ recognitionRef.current && recognitionRef.current.stop(); }catch{} },[]);

  return { supported, listening, error, start, stop };
}
