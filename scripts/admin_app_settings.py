from pydantic import BaseSettings, Field


class Settings(BaseSettings):
    certificate_path: str = Field(..., env="TWENTYTHIRTYDOTFIVE_CERTIFICATE_PATH")
    key_path: str = Field(..., env="TWENTYTHIRTYDOTFIVE_KEY_PATH")
    server_url: str = Field(..., env="TWENTYTHIRTYDOTFIVE_SERVER_URL")
    client_lfdi: str = Field(..., env="TWENTYTHIRTYDOTFIVE_CLIENT_LFDI")
    use_ssl_auth: bool = Field(..., env="TWENTYTHIRTYDOTFIVE_USE_SSL_AUTH")


settings = Settings(_env_file=".env.local", _env_file_encoding="utf-8")
