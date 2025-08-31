// Placeholder: integrate local whisper.cpp or remote STT
// For now returns dummy transcript
export async function transcribe(path){
  return { text: 'Dummy transcript for file '+path, segments: [] };
}
