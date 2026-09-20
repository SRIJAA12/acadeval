"""
Unit tests for Module 1 Extension — GitHub Repository Data Fetcher
"""

import pytest
from app.services.github_fetcher import (
    parse_github_url,
    github_fetcher_service,
)


def test_parse_github_url_valid():
    assert parse_github_url("https://github.com/facebook/react") == ("facebook", "react")
    assert parse_github_url("https://github.com/psf/requests.git") == ("psf", "requests")
    assert parse_github_url("github.com/fastapi/fastapi/") == ("fastapi", "fastapi")


def test_parse_github_url_invalid():
    assert parse_github_url("https://google.com") is None
    assert parse_github_url("") is None
    assert parse_github_url(None) is None


def test_fetch_repository_data_invalid_url():
    result = github_fetcher_service.fetch_repository_data("invalid-url")
    assert result["valid"] is False
    assert result["error"] == "Invalid GitHub URL format"


def test_fetch_repository_data_live_public_repo():
    # Test with public repository (psf/requests)
    url = "https://github.com/psf/requests"
    result = github_fetcher_service.fetch_repository_data(url)

    assert result["owner"] == "psf"
    assert result["repo"] == "requests"
    assert result["github_url"] == url
    if result["valid"]:
        assert len(result["readme_text"]) > 0
        assert "formatted_text" in result
        assert isinstance(result["detected_stack"], list)
