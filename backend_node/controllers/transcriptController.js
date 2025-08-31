import { memory } from './uploadController.js';
import { transcribe } from '../services/whisperService.js';
import { getSession, setTranscript, updateSessionStatus } from '../db.js';

export async function transcribeFile(req, res, next){
  try {
    const { fileId } = req.params;
  const meta = memory.files[fileId];
  const session = getSession(fileId);
  if(!meta || !session) return res.status(404).json({error:'File not found'});
  updateSessionStatus(fileId,'transcribing');
  const result = await transcribe(meta.path);
  memory.transcripts[fileId] = result.text;
  setTranscript(fileId, result.text);
  res.json({ fileId, transcript: result.text, status: 'transcribed' });
  } catch(e){ next(e); }
}
