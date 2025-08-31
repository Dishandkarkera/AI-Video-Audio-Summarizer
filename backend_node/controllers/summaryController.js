import { memory } from './uploadController.js';
import { summarize } from '../services/geminiService.js';
import { getSession, setSummary } from '../db.js';

export async function summarizeTranscript(req, res, next){
  try {
    const { fileId, transcript } = req.body;
  const text = transcript || memory.transcripts[fileId];
  if(!text) return res.status(404).json({error:'Transcript not found'});
  const out = await summarize(text);
  setSummary(fileId, JSON.stringify(out));
  res.json(out);
  } catch(e){ next(e); }
}
