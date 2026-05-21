# PR Review Agent

An automated pull request reviewer that uses a multi-agent LLM system to analyze code diffs for security vulnerabilities, performance issues, and style violations. It posts a consolidated review summary directly to GitHub PRs, with full observability via LangSmith tracing.

## Architecture

The system is orchestrated as a LangGraph state graph:

```
orchestrator
    ├── security_agent    (hardcoded secrets, injection vulnerabilities)  ─┐
    ├── performance_agent (O(n²) patterns, N+1 queries, memory issues)    ─┼─► critic ─► reporter ─► post_to_github
    └── style_agent       (PEP8, naming, missing docstrings, dead code)   ─┘
```

- **Orchestrator** — fetches the PR diff from GitHub and splits it into per-file chunks
- **Security / Performance / Style agents** — run in parallel, each analyzing chunks with a specialized prompt
- **Critic** — reconciles findings across all three agents, removes duplicates, assigns severity
- **Reporter** — formats findings into a readable summary report
- **post_to_github** — posts the report as a PR comment (set `DRY_RUN=true` to print locally instead)

## Tech Stack

| Component | Tool |
|---|---|
| Agent orchestration | LangGraph |
| LLM wrapper | LangChain (`langchain-groq`) |
| LLM | Groq (`llama-3.3-70b-versatile`) |
| Observability | LangSmith |
| GitHub API | PyGithub |

## Setup

```bash
git clone https://github.com/madhura1396/pr-review-agent.git
cd pr-review-agent
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

Copy `.env.example` to `.env` and fill in your credentials:

```
GROQ_API_KEY=your_groq_api_key
GITHUB_TOKEN=your_github_token
LANGSMITH_API_KEY=your_langsmith_api_key
LANGSMITH_PROJECT=pr-review-agent
DRY_RUN=true   # set to false to post comments to GitHub
```

## Usage

```bash
python main.py https://github.com/owner/repo/pull/123
```

Traces will appear in your LangSmith project at [smith.langchain.com](https://smith.langchain.com).
