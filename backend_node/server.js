import express from 'express';
import cors from 'cors';
import dotenv from 'dotenv';
import uploadRoutes from './routes/uploadRoutes.js';
import transcriptRoutes from './routes/transcriptRoutes.js';
import summaryRoutes from './routes/summaryRoutes.js';
import qaRoutes from './routes/qaRoutes.js';
import { errorHandler } from './middleware/errorHandler.js';
import { WebSocketServer } from 'ws';
import fs from 'fs';

dotenv.config();

const app = express();
app.use(cors());
app.use(express.json({limit:'20mb'}));

// ensure upload dir
const uploadDir = process.env.UPLOAD_DIR || './uploads';
if(!fs.existsSync(uploadDir)) fs.mkdirSync(uploadDir,{recursive:true});

app.get('/health', (_req,res)=>res.json({status:'ok'}));

app.use('/api/upload', uploadRoutes);
app.use('/api/transcribe', transcriptRoutes);
app.use('/api/summarize', summaryRoutes);
app.use('/api/qa', qaRoutes);

app.use(errorHandler);

const port = process.env.PORT || 8000;
const serverInstance = app.listen(port, ()=> console.log('Node backend listening on', port));

// WebSocket realtime placeholder
const wss = new WebSocketServer({ server: serverInstance, path: '/ws/capture' });
wss.on('connection', ws => {
	ws.send(JSON.stringify({type:'welcome', message:'Send binary audio chunks; placeholder will echo partial text.'}));
	ws.on('message', data => {
		if(Buffer.isBuffer(data)){
			ws.send(JSON.stringify({type:'partial', text:'(audio chunk '+data.length+' bytes received)'}));
		} else {
			ws.send(JSON.stringify({type:'ack'}));
		}
	});
});
