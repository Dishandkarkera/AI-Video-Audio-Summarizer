import dotenv from 'dotenv';
dotenv.config();
// Use environment variable for key; never commit a real key. Placeholder if unset.
export const GEMINI_API_KEY = process.env.GEMINI_API_KEY || 'Your-API-Key';
export const API_BASE = 'https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent';
