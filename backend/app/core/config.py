from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

LOCAL_DEV_JWT_SECRET = "local-dev-only-change-before-production"

class Settings(BaseSettings):
    PROJECT_NAME: str = "Portal Vesper"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    API_V1_STR: str = "/api/v1"

    # JWT e Segurança
    JWT_SECRET: str = LOCAL_DEV_JWT_SECRET
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    COOKIE_SECURE: bool = False
    COOKIE_SAMESITE: str = "lax"
    BACKEND_CORS_ORIGINS: str = (
        "http://localhost:5173,"
        "http://127.0.0.1:5173,"
        "http://localhost:3000,"
        "http://127.0.0.1:3000"
    )
    SECURITY_HEADERS_ENABLED: bool = True
    CONTENT_SECURITY_POLICY: str = "default-src 'self'; frame-ancestors 'none'; object-src 'none'; base-uri 'self'"
    LOGIN_RATE_LIMIT_MAX_ATTEMPTS: int = 5
    LOGIN_RATE_LIMIT_WINDOW_SECONDS: int = 300

    # PostgreSQL
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_PORT: int = 55432
    POSTGRES_DB: str = "portal_vesper"
    POSTGRES_USER: str = "vesper_admin"
    POSTGRES_PASSWORD: str = "local-dev-postgres-password"
    DATABASE_URL: str = Field(
        default="postgresql://vesper_admin:local-dev-postgres-password@localhost:55432/portal_vesper"
    )

    # Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str = "local-dev-redis-password"
    NOTIFICATIONS_REDIS_FANOUT_ENABLED: bool = False


    # MinIO
    MINIO_ROOT_USER: str = "vesper_minio_user"
    MINIO_ROOT_PASSWORD: str = "local-dev-minio-password"
    MINIO_PORT: int = 9000
    MINIO_CONSOLE_PORT: int = 9001
    MINIO_BUCKET_NAME: str = "knowledge-base"

    # n8n
    N8N_PORT: int = 5678

    # Event Dispatcher (Outbox Worker Scheduler)
    EVENT_DISPATCHER_ENABLED: bool = False
    EVENT_DISPATCHER_INTERVAL_SECONDS: int = 5
    EVENT_DISPATCHER_BATCH_SIZE: int = 50
    EVENT_DISPATCHER_MAX_ATTEMPTS: int = 5
    EVENT_PAYLOAD_VALIDATION_MODE: str = "warn"

    # n8n Webhook Bridge
    N8N_WEBHOOK_BRIDGE_ENABLED: bool = False
    N8N_BASE_URL: str = "http://localhost:5678"
    N8N_WEBHOOK_SECRET: str | None = None
    N8N_WEBHOOK_TIMEOUT_SECONDS: int = 10
    N8N_WEBHOOK_MAX_ATTEMPTS: int = 3
    N8N_ALLOWED_EVENT_TYPES: str = ""

    # n8n Response Gateway (callbacks)
    N8N_CALLBACKS_ENABLED: bool = False
    N8N_CALLBACK_MAX_AGE_SECONDS: int = 300
    N8N_CALLBACK_ALLOWED_TYPES: str = ""

    # TI / Cofre de credenciais
    # Em producao, defina uma chave forte em variavel de ambiente.
    IT_CREDENTIAL_VAULT_KEY: str | None = None

    # Rastreabilidade de preços de compras
    PURCHASE_PRICE_VARIATION_ALERT_PERCENT: float = 10.0
    PURCHASE_PRICE_REQUIRE_APPROVAL: bool = True

    # Compras Inteligentes - pesquisa externa e recomendacao
    SERPAPI_API_KEY: str | None = None
    GEMINI_API_KEY: str | None = None
    PURCHASES_SEARXNG_URL: str = "http://localhost:8088"
    PURCHASES_SEARCH_MAX_PROVIDER_CALLS: int = 12
    PURCHASES_SEARCH_CACHE_TTL_SECONDS: int = 3600
    PURCHASES_PLAYWRIGHT_VERIFY_ENABLED: bool = False
    PURCHASES_TEST_EMAIL_RECIPIENT: str | None = None
    PURCHASES_GEMINI_MODEL: str = "gemini-3.5-flash"
    PURCHASES_RESEARCH_ASYNC_ENABLED: bool = False
    PURCHASES_RESEARCH_QUEUE_NAME: str = "purchases_research"


    model_config = SettingsConfigDict(
        # Procura por .env tanto na pasta backend quanto na pasta raiz (um nível acima)
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @property
    def cors_origins(self) -> list[str]:
        return [
            origin.strip()
            for origin in self.BACKEND_CORS_ORIGINS.split(",")
            if origin.strip()
        ]

    @property
    def allowed_event_types(self) -> list[str]:
        if not self.N8N_ALLOWED_EVENT_TYPES:
            return []
        return [t.strip() for t in self.N8N_ALLOWED_EVENT_TYPES.split(",") if t.strip()]

    @property
    def allowed_callback_types(self) -> list[str]:
        if not self.N8N_CALLBACK_ALLOWED_TYPES:
            return []
        return [t.strip() for t in self.N8N_CALLBACK_ALLOWED_TYPES.split(",") if t.strip()]

    def model_post_init(self, __context) -> None:
        is_production = self.ENVIRONMENT.lower() in {"production", "prod"}
        if is_production and self.JWT_SECRET == LOCAL_DEV_JWT_SECRET:
            raise ValueError("JWT_SECRET must be set to a strong non-default value in production.")
        if is_production and (self.N8N_WEBHOOK_BRIDGE_ENABLED or self.N8N_CALLBACKS_ENABLED) and not self.N8N_WEBHOOK_SECRET:
            raise ValueError("N8N_WEBHOOK_SECRET must be configured when N8N_WEBHOOK_BRIDGE_ENABLED or N8N_CALLBACKS_ENABLED is enabled in production.")

settings = Settings()

