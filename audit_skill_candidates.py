#!/usr/bin/env python3
"""Audit skill candidates mentioned in an article or supplied by name."""

from __future__ import annotations

import argparse
import json
import os
import re
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Iterable


NAME_RE = re.compile(r"^[a-z0-9][a-z0-9-]{1,62}$")
TOKEN_RE = re.compile(r"(?<![A-Za-z0-9_-])\$?([A-Za-z][A-Za-z0-9_-]{1,63})(?![A-Za-z0-9_-])")

RISK_PATTERNS = [
    ("high", "destructive shell command", re.compile(r"\brm\s+-rf\b|\bgit\s+reset\s+--hard\b")),
    ("high", "remote code execution pattern", re.compile(r"\b(curl|wget)\b[^\n]{0,200}\|\s*(sh|bash)\b", re.I)),
    ("high", "secret exfiltration indicator", re.compile(r"(OPENAI_API_KEY|SECRET|TOKEN|PASSWORD)[^\n]{0,200}(curl|requests\.post|fetch\()", re.I)),
    ("medium", "shell execution", re.compile(r"\bos\.system\(|subprocess\.[A-Za-z_]+\(.{0,120}shell\s*=\s*True", re.S)),
    ("medium", "dynamic code execution", re.compile(r"\beval\(|\bexec\(")),
    ("medium", "network access", re.compile(r"\b(requests\.|urllib\.request|fetch\(|curl\b|wget\b)", re.I)),
    ("medium", "privilege or permission change", re.compile(r"\bsudo\b|\bchmod\s+777\b")),
]

EXPLANATORY_LINE_RE = re.compile(
    r"\b(do not|never|avoid|example|examples|such as|risk|risky|danger|dangerous|"
    r"scanner|scan|pattern|patterns|regex|re\.compile)\b",
    re.I,
)


def normalize_name(value: str) -> str:
    value = value.strip().strip("`'\"“”‘’.,:;()[]{}<>")
    value = value.replace("_", "-")
    value = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "-", value)
    value = value.lower()
    value = re.sub(r"[^a-z0-9-]+", "-", value)
    value = re.sub(r"-{2,}", "-", value).strip("-")
    return value


def parse_skills_arg(value: str | None) -> list[str]:
    if not value:
        return []
    parts = re.split(r"[,;\n]", value)
    return [normalize_name(part) for part in parts if normalize_name(part)]


def extract_mentions(text: str) -> list[str]:
    mentions: set[str] = set()
    stopwords = {"skill", "skills", "must", "have", "best", "top", "new", "old"}
    for line in text.splitlines():
        for match in TOKEN_RE.finditer(line):
            raw = match.group(1)
            token = match.group(0)
            normalized = normalize_name(raw)
            if not normalized or len(normalized) < 2 or normalized in stopwords:
                continue

            raw_has_separator = "-" in raw or "_" in raw
            explicit_skill_ref = token.startswith("$") or "skill" in normalized
            looks_like_version_or_id = bool(re.search(r"\d{3,}", raw))

            if looks_like_version_or_id:
                continue

            # Plain CamelCase product names often normalize into hyphenated words
            # (NotebookLM -> notebook-lm). Do not treat them as skill candidates
            # unless the original token is explicitly skill-like.
            if raw_has_separator or explicit_skill_ref:
                mentions.add(normalized)
    return sorted(mentions)


def default_roots(extra_roots: Iterable[str]) -> list[Path]:
    roots: list[Path] = []
    for raw in extra_roots:
        roots.append(Path(raw).expanduser())
    codex_home = os.environ.get("CODEX_HOME")
    if codex_home:
        roots.append(Path(codex_home).expanduser() / "skills")
    roots.append(Path.home() / ".codex" / "skills")
    roots.append(Path.cwd())

    unique: list[Path] = []
    seen: set[Path] = set()
    for root in roots:
        resolved = root.resolve() if root.exists() else root
        if resolved not in seen:
            seen.add(resolved)
            unique.append(root)
    return unique


def find_skill_dir(name: str, roots: list[Path]) -> Path | None:
    for root in roots:
        direct = root / name
        if (direct / "SKILL.md").is_file():
            return direct
        if root.is_dir():
            for match in root.glob(f"**/{name}/SKILL.md"):
                return match.parent
    return None


def read_frontmatter(skill_md: Path) -> dict[str, str]:
    try:
        text = skill_md.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        text = skill_md.read_text(errors="replace")
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end == -1:
        return {}
    data: dict[str, str] = {}
    for line in text[3:end].splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        data[key.strip()] = value.strip().strip("\"'")
    return data


def parse_source_arg(values: list[str]) -> dict[str, str]:
    sources: dict[str, str] = {}
    for value in values:
        if "=" not in value:
            raise SystemExit(f"--source must use candidate=/path/or/url format: {value}")
        key, source = value.split("=", 1)
        normalized = normalize_name(key)
        if not normalized or not source.strip():
            raise SystemExit(f"invalid --source value: {value}")
        sources[normalized] = source.strip()
    return sources


def scan_risks(skill_dir: Path) -> tuple[str, list[str], int]:
    findings: list[tuple[str, str, str]] = []
    scanned_files = 0
    for path in skill_dir.rglob("*"):
        if not path.is_file() or path.stat().st_size > 2_000_000:
            continue
        if ".git" in path.parts:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        scanned_files += 1
        rel = str(path.relative_to(skill_dir))
        for line_no, line in enumerate(text.splitlines(), start=1):
            if line_is_explanatory(line):
                continue
            for level, label, pattern in RISK_PATTERNS:
                if pattern.search(line):
                    findings.append((level, label, f"{rel}:{line_no}"))

    if any(level == "high" for level, _, _ in findings):
        risk = "high"
    elif findings:
        risk = "medium"
    else:
        risk = "low"

    warnings = [f"{level}: {label} ({rel})" for level, label, rel in findings]
    return risk, sorted(set(warnings)), scanned_files


def resolve_source_dir(source: str) -> Path | None:
    if re.match(r"^https?://", source):
        return None
    path = Path(source).expanduser()
    if path.is_file():
        return path.parent
    if path.is_dir():
        return path
    return None


def github_source_parts(url: str) -> tuple[str, str, str, str] | None:
    parsed = urllib.parse.urlparse(url)
    if parsed.netloc.lower() not in {"github.com", "www.github.com"}:
        return None
    parts = [part for part in parsed.path.split("/") if part]
    if len(parts) < 4 or parts[2] not in {"blob", "tree"}:
        return None
    owner, repo, mode, ref = parts[:4]
    source_path = "/".join(parts[4:]) if len(parts) > 4 else ""
    if mode == "blob" and not source_path:
        return None
    if mode == "blob" and source_path.endswith("/SKILL.md"):
        source_path = source_path[: -len("/SKILL.md")]
    elif mode == "blob" and source_path == "SKILL.md":
        source_path = ""
    return owner, repo, ref, source_path


def github_api_json(url: str) -> object:
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "skill-install-advisor",
        },
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def download_github_contents(owner: str, repo: str, ref: str, path: str, destination: Path) -> None:
    quoted_path = urllib.parse.quote(path)
    contents_path = f"contents/{quoted_path}" if quoted_path else "contents"
    api_url = f"https://api.github.com/repos/{owner}/{repo}/{contents_path}?ref={urllib.parse.quote(ref)}"
    data = github_api_json(api_url)
    if isinstance(data, dict) and data.get("type") == "file":
        download_url = data.get("download_url")
        if not download_url:
            return
        destination.parent.mkdir(parents=True, exist_ok=True)
        request = urllib.request.Request(str(download_url), headers={"User-Agent": "skill-install-advisor"})
        with urllib.request.urlopen(request, timeout=30) as response:
            destination.write_bytes(response.read())
        return

    if not isinstance(data, list):
        return

    for item in data:
        if not isinstance(item, dict):
            continue
        item_type = item.get("type")
        item_path = item.get("path", "")
        rel_path = Path(item_path).relative_to(path) if path else Path(item_path)
        target = destination / rel_path
        if item_type == "file":
            download_url = item.get("download_url")
            if not download_url:
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            request = urllib.request.Request(str(download_url), headers={"User-Agent": "skill-install-advisor"})
            with urllib.request.urlopen(request, timeout=30) as response:
                target.write_bytes(response.read())
        elif item_type == "dir":
            download_github_contents(owner, repo, ref, item_path, destination / rel_path)


def fetch_github_source(source: str, candidate: str, tmp_dir: Path | None = None) -> tuple[Path | None, str | None]:
    parts = github_source_parts(source)
    if not parts:
        return None, "URL is not a supported GitHub blob/tree source"
    owner, repo, ref, source_path = parts
    base_tmp = tmp_dir or Path(tempfile.gettempdir())
    base_tmp.mkdir(parents=True, exist_ok=True)
    destination = Path(tempfile.mkdtemp(prefix=f"skill-advisor-{candidate}-", dir=str(base_tmp)))
    try:
        download_github_contents(owner, repo, ref, source_path, destination)
    except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
        return None, f"failed to fetch GitHub source: {exc}"
    return destination, None


def line_is_explanatory(line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return True
    if "re.compile(" in stripped or "RISK_PATTERNS" in stripped:
        return True
    if stripped.startswith("#"):
        return True
    return bool(EXPLANATORY_LINE_RE.search(stripped))


def audit_candidate(
    name: str,
    roots: list[Path],
    sources: dict[str, str],
    fetch_remote: bool,
    tmp_dir: Path | None = None,
) -> dict[str, object]:
    normalized = normalize_name(name)
    result: dict[str, object] = {
        "candidate": name,
        "normalized": normalized,
        "valid_skill_name": bool(NAME_RE.match(normalized)),
        "installed": False,
        "scan_status": "not_started",
        "source": sources.get(normalized),
        "path": None,
        "risk": "not_scanned",
        "scanned_files": 0,
        "warnings": [],
        "frontmatter": {},
    }
    if not result["valid_skill_name"]:
        result["scan_status"] = "invalid_name"
        result["warnings"] = ["invalid Codex skill folder/name format"]
        return result

    skill_dir = None
    if normalized in sources:
        source_dir = resolve_source_dir(sources[normalized])
        if source_dir:
            skill_dir = source_dir
            result["scan_status"] = "provided_source_scanned"
        elif fetch_remote and re.match(r"^https?://", sources[normalized]):
            fetched_dir, error = fetch_github_source(sources[normalized], normalized, tmp_dir)
            if fetched_dir:
                skill_dir = fetched_dir
                result["scan_status"] = "remote_source_fetched_and_scanned"
            else:
                result["scan_status"] = "source_url_not_fetched"
                result["warnings"] = [error or "source URL could not be fetched"]
                return result
        else:
            result["scan_status"] = "source_url_not_fetched"
            result["warnings"] = [
                "source is a URL or unavailable path; pass --fetch-remote for supported GitHub sources or clone it before static scanning"
            ]
            return result

    if not skill_dir:
        skill_dir = find_skill_dir(normalized, roots)
        if skill_dir:
            result["scan_status"] = "local_source_scanned"

    if not skill_dir:
        result["scan_status"] = "no_source"
        result["warnings"] = [
            "no local or provided source found; risk scan could not be performed"
        ]
        return result

    skill_md = skill_dir / "SKILL.md"
    frontmatter = read_frontmatter(skill_md) if skill_md.is_file() else {}
    risk, warnings, scanned_files = scan_risks(skill_dir)
    result.update(
        {
            "installed": bool(find_skill_dir(normalized, roots)),
            "path": str(skill_dir),
            "risk": risk,
            "scanned_files": scanned_files,
            "warnings": warnings,
            "frontmatter": frontmatter,
        }
    )
    if not skill_md.is_file():
        result["warnings"] = list(result["warnings"]) + [
            "provided source does not contain SKILL.md at its root"
        ]
    if frontmatter.get("name") and frontmatter["name"] != normalized:
        result["warnings"] = list(result["warnings"]) + [
            f"frontmatter name differs: {frontmatter['name']}"
        ]
    return result


def format_text(results: list[dict[str, object]]) -> str:
    lines = []
    for item in results:
        state = "installed" if item["installed"] else "not-found"
        lines.append(
            f"- {item['normalized']}: {state}, scan={item['scan_status']}, "
            f"risk={item['risk']}, files={item['scanned_files']}"
        )
        for warning in item["warnings"]:
            lines.append(f"  - {warning}")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit locally inspectable skill candidates.")
    parser.add_argument("--article", help="Path to article text/markdown to extract candidate mentions from.")
    parser.add_argument("--skills", help="Comma/newline separated candidate skill names.")
    parser.add_argument("--scan-root", action="append", default=[], help="Additional skill root to scan.")
    parser.add_argument(
        "--source",
        action="append",
        default=[],
        help="Candidate source to scan, as candidate=/path/to/source. URL values are recorded but not fetched.",
    )
    parser.add_argument(
        "--fetch-remote",
        action="store_true",
        help="Fetch supported GitHub blob/tree sources from --source into the platform temp directory before scanning.",
    )
    parser.add_argument(
        "--tmp-dir",
        help="Directory for temporary remote-source fetches. Defaults to the platform temp directory.",
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON.")
    args = parser.parse_args()

    candidates = parse_skills_arg(args.skills)
    if args.article:
        text = Path(args.article).expanduser().read_text(encoding="utf-8", errors="replace")
        candidates.extend(extract_mentions(text))

    deduped = sorted({candidate for candidate in candidates if candidate})
    roots = default_roots(args.scan_root)
    sources = parse_source_arg(args.source)
    tmp_dir = Path(args.tmp_dir).expanduser() if args.tmp_dir else None
    results = [audit_candidate(candidate, roots, sources, args.fetch_remote, tmp_dir) for candidate in deduped]
    output = {"scan_roots": [str(root) for root in roots], "results": results}

    if args.json:
        print(json.dumps(output, ensure_ascii=False, indent=2))
    else:
        print(format_text(results) if results else "No candidates found.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
