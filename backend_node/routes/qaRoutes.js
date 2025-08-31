import { Router } from 'express';
import { askQuestion } from '../controllers/qaController.js';
const router = Router();
router.post('/', askQuestion);
export default router;
