from pydantic import BaseModel
from dotenv import load_dotenv
import os

load_dotenv()


class Settings(BaseModel):
    openai_api_key: str | None = os.getenv("OPENAI_API_KEY")
    host: str = os.getenv("BACKEND_HOST", "0.0.0.0")
    port: int = os.getenv("BACKEND_PORT", "8000")
    cors_origins: list[str] = ["*"]


settings = Settings()
