from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str
    test_database_url: str = ""

    jwt_secret: str
    jwt_algorithm: str = "HS256"
    jwt_expire_days_customer: int = 7
    jwt_expire_hours_admin: int = 8

    resend_api_key: str = ""
    resend_from_email: str = "onboarding@resend.dev"
    frontend_url: str = "http://localhost:5173"
    admin_url: str = "http://localhost:5174"

    firebase_credentials: str = ""
    firebase_storage_bucket: str = ""

    redis_url: str = "redis://localhost:6379/0"

    class Config:
        env_file = ".env"


settings = Settings()
