# Idea Diligence Agent

> An autonomous AI agent that takes a raw product idea, researches competitors, markets, pricing, and revenue in the background, challenges your assumptions, and delivers an evidence-backed **GO**, **MODIFY**, or **KILL** verdict.

**Hackathon:** AWS Strands Agents SDK Hackathon  
**Track:** Professional Agents  
**Deadline:** Sep 15, 2026 @ 1:00am GMT+1  
**Team:** Edmund & Gokul

---

## What It Does

You give the agent a product idea in plain English. It:

1. **Researches the problem** — who has it, how painful it is, how they currently cope
2. **Finds competitors** — direct competitors, indirect alternatives, their pricing, their weaknesses
3. **Evaluates the economics** — can it make money? what should it charge? how big is the market?
4. **Challenges assumptions** — it doesn't just agree with you; if the idea has a fatal flaw, it says so
5. **Delivers a verdict** — **GO** (build it), **MODIFY** (pivot this specific thing), or **KILL** (don't waste your time)

The user does nothing during the investigation. Submit an idea → get a verdict. Zero babysitting.

---

## Architecture Overview

```
User submits idea
        │
        ▼
┌──────────────────────┐
│ Safety & Scope Gate  │  ← Boundary 1: Rejects adversarial prompts & out-of-scope ideas
└──────────┬───────────┘
           │ ACCEPT
           ▼
┌──────────────────────┐
│   DiligenceState     │  ← Canonical state for the session
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│    Orchestrator      │  ← Controlled by Hard Runtime & Budget Governor (Boundary 2)
└──────────┬───────────┘     Triage unknowns by decision impact (Boundary 5)
           │
     ┌─────┴─────┐  ┌───────────┐  ┌───────────────┐
     │  Problem  │  │Competition│  │  Economics     │
     │   Agent   │  │   Agent   │  │    Agent       │
     └─────┬─────┘  └─────┬─────┘  └──────┬────────┘
           │              │               │
           └──────────────┼───────────────┘
                          │ Calls tools (Web search / Scraper)
                          ▼
            [Untrusted Web Content Boundary]  ← Boundary 3: Envelopes external text as inert XML
                          │
                          ▼
             Candidate Finding Proposals
                          │
                          ▼
            [State Authority & Update Layer]  ← Boundary 4: Validate Schema ➔ Policy ➔ Merge
                          │
                          ▼
                Update DiligenceState
                          │
                          ▼
                 Enough evidence?
                    ╱          ╲
                  NO           YES
                   │             │
            Loop back to      Render
            Orchestrator      Verdict
```

### Key Design & Governance Invariants

- **Adaptive loop, not a fixed pipeline.** The orchestrator decides what to research next based on what's currently unknown — not a rigid sequential chain.
- **Canonical DiligenceState & Session Isolation.** Single source of truth per investigation. No state leakage between sessions.
- **Evidence classification.** Every finding is classified as `FACT`, `ASSUMPTION`, `INFERENCE`, or `UNKNOWN`, preserving provenance and source URLs.
- **5 Defense-in-Depth Boundaries (Phase 2):**
  1. **Safety & Scope Gate:** Pre-flight screen rejects jailbreaks, malicious prompts, and off-topic requests before agent invocation.
  2. **Hard Runtime Budget Governor:** Deterministic limits in Python (`MAX_ITERATIONS = 5`, `MAX_TOOL_CALLS = 25`, `MAX_WALLCLOCK_SECONDS = 180s`) prevent runaway loops and cloud bill spikes.
  3. **Untrusted Web Content Boundary:** Web scrape content is quarantined in `<untrusted_external_evidence>` XML tags so third-party sites cannot perform indirect prompt injections.
  4. **Restricted Authority (Propose-Validate-Merge):** Specialist agents propose candidate findings; a deterministic Python layer validates schema, checks domain authorization, and verifies provenance before merging into state.
  5. **Decision-Impact Unknown Triage:** Unknowns are prioritized by decision impact (`CRITICAL` vs `LOW`), ensuring research targets thesis dealbreakers rather than trivia.

---

## Tech Stack

| Component | Technology | Why |
|---|---|---|
| Agent framework | **Strands Agents SDK** (Python) | Required by hackathon. We use the "agents-as-tools" pattern. |
| Foundation model | **Amazon Bedrock** — Claude Sonnet 4 | Strong reasoning + structured output. Strengthens our "built on AWS" score. |
| Data models | **Pydantic v2** | Type-safe, validated, serializable state. |
| Web research | **DuckDuckGo** (via `http_request`) | Free, no API key, works immediately. |
| Interface | **Python CLI** | MVP for hackathon demo. Web UI planned for Phase 3. |

---

## Project Structure

```
idea-diligence-agent/
├── requirements.txt              # Python dependencies
├── CHANGELOG.md                  # Phase progress tracking
├── brainstorming/                # Project design & discussion documents
│   ├── Idea Diligence Agent - Project.docx   # Full project spec (Edmund + Gokul points)
│   ├── Idea Diligence Agent - Project.pdf    # PDF export of the project spec
│   ├── Idea Diligence Agent - Security & Governance Architecture.docx  # Phase 2 security architecture (Word)
│   └── SECURITY_AND_GOVERNANCE_ARCHITECTURE.md                        # Phase 2 security architecture (Markdown)
├── scripts/                      # Utility and document generation scripts
│   ├── build_security_doc.py     # Generates styled Word doc for security architecture
│   ├── generate_pdf.py           # Generates styled PDF from docx
│   └── update_project_doc.py     # Injects synthesized points into spec
├── src/
│   ├── __init__.py               # Package marker
│   ├── main.py                   # CLI entry point
│   ├── models.py                 # DiligenceState + all Pydantic data models
│   ├── prompts.py                # System prompts for all 4 agents
│   ├── tools.py                  # Custom Strands tools (search, read, save)
│   └── agents/
│       ├── __init__.py           # Package marker
│       ├── orchestrator.py       # Orchestrator agent + agents-as-tools wiring
│       ├── problem_agent.py      # Problem Analysis specialist
│       ├── competition_agent.py  # Competition Analysis specialist
│       └── economics_agent.py    # Economics Analysis specialist
└── LICENSE                       # Apache 2.0
```

---

## Phase 1 Status: ✅ COMPLETE — Walking Skeleton

> **Goal:** Get the full project structure built end-to-end with all agents wired up, all imports verified, and Bedrock connectivity confirmed. Prove the SDK works before adding complexity.

### What Was Built

#### 1. Data Models ([`src/models.py`](src/models.py))

The `DiligenceState` — our canonical research state (Gokul's core architecture recommendation). Contains:

| Model | Purpose |
|---|---|
| `DiligenceState` | Top-level state: holds the idea, all findings, audit trail, and final verdict |
| `Evidence` | A single finding tagged with `EvidenceType` (FACT / ASSUMPTION / INFERENCE / UNKNOWN) |
| `CustomerSegment` | A target persona with pain points and size estimate |
| `Competitor` | A competing product with pricing, strengths, weaknesses, URL |
| `BusinessModel` | A revenue model option (subscription, freemium, etc.) with reasoning |
| `ProblemAnalysis` | Problem statement, severity, existing workarounds, demand signals |
| `EconomicAnalysis` | Market size, revenue potential, unit economics |
| `VerdictReport` | Final GO/MODIFY/KILL decision with confidence, evidence, unknowns, assumptions |
| `ResearchAction` | Audit trail entry: which agent did what and when |

Helper methods on `DiligenceState`:
- `is_research_complete()` — check if a verdict has been rendered
- `has_budget_remaining()` — check if we're under the 5-cycle safety limit
- `get_critical_unknowns()` — collect all UNKNOWN evidence for the orchestrator
- `add_evidence()` / `log_action()` — structured helpers for agents to update state

#### 2. Custom Research Tools ([`src/tools.py`](src/tools.py))

Three `@tool`-decorated functions that the specialist agents call during research:

| Tool | What It Does |
|---|---|
| `search_web(query)` | Searches DuckDuckGo for competitors, pricing, market data. No API key needed. |
| `read_webpage(url)` | Fetches and extracts text from a URL. Truncates to 15K chars to stay within context limits. |
| `save_finding(category, content, evidence_type, source, confidence)` | Records a structured finding tagged as FACT/ASSUMPTION/INFERENCE/UNKNOWN with a source URL and confidence score (0.0–1.0). Returns JSON for the orchestrator to collect. |

#### 3. Agent System Prompts ([`src/prompts.py`](src/prompts.py))

Each agent has a detailed system prompt telling it exactly what to research and how to report findings:

| Prompt | Key Instructions |
|---|---|
| `PROBLEM_AGENT_PROMPT` | Research the problem, identify specific customer segments (not "small businesses" — "independent restaurants with 1-3 locations"), assess severity, find demand signals. Mark everything with evidence types. |
| `COMPETITION_AGENT_PROMPT` | Search for "[category] software", visit pricing pages, check G2/Capterra/Reddit reviews. Finding many competitors validates the market. Pay attention to pricing ranges. |
| `ECONOMICS_AGENT_PROMPT` | Be realistic, not optimistic. Base pricing on competitor data, not wishful thinking. "The market is huge" is useless; "$4.2B TAM based on [source]" is useful. |
| `ORCHESTRATOR_PROMPT` | Coordinate all three agents, synthesize findings, render a verdict. Be honest — don't default to GO because the user wants to hear it. |

#### 4. Specialist Agents ([`src/agents/`](src/agents/))

Three agent factory functions, each returning a configured `strands.Agent`:

| File | Agent | Model | Tools |
|---|---|---|---|
| `problem_agent.py` | Problem Analysis | Claude Sonnet 4 (Bedrock, us-east-1) | `search_web`, `read_webpage`, `save_finding` |
| `competition_agent.py` | Competition Analysis | Claude Sonnet 4 (Bedrock, us-east-1) | `search_web`, `read_webpage`, `save_finding` |
| `economics_agent.py` | Economics Analysis | Claude Sonnet 4 (Bedrock, us-east-1) | `search_web`, `read_webpage`, `save_finding` |

#### 5. Orchestrator ([`src/agents/orchestrator.py`](src/agents/orchestrator.py))

Uses the **agents-as-tools** pattern from Strands SDK:
- Each specialist agent is wrapped in a `@tool` function (`problem_agent`, `competition_agent`, `economics_agent`)
- The orchestrator LLM calls these tools to dispatch research tasks
- `run_diligence(idea: str) -> str` is the main entry point — give it an idea, get a verdict

#### 6. CLI Entry Point ([`src/main.py`](src/main.py))

```bash
# Pass idea as argument
python -m src.main "An app that helps small restaurants track food inventory"

# Or interactive mode (prompts for input)
python -m src.main
```

### What Was Verified

| Check | Status |
|---|---|
| Pydantic models import and instantiate correctly | ✅ |
| `EvidenceType` and `Verdict` enums work | ✅ |
| Strands SDK `Agent` and `@tool` imports work | ✅ |
| `BedrockModel` import works | ✅ |
| `strands_tools.http_request` import works | ✅ |
| Custom tools (`search_web`, `read_webpage`, `save_finding`) import | ✅ |
| System prompts import | ✅ |
| Orchestrator creation chain imports | ✅ |
| AWS credentials configured and authenticated | ✅ |
| All dependencies installed (`strands-agents`, `strands-agents-tools`, `pydantic`) | ✅ |

### What Was NOT Done Yet (Phase 2+)

- ❌ No live end-to-end test run with a real idea (agents built, not exercised yet)
- ❌ DiligenceState is not yet wired into the orchestrator loop (agents return strings, not structured state updates)
- ❌ No Strands Graph pattern yet (currently using agents-as-tools; Graph adds cyclic support)
- ❌ No verdict formatting / pretty output
- ❌ No web UI
- ❌ No demo video
- ❌ No README submission copy

---

## What's Next

### Phase 2: Multi-Agent Loop & Governance (Priority)

1. **Governance & Safety Package (`src/governance/`):**
   - `safety_gate.py`: Pre-flight screening to reject jailbreaks and off-topic tasks before invoking agents.
   - `budget_governor.py`: Deterministic circuit breakers capping iterations (max 5), tool calls (max 25), and wallclock time (180s).
   - `data_sanitizer.py`: Quarantine raw scraped web text inside inert `<untrusted_external_evidence>` XML tags.
   - `state_updater.py`: Propose ➔ Validate ➔ Policy Check ➔ Merge pipeline ensuring LLMs cannot freely mutate state.
2. **Decision-Impact Unknowns:** Upgrade `UnknownItem` in `src/models.py` to prioritize research on thesis dealbreakers (`CRITICAL`) over minor trivia (`LOW`).
3. **Adaptive Loop:** Orchestrator inspects prioritized UNKNOWNs → dispatches specialists → merges findings via governance layer → evaluates budget/evidence → repeat or render verdict.
4. **Live End-to-End Test:** Run the complete loop against a real business idea.

### Phase 3: Verdict & Polish

1. Build the verdict synthesis engine (GO / MODIFY / KILL with structured evidence)
2. Format output as a professional diligence report
3. Add a simple web UI or rich CLI for the demo video

### Phase 4: Demo & Submission

1. Record 5-min hackathon video
2. Write submission description
3. Finalize README
4. (Optional) Deploy on AWS AgentCore for bonus points
5. (Bonus) Post on builder.aws.com

---

## How to Run

### Prerequisites

- Python 3.12+
- An AWS account with **Amazon Bedrock** access enabled for `us.anthropic.claude-sonnet-4-20250514-v1:0` in `us-east-1`

### Setup

**1. Configure AWS credentials:**

```bash
aws configure
```

It will prompt you for four values:

```
AWS Access Key ID:     <your-access-key>
AWS Secret Access Key: <your-secret-key>
Default region name:   us-east-1
Default output format: json
```

> **Where to get these keys:** AWS Console → IAM → Users → your user → Security credentials → Create access key. Make sure your IAM user/role has the `bedrock:InvokeModel` permission.

**2. Verify credentials work:**

```bash
aws sts get-caller-identity
```

You should see your account ID and ARN. If this fails, the agent won't be able to call Bedrock.

**3. Install Python dependencies:**

```bash
pip install -r requirements.txt
```

### Run

```bash
python -m src.main "An app that helps small restaurants track food inventory to reduce waste"
```

---

## License

Apache 2.0 — see [LICENSE](LICENSE)
