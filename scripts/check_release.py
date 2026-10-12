"""Audit source files for sensitive release artifacts without printing matched values.

Run from the project root: python scripts/check_release.py
This is a heuristic scan, not proof that a repository/history contains no secrets.
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXCLUDED = {".git", ".venv", "__pycache__", ".pytest_cache", ".ruff_cache", "dist", "build"}
PATTERNS = {
    "Google API key": re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b"),
    "AWS access key": re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"),
    "private key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "assigned bearer token": re.compile(
        r"(?:GEMINI_API_KEY|GOOGLE_API_KEY|AWS_BEARER_TOKEN_BEDROCK)\s*=\s*[\"']?[A-Za-z0-9/+_.=-]{20,}"
    ),
}


def main() -> int:
    issues = []
    checked = 0
    for path in sorted(ROOT.rglob("*")):
        relative = path.relative_to(ROOT)
        if not path.is_file() or any(part in EXCLUDED for part in relative.parts):
            continue
        if any(part.endswith(".egg-info") for part in relative.parts):
            continue
        if path.name in {".gemini-key.dpapi", "secrets.toml"}:
            issues.append((relative, "private encrypted key; exclude from release"))
            continue
        if path.name.startswith(".env") and path.name != ".env.example":
            issues.append((relative, "private environment file; exclude from release"))
            continue
        if path.suffix in {".db", ".sqlite", ".sqlite3", ".pyc"} or ".db-" in path.name:
            issues.append((relative, "runtime/private artifact; exclude from release"))
            continue
        if relative.parts[0] == "assets" and path.suffix.lower() in {".png", ".mp4", ".gif"}:
            issues.append((relative, "screenshot/clip requires manual privacy review"))
            continue
        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeError:
            issues.append((relative, "binary file requires manual review"))
            continue
        checked += 1
        for label, pattern in PATTERNS.items():
            if pattern.search(content):
                issues.append((relative, label))
    for path, issue in issues:
        print(f"REVIEW {path}: {issue}")
    print(f"Checked {checked} text files; {len(issues)} item(s) need review.")
    print("Review any Git history and screenshots separately before publishing.")
    return 1 if issues else 0


if __name__ == "__main__":
    raise SystemExit(main())
