"""Fetches a project's own linked GitHub repo's source files for code-similarity
fingerprinting (see app/services/plagiarism_checker.py). Distinct from
app/services/github_client.py, which searches OTHER people's repos for prior
art by keyword — this module reads one specific repo's own file tree and
content, via the GitHub REST API (no git clone — mirrors the resilience idiom
already used by github_client.py: short timeout, status-code branching,
graceful degrade to a reported error, never raises)."""
from __future__ import annotations

import logging
from typing import Optional

import requests

from app.config import settings

log = logging.getLogger(__name__)

GH_API_BASE = "https://api.github.com"

CODE_EXTENSIONS = {
    "py", "java", "c", "cpp", "cc", "h", "hpp", "js", "jsx", "ts", "tsx",
    "go", "rb", "php", "cs", "kt", "swift", "rs", "scala", "m", "r",
}
SKIP_PATH_PARTS = (
    "node_modules/", "/dist/", "/build/", "__pycache__/", "/vendor/",
    ".min.js", "package-lock.json", "yarn.lock", "/.git/", "/venv/", "/.venv/",
)
MAX_FILES = 40
MAX_TOTAL_BYTES = 2_000_000
MAX_FILE_BYTES = 200_000


def _parse_github_url(url: str) -> Optional[tuple[str, str]]:
    if not url or "github.com" not in url:
        return None
    clean = url.strip().rstrip("/")
    parts = clean.split("github.com/")[-1].split("/")
    if len(parts) < 2:
        return None
    owner, repo = parts[0], parts[1].replace(".git", "")
    if not owner or not repo:
        return None
    return owner, repo


def _headers() -> dict:
    h = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
    token = getattr(settings, "GITHUB_TOKEN", "")
    if token:
        h["Authorization"] = f"Bearer {token}"
    return h


def _get(url: str, params: dict | None = None):
    try:
        resp = requests.get(url, params=params, headers=_headers(), timeout=8.0)
        if resp.status_code == 200:
            return resp.json()
        if resp.status_code == 403:
            log.warning("GitHub rate-limited fetching %s", url)
            return None
        log.warning("GitHub API HTTP %d for %s", resp.status_code, url)
        return None
    except Exception as exc:
        log.warning("GitHub API error for %s: %s", url, exc)
        return None


def fetch_repo_source_files(github_url: str) -> dict:
    """
    Best-effort — never raises. Returns:
      {
        "repo_owner": str | None, "repo_name": str | None, "branch": str | None,
        "files": [{"path": str, "content": str}], "fetch_error": str | None,
      }
    An empty "files" list with a set "fetch_error" means the failure is visible
    (private/deleted repo, rate limit, no comparable source files) rather than
    silently treated as "no code".
    """
    parsed = _parse_github_url(github_url)
    if not parsed:
        return {"repo_owner": None, "repo_name": None, "branch": None, "files": [],
                "fetch_error": "Not a recognizable GitHub URL"}
    owner, repo = parsed

    repo_meta = _get(f"{GH_API_BASE}/repos/{owner}/{repo}")
    if not repo_meta:
        return {"repo_owner": owner, "repo_name": repo, "branch": None, "files": [],
                "fetch_error": "Could not fetch repository metadata (private, deleted, or rate-limited)"}
    branch = repo_meta.get("default_branch", "main")

    tree = _get(f"{GH_API_BASE}/repos/{owner}/{repo}/git/trees/{branch}", params={"recursive": "1"})
    if not tree or "tree" not in tree:
        return {"repo_owner": owner, "repo_name": repo, "branch": branch, "files": [],
                "fetch_error": "Could not fetch the repository file tree"}

    candidates = []
    for entry in tree["tree"]:
        if entry.get("type") != "blob":
            continue
        path = entry.get("path", "")
        if any(skip in f"/{path}" for skip in SKIP_PATH_PARTS):
            continue
        ext = path.rsplit(".", 1)[-1].lower() if "." in path else ""
        if ext not in CODE_EXTENSIONS:
            continue
        size = entry.get("size", 0) or 0
        if size > MAX_FILE_BYTES:
            continue
        candidates.append((path, size))

    # Largest-first is a weak proxy for "most substantive"; still capped below.
    candidates.sort(key=lambda c: -c[1])
    files: list[dict] = []
    total_bytes = 0
    for path, size in candidates:
        if len(files) >= MAX_FILES or total_bytes + size > MAX_TOTAL_BYTES:
            break
        raw_url = f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{path}"
        try:
            resp = requests.get(raw_url, headers=_headers(), timeout=6.0)
            if resp.status_code == 200:
                files.append({"path": path, "content": resp.text})
                total_bytes += size
        except Exception as exc:
            log.warning("Failed to fetch %s: %s", raw_url, exc)
            continue

    fetch_error = None if files else "No comparable source files found, or all fetches failed"
    return {"repo_owner": owner, "repo_name": repo, "branch": branch, "files": files, "fetch_error": fetch_error}
