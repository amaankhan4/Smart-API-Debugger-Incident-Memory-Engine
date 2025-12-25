from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    MONGODB_URI: str
    MONGODB_DB: str
    REDIS_URL: str
    CHROMA_HOST: str
    CHROMA_PORT: int

    class Config:
        env_file = ".env"

settings = Settings()
