import React, { useEffect, useState } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from './ui/Card';
import axios from 'axios';

export default function SummaryPage({mediaId}){
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const apiBase = import.meta.env.VITE_API || 'http://localhost:5000';

  useEffect(()=>{
    if(!mediaId) return;
    setLoading(true);
    axios.get(`${apiBase}/media/${mediaId}/summary`).then(r=>setData(r.data)).finally(()=>setLoading(false));
  }, [mediaId]);

  return (
    <div className="container mx-auto py-8 space-y-6">
      <h1 className="text-2xl font-semibold">Project Summary</h1>
      {loading && <p>Loading...</p>}
      {data && (
        (()=>{
          // Normalize keys
          const s = data.summary || data; // backend may already return flat summary
          const shortTxt = s.summary_short || s.short || '';
          const detailedTxt = s.summary_detailed || s.detailed || '';
          const highlights = s.highlights || s.key_highlights || [];
          const sentiment = s.sentiment;
          const actionPoints = s.action_points || s.actionPoints || [];
          const topicsRaw = data.topics_raw;
          const actionRaw = data.action_items_raw;
          return (
            <div className="grid md:grid-cols-2 gap-6">
              <Card className="md:col-span-2">
                <CardHeader><CardTitle>Executive Summary</CardTitle></CardHeader>
                <CardContent className="space-y-4 text-sm">
                  {shortTxt && <p className="font-medium leading-relaxed">{shortTxt}</p>}
                  {detailedTxt && detailedTxt.split(/\n+/).map((p,i)=> p.trim() && <p key={i} className="text-[13px] leading-relaxed opacity-90">{p.trim()}</p>)}
                  {sentiment && <p className="text-xs"><strong>Sentiment:</strong> <span className="uppercase tracking-wide">{sentiment}</span></p>}
                </CardContent>
              </Card>
              <Card>
                <CardHeader><CardTitle>Highlights</CardTitle></CardHeader>
                <CardContent className="text-xs">
                  {highlights.length ? (
                    <ul className="list-disc ml-5 space-y-1">
                      {highlights.map((h,i)=><li key={i}>{h}</li>)}
                    </ul>
                  ) : <p className="italic text-gray-500">No highlights.</p>}
                </CardContent>
              </Card>
              <Card>
                <CardHeader><CardTitle>Topics</CardTitle></CardHeader>
                <CardContent className="text-xs whitespace-pre-wrap">{topicsRaw || '—'}</CardContent>
              </Card>
              <Card className="md:col-span-2">
                <CardHeader><CardTitle>Action Items</CardTitle></CardHeader>
                <CardContent className="text-xs">
                  {actionPoints.length ? (
                    <ul className="list-decimal ml-5 space-y-1">
                      {actionPoints.map((a,i)=><li key={i}>{a}</li>)}
                    </ul>
                  ) : (actionRaw ? <pre className="whitespace-pre-wrap text-[11px]">{actionRaw}</pre> : <p className="italic text-gray-500">No action points.</p>)}
                </CardContent>
              </Card>
            </div>
          );
        })()
      )}
    </div>
  )
}