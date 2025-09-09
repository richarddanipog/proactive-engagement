from pydantic import BaseModel
from dotenv import load_dotenv
import os

load_dotenv()


class Settings(BaseModel):
    openai_api_key: str | None = os.getenv("OPENAI_API_KEY")
    host: str = os.getenv("BACKEND_HOST", "0.0.0.0")
    port: int = os.getenv("BACKEND_PORT", "8000")
    cors_origins: list[str] = ["*"]

    # LLM config
    llm_model: str = os.getenv("LLM_MODEL", "gpt-4o-mini")
    llm_temperature: float = float(os.getenv("LLM_TEMPERATURE", "0.2"))
    llm_max_tokens: int = int(os.getenv("LLM_MAX_TOKENS", "150"))


settings = Settings()
