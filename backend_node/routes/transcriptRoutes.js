import { Router } from 'express';
import { transcribeFile } from '../controllers/transcriptController.js';
const router = Router();
router.post('/:fileId', transcribeFile);
export default router;
