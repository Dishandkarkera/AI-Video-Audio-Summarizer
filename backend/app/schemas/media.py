from pydantic import BaseModel, ConfigDict
from typing import Optional, List

class MediaOut(BaseModel):
    id: int
    filename: str
    original_name: str
    status: str
    language: Optional[str]
    transcript: Optional[str]
    summary_json: Optional[str]

    model_config = ConfigDict(from_attributes=True)

class SummaryRequest(BaseModel):
    media_id: int

class ChatRequest(BaseModel):
    media_id: int
    message: str

class ChatRef(BaseModel):
    start: float
    end: float
    text: str

class ChatResponse(BaseModel):
    answer: str
    refs: List[ChatRef] | None = None

class SummaryResponse(BaseModel):
    summary_short: str
    summary_detailed: str
    highlights: List[str]
    sentiment: str
    action_points: List[str]

class AnalyticsOut(BaseModel):
    media_id: int
    word_count: int
    sentiment: str | None = None
    processing_seconds: float | None = None
