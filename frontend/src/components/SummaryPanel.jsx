import React, { useState } from 'react';
import axios from 'axios';
import { Card, CardHeader, CardTitle, CardContent } from './ui/Card';
import { Tabs } from './ui/Tabs';
import { Check } from 'lucide-react';

export default function SummaryPanel({media, summary, setSummary}){
  const [loading, setLoading] = useState(false);
  const [tab, setTab] = useState('Summary');
  const [progress, setProgress] = useState(0); // 0-100 while generating

  const generate = async ()=>{
    if(!media) return;
    setLoading(true);
    setProgress(0);
    try {
      const apiBase = import.meta.env.VITE_API || 'http://localhost:5000';
      // Poll GET summary endpoint; backend returns 202 while processing
      const maxAttempts = 40; // ~2 minutes
      for(let attempt=0; attempt<maxAttempts; attempt++){ // up to ~2 minutes @3s
        const res = await axios.get(`${apiBase}/media/${media.id}/summary`, {
          validateStatus: s => s === 200 || s === 202
        });
        if(res.status === 202){
          // still processing
          setProgress(Math.min(99, Math.round(((attempt+1)/maxAttempts)*100)));
          await new Promise(r=>setTimeout(r, 3000));
          continue;
        }
        setSummary(res.data);
        setProgress(100);
        break;
      }
    } catch(e){
      alert('Summary failed: '+e.message);
    } finally { setLoading(false); }
  }

  return (
    <Card className="animate-scale-in">
      <CardHeader className="animate-fade-in relative justify-center">
        <CardTitle className="text-center mx-auto">AI Summary</CardTitle>
        <button disabled={!media || loading} onClick={generate} className="absolute right-4 top-1/2 -translate-y-1/2 text-xs px-2 py-1 rounded bg-blue-600 text-white disabled:opacity-50">{loading? '...':'Generate'}</button>
      </CardHeader>
  <CardContent className="animate-slide-up">
        {!summary && !loading && <p className="text-sm text-gray-500">No summary yet.</p>}
        {loading && (
          <div className="space-y-2">
            <p className="text-sm">Generating...</p>
            <div className="w-full h-2 rounded bg-gray-200 dark:bg-gray-700 overflow-hidden">
              <div className="h-full bg-blue-600 transition-all" style={{width: progress+'%'}}></div>
            </div>
            <p className="text-[10px] text-gray-500">{progress}%</p>
          </div>
        )}
        {summary && (
          (()=>{
            // ---- Normalization / cleanup ----
            const cleanText = (val)=>{
              if(!val || typeof val !== 'string') return val;
              return val.replace(/```json/gi,'').replace(/```/g,'').trim();
            };
            const deepMerge = (base, extra)=>{
              if(extra && typeof extra === 'object'){
                for(const k of Object.keys(extra)){
                  if(base[k] === undefined) base[k] = extra[k];
                }
              }
              return base;
            };
            let normalized = {...summary};
            // Attempt to parse embedded JSON inside summary_short if it looks like a JSON object
            try {
              if(typeof normalized.summary_short === 'string'){
                const stripped = cleanText(normalized.summary_short);
                if(/\{\s*"summary_short"/i.test(stripped)){
                  const parsed = JSON.parse(stripped);
                  normalized = deepMerge(parsed, normalized);
                } else {
                  normalized.summary_short = stripped;
                }
              }
              if(typeof normalized.summary_detailed === 'string'){
                normalized.summary_detailed = cleanText(normalized.summary_detailed);
              }
            } catch{/* ignore parse errors */}
            // Field aliases
            normalized.highlights = normalized.highlights || normalized.key_highlights || [];
            normalized.action_points = normalized.action_points || normalized.actionPoints || [];
            const highlightsRaw = Array.isArray(normalized.highlights) ? normalized.highlights : [];
            // Clean highlight entries: strip leading bullets/ticks and trim, ensure string
            const cleanHighlight = (h)=>{
              if(h == null) return '';
              let txt = typeof h === 'string' ? h : (h.text || JSON.stringify(h));
              txt = txt.replace(/^\s*[\-•*✔✅☑️\u2713\u2705\u2611]+\s*/,'').trim();
              return txt;
            };
            const highlights = highlightsRaw.map(cleanHighlight).filter(Boolean);
            const actionPoints = Array.isArray(normalized.action_points) ? normalized.action_points : [];
            const shortTxt = normalized.summary_short || normalized.short || '';
            const detailedTxt = normalized.summary_detailed || normalized.detailed || '';
            return (
              <div className="space-y-4">
                <Tabs tabs={['Summary','Sentiment','Action Points']} current={tab} onChange={setTab} />
                {tab==='Summary' && (
                  <div className="space-y-2 text-xs">
                    <div>
                      <p className="font-semibold mb-1">Short</p>
                      <p className="text-[11px] leading-relaxed whitespace-pre-wrap">{shortTxt || '—'}</p>
                    </div>
                    <div>
                      <p className="font-semibold mb-1">Detailed</p>
                      {detailedTxt
                        ? detailedTxt.split(/\n+/).map((p,i)=>p.trim() && <p key={i} className="text-[11px] leading-relaxed mb-2">{p.trim()}</p>)
                        : <p className="text-[11px] italic text-gray-500">—</p>}
                    </div>
                    <div className="space-y-1">
                      <p className="font-medium">Highlights</p>
                      {highlights.length ? (
                        <ul className="space-y-1">
                          {highlights.map((h,i)=>(
                            <li key={i} className="flex gap-2">
                              <span className="inline-flex items-center justify-center w-5 h-5 rounded-full bg-green-100 dark:bg-green-900 text-green-600 dark:text-green-300 shrink-0">
                                <Check className="w-3.5 h-3.5" />
                              </span>
                              <p className="text-[11px] leading-relaxed whitespace-pre-wrap m-0 flex-1">{h}</p>
                            </li>
                          ))}
                        </ul>
                      ) : <p className="text-[11px] italic text-gray-500">No highlights.</p>}
                    </div>
                  </div>
                )}
                {tab==='Sentiment' && (
                  <div className="text-xs">
                    <p><strong>Overall Sentiment:</strong> <span className="uppercase tracking-wide">{normalized.sentiment || 'unknown'}</span></p>
                    <p className="mt-2 text-[11px] text-gray-600 dark:text-gray-400">Sentiment inferred from tone and wording patterns in transcript.</p>
                  </div>
                )}
                {tab==='Action Points' && (
                  actionPoints.length ? (
                    <ul className="space-y-1 text-xs list-disc ml-5">
                      {actionPoints.map((a,i)=><li key={i}>{a}</li>)}
                    </ul>
                  ) : <p className="text-[11px] italic text-gray-500">No action points.</p>
                )}
              </div>
            );
          })()
        )}
      </CardContent>
    </Card>
  )}
