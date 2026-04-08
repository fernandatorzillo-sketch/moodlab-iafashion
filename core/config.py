import logging
import os
from typing import Any

from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    # Application
    app_name: str = "FastAPI Modular Template"
    debug: bool = False
    version: str = "1.0.0"

    # Server
    host: str = "0.0.0.0"
    port: int = 8000

    # Database
    database_url: str = "sqlite+aiosqlite:///./moodlab.db"

    # AWS Lambda Configuration
    is_lambda: bool = False
    lambda_function_name: str = "fastapi-backend"
    aws_region: str = "us-east-1"

    @property
    def backend_url(self) -> str:
        """Generate backend URL from host and port."""
        if self.is_lambda:
            return os.environ.get(
                "PYTHON_BACKEND_URL",
                f"https://{self.lambda_function_name}.execute-api.{self.aws_region}.amazonaws.com"
            )
        else:
            display_host = "127.0.0.1" if self.host == "0.0.0.0" else self.host
            return os.environ.get(
                "PYTHON_BACKEND_URL",
                f"http://{display_host}:{self.port}"
            )

    class Config:
        case_sensitive = False
        extra = "ignore"

    def __getattr__(self, name: str) -> Any:
        env_var_name = name.upper()

        if env_var_name in os.environ:
            value = os.environ[env_var_name]
            self.__dict__[name] = value
            logger.debug(f"Read dynamic attribute {name} from environment variable {env_var_name}")
            return value

        raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{name}'")


settings = Settings()