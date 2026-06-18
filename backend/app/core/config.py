from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str
    CORS_ORIGINS: list[str] = ["http://localhost:4200"]
    OPENAI_API_KEY: str

    class Config:
        env_file = ".env"

settings = Settings()