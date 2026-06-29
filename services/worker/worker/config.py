from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    redis_url: str = "redis://redis:6379"
    ollama_base_url: str = "http://ollama:11434"
    qdrant_host: str = "qdrant"
    qdrant_port: int = 6333
    storage_path: str = "/data/documents"
    embed_model: str = "nomic-embed-text"
    chunk_size: int = 4000
    chunk_overlap: int = 400
    max_retries: int = 3
    embed_batch_size: int = 32
    health_port: int = 8080

    class Config:
        env_file = ".env"


settings = Settings()
