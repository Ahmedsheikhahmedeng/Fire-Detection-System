from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "Fire Detection API"
    APP_ENV: str = "development"
    APP_VERSION: str = "v3"
    DB_HOST: str
    DB_PORT: int
    DB_NAME: str
    DB_USER: str
    DB_PASSWORD: str
    DATABASE_URL: str = ""
    NASA_API_KEY: str = ""
    OPENWEATHER_API_KEY: str = ""
    FRONTEND_URL: str = "http://localhost:5173"
    ALLOWED_ORIGINS: str = ""
    API_KEY: str = ""

    # ML / V3 model settings
    ENABLE_ML_PREDICTION: bool = True

    V3_MODEL_DIR: str = "app/ml/final_models_v3"

    V3_HGB_CORE_MODEL: str = "v3_hgb_core_model.joblib"
    V3_XGBOOST_MODEL: str = "v3_xgboost_full_model.joblib"
    V3_LIGHTGBM_MODEL: str = "v3_lightgbm_watch_model.joblib"
    V3_CATBOOST_MODEL: str = "v3_catboost_watch_model.joblib"
    V3_RF_MODEL: str = "v3_rf_balanced_verifier_model.joblib"
    V3_EXTRATREES_MODEL: str = "v3_extratrees_strict_verifier_model.joblib"

    V3_HGB_FEATURES: str = "hgb_core_feature_columns.json"
    V3_FULL_FEATURES: str = "full_feature_columns.json"
    V3_THRESHOLD_CONFIG: str = "threshold_config_v3.json"
    V3_METADATA: str = "model_package_metadata_v3.json"

    # NASA -> V3 prediction integration
    ENABLE_V3_PREDICTION_ON_NASA_FETCH: bool = True
    V3_MAX_PREDICTIONS_PER_NASA_FETCH: int = 100
    ENABLE_SCHEDULER: bool = True

    # Fire cluster status windows
    CLUSTER_ACTIVE_HOURS: int = 24
    CLUSTER_MONITORING_HOURS: int = 72

    # Alert notifications
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_CHAT_ID: str = ""
    ALERT_MIN_RISK_LEVEL: str = "HIGH"
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_EMAIL: str = ""
    ALERT_EMAIL_TO: str = ""

    class Config:
        env_file = ".env"
        extra = "ignore"

    @property
    def database_url(self) -> str:
        if self.DATABASE_URL:
            return self.DATABASE_URL
        return (
            f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )

    @property
    def allowed_origins(self) -> list[str]:
        configured_origins = [
            origin.strip()
            for origin in self.ALLOWED_ORIGINS.split(",")
            if origin.strip()
        ]
        fallback_origins = [
            self.FRONTEND_URL,
            "http://localhost:5173",
            "http://localhost:3000",
        ]

        seen = set()
        origins: list[str] = []
        for origin in [*configured_origins, *fallback_origins]:
            if origin and origin != "*" and origin not in seen:
                origins.append(origin)
                seen.add(origin)
        return origins


settings = Settings()
