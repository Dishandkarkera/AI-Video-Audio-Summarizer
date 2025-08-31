import React, { useState } from 'react';
import axios from 'axios';

export default function UploadPanel(){
  // Using any typings fallback due to temporary shim environment
  const [file, setFile] = useState(null as any);
  const [mediaId, setMediaId] = useState(null as any);
  const api = (import.meta as any).env.VITE_API || '';

  const handleUpload = async () => {
    if(!file) return;
    const form = new FormData();
    form.append('file', file);
    try {
      const res = await axios.post(`${api}/media/upload`, form, { headers: { 'Content-Type': 'multipart/form-data' }, timeout: 60000 });
      setMediaId(res.data.id);
      alert(`Uploaded! Media ID: ${res.data.id}`);
    } catch(err:any){
      console.error('Upload failed', err);
      alert('Upload failed: ' + (err.response?.data?.detail || err.message || 'Unknown error'));
    }
  };

  return (
    <div className="p-4 border rounded-xl shadow-md space-y-2">
      <h2 className="font-bold text-xl">Upload Audio/Video</h2>
      <input type="file" onChange={e=>setFile(e.target.files?.[0] || null)} />
      <button onClick={handleUpload} className="bg-blue-500 text-white px-4 py-2 rounded mt-2 disabled:opacity-50" disabled={!file}>Upload</button>
      {mediaId && <p className="text-xs text-green-600">Media ID: {mediaId}</p>}
    </div>
  );
}
