import { Router } from 'express';
import { summarizeTranscript } from '../controllers/summaryController.js';
const router = Router();
router.post('/', summarizeTranscript);
export default router;
