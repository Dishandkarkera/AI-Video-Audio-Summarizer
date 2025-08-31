import fs from 'fs';
import path from 'path';
import { v4 as uuid } from 'uuid';

const ALLOWED = ['.mp4','.mp3','.wav','.m4a','.mov','.avi','.mkv'];
export function ensureDir(dir){ if(!fs.existsSync(dir)) fs.mkdirSync(dir,{recursive:true}); }
export function validateExt(filename){
  const ext = path.extname(filename).toLowerCase();
  if(!ALLOWED.includes(ext)) throw new Error('Unsupported file type: '+ext);
  return ext;
}
export function saveUploaded(file, uploadDir){
  ensureDir(uploadDir);
  const ext = validateExt(file.originalname);
  const id = uuid();
  const stored = id+ext;
  const dest = path.join(uploadDir, stored);
  fs.renameSync(file.path, dest);
  return {id, filename: stored, path: dest, original: file.originalname, ext};
}
