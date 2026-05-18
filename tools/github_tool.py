import os
import re
from dataclasses import dataclass
from typing import Optional

from dotenv import load_dotenv
from github import Github, GithubException, UnknownObjectException

load_dotenv()


@dataclass
class DiffChunk:
    filename: str
    diff: str
    start_line: Optional[int]
    end_line: Optional[int]


def parse_pr_url(url: str) -> tuple[str, str, int]:
    """Extract owner, repo, and PR number from a GitHub PR URL."""
    pattern = r"https://github\.com/([^/]+)/([^/]+)/pull/(\d+)"
    match = re.match(pattern, url.strip())
    if not match:
        raise ValueError(f"Invalid GitHub PR URL: {url!r}")
    owner, repo, pr_number = match.groups()
    return owner, repo, int(pr_number)


def _extract_line_range(patch: str) -> tuple[Optional[int], Optional[int]]:
    """Parse the first @@ hunk header to get starting line numbers."""
    if not patch:
        return None, None
    match = re.search(r"@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@", patch)
    if not match:
        return None, None
    start = int(match.group(1))
    count = int(match.group(2)) if match.group(2) is not None else 1
    end = start + count - 1
    return start, end


def fetch_pr_chunks(pr_url: str) -> list[DiffChunk]:
    """
    Fetch a GitHub PR and return its diff parsed into per-file chunks.

    Raises:
        ValueError: for a malformed PR URL
        PermissionError: for auth failure or private repo access
        LookupError: for a repo or PR that doesn't exist
        RuntimeError: for unexpected GitHub API errors
    """
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        raise PermissionError("GITHUB_TOKEN is not set in environment / .env")

    owner, repo_name, pr_number = parse_pr_url(pr_url)

    g = Github(token)

    try:
        repo = g.get_repo(f"{owner}/{repo_name}")
    except UnknownObjectException:
        raise LookupError(f"Repository '{owner}/{repo_name}' not found or not accessible")
    except GithubException as e:
        if e.status == 401:
            raise PermissionError("GitHub authentication failed — check your GITHUB_TOKEN")
        raise RuntimeError(f"GitHub API error fetching repo: {e}")

    try:
        pr = repo.get_pull(pr_number)
    except UnknownObjectException:
        raise LookupError(f"PR #{pr_number} not found in '{owner}/{repo_name}'")
    except GithubException as e:
        raise RuntimeError(f"GitHub API error fetching PR: {e}")

    try:
        files = pr.get_files()
    except GithubException as e:
        raise RuntimeError(f"GitHub API error fetching PR files: {e}")

    chunks: list[DiffChunk] = []
    for f in files:
        patch = f.patch or ""
        start_line, end_line = _extract_line_range(patch)
        chunks.append(DiffChunk(
            filename=f.filename,
            diff=patch,
            start_line=start_line,
            end_line=end_line,
        ))

    return chunks


if __name__ == "__main__":
    TEST_PR_URL = "https://github.com/psf/requests/pull/6655"
    print(f"Fetching PR diff from: {TEST_PR_URL}\n")
    try:
        chunks = fetch_pr_chunks(TEST_PR_URL)
    except (ValueError, PermissionError, LookupError, RuntimeError) as e:
        print(f"Error: {e}")
        raise SystemExit(1)

    print(f"Found {len(chunks)} file(s) in diff:\n")
    for chunk in chunks:
        print(f"  File:  {chunk.filename}")
        print(f"  Lines: {chunk.start_line} – {chunk.end_line}")
        preview = chunk.diff[:200].replace("\n", "\n         ") if chunk.diff else "(no patch)"
        print(f"  Diff:  {preview}")
        print()
