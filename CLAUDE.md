# PR Review Agent

## Architecture
Multi-agent PR review system built with LangGraph, LangChain, and Groq.

## Agents
- Orchestrator: manages graph state, routes diff chunks to specialist agents
- Security Agent: hardcoded secrets, injection vulnerabilities, insecure patterns
- Performance Agent: O(n²) patterns, N+1 queries, memory issues
- Style Agent: PEP8, naming, missing docstrings, dead code
- Critic Agent: reconciles findings, removes duplicates, assigns severity
- Reporter Agent: formats inline comments + summary report, posts to GitHub

## Stack
- LangGraph for agent orchestration
- LangChain (langchain-groq) as LLM wrapper
- Groq (llama-3.3-70b-versatile) as LLM
- PyGitHub for GitHub API integration
- LangSmith for observability and tracing
- DeepEval for LLM evaluation
- GitHub Actions for CI/CD
- Python 3.11+

## Gaps this project addresses
- Orchestration: LangGraph + LangChain
- Observability: LangSmith
- Evaluation: DeepEval
- CI/CD: GitHub Actions

## Build Order
1. GitHub tool (fetch and parse PR diff)
2. LangGraph graph skeleton
3. Security agent end to end (langchain-groq as LLM wrapper)
4. Performance and Style agents
5. Critic agent
6. Reporter + GitHub posting
7. LangSmith tracing
8. DeepEval evaluation harness
9. GitHub Actions CI/CD workflow

## Environment Variables
GROQ_API_KEY
GITHUB_TOKEN
LANGSMITH_API_KEY
LANGSMITH_PROJECT
