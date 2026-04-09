import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    service_name: str
    host: str
    port: int
    debug: bool


settings = Settings(
    service_name=os.getenv("SERVICE_NAME", "event-api"),
    host=os.getenv("HOST", "0.0.0.0"),
    port=int(os.getenv("PORT", "8012")),
    debug=os.getenv("DEBUG", "false").lower() == "true",
)
