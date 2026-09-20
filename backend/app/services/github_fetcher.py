"""
Module 1 Extension — GitHub Repository Data Fetcher
===================================================
Fetches and extracts metadata, README documentation, project file structures,
tech stack dependencies, test detection, and activity metrics from public GitHub repository URLs.
"""

import os
import re
import logging
import base64
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, Tuple, List
import httpx

log = logging.getLogger(__name__)

# Regular expression to extract owner and repository name from GitHub URLs
_GITHUB_URL_PATTERN = re.compile(
    r"(?:https?://)?(?:www\.)?github\.com/([a-zA-Z0-9_.-]+)/([a-zA-Z0-9_.-]+?)(?:\.git|/.*)?$"
)

# Key dependency files to check for framework/stack detection
_CONFIG_FILES = {
    "requirements.txt": "python",
    "pyproject.toml": "python",
    "Pipfile": "python",
    "package.json": "javascript/typescript",
    "Cargo.toml": "rust",
    "go.mod": "go",
    "Dockerfile": "docker",
    "docker-compose.yml": "docker",
    "pom.xml": "java",
    "build.gradle": "java/kotlin",
}

# Known key frameworks/libraries to detect in dependency files
_KEY_TECH_KEYWORDS = [
    "react", "next", "vue", "angular", "fastapi", "flask", "django", "express", "nestjs",
    "torch", "pytorch", "tensorflow", "keras", "scikit-learn", "transformers", "spacy",
    "opencv", "pandas", "numpy", "postgresql", "mysql", "mongodb", "redis", "neo4j",
    "docker", "kubernetes", "tailwind", "graphql", "celery", "langchain", "llamaindex",
    "faster-whisper", "weasyprint", "reportlab", "vite", "pytest", "jest"
]

_TEST_FILE_PATTERN = re.compile(
    r"(?:^|/)(?:tests?/|test_.*\.py|.*_test\.(?:py|js|ts|jsx|tsx)|.*_spec\.(?:js|ts)|pytest\.ini|conftest\.py|jest\.config\..*)$",
    re.IGNORECASE,
)


def parse_github_url(url: str) -> Optional[Tuple[str, str]]:
    """
    Extracts (owner, repo) from a GitHub URL.
    Example: https://github.com/facebook/react -> ('facebook', 'react')
    """
    if not url:
        return None
    url = url.strip()
    match = _GITHUB_URL_PATTERN.search(url)
    if match:
        owner, repo = match.groups()
        if repo.endswith(".git"):
            repo = repo[:-4]
        return owner, repo
    return None


class GitHubFetcherService:
    def __init__(self):
        self.headers = {"Accept": "application/vnd.github.v3+json"}
        token = os.getenv("GITHUB_TOKEN")
        if token:
            self.headers["Authorization"] = f"token {token}"

    def fetch_repository_data(self, github_url: str) -> Dict[str, Any]:
        """
        Fetches repository metadata, README, file tree structure, tech stack,
        languages breakdown, test presence, and recent commit velocity.
        """
        parsed = parse_github_url(github_url)
        if not parsed:
            log.warning("Invalid GitHub URL provided: %s", github_url)
            return {
                "valid": False,
                "error": "Invalid GitHub URL format",
                "github_url": github_url,
                "readme_text": "",
                "formatted_text": "",
                "detected_stack": [],
                "file_structure": [],
                "languages": [],
                "license": "",
                "has_tests": False,
                "recent_commits": 0,
            }

        owner, repo = parsed
        api_base = f"https://api.github.com/repos/{owner}/{repo}"

        try:
            with httpx.Client(headers=self.headers, timeout=10.0, follow_redirects=True) as client:
                # 1. Fetch Repository Metadata
                repo_resp = client.get(api_base)
                if repo_resp.status_code != 200:
                    log.warning("Failed to fetch GitHub repo metadata for %s/%s: HTTP %d", owner, repo, repo_resp.status_code)
                    return self._fallback_raw_fetch(owner, repo, github_url)

                repo_data = repo_resp.json()
                default_branch = repo_data.get("default_branch", "main")
                description = repo_data.get("description") or ""
                topics = repo_data.get("topics", [])
                primary_language = repo_data.get("language") or ""
                stars = repo_data.get("stargazers_count", 0)

                # License extraction
                license_name = ""
                if repo_data.get("license") and isinstance(repo_data["license"], dict):
                    license_name = repo_data["license"].get("spdx_id") or repo_data["license"].get("name") or ""

                # 2. Languages breakdown
                languages = self._fetch_languages(client, owner, repo)
                if not languages and primary_language:
                    languages = [primary_language]

                # 3. Fetch README Content
                readme_text = self._fetch_readme(client, owner, repo, default_branch)

                # 4. Fetch File Tree & Tech Stack & Test detection
                file_tree, detected_stack, has_tests = self._fetch_tree_and_stack(
                    client, owner, repo, default_branch, primary_language, topics, languages
                )

                # 5. Recent Activity (commits in last 90 days)
                recent_commits = self._fetch_recent_activity(client, owner, repo)

                # Assemble formatted text for Module 1-6 NLP analysis
                formatted_text = self._build_formatted_text(
                    owner=owner,
                    repo=repo,
                    description=description,
                    primary_language=primary_language,
                    license_name=license_name,
                    languages=languages,
                    topics=topics,
                    detected_stack=detected_stack,
                    has_tests=has_tests,
                    recent_commits=recent_commits,
                    file_tree=file_tree,
                    readme_text=readme_text
                )

                return {
                    "valid": True,
                    "owner": owner,
                    "repo": repo,
                    "github_url": github_url,
                    "description": description,
                    "topics": topics,
                    "primary_language": primary_language,
                    "license": license_name,
                    "languages": languages,
                    "has_tests": has_tests,
                    "recent_commits": recent_commits,
                    "stars": stars,
                    "default_branch": default_branch,
                    "readme_text": readme_text,
                    "detected_stack": detected_stack,
                    "file_structure": file_tree[:25],
                    "formatted_text": formatted_text
                }

        except Exception as e:
            log.error("Exception fetching GitHub data for %s: %s", github_url, e, exc_info=True)
            return self._fallback_raw_fetch(owner, repo, github_url)

    def _fetch_languages(self, client: httpx.Client, owner: str, repo: str) -> List[str]:
        """Fetches top languages by bytes from GitHub Languages API."""
        try:
            resp = client.get(f"https://api.github.com/repos/{owner}/{repo}/languages")
            if resp.status_code == 200:
                lang_data = resp.json()
                # Sort by bytes descending
                sorted_langs = sorted(lang_data.keys(), key=lambda k: lang_data[k], reverse=True)
                return sorted_langs
        except Exception as exc:
            log.debug("Language fetch failed: %s", exc)
        return []

    def _fetch_recent_activity(self, client: httpx.Client, owner: str, repo: str) -> int:
        """Fetches commit count in the last 90 days."""
        try:
            since = (datetime.now(timezone.utc) - timedelta(days=90)).isoformat()
            resp = client.get(f"https://api.github.com/repos/{owner}/{repo}/commits?since={since}&per_page=100")
            if resp.status_code == 200:
                commits = resp.json()
                if isinstance(commits, list):
                    return len(commits)
        except Exception as exc:
            log.debug("Activity fetch failed: %s", exc)
        return 0

    def _fetch_readme(self, client: httpx.Client, owner: str, repo: str, default_branch: str) -> str:
        """Fetches README text from GitHub API or raw content URL."""
        readme_url = f"https://api.github.com/repos/{owner}/{repo}/readme"
        try:
            resp = client.get(readme_url)
            if resp.status_code == 200:
                data = resp.json()
                content = data.get("content", "")
                encoding = data.get("encoding", "")
                if encoding == "base64" and content:
                    try:
                        return base64.b64decode(content).decode("utf-8", errors="ignore")
                    except Exception:
                        pass
        except Exception:
            pass

        # Raw URL fallback
        for filename in ["README.md", "readme.md", "README.rst", "README.txt", "README"]:
            raw_url = f"https://raw.githubusercontent.com/{owner}/{repo}/{default_branch}/{filename}"
            try:
                raw_resp = client.get(raw_url)
                if raw_resp.status_code == 200 and raw_resp.text:
                    return raw_resp.text
            except Exception:
                continue

        return ""

    def _fetch_tree_and_stack(
        self,
        client: httpx.Client,
        owner: str,
        repo: str,
        default_branch: str,
        primary_lang: str,
        topics: List[str],
        languages: List[str]
    ) -> Tuple[List[str], List[str], bool]:
        """Fetches file tree and infers technologies/frameworks used and tests presence."""
        tree_url = f"https://api.github.com/repos/{owner}/{repo}/git/trees/{default_branch}?recursive=1"
        try:
            resp = client.get(tree_url)
        except Exception:
            resp = None

        file_list: List[str] = []
        stack_set = set(topics)
        if primary_lang:
            stack_set.add(primary_lang)
        for lang in languages[:3]:
            stack_set.add(lang)

        has_tests = False

        if resp and resp.status_code == 200:
            tree_data = resp.json().get("tree", [])
            for item in tree_data:
                path = item.get("path", "")
                if path:
                    file_list.append(path)
                    if _TEST_FILE_PATTERN.search(path):
                        has_tests = True
                    filename = path.split("/")[-1]
                    if filename in _CONFIG_FILES:
                        stack_set.add(_CONFIG_FILES[filename])

            # Deep dependency scanning
            for dep_file in ["requirements.txt", "package.json", "pyproject.toml", "go.mod"]:
                if dep_file in file_list:
                    content = self._get_file_content(client, owner, repo, default_branch, dep_file)
                    content_lower = content.lower()
                    for kw in _KEY_TECH_KEYWORDS:
                        if kw in content_lower:
                            stack_set.add(kw.capitalize())

        return file_list, sorted(list(stack_set)), has_tests

    def _get_file_content(self, client: httpx.Client, owner: str, repo: str, branch: str, path: str) -> str:
        raw_url = f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{path}"
        try:
            resp = client.get(raw_url)
            if resp.status_code == 200:
                return resp.text
        except Exception:
            pass
        return ""

    def _fallback_raw_fetch(self, owner: str, repo: str, github_url: str) -> Dict[str, Any]:
        """Raw fetch fallback when API endpoint is rate-limited or fails."""
        try:
            with httpx.Client(timeout=8.0, follow_redirects=True) as client:
                readme_text = ""
                for branch in ["main", "master"]:
                    for filename in ["README.md", "readme.md", "README.txt"]:
                        raw_url = f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{filename}"
                        resp = client.get(raw_url)
                        if resp.status_code == 200 and resp.text:
                            readme_text = resp.text
                            break
                    if readme_text:
                        break

                formatted = (
                    f"GitHub Repository: {owner}/{repo}\nURL: {github_url}\n\nREADME Document:\n{readme_text}"
                    if readme_text else ""
                )
                return {
                    "valid": bool(readme_text),
                    "owner": owner,
                    "repo": repo,
                    "github_url": github_url,
                    "description": f"GitHub repository {owner}/{repo}",
                    "topics": [],
                    "primary_language": "",
                    "license": "",
                    "languages": [],
                    "has_tests": False,
                    "recent_commits": 0,
                    "stars": 0,
                    "readme_text": readme_text,
                    "detected_stack": [],
                    "file_structure": [],
                    "formatted_text": formatted
                }
        except Exception as e:
            log.error("Fallback raw fetch failed for %s/%s: %s", owner, repo, e)
            return {
                "valid": False,
                "error": str(e),
                "github_url": github_url,
                "readme_text": "",
                "formatted_text": "",
                "detected_stack": [],
                "file_structure": [],
                "languages": [],
                "license": "",
                "has_tests": False,
                "recent_commits": 0,
            }

    def _build_formatted_text(
        self,
        owner: str,
        repo: str,
        description: str,
        primary_language: str,
        license_name: str,
        languages: List[str],
        topics: List[str],
        detected_stack: List[str],
        has_tests: bool,
        recent_commits: int,
        file_tree: List[str],
        readme_text: str
    ) -> str:
        parts = [
            f"GitHub Repository: {owner}/{repo}",
            f"Repository Description: {description}",
            f"Primary Language: {primary_language}",
            f"License: {license_name or 'Not specified'}",
            f"Languages Used: {', '.join(languages) if languages else 'Not detected'}",
            f"Test Suite Detected: {'Yes' if has_tests else 'No'}",
            f"Commits in Last 90 Days: {recent_commits}",
            f"Repository Tags & Technologies: {', '.join(detected_stack or topics)}",
            f"Top Directory Structure: {', '.join(file_tree[:20])}"
        ]
        if readme_text:
            parts.append(f"\n--- GitHub README Content ---\n{readme_text}")
        return "\n".join(parts)


# Singleton instance
github_fetcher_service = GitHubFetcherService()
