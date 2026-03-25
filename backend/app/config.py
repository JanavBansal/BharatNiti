from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://caai:caai_dev@localhost:5432/caai"
    anthropic_api_key: str = ""
    openai_api_key: str = ""

    environment: str = "development"
    log_level: str = "DEBUG"

    # RAG settings
    embedding_model: str = "text-embedding-3-large"
    embedding_dimensions: int = 3072
    llm_model: str = "gpt-4o"
    retrieval_top_k: int = 10
    retrieval_threshold: float = 0.35
    chunk_token_budget: int = 12000

    # Rate limiting
    rate_limit: str = "120/hour"

    # Cache
    query_cache_ttl_days: int = 7

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
