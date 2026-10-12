from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    database_url: str = "postgresql+psycopg://demo:demo_local_only@localhost:55439/bari_demo"
    demo_seed: int = 20260101
    max_usable_accuracy_m: float = Field(200, gt=0)
    min_dedup_precision: float = Field(0.98, ge=0, le=1)
    min_dedup_recall: float = Field(0.75, ge=0, le=1)
    max_volume_change: float = Field(0.30, ge=0)
    stale_days: int = Field(3, ge=1)
    simulated_provider_per_record_eur: float = Field(0.0002, ge=0)
    simulated_processing_per_run_eur: float = Field(0.015, ge=0)
    simulated_infrastructure_per_day_eur: float = Field(0.75, ge=0)


settings = Settings()
