import React, { useState } from 'react';
import axios from 'axios';
import { Card, CardHeader, CardTitle, CardContent } from './ui/Card';

export default function UploadArea({onUploaded, onSummarize}){
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [drag, setDrag] = useState(false);
  const [fileMeta, setFileMeta] = useState(null);
  const [recording, setRecording] = useState(false);
  const [mediaRecorder, setMediaRecorder] = useState(null);

  // Prefer relative path (proxy) if no explicit API configured
  const apiBase = import.meta.env.VITE_API || '';
  const handleFiles = async (files) => {
    const file = files[0];
    if(!file) return;
    setFileMeta({name: file.name, size: file.size});
    const form = new FormData();
    form.append('file', file);
    setUploading(true);
    try {
  console.log('Uploading to base', apiBase, 'file', file.name, file.size);
      // Try FastAPI path first, fallback to Node.js path
      let res;
      try {
        res = await axios.post(`${apiBase}/media/upload`, form, {
          headers: { 'Content-Type': 'multipart/form-data' },
          timeout: 60000,
          onUploadProgress: (e)=>{
            if(e.total) setProgress(Math.round((e.loaded/e.total)*100));
          }
        });
      } catch(err){
        console.error('Primary /media/upload failed', err?.response?.status, err?.message);
        if(err?.response?.status === 404) {
          // Optional legacy Node server path
          try {
            res = await axios.post(`${apiBase}/api/upload`, form, {
              headers: { 'Content-Type': 'multipart/form-data' },
              timeout: 60000,
              onUploadProgress: (e)=>{
                if(e.total) setProgress(Math.round((e.loaded/e.total)*100));
              }
            });
          } catch(e2){
            throw e2; // rethrow secondary error
          }
        } else {
          throw err;
        }
      }
      const d = res.data || {};
      const normalized = {
        id: d.id || d.fileId || d.media_id || null,
        filename: d.filename || d.original || 'unknown',
        original_name: d.original_name || d.original || d.filename || 'unknown',
        status: d.status || (typeof d.segments === 'number' ? (d.segments>0? 'done':'processing') : 'uploaded'),
        segments: d.segments || 0,
        language: d.language || null,
      };
      onUploaded(normalized);
    } catch (e) {
      console.error('Upload error object:', e);
      const detail = e?.response?.data?.detail || e?.message || 'Unknown error';
      alert('Upload failed: ' + detail);
    } finally {
      setUploading(false);
      setProgress(0);
    }
  }

  return (
    <Card className="animate-scale-in">
      <CardHeader className="animate-fade-in">
        <CardTitle className="relative inline-block">
          <span className="pr-3">Upload & Record</span>
          <span className="absolute inset-y-0 right-0 w-px bg-gradient-to-b from-transparent via-blue-400 to-transparent animate-pulse-soft" />
        </CardTitle>
      </CardHeader>
      <CardContent className="animate-slide-up">
        <div
          onDragOver={e=>{e.preventDefault(); setDrag(true);} }
          onDragLeave={e=>{e.preventDefault(); setDrag(false);} }
          onDrop={e=>{e.preventDefault(); setDrag(false); handleFiles(e.dataTransfer.files);} }
          className={`border-2 border-dashed rounded p-6 text-center transition ${drag? 'border-blue-500 bg-blue-50 dark:bg-blue-900/30':'border-gray-300 dark:border-gray-600'}`}
        >
          <input id="uploadInput" type="file" className="hidden" onChange={e=>handleFiles(e.target.files)} />
          <p className="mb-4">Drag & drop or <label htmlFor="uploadInput" className="underline cursor-pointer">browse</label> a file.<br/>Or record live audio.</p>
          {uploading && <div className="w-full bg-gray-200 dark:bg-gray-700 rounded h-2 overflow-hidden"><div className="bg-blue-500 h-full transition-all" style={{width: progress+'%'}}></div></div>}
        </div>
        {fileMeta && (
          <div className="mt-4 text-xs flex items-center justify-between bg-gray-50 dark:bg-gray-700/50 px-3 py-2 rounded">
            <span className="truncate">{fileMeta.name}</span>
            <span>{(fileMeta.size/1024/1024).toFixed(2)} MB</span>
          </div>
        )}
        <div className="mt-4 flex flex-wrap gap-2 text-xs">
          <button disabled={uploading} onClick={()=>document.getElementById('uploadInput').click()} className="px-3 py-1 rounded bg-gray-200 dark:bg-gray-700 hover:shadow transition-shadow">📂 Upload Another</button>
          <button disabled={!fileMeta} onClick={onSummarize} className="px-3 py-1 rounded bg-blue-600 text-white disabled:opacity-50 hover:bg-blue-500 transition-colors shadow-sm">⚡ Summarize Now</button>
          <button onClick={async ()=>{
            if(recording){ mediaRecorder.stop(); return; }
            try {
              const stream = await navigator.mediaDevices.getUserMedia({audio:true});
              const mr = new MediaRecorder(stream);
              const chunks = [];
              mr.ondataavailable = e=>chunks.push(e.data);
              mr.onstop = ()=>{
                const blob = new Blob(chunks, {type:'audio/webm'});
                const file = new File([blob], 'recording.webm');
                handleFiles([file]);
                stream.getTracks().forEach(t=>t.stop());
                setRecording(false);
              };
              mr.start();
              setMediaRecorder(mr);
              setRecording(true);
            } catch(e){ alert('Mic blocked'); }
          }} className={`px-3 py-1 rounded ${recording? 'bg-red-600 text-white':'bg-green-600 text-white'}`}>{recording? '⏹ Stop':'🎤 Record'}</button>
        </div>
      </CardContent>
    </Card>
  )
}
