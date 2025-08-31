import React, { useEffect, useState } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from './ui/Card';

export default function MediaPlayer({ media }){
  const [url, setUrl] = useState(null);
  const apiBase = import.meta.env.VITE_API || 'http://localhost:8000';

  useEffect(()=>{
    if(media?.id){
      setUrl(`${apiBase.replace(/\/$/, '')}/media/${media.id}/raw`);
    } else {
      setUrl(null);
    }
  }, [media, apiBase]);

  const ext = media?.filename?.split('.').pop()?.toLowerCase();
  const isAudio = ext && ['mp3','wav','m4a','aac','ogg','webm'].includes(ext);
  const isVideo = ext && ['mp4','mov','mkv','webm'].includes(ext);

  return (
    <Card>
      <CardHeader>
        <CardTitle>Player</CardTitle>
      </CardHeader>
      <CardContent>
        {!media && <p className="text-xs text-gray-500">No media selected.</p>}
        {media && !url && <p className="text-xs text-gray-500">Preparing...</p>}
        {media && url && (
          isVideo ? (
            <video key={url} src={url} className="w-full rounded" controls preload="metadata" />
          ) : isAudio ? (
            <audio key={url} src={url} className="w-full" controls preload="metadata" />
          ) : (
            <p className="text-xs text-gray-500">Unknown media type.</p>
          )
        )}
      </CardContent>
    </Card>
  );
}
