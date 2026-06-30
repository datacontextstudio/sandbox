from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    valkey_url: str = "redis://valkey:6379"
    ollama_base_url: str = "http://ollama:11434"
    qdrant_host: str = "qdrant"
    qdrant_port: int = 6333
    storage_path: str = "/data/documents"
    embed_model: str = "nomic-embed-text"

    class Config:
        env_file = ".env"


settings = Settings()
