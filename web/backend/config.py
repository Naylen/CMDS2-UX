"""Application configuration from environment variables."""

from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Auth
    admin_user: str = "admin"
    admin_password: str = "changeme"
    jwt_secret: str = "cmds2-change-me-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7

    # Paths
    cloud_admin_dir: Path = Path("/root/.cloud_admin")
    hybrid_admin_dir: Path = Path("/root/.hybrid_admin")
    cat_admin_dir: Path = Path("/root/.cat_admin")
    server_admin_dir: Path = Path("/root/.server_admin")
    tftpboot_dir: Path = Path("/var/lib/tftpboot")
    firmware_dir: Path = Path("/var/lib/tftpboot/images")
    db_path: Path = Path("/var/lib/cmds2/cmds2.db")

    # Docker
    cmds_docker: bool = True

    # Server
    host: str = "127.0.0.1"
    port: int = 8000

    model_config = {"env_prefix": "CMDS_"}


settings = Settings()
