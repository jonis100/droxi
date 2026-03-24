import json
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://clinic:clinic_pass@db:5432/clinic_inbox"
    cors_origins: str = '["http://localhost:4200","http://localhost"]'

    @property
    def cors_origin_list(self) -> list[str]:
        return json.loads(self.cors_origins)

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
