from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # pydantic-settings loads env_file entries in order and LATER files
    # override earlier ones. This used to be (".env", "../.env"), which let
    # the root ../.env (Docker-compose values, e.g. NEO4J_URI=bolt://neo4j:7687)
    # silently override backend/.env's real values whenever the backend ran
    # outside Docker. Local backend/.env must win, so it goes last.
    model_config = SettingsConfigDict(env_file=("../.env", ".env"), extra="ignore")

    DATABASE_URL: str
    JWT_SECRET: str
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 10080  # 7 days

    GEMINI_API_KEY: str = ""
    SEMANTIC_SCHOLAR_KEY: str = ""
    GITHUB_TOKEN: str = ""            # Optional — raises rate limit 60→5000 req/hr

    # Module 13 — Moodle LMS integration (optional)
    MOODLE_URL: str = ""              # e.g. https://moodle.yourcollege.edu
    MOODLE_TOKEN: str = ""            # Moodle web service token
    MOODLE_ASSIGNMENT_ID: int = 0     # Moodle assignment ID to sync
    MOODLE_FACULTY_USER_ID: str = "" # AcadEval UUID of the faculty uploader

    # Module 14 — Email & Notification Service (Gmail SMTP)
    SMTP_SERVER: str = "smtp.gmail.com"
    SMTP_PORT: int = 465
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_NAME: str = "AcadEval+ Platform"

    NEO4J_URI: str = "bolt://localhost:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_USERNAME: str = ""
    NEO4J_PASSWORD: str = ""
    NEO4J_DATABASE: str = ""

    @property
    def effective_neo4j_user(self) -> str:
        return self.NEO4J_USERNAME or self.NEO4J_USER or "neo4j"

    # Which engine is authoritative for the novelty score on a report.
    #   corpus -> always use the in-memory/CSV corpus index (default). Neo4j
    #             is a visualization-only layer and never affects the score,
    #             so the same submission scores the same regardless of Neo4j
    #             uptime.
    #   auto   -> try Neo4j first, fall back to the corpus index on failure.
    #   neo4j  -> require Neo4j; raises on failure (old crash-on-failure
    #             behavior — only for explicit strict-mode testing).
    NOVELTY_GRAPH_BACKEND: Literal["auto", "corpus", "neo4j"] = "corpus"

    REDIS_URL: str = "redis://localhost:6379/0"
    GROBID_URL: str = "http://localhost:8070"

    UPLOAD_DIR: str = "uploads"
    MAX_UPLOAD_SIZE_MB: int = 500

    APP_ENV: str = "development"
    FRONTEND_ORIGIN: str = "http://localhost:5173"

    @property
    def cors_origins(self) -> list[str]:
        """Return explicit browser origins accepted by the credentialed API."""
        return [
            origin.strip().rstrip("/")
            for origin in self.FRONTEND_ORIGIN.split(",")
            if origin.strip()
        ]


settings = Settings()
