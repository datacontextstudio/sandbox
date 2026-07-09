from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://dcs:dcs_password@postgres:5432/datacontext"
    api_base_url: str = "http://api:8000"

    class Config:
        env_file = ".env"


settings = Settings()
