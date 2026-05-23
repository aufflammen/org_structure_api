from functools import lru_cache

from pydantic import BaseModel, Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict

from ..enums import Env


class DatabaseConfig(BaseModel):
    name: str = Field(alias="db")
    user: str
    password: str
    host: str
    port: int

    @computed_field  # type: ignore[prop-decorator]
    @property
    def url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.user}:{self.password}"
            f"@{self.host}:{self.port}/{self.name}"
        )


class Config(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
        env_nested_delimiter="_",
        env_nested_max_split=1,
    )

    env: Env
    db: DatabaseConfig = Field(alias="postgres")


@lru_cache
def get_config() -> Config:
    return Config()


if __name__ == "__main__":
    print(get_config().model_dump_json(indent=4))
