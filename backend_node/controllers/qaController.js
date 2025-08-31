import { memory } from './uploadController.js';
import { qa } from '../services/geminiService.js';
import { logQA } from '../db.js';

export async function askQuestion(req, res, next){
  try {
    const { fileId, question } = req.body;
    const transcript = memory.transcripts[fileId];
    if(!transcript) return res.status(404).json({error:'Transcript not found'});
  const answer = await qa(transcript, question);
  logQA(fileId, question, answer);
  res.json({ answer });
  } catch(e){ next(e); }
}
