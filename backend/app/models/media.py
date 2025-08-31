from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, func
from sqlalchemy.orm import relationship
from app.db.database import Base

class Media(Base):
    __tablename__ = 'media'
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    filename = Column(String, nullable=False)
    original_name = Column(String, nullable=False)
    content_type = Column(String, nullable=False)
    status = Column(String, default='uploaded')  # uploaded|processing|done|error
    language = Column(String, nullable=True)
    duration_seconds = Column(Integer, nullable=True)
    transcript = Column(Text, nullable=True)
    segments_json = Column(Text, nullable=True)
    transcript_path = Column(String, nullable=True)
    summary_json = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship('User')
