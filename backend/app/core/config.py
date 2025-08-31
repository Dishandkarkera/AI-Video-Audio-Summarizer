from pydantic import BaseModel, ConfigDict
from functools import lru_cache
import os
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseModel):
    # IMPORTANT: Real API keys must come from environment variables (.env not committed).
    # The default placeholder intentionally breaks external calls if not overridden.
    gemini_api_key: str = os.getenv("GEMINI_API_KEY") or "Your-API-Key"
    jwt_secret: str = os.getenv("JWT_SECRET", "change_me")
    jwt_alg: str = os.getenv("JWT_ALG", "HS256")
    database_url: str = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./app.db")
    app_env: str = os.getenv("APP_ENV", "development")
    upload_dir: str = os.getenv("UPLOAD_DIR", "uploads")
    max_upload_size_mb: int = int(os.getenv("MAX_UPLOAD_MB", "1024"))  # 1GB

    model_config = ConfigDict(arbitrary_types_allowed=True)

@lru_cache
def get_settings() -> Settings:
    return Settings()
