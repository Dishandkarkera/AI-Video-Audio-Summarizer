import { saveUploaded } from '../utils/fileUtils.js';
import { insertSession, getSession } from '../db.js';
const memory = { files: {}, transcripts: {} };
export { memory };

export function uploadFile(req, res, next){
  try {
    const meta = saveUploaded(req.file, process.env.UPLOAD_DIR || './uploads');
    memory.files[meta.id] = meta;
    insertSession({ id: meta.id, original_name: meta.original, stored_name: meta.filename, status: 'uploaded' });
    res.json({ fileId: meta.id, original: meta.original, filename: meta.filename });
  } catch(e){ next(e); }
}
