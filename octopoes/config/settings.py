import os
from pathlib import Path

from pydantic import BaseSettings, Field


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Application settings
    debug: bool = False
    log_cfg: str = os.path.join(Path(__file__).parent.parent.parent, "logging.yml")

    # Server settings
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    # Application settings

    # External services settings
    dsn_katalogus: str = "http://katalogus:8000/"
    dsn_xtdb: str = "http://xtdb:3000/_xtdb"
    dsn_rabbitmq: str = "amqp://guest:guest@rabbitmq:5672/kat"

    class Config:
        env_prefix = "octopoes_"
