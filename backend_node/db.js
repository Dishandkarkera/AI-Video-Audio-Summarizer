import Database from 'better-sqlite3';
import fs from 'fs';
const dbFile = process.env.DB_FILE || 'data.db';
const first = !fs.existsSync(dbFile);
export const db = new Database(dbFile);
if(first){
  db.exec(`CREATE TABLE sessions (id TEXT PRIMARY KEY, original_name TEXT, stored_name TEXT, status TEXT, created_at TEXT, transcript TEXT, summary_json TEXT);
           CREATE TABLE qa_logs (id INTEGER PRIMARY KEY AUTOINCREMENT, session_id TEXT, question TEXT, answer TEXT, created_at TEXT);`);
}
export function insertSession(row){
  db.prepare('INSERT INTO sessions (id, original_name, stored_name, status, created_at) VALUES (?,?,?,?,datetime("now"))').run(row.id,row.original_name,row.stored_name,row.status);
}
export function updateSessionStatus(id,status){ db.prepare('UPDATE sessions SET status=? WHERE id=?').run(status,id); }
export function setTranscript(id, transcript){ db.prepare('UPDATE sessions SET transcript=?, status=? WHERE id=?').run(transcript,'transcribed',id); }
export function setSummary(id, summaryJson){ db.prepare('UPDATE sessions SET summary_json=?, status=? WHERE id=?').run(summaryJson,'summarized',id); }
export function getSession(id){ return db.prepare('SELECT * FROM sessions WHERE id=?').get(id); }
export function logQA(session_id, question, answer){ db.prepare('INSERT INTO qa_logs (session_id, question, answer, created_at) VALUES (?,?,?,datetime("now"))').run(session_id, question, answer); }
