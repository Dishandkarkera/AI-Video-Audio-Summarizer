import React, { useState } from 'react';
import axios from 'axios';

export default function ChatQnA({ transcriptId }: any){
  const [question, setQuestion] = useState('');
  const [chat, setChat] = useState([] as any);
  // Expect backend on 8000 unless overridden
  const apiBase = (import.meta as any).env.VITE_API || 'http://localhost:8000';

  const askQuestion = async () => {
    if(!question.trim() || !transcriptId) return;
    try {
      const url = `${apiBase.replace(/\/$/, '')}/media/${transcriptId}/chat`;
      const res = await axios.post(url, { question });
      setChat([...chat, { q: question, a: res.data.answer, refs: res.data.references || [] }]);
    } catch (err:any) {
      const msg = err?.response?.status === 404 ? 'Endpoint not found (check /media/{id}/chat).' : err.message;
      setChat([...chat, { q: question, a: 'Error: ' + msg, refs: [] }]);
    } finally {
      setQuestion('');
    }
  };

  return (
    <div className="p-4 border rounded-xl mt-4">
      <h2 className="font-bold">Ask Questions</h2>
      <input className="border p-2 w-full" value={question} onChange={e=>setQuestion(e.target.value)} placeholder="Ask about the transcript..." />
      <button onClick={askQuestion} className="bg-green-500 text-white px-4 py-2 mt-2 rounded">Ask</button>
      <div className="mt-4 space-y-2">
        {chat.map((c,idx)=>(
          <div key={idx} className="p-2 border rounded">
            <p className="font-semibold">Q: {c.q}</p>
            <p>A: {c.a}</p>
            {c.refs.map((r:any,i:any)=>(
              <span key={i} className="text-xs bg-gray-200 px-2 py-1 rounded">{(r.start||0).toFixed(2)}s</span>
            ))}
          </div>
        ))}
      </div>
    </div>
  );
}
