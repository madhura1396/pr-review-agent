# LangGraph Reference Notes
*Based on building the PR Review Agent*

---

## 1. What is LangGraph and Why Does It Exist

LangGraph is a library for building workflows where the steps involve LLM calls. You define steps as nodes and connections between them as edges. LangGraph handles running them in the right order.

### The problem with simple function chaining

Without LangGraph you write:

```python
chunks = fetch_pr(url)
security = run_security_agent(chunks)
performance = run_performance_agent(chunks)
style = run_style_agent(chunks)
critic_output = run_critic(security, performance, style)
report = run_reporter(critic_output)
```

This works for simple linear flows. But it cannot handle:
- Running three agents in parallel
- Retrying a failed agent
- Conditionally skipping steps
- Cycles and self-correction loops
- Human approval steps
- Resuming after failures

LangGraph handles all of this through the graph structure.

### The relationship between LangChain and LangGraph

These are two different things that work together:
- **LangChain** — talks to LLMs. Handles the API call, the prompt, the response. One call at a time.
- **LangGraph** — controls the flow between multiple steps. Decides what runs when and in what order.

In our project:

```python
# LangChain — talks to Groq
from langchain_groq import ChatGroq
llm = ChatGroq(model="llama-3.3-70b-versatile")
response = llm.invoke("review this code")

# LangGraph — controls the flow
graph.add_edge("orchestrator", "security_agent")
graph.add_edge("security_agent", "critic")
```

LangChain does not know there are multiple agents. LangGraph does not know how to talk to an LLM. They work together but solve completely different problems.

---

## 2. Core Concepts

### What is a Graph

A graph is a data structure made of nodes connected by edges. LangGraph uses a **directed graph** — edges have a direction, data flows one way.

Our pipeline is a **DAG** (Directed Acyclic Graph) — no cycles, edges have direction:

```
START → orchestrator → security_agent  → critic → reporter → END
                     → performance_agent ↗
                     → style_agent ↗
```

LangGraph also supports **cycles** for self-correction loops — when an agent evaluates its own output and loops back if quality is insufficient.

### Nodes

A node is a Python function that:
1. Reads from shared state
2. Does work (calls LLM, fetches data, etc.)
3. Returns a dict of what it wants to write back to state

```python
def security_agent(state: PRReviewState) -> dict:
    chunks = state.get("diff_chunks", [])
    # ... calls LLM ...
    return {"security_findings": findings}
```

You register a function as a node:

```python
graph.add_node("security_agent", security_agent)
```

### Edges

Edges connect nodes and define execution order.

**Regular edge** — always goes from A to B:
```python
graph.add_edge("critic", "reporter")
```

**Parallel edges** — fan out to multiple nodes simultaneously:
```python
graph.add_edge("orchestrator", "security_agent")
graph.add_edge("orchestrator", "performance_agent")
graph.add_edge("orchestrator", "style_agent")
```

All three start at the same time. LangGraph knows to wait for all three before running critic.

**Conditional edge** — routes to different nodes based on state:
```python
def route_after_orchestrator(state: PRReviewState) -> str:
    if state.get("error") is not None:
        return "end"
    return "continue"

graph.add_conditional_edges(
    "orchestrator",
    route_after_orchestrator,
    {
        "end": END,
        "continue": ["security_agent", "performance_agent", "style_agent"],
    },
)
```

The routing function reads state and returns a string. The dict maps strings to destination nodes.

### State and TypedDict

State is the shared notepad that every agent reads from and writes to.

**Why not pass data directly between functions?**

In parallel execution, three agents finish at different times. How do you collect all three results and pass them to critic? State solves this — each agent writes to its own field, LangGraph waits until all three have written before running critic.

**Why TypedDict instead of a plain dict?**

A plain dict works at runtime but Python has no idea what keys exist or what type each value should be. TypedDict makes the structure explicit:

```python
from typing_extensions import TypedDict
from typing import Optional
from tools.github_tool import DiffChunk

class PRReviewState(TypedDict):
    pr_url: str
    diff_chunks: list[DiffChunk]
    security_findings: list[str]
    performance_findings: list[str]
    style_findings: list[str]
    critic_output: list[str]
    final_report: str
    error: Optional[str]
```

Benefits:
- Editor autocompletes key names
- Typos in key names get caught immediately
- Every agent knows exactly what fields exist and what types they hold
- It is a contract every agent agrees to

TypedDict behaves exactly like a dict at runtime. LangGraph requires state to be dict-like so it can merge partial updates.

**Why use `state.get()` instead of `state[]`?**

```python
state["error"]      # crashes with KeyError if key missing
state.get("error")  # returns None if key missing
```

TypedDict enforces schema at type-checking level but not at runtime. `state.get()` is defensive — handles unexpected incomplete state without crashing.

### Compile and Invoke

```python
# workflow.py — define and compile
graph = StateGraph(PRReviewState)
graph.add_node(...)
graph.add_edge(...)
compiled_graph = graph.compile()

# main.py — run it
output = compiled_graph.invoke(initial_state)
```

**`compile()` does three things:**
1. Validates the graph — every node has a path to END
2. Builds an execution plan — determines dependency order, which nodes run in parallel
3. Returns a runnable object with an `invoke()` method

**`invoke()` follows the execution plan:**
1. Starts with initial state
2. Runs nodes when their dependencies are satisfied
3. Merges partial state updates after each node
4. Returns the final complete state when END is reached

**Why initialize all state fields upfront:**

```python
initial_state = {
    "pr_url": pr_url,
    "diff_chunks": [],
    "security_findings": [],
    "performance_findings": [],
    "style_findings": [],
    "critic_output": [],
    "final_report": "",
    "error": None,
}
```

Guarantees every key exists from the start. Any agent can safely read any field without risking KeyErrors. Also ensures LangGraph merges cleanly — the key always exists, no ambiguity.

### Parallel Execution

When multiple edges leave the same node, LangGraph runs all target nodes simultaneously:

```python
graph.add_conditional_edges(
    "orchestrator",
    route_after_orchestrator,
    {
        "continue": ["security_agent", "performance_agent", "style_agent"],
    },
)
```

LangGraph tracks incoming edges for each node. Critic has three incoming edges. LangGraph only runs critic after all three agents have completed and written their findings to state.

**Why parallel instead of sequential?**

Security, performance, and style are independent concerns. The security agent does not need to know about style violations before it can do its job. Running in parallel means total time is roughly equal to the slowest single agent rather than the sum of all three.

**Why sequential would make sense:**

If agents needed each other's context — for example if the performance agent needed to know what lines security already flagged to avoid duplicate findings. Sequential would let each agent read the previous agent's output. We solve this differently using the critic layer instead.

---

## 3. Advanced Concepts

### Reducers

**The problem:**

When multiple parallel agents write to the same state key simultaneously, LangGraph defaults to last-write-wins. The last agent to finish overwrites the others. Data is lost.

**When this happens:**
- If all agents wrote to one shared `findings` key instead of separate keys
- When spinning up N parallel agents per file (one agent per file, all writing to `security_findings`)

**Our design avoids this:**

We gave each agent its own key — `security_findings`, `performance_findings`, `style_findings`. Each key has exactly one writer. No conflicts, no reducer needed.

**How reducers work:**

```python
from typing import Annotated
from operator import add

class PRReviewState(TypedDict):
    all_findings: Annotated[list[str], add]
```

`Annotated[list[str], add]` tells LangGraph: when two agents write to `all_findings` simultaneously, combine them using `add` (list concatenation) instead of overwriting.

```python
# agent 1 writes
{"all_findings": ["CRITICAL | main.py | 14 | hardcoded key"]}

# agent 2 writes
{"all_findings": ["WARNING | main.py | 45 | N+1 query"]}

# reducer combines
all_findings = ["CRITICAL | main.py | 14 | hardcoded key", "WARNING | main.py | 45 | N+1 query"]
```

**What `Annotated` is:**

A Python typing tool that attaches metadata to a type hint:
```
Annotated[actual_type, metadata]
```

The first argument is the real type. Everything after is metadata. LangGraph reads the reducer function from this metadata during `compile()`.

**Reducers are not always concatenation:**

```python
Annotated[list[str], add]                                         # concatenate lists
Annotated[str, lambda old, new: new]                              # keep latest
Annotated[int, lambda old, new: old + new]                        # sum counts
Annotated[str, lambda old, new: old if old == "CRITICAL" else new] # keep highest severity
```

### Checkpointing

**The problem:**

If the reporter agent fails after security, performance, style, and critic all completed successfully, the entire graph crashes. All that work and those LLM calls are wasted. You restart from scratch.

**What checkpointing does:**

Saves state after every node completes. If a node fails, resume from the last checkpoint — retry only the failed node.

**Three checkpointer types:**

| Checkpointer | Storage | Persists across restarts | Use case |
|---|---|---|---|
| MemorySaver | RAM | No | Development, short runs |
| SqliteSaver | Local file | Yes | Single user, local app |
| PostgresSaver | PostgreSQL | Yes | Production, multiple users |

**How to add it:**

```python
from langgraph.checkpoint.memory import MemorySaver

checkpointer = MemorySaver()
graph = workflow.compile(checkpointer=checkpointer)
```

The checkpointer is attached to the compiled graph permanently. Every `invoke()` call uses it automatically.

**Thread ID:**

```python
config = {"configurable": {"thread_id": pr_url}}
output = graph.invoke(initial_state, config=config)
```

Thread ID identifies each run. Checkpoints are saved under this ID. To resume a failed run, pass the same `thread_id` — LangGraph finds the checkpoint and skips completed nodes.

We use the PR URL as thread ID because each PR is unique. Same PR failing and retrying uses the same thread ID and resumes correctly.

**Why MemorySaver for GitHub Actions:**

Our pipeline takes 10-15 seconds. Restarting from scratch costs 10-15 seconds. The resume benefit does not justify PostgreSQL overhead for such a short pipeline. MemorySaver is the right call.

PostgresSaver makes sense for long-running agents (minutes or hours) where restarting from scratch is genuinely costly.

### Human in the Loop

**The problem:**

LLMs hallucinate. The security agent might flag a CRITICAL issue that is actually a false positive. If the agent automatically posts this to a public PR, the developer panics, wastes time investigating, and loses trust in the tool.

**What human in the loop does:**

Pauses the graph before posting, shows a human the findings, waits for approval, then resumes.

**Why only for CRITICAL findings:**

WARNING and SUGGESTION findings are low stakes. False positives are annoying but not damaging. CRITICAL findings posted publicly are a reputational failure for the tool. Only high stakes findings need human review.

**How it works:**

```python
from langgraph.types import interrupt

def human_approval(state: PRReviewState) -> dict:
    critical = [f for f in state.get("critic_output", []) if "CRITICAL" in f.upper()]
    interrupt({
        "message": "CRITICAL findings require approval before posting.",
        "findings": critical,
    })
    return {}
```

`interrupt()` pauses the graph and sends data to the caller. The graph state is saved via checkpointer (this is why checkpointing is required for human in the loop).

**Routing to human approval only when needed:**

```python
def route_after_critic(state: PRReviewState) -> str:
    if any("CRITICAL" in f.upper() for f in state.get("critic_output", [])):
        return "needs_approval"
    return "proceed"
```

Clean PRs with no CRITICAL findings skip human approval entirely and go straight to reporter.

**Why `.upper()`:**

LLMs do not guarantee consistent casing. `.upper()` converts to uppercase before checking so `"critical"`, `"Critical"`, and `"CRITICAL"` all match.

**Resuming after approval in `main.py`:**

```python
from langgraph.types import Command

while "__interrupt__" in output:
    # show human the findings
    answer = input("Post this review to GitHub? [y/N]: ").strip().lower()
    if answer != "y":
        sys.exit(0)
    output = graph.invoke(Command(resume=True), config=config)
```

`Command(resume=True)` tells LangGraph the human approved — continue from the checkpoint. The while loop handles multiple interrupts if the graph has more than one interrupt point.

**Checkpointing is required:**

When the graph pauses at `interrupt()`, the state must be saved somewhere so it can be resumed. Without a checkpointer the paused state is lost and the graph cannot resume.

### Streaming

**The problem:**

With `graph.invoke()` the user stares at a blank terminal for 10-15 seconds then sees the full report appear at once. No sense of progress. Looks like it crashed.

**What streaming does:**

Yields output as each node completes instead of waiting for the full graph.

```python
for event in graph.stream(initial_state, config):
    for node_name, node_output in event.items():
        print(f"✓ {node_name} completed")
```

**Two streaming modes:**

```python
graph.stream(initial_state, stream_mode="updates")  # yields state updates per node
graph.stream(initial_state, stream_mode="values")   # yields full state per node
```

Not implemented in our project. Mentioned as a known improvement for interviews.

### Memory

**The difference from checkpointing:**
- **Checkpointing** — saves state within a single run so you can resume if it fails
- **Memory** — saves information across multiple separate runs so the agent remembers past interactions

**When memory is relevant:**

Chatbots where the user refers to previous conversations. Not relevant for our PR review agent — each review is independent. Knowing PR #5 had a hardcoded password does not help when reviewing PR #6.

**When memory would become relevant:**

If the agent built a codebase profile over time — learning recurring patterns and biasing attention accordingly. "This codebase tends to have N+1 query problems, pay extra attention to database calls."

### Subgraphs

**The problem:**

Adding multi-language support to a single graph creates 20+ nodes. The graph becomes a mess to read and debug.

**What subgraphs are:**

A complete compiled graph that runs as a single node inside a parent graph.

```python
# build python subgraph
python_graph = StateGraph(PythonReviewState)
python_graph.add_node("security", python_security_agent)
python_graph.add_node("performance", python_performance_agent)
python_compiled = python_graph.compile()

# use as a node in parent graph
parent_graph.add_node("python_review", python_compiled)
```

Benefits:
- Each subgraph is independently testable
- Parent graph stays clean and readable
- Subgraphs are reusable across projects

**When relevant for our project:**

Not needed now — Python only. Would become relevant with multi-language support. Each language's review pipeline becomes its own subgraph.

---

## 4. Our PR Review Agent Graph

### Full structure

```
START
  ↓
orchestrator (fetches PR diff, stores in state)
  ↓
route_after_orchestrator()
  ↓ error → END
  ↓ ok →
    ├── security_agent    (parallel)
    ├── performance_agent (parallel)
    └── style_agent       (parallel)
         ↓ (all three complete)
       critic (reconciles, deduplicates, ranks by severity)
         ↓
       route_after_critic()
         ↓ CRITICAL findings → human_approval → reporter
         ↓ no CRITICAL → reporter
                            ↓
                        post_to_github
                            ↓
                           END
```

### Key architectural decisions

**Why parallel agents:** Security, performance, and style are independent concerns. Parallel execution means total time equals the slowest single agent, not the sum of all three.

**Why separate state keys per agent:** Avoids reducer complexity. Each agent has exactly one key it writes to. No concurrent write conflicts.

**Why the critic layer:** Three independent agents produce overlapping, unranked, inconsistently formatted findings. Critic deduplicates, resolves severity conflicts, ranks by CRITICAL/WARNING/SUGGESTION. Without critic, the reporter receives noise.

**Why conditional edge after orchestrator:** If fetching the PR fails (bad token, private repo, rate limit), there is no point running six agents on empty data. Stop immediately with a clear error message.

**Why human in the loop only for CRITICAL:** Low stakes findings (WARNING, SUGGESTION) can post automatically. CRITICAL false positives posted publicly damage trust. Human review is a quality gate for high stakes findings only.

**Why MemorySaver:** Our pipeline takes 10-15 seconds. Restarting from scratch on failure costs 10-15 seconds. The resume benefit does not justify PostgreSQL overhead. MemorySaver is appropriate for short-running pipelines.

---

## 5. Interview Q&A

**Why LangGraph over raw function chaining?**

Raw chaining cannot handle parallel execution, cycles, conditional routing, or human in the loop. LangGraph handles all of these through the graph structure and gives you checkpointing, streaming, and observability via LangSmith for free.

**Why parallel agents instead of sequential?**

Security, performance, and style are independent concerns. Parallel execution means total time equals the slowest agent, not the sum of all three. Sequential would only make sense if agents needed each other's context — which we handle via the critic layer instead.

**What does the critic agent do and why does it exist?**

Three independent agents produce overlapping and unranked findings. The critic deduplicates findings about the same issue, resolves severity conflicts by keeping the highest severity, and ranks everything CRITICAL first, then WARNING, then SUGGESTION. Without critic the reporter gets noise and the output is unprofessional.

**How does state flow through the graph?**

Every agent reads the full state and returns a partial dict of only what it changed. LangGraph merges that partial dict into the full state. Agents communicate through state rather than directly with each other. By the time critic runs, security, performance, and style findings are all available in state.

**What happens if an agent fails?**

Currently the graph crashes and returns whatever state was accumulated. A production improvement would be try/except inside each agent that writes an error flag to state, combined with a conditional edge that routes to a fallback or END with a partial report.

**How would you scale this to 50 files?**

Currently we loop over files sequentially inside each agent — one LLM call per file. For 50 files that is 50 sequential calls per agent. The alternative is spawning one agent per file in parallel, all writing to a shared findings key using a reducer with `Annotated[list[str], add]`. Faster but more complex.

**How would you add multi-language support?**

Extract each language's review pipeline into its own subgraph — `python_review`, `javascript_review`, `go_review`. Add a language detection node after orchestrator that routes to the appropriate subgraph. Parent graph stays clean. Each language subgraph is independently testable.

**What is a reducer and when do you need one?**

A reducer is a merge function that tells LangGraph how to combine values when multiple agents write to the same state key simultaneously. Default behavior is last-write-wins which causes data loss. We avoided reducers by giving each agent its own state key. You need reducers when you have dynamic parallelism — N agents all writing to the same shared key.

**How does human in the loop work?**

A routing function after critic checks for CRITICAL findings. If any exist, the graph routes to a `human_approval` node that calls `interrupt()` to pause the graph and send findings to the caller. The caller shows the human the findings and waits for input. If approved, `Command(resume=True)` resumes from the checkpoint. Checkpointing is required because the paused state must be saved somewhere between the pause and resume.

**How would you add streaming?**

Replace `graph.invoke()` with `graph.stream()` and iterate over events. Each event contains the node name and its output as it completes. Use `stream_mode="updates"` to yield state updates after each node, giving the user real-time progress instead of waiting for the full report.

**Why does the prompt quality improve with separate agents?**

Attention weights are a zero-sum distribution across all tokens in a prompt. When a prompt covers security, performance, and style simultaneously, attention is split three ways. Each concern gets roughly one third of the attention it would get in a focused prompt. Security-relevant patterns in the code receive lower attention weights and findings are less precise. Focused prompts keep attention concentrated on one concern, producing deeper and more accurate findings.
