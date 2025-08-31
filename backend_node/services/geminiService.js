import axios from 'axios';
import { GEMINI_API_KEY, API_BASE } from '../config/geminiConfig.js';

async function callGemini(prompt){
  const body = { contents: [{ parts: [{ text: prompt }]}] };
  const params = { key: GEMINI_API_KEY };
  const { data } = await axios.post(API_BASE, body, { params });
  try {
    return data.candidates[0].content.parts[0].text;
  } catch (e){
    return JSON.stringify(data);
  }
}

export async function summarize(transcript){
  const system = `Return JSON with keys: summary, key_highlights (array), sentiment, action_points (array).`;
  const raw = await callGemini(`${system}\nTranscript:\n${transcript.slice(0,15000)}`);
  let parsed;
  try { parsed = JSON.parse(raw.match(/\{[\s\S]*\}$/m)[0]); } catch { parsed = { summary: raw.slice(0,400), key_highlights: [], sentiment: 'neutral', action_points: [] }; }
  return parsed;
}

export async function qa(transcript, question){
  const prompt = `You answer questions about the transcript. Keep answers grounded and cite approximate timestamps if present.\nTranscript:\n${transcript.slice(0,15000)}\nQuestion: ${question}`;
  return await callGemini(prompt);
}
