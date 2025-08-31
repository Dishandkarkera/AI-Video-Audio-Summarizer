import { useEffect, useRef, useState } from "react";

/**
 * useRealtimeWS - handles websocket + MediaRecorder streaming to backend
 * - wsUrl: ws endpoint (default ws://localhost:8000/v1/ws/capture)
 * - buffer_seconds: how often backend will transcribe (default 4s)
 */
export default function useRealtimeWS({ wsUrl = "ws://localhost:8000/v1/ws/capture", buffer_seconds = 4.0 } = {}) {
  const wsRef = useRef(null);
  const mediaRecorderRef = useRef(null);
  const [status, setStatus] = useState("idle");
  const [captions, setCaptions] = useState([]); // array of {text, segments, final?}
  const [sessionId, setSessionId] = useState(null);

  useEffect(() => {
    return () => {
      if (mediaRecorderRef.current && mediaRecorderRef.current.state !== "inactive") {
        mediaRecorderRef.current.stop();
      }
      if (wsRef.current) wsRef.current.close();
    };
  }, []);

  const connectAndStart = async () => {
    if (!navigator.mediaDevices?.getUserMedia) {
      throw new Error("getUserMedia not supported");
    }
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    const ws = new WebSocket(wsUrl);
    ws.binaryType = "arraybuffer";

    ws.onopen = () => {
      ws.send(JSON.stringify({ type: "start", buffer_seconds }));
    };

    ws.onmessage = (ev) => {
      try {
        const data = JSON.parse(ev.data);
        if (data.type === "started") {
          setSessionId(data.session_id);
          setStatus("recording");
        } else if (data.type === "ack") {
          // ignore
        } else if (data.type === "partial") {
          setCaptions((c) => [...c, { text: data.text, segments: data.segments }]);
        } else if (data.type === "final") {
          setCaptions((c) => [...c, { text: data.text, final: true }]);
          setStatus("idle");
          ws.close();
        } else if (data.type === "error") {
          console.error("WS error:", data.message);
        }
      } catch (err) {
        console.log("WS non-json:", ev.data);
      }
    };

    ws.onerror = (err) => {
      console.error("WS error", err);
    };
    ws.onclose = () => {
      setStatus("idle");
    };

    wsRef.current = ws;

    const options = { mimeType: "audio/webm" };
    const mediaRecorder = new MediaRecorder(stream, options);

    mediaRecorder.ondataavailable = (e) => {
      if (e.data && e.data.size > 0 && wsRef.current && wsRef.current.readyState === 1) {
        e.data.arrayBuffer().then((ab) => wsRef.current.send(ab));
      }
    };

    mediaRecorder.onstop = () => {
      if (wsRef.current && wsRef.current.readyState === 1) {
        wsRef.current.send(JSON.stringify({ type: "stop" }));
      }
      stream.getTracks().forEach((t) => t.stop());
      setStatus("stopping");
    };

    mediaRecorderRef.current = mediaRecorder;
    mediaRecorder.start(1000); // 1s blobs
    setStatus("starting");
    return { ws, mediaRecorder };
  };

  const stop = () => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state === "recording") {
      mediaRecorderRef.current.stop();
      setStatus("stopping");
    }
  };

  return {
    status,
    captions,
    sessionId,
    connectAndStart,
    stop,
    rawWs: wsRef.current
  };
}