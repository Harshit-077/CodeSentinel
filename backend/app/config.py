from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # LLM
    groq_api_key: str
    groq_model: str = "llama-3.3-70b-versatile"

    # Database
    database_url: str

    # Vector DB
    chroma_persist_dir: str = "./chroma_db"

    # Embeddings
    embedding_model: str = "all-MiniLM-L6-v2"

    # App
    app_env: str = "development"
    secret_key: str
    demo_username: str = "admin"
    demo_password: str = "demo1234"

    # File storage
    upload_dir: str = "./uploads"
    report_dir: str = "./reports"

    # CORS
    frontend_url: str = "http://localhost:3000"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    return Settings()